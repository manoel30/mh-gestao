# routes/comercial.py
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from database import db
from models import PedidoVenda, ItemPedido, Produto, StructuralProduto, Cliente, Usuario 
from decimal import Decimal
from datetime import datetime

comercial_bp = Blueprint('comercial', __name__)

# =============================================================================
# REGRA DE DESCONTO AUTOMATIZADA
# =============================================================================
def calcular_desconto_pedido(valor_bruto, prazo_pagamento):
    """
    Retorna o percentual de desconto (Decimal) baseado no valor e prazo de pagamento.
    """
    desconto = Decimal('0.00')
    
    if prazo_pagamento == 'A_VISTA':
        desconto = Decimal('0.05')  # 5% em qualquer valor à vista
    elif prazo_pagamento == '30_DIAS' and valor_bruto >= Decimal('5000.00'):
        desconto = Decimal('0.03')  # 3% para prazo de 30 dias acima de R$ 5.000
    elif prazo_pagamento == '30_60_DIAS' and valor_bruto >= Decimal('10000.00'):
        desconto = Decimal('0.00')  # Preço cheio (0%) para prazos longos acima de R$ 10.000
    elif valor_bruto < Decimal('3000.00') and prazo_pagamento in ['30_DIAS', '30_60_DIAS']:
        desconto = Decimal('-0.02') # Acréscimo de 2% caso o pedido seja baixo a prazo
        
    return desconto

# =============================================================================
# ROTA PRINCIPAL DO PAINEL (Com Filtro de Busca por Descrição Ativo)
# =============================================================================
@comercial_bp.route('/comercial')
def painel_comercial():
    # SIMULAÇÃO: Usuário logado
    usuario_id = 1 
    usuario_tipo = 'VENDEDOR'
    
    # REMOVIDA A TRAVA: Busca TODOS os clientes do banco para você enxergar tudo o que foi cadastrado
    clientes_carteira = Cliente.query.order_by(Cliente.razao_social).all()
    
    # Carrega os vendedores para o formulário
    vendedores_disponiveis = Usuario.query.filter(Usuario.tipo.in_(['VENDEDOR', 'ADMIN'])).order_by(Usuario.nome).all()
        
    # --- NOVO: CAPTURA O TERMO DE BUSCA DA TELA (Ex: /comercial?busca=grelha) ---
    termo_busca = request.args.get('busca', '').strip()
    
    # Base da consulta: Sempre traz apenas os produtos acabados (PA)
    query_produtos = Produto.query.filter_by(tipo_produto='PA')
    
    # Se você digitou algo no campo de busca, o banco filtra (ilike ignora maiúsculas/minúsculas)
    if termo_busca:
        query_produtos = query_produtos.filter(Produto.descricao.ilike(f"%{termo_busca}%"))
    
    # Executa a busca ordenando por descrição
    produtos_banco = query_produtos.order_by(Produto.descricao).all()
    
    lista_produtos = []
    for prod in produtos_banco:
        # Cálculo do Custo Apurado na Estrutura
        componentes = StructuralProduto.query.filter_by(produto_pai_id=prod.id).all()
        custo_composto = Decimal('0.00')
        
        if componentes:
            for comp in componentes:
                item_insumo = Produto.query.get(comp.componente_id)
                if item_insumo and item_insumo.custo_medio_compra:
                    custo_composto += Decimal(str(comp.quantidade_necessaria)) * item_insumo.custo_medio_compra
        else:
            custo_composto = prod.custo_medio_compra if prod.custo_medio_compra else Decimal('0.00')
        
        # LENDO O ÍNDICE DO BANCO: se estiver nulo ou não existir, usa 1.50 como padrão
        indice_venda = getattr(prod, 'indice_venda', Decimal('1.50'))
        if indice_venda is None:
            indice_venda = Decimal('1.50')
            
        preco_venda_final = custo_composto * Decimal(str(indice_venda))
        
        lista_produtos.append({
            "id": prod.id,
            "codigo_interno": prod.codigo_interno,
            "descricao": prod.descricao,
            "unidade_consumo": prod.unidade_consumo,
            "custo_base": float(custo_composto),
            "indice": float(indice_venda),
            "preco_tabela": float(preco_venda_final),
            "imagem_url": getattr(prod, 'imagem_url', None)
        })
    
    return render_template('comercial.html', 
                           clientes=clientes_carteira, 
                           vendedores=vendedores_disponiveis,
                           produtos=lista_produtos, 
                           tipo_usuario=usuario_tipo,
                           busca_atual=termo_busca) # Envia o termo de volta para a tela se quiser manter no campo

# =============================================================================
# CRUD DE CLIENTES (Cadastro amarrando o Vendedor dinamicamente)
# =============================================================================
@comercial_bp.route('/api/cliente', methods=['POST'])
def cadastrar_cliente():
    data = request.form if request.form else request.json
    try:
        existente = Cliente.query.filter_by(cnpj_cpf=data['cnpj_cpf']).first()
        if existente:
            if request.form:
                flash('Já existe um cliente cadastrado com este CNPJ/CPF.', 'danger')
                return redirect('/comercial')
            return jsonify({"error": "Já existe um cliente cadastrado com este CNPJ/CPF."}), 400

        # PEGA O VENDEDOR ESCOLHIDO NO FORMULÁRIO HTML
        vendedor_escolhido = data.get('vendedor_id')
        if not vendedor_escolhido:
            # Caso falte no payload, assume o ID 1 como segurança para não quebrar
            vendedor_id = 1
        else:
            vendedor_id = int(vendedor_escolhido)

        novo_cliente = Cliente(
            razao_social=data['razao_social'],
            nome_fantasia=data.get('nome_fantasia'),
            cnpj_cpf=data['cnpj_cpf'],
            telefone=data.get('telefone'),
            email=data.get('email'),
            cidade=data.get('cidade', 'Feira de Santana'),
            estado=data.get('estado', 'BA').upper(),
            latitude=Decimal(str(data['latitude'])) if data.get('latitude') else None,
            longitude=Decimal(str(data['longitude'])) if data.get('longitude') else None,
            vendedor_id=vendedor_id
        )
        db.session.add(novo_cliente)
        db.session.commit()
        
        if request.form:
            flash('Cliente cadastrado com sucesso e vinculado ao vendedor!', 'success')
            return redirect('/comercial')
        return jsonify({"message": "Cliente cadastrado com sucesso!"}), 201
    except Exception as e:
        db.session.rollback()
        if request.form:
            flash(f"Erro ao salvar cliente: {str(e)}", 'danger')
            return redirect('/comercial')
        return jsonify({"error": f"Erro ao salvar cliente: {str(e)}"}), 500

@comercial_bp.route('/api/cliente/<int:id>', methods=['PUT', 'POST'])
def editar_cliente(id):
    data = request.form if request.form else request.json
    cliente = db.session.get(Cliente, id)
    
    if not cliente:
        return jsonify({"error": "Cliente não encontrado"}), 404
        
    cliente.razao_social = data.get('razao_social', cliente.razao_social)
    cliente.nome_fantasia = data.get('nome_fantasia', cliente.nome_fantasia)
    cliente.cnpj_cpf = data.get('cnpj_cpf', cliente.cnpj_cpf)
    cliente.telefone = data.get('telefone', cliente.telefone)
    cliente.email = data.get('email', cliente.email)
    cliente.cidade = data.get('cidade', cliente.cidade)
    cliente.estado = data.get('estado', cliente.estado).upper()
    
    if 'vendedor_id' in data and data['vendedor_id']:
        cliente.vendedor_id = int(data['vendedor_id'])
    if 'latitude' in data:
        cliente.latitude = Decimal(str(data['latitude'])) if data['latitude'] else None
    if 'longitude' in data:
        cliente.longitude = Decimal(str(data['longitude'])) if data['longitude'] else None
    
    db.session.commit()
    
    if request.form:
        flash('Dados do cliente updated com sucesso!', 'success')
        return redirect('/comercial')
    return jsonify({"message": "Dados do cliente updated com sucesso!"}), 200

@comercial_bp.route('/api/cliente/<int:id>/deletar', methods=['POST', 'DELETE'])
def deletar_cliente(id):
    cliente = db.session.get(Cliente, id)
    if not cliente:
        return jsonify({"error": "Cliente não encontrado"}), 404
        
    pedido_vinculado = PedidoVenda.query.filter_by(cliente_id=id).first()
    if pedido_vinculado:
        if request.form:
            flash('Não é possível remover este cliente pois ele possui histórico de pedidos.', 'danger')
            return redirect('/comercial')
        return jsonify({"error": "Não é possível remover este cliente pois ele possui histórico de pedidos."}), 400
        
    db.session.delete(cliente)
    db.session.commit()
    
    if request.form:
        flash('Cliente removido da carteira com sucesso!', 'success')
        return redirect('/comercial')
    return jsonify({"message": "Cliente removido com sucesso!"}), 200

@comercial_bp.route('/api/clientes', methods=['GET'])
def listar_clientes():
    busca = request.args.get('busca', '')
    usuario_tipo = 'VENDEDOR' 
    usuario_id = 1
    
    query = Cliente.query
    if usuario_tipo == 'VENDEDOR':
        query = query.filter_by(vendedor_id=usuario_id)
        
    if busca:
        query = query.filter(
            (Cliente.razao_social.ilike(f"%{busca}%")) | 
            (Cliente.nome_fantasia.ilike(f"%{busca}%")) |
            (Cliente.cnpj_cpf.like(f"%{busca}%"))
        )
        
    clientes = query.all()
    output = []
    for c in clientes:
        output.append({
            "id": c.id, "razao_social": c.razao_social, "nome_fantasia": c.nome_fantasia or c.razao_social,
            "cnpj_cpf": c.cnpj_cpf, "telefone": c.telefone, "cidade": c.cidade, "estado": c.estado
        })
    return jsonify(output), 200

# =============================================================================
# GESTÃO DE PEDIDOS
# =============================================================================
@comercial_bp.route('/api/comercial/pedido', methods=['POST'])
def criar_pedido():
    data = request.json
    try:
        print("DADOS RECEBIDOS NO PEDIDO:", data)

        if not data or 'cliente_id' not in data or 'itens' not in data:
            return jsonify({"error": "Dados do pedido ou itens não foram preenchidos."}), 400

        cliente = db.session.get(Cliente, int(data['cliente_id']))
        if not cliente:
            return jsonify({"error": "Cliente associado não foi encontrado."}), 404

        # SEGURANÇA DO VENDEDOR: Se o cliente não tiver vendedor cadastrado, assume o ID 1
        vendedor_id = cliente.vendedor_id if cliente.vendedor_id else 1

        prazo_pagamento = data.get('prazo_pagamento', 'A_VISTA').upper()
        valor_bruto = Decimal('0.00')
        
        itens_processados = []
        for item in data['itens']:
            preco_cru = str(item.get('preco_tabela', '0')).replace('R$', '').replace(' ', '')
            if ',' in preco_cru:
                preco_cru = preco_cru.replace('.', '').replace(',', '.')
            if not preco_cru or preco_cru == '':
                preco_cru = '0.00'
                
            qtd = Decimal(str(item.get('quantidade', 1)))
            preco_tabela = Decimal(preco_cru)
            valor_bruto += qtd * preco_tabela
            
            itens_processados.append({
                "produto_id": int(item['produto_id']),
                "quantidade": float(qtd),
                "preco_tabela": preco_tabela
            })
            
        valor_bruto = valor_bruto.quantize(Decimal('0.01'))
        percentual_desconto = calcular_desconto_pedido(valor_bruto, prazo_pagamento)
        
        valor_desconto_monetario = (valor_bruto * percentual_desconto).quantize(Decimal('0.01'))
        valor_liquido_total = (valor_bruto - valor_desconto_monetario).quantize(Decimal('0.01'))

        # --- INSTÂNCIA EM PERFEITA HARMONIA COM O SEU MODELS.PY ---
        novo_pedido = PedidoVenda(
            cliente_id=cliente.id,
            vendedor_id=vendedor_id,
            data_pedido=datetime.now().replace(microsecond=0),
            status='ORÇAMENTO',
            prazo_pagamento=prazo_pagamento,
            valor_bruto=valor_bruto,
            desconto_aplicado=valor_desconto_monetario,
            valor_total=valor_liquido_total
        )
        db.session.add(novo_pedido)
        db.session.flush() 
        
        for item in itens_processados:
            preco_tabela = item['preco_tabela']
            preco_praticado = (preco_tabela * (Decimal('1.00') - percentual_desconto)).quantize(Decimal('0.01'))
            subtotal_item = (Decimal(str(item['quantidade'])) * preco_praticado).quantize(Decimal('0.01'))
            
            novo_item = ItemPedido(
                pedido_id=novo_pedido.id,
                produto_id=item['produto_id'],
                quantidade=item['quantidade'],
                preco_unitario=preco_praticado,
                subtotal=subtotal_item
            )
            db.session.add(novo_item)
            
        db.session.commit()
        return jsonify({
            "message": "Pedido gerado com sucesso!", 
            "pedido_id": novo_pedido.id,
            "valor_bruto": float(valor_bruto),
            "desconto": float(valor_desconto_monetario),
            "valor_final": float(valor_liquido_total)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"ERRO CRÍTICO NO POST DE PEDIDO: {str(e)}")
        return jsonify({"error": f"Erro interno ao processar pedido: {str(e)}"}), 500

@comercial_bp.route('/api/comercial/pedidos', methods=['GET'])
def listar_pedidos():
    usuario_tipo = 'VENDEDOR' 
    usuario_id = 1
    
    query = PedidoVenda.query
    if usuario_tipo == 'VENDEDOR':
        query = query.filter_by(vendedor_id=usuario_id)
        
    pedidos = query.order_by(PedidoVenda.id.desc()).all()
    output = []
    for p in pedidos:
        output.append({
            "id": p.id, "cliente_name": p.cliente.razao_social,
            "data": p.data_pedido.strftime('%d/%m/%Y %H:%M') if p.data_pedido else '',
            "status": p.status, "prazo": p.prazo_pagamento, "valor_total": float(p.valor_total)
        })
    return jsonify(output), 200

@comercial_bp.route('/api/comercial/pedido/<int:id>/status', methods=['PUT'])
def atualizar_status_pedido(id):
    data = request.json
    novo_status = str(data['status']).upper()
    pedido = db.session.get(PedidoVenda, id)
    
    if not pedido:
        return jsonify({"error": "Pedido não encontrado"}), 404
        
    if novo_status == 'APROVADO' and pedido.status != 'APROVADO':
        itens_pedido = ItemPedido.query.filter_by(pedido_id=id).all()
        for item in itens_pedido:
            componentes_bom = StructuralProduto.query.filter_by(produto_pai_id=item.produto_id).all()
            for comp in componentes_bom:
                insumo = db.session.get(Produto, comp.componente_id)
                if insumo:
                    fator_perda = 1 + (float(comp.perda_estimada or 0) / 100)
                    # --- CORRIGIDO: de 'factor_perda' para 'fator_perda' ---
                    total_baixa = float(item.quantidade) * float(comp.quantidade_necessaria) * fator_perda
                    insumo.estoque_atual_consumo = float(insumo.estoque_atual_consumo or 0) - total_baixa
                    
                    fator_conv = float(insumo.fator_conversao or 1)
                    # --- CORRIGIDO: de 'fatur_conv' para 'fator_conv' ---
                    if insumo.unidade_consumo == 'M2' and fator_conv > 0:
                        insumo.estoque_atual_compra = float(insumo.estoque_atual_compra or 0) - (total_baixa * fator_conv)
                    else:
                        insumo.estoque_atual_compra = float(insumo.estoque_atual_compra or 0) - total_baixa

    pedido.status = novo_status
    db.session.commit()
    return jsonify({"message": f"Pedido atualizado para {novo_status} e estoque deduzido!"}), 200

@comercial_bp.route('/api/estoque/critico', methods=['GET'])
def estoque_critico():
    insumos_criticos = Produto.query.filter(Produto.estoque_atual_consumo <= 0).all()
    output = []
    for i in insumos_criticos:
        output.append({
            "codigo": i.codigo_interno, "descricao": i.descricao,
            "estoque_atual": float(i.estoque_atual_consumo), "unidade": i.unidade_consumo,
            "custo_medio_ref": float(i.custo_medio_compra)
        })
    return jsonify(output), 200