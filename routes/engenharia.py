# routes/engenharia.py
import io
from decimal import Decimal
from flask import Blueprint, request, jsonify, send_file, render_template
from database import db
from models import Fornecedor, Produto, StructuralProduto, HistoricoEntrada, CadastroRetalhos

# ReportLab para PDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

engenharia_bp = Blueprint('engenharia', __name__)

# --- FORNECEDORES ---
@engenharia_bp.route('/api/fornecedor', methods=['POST'])
def cadastrar_fornecedor():
    data = request.json
    try:
        razao_social = str(data.get('razao_social', '')).strip()
        cnpj = str(data.get('cnpj', '')).strip()
        
        if not razao_social or not cnpj:
            return jsonify({"error": "Razão Social e CNPJ são obrigatórios!"}), 400

        fornecedor_existente = Fornecedor.query.filter_by(cnpj=cnpj).first()
        if fornecedor_existente:
            return jsonify({"error": f"O CNPJ {cnpj} já está cadastrado para o fornecedor: {fornecedor_existente.razao_social}."}), 400

        novo = Fornecedor(
            razao_social=razao_social,
            cnpj=cnpj,
            telefone=data.get('telefone', '').strip() or None,
            email=data.get('email', '').strip() or None
        )
        
        db.session.add(novo)
        db.session.commit()
        return jsonify({"message": "Fornecedor cadastrado com sucesso!"}), 201

    except Exception as e:
        db.session.rollback()
        print(f"❌ ERRO CRÍTICO NO BANCO DE DADOS: {str(e)}")
        return jsonify({"error": "Erro interno ao processar o cadastro do fornecedor no banco de dados."}), 500

# =============================================================================
# --- PRODUTOS CORRIGIDOS (COM GRAVAÇÃO DE IMAGEM ATIVA) ---
# =============================================================================
@engenharia_bp.route('/api/produto', methods=['POST'])
def cadastrar_produto():
    data = request.json
    try:
        fator_cru = str(data.get('fator_conversao', '1.0000')).replace(' ', '').replace(',', '.')
        if not fator_cru or fator_cru == '':
            fator_cru = '1.0000'

        indice_cru = str(data.get('indice_venda', '1.50')).replace(' ', '').replace(',', '.')
        if not indice_cru or indice_cru == '':
            indice_cru = '1.50'

        espessura_cru = data.get('espessura')
        espessura_final = None
        if espessura_cru is not None and str(espessura_cru).strip() != '':
            espessura_final = Decimal(str(espessura_cru).replace(' ', '').replace(',', '.'))

        material_cru = data.get('material')
        material_final = str(material_cru).strip() if material_cru else None
        if material_final == '':
            material_final = None

        novo = Produto(
            codigo_interno=str(data['codigo_interno']).strip(),
            descricao=str(data['descricao']).strip(),
            tipo_produto=str(data.get('tipo_produto', 'MP')).strip().upper(),
            unidade_compra=str(data['unidade_compra']).strip().upper(),
            unidade_consumo=str(data['unidade_consumo']).strip().upper(),
            fator_conversao=Decimal(fator_cru),
            indice_venda=Decimal(indice_cru),
            material=material_final,
            espessura=espessura_final,
            imagem_url=data.get('imagem_url')
        )
        db.session.add(novo)
        db.session.commit()
        return jsonify({"message": "Produto cadastrado com sucesso!"}), 201
    except Exception as e:
        db.session.rollback()
        print(f"ERRO NO CADASTRO DE PRODUTO: {str(e)}")
        return jsonify({"error": f"Erro ao salvar produto: {str(e)}"}), 500
    
@engenharia_bp.route('/api/produto/<int:id>', methods=['PUT'])
def editar_produto(id):
    data = request.json
    produto = db.session.get(Produto, id)
    
    if not produto:
        return jsonify({"error": "Produto não encontrado no banco de dados."}), 404
        
    try:
        fator_cru = str(data.get('fator_conversao', '1.0000')).replace(' ', '').replace(',', '.')
        if not fator_cru or fator_cru == '':
            fator_cru = '1.0000'

        indice_cru = str(data.get('indice_venda', '1.50')).replace(' ', '').replace(',', '.')
        if not indice_cru or indice_cru == '':
            indice_cru = '1.50'

        espessura_cru = data.get('espessura')
        espessura_final = None
        if espessura_cru is not None and str(espessura_cru).strip() != '':
            espessura_final = Decimal(str(espessura_cru).replace(' ', '').replace(',', '.'))

        material_cru = data.get('material')
        material_final = str(material_cru).strip() if material_cru else None
        if material_final == '':
            material_final = None

        produto.codigo_interno = str(data['codigo_interno']).strip()
        produto.descricao = str(data['descricao']).strip()
        produto.tipo_produto = str(data.get('tipo_produto', 'MP')).strip().upper()
        produto.unidade_compra = str(data['unidade_compra']).strip().upper()
        produto.unidade_consumo = str(data['unidade_consumo']).strip().upper()
        produto.fator_conversao = Decimal(fator_cru)
        produto.indice_venda = Decimal(indice_cru)
        produto.material = material_final
        produto.espessura = espessura_final
        produto.imagem_url = data.get('imagem_url')
        
        db.session.commit()
        return jsonify({"message": "Produto atualizado com sucesso!"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"ERRO NA EDIÇÃO DE PRODUTO: {str(e)}")
        return jsonify({"error": f"Erro ao atualizar produto: {str(e)}"}), 500

@engenharia_bp.route('/api/produtos', methods=['GET'])
def listar_produtos():
    try:
        tipo_filtro = request.args.get('tipo', '').strip().upper()
        if tipo_filtro:
            produtos = Produto.query.filter_by(tipo_produto=tipo_filtro).all()
        else:
            produtos = Produto.query.all()
            
        return jsonify([{
            "id": p.id, 
            "codigo": p.codigo_interno, 
            "descricao": p.descricao, 
            "tipo_produto": p.tipo_produto, 
            "estoque_consumo": float(p.estoque_atual_consumo or 0), 
            "unidade_compra": p.unidade_compra or 'UN',
            "unidade_consumo": p.unidade_consumo or 'UN', 
            "fator_conversao": float(p.fator_conversao or 1.0000),
            "peso_m2": float(getattr(p, 'peso_m2', 1.0000) or 1.0000),
            "custo_medio": float(p.custo_medio_compra or 0),
            "indice_venda": float(p.indice_venda) if p.indice_venda is not None else 1.50,
            "material": p.material,
            "espessura": float(p.espessura) if p.espessura is not None else None,
            "imagem_url": getattr(p, 'imagem_url', None)
        } for p in produtos]), 200
        
    except Exception as e:
        print(f"ERRO AO LISTAR PRODUTOS COM FILTRO: {str(e)}")
        return jsonify({"error": str(e)}), 500

@engenharia_bp.route('/api/produtos/pais', methods=['GET'])
def listar_produtos_pais():
    try:
        produtos = Produto.query.filter_by(tipo_produto='PA').all()
        return jsonify([{
            "id": p.id, 
            "codigo": p.codigo_interno, 
            "descricao": p.descricao, 
            "tipo_produto": p.tipo_produto
        } for p in produtos]), 200
    except Exception as e:
        print(f"ERRO AO LISTAR PRODUTOS PAIS: {str(e)}")
        return jsonify({"error": str(e)}), 500

# --- NF ENTRADA ---
@engenharia_bp.route('/api/entrada', methods=['POST'])
def lancar_entrada():
    data = request.json 
    produto = db.session.get(Produto, data['produto_id'])
    if not produto: 
        return jsonify({"error": "Produto não encontrado"}), 404
    
    try:
        qtd_compra = float(data['quantidade'])
        preco_unitario = float(data['preco_unitario'])
        fator = float(produto.fator_conversao or 1.0000)
        
        u_consumo = str(produto.unidade_consumo or '').strip().upper()
        u_compra = str(produto.unidade_compra or '').strip().upper()
        
        if 'M2' in u_consumo or 'M²' in u_consumo:
            qtd_consumo_nova = qtd_compra / fator if fator > 0 else qtd_compra
            preco_unitario_consumo = preco_unitario * fator 
        elif u_compra == 'UN' and ('METRO' in u_consumo or u_consumo == 'M'):
            qtd_consumo_nova = qtd_compra * fator
            preco_unitario_consumo = preco_unitario / fator if fator > 0 else preco_unitario
        else:
            qtd_consumo_nova = qtd_compra
            preco_unitario_consumo = preco_unitario

        nova_entrada = HistoricoEntrada(
            produto_id=produto.id, 
            fornecedor_id=data.get('fornecedor_id'), 
            numero_nota=data.get('numero_nota', 'N/E'), 
            quantidade=qtd_compra, 
            preco_unitario=preco_unitario
        )
        db.session.add(nova_entrada)

        produto.estoque_atual_compra = float(produto.estoque_atual_compra or 0) + qtd_compra
        
        qtd_antiga_consumo = float(produto.estoque_atual_consumo or 0)
        produto.estoque_atual_consumo = qtd_antiga_consumo + qtd_consumo_nova
        produto.custo_medio_compra = preco_unitario_consumo

        db.session.commit()
        return jsonify({"message": "Entrada processada com sucesso!"}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erro no cálculo de conversão da entrada: {str(e)}"}), 500

# --- ESTRUTURA (BOM) ---
@engenharia_bp.route('/api/estrutura', methods=['POST'])
def adicionar_componente_estrutura():
    data = request.json
    try:
        comp_id = data.get('componente_id')
        pai_id = data.get('produto_pai_id')
        
        if not comp_id or not pai_id:
            return jsonify({"error": "Código do Pai e Componente são obrigatórios!"}), 400

        comp = db.session.get(Produto, int(comp_id))
        if comp and comp.tipo_produto == 'PA':
            return jsonify({"error": "Bloqueio: Um PA não pode ser componente filho!"}), 400
            
        largura = float(data.get('largura_mm') or 0.0) if data.get('largura_mm') != '' else 0.0
        comprimento = float(data.get('comprimento_mm') or 0.0) if data.get('comprimento_mm') != '' else 0.0
        qtd_pecas = int(data.get('quantidade_pecas') or 1) if data.get('quantidade_pecas') != '' else 1
        qtd_nec = float(data.get('quantidade_necessaria') or 0.0)

        nova = StructuralProduto(
            produto_pai_id=int(pai_id), 
            componente_id=int(comp_id),
            largura_mm=largura, 
            comprimento_mm=comprimento,
            quantidade_pecas=qtd_pecas, 
            quantidade_necessaria=qtd_nec,
            perda_estimada=float(data.get('perda_estimada') or 0.0) if data.get('perda_estimada') != '' else 0.0, 
            observacao=data.get('observacao', '')
        )
        db.session.add(nova)
        db.session.commit()
        return jsonify({"message": "Componente adicionado com sucesso!"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erro ao adicionar componente: {str(e)}"}), 500
    
@engenharia_bp.route('/api/estrutura/<int:id>', methods=['PUT'])
def editar_componente_estrutura(id):
    data = request.json
    item = db.session.get(StructuralProduto, id)
    
    if not item:
        return jsonify({"error": "Componente da estrutura não encontrado."}), 404
        
    try:
        item.largura_mm = float(data.get('largura_mm') or 0.0) if data.get('largura_mm') != '' else 0.0
        item.comprimento_mm = float(data.get('comprimento_mm') or 0.0) if data.get('comprimento_mm') != '' else 0.0
        item.quantidade_pecas = int(data.get('quantidade_pecas') or 1) if data.get('quantidade_pecas') != '' else 1
        item.quantidade_necessaria = float(data.get('quantidade_necessaria') or 0.0)
        item.perda_estimada = float(data.get('perda_estimada') or 0.0) if data.get('perda_estimada') != '' else 0.0
        item.observacao = data.get('observacao', '')
        
        db.session.commit()
        return jsonify({"message": "Componente da estrutura atualizado com sucesso!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erro ao atualizar componente: {str(e)}"}), 500

@engenharia_bp.route('/api/estrutura/<int:id>', methods=['DELETE'])
def deletar_componente_estrutura(id):
    item = db.session.get(StructuralProduto, id)
    if not item:
        return jsonify({"error": "Componente não encontrado na estrutura."}), 404
    try:
        db.session.delete(item)
        db.session.commit()
        return jsonify({"message": "Componente removido da estrutura com sucesso!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Erro ao remover componente: {str(e)}"}), 500

@engenharia_bp.route('/api/estrutura/<int:pai_id>', methods=['GET'])
def obter_estrutura(pai_id):
    try:
        itens = StructuralProduto.query.filter_by(produto_pai_id=pai_id).all()
        lista = []
        for item in itens:
            try:
                prod = db.session.get(Produto, item.componente_id)
                if not prod:
                    continue
                
                custo_banco = float(prod.custo_medio_compra or 0.0)
                peso_m2_banco = float(prod.peso_m2 or 1.0000)
                u_consumo = str(prod.unidade_consumo or '').strip().upper()
                u_compra = str(prod.unidade_compra or '').strip().upper()

                qtd_nec = float(item.quantidade_necessaria or 0.0)
                custo_unitario_tela = custo_banco

                if 'M2' in u_consumo or 'M²' in u_consumo:
                    if u_compra == 'KG':
                        custo_unitario_tela = custo_banco * peso_m2_banco

                elif 'METRO' in u_consumo or u_consumo == 'M':
                    if u_compra == 'UN' and float(prod.fator_conversao or 1) > 0:
                        custo_unitario_tela = custo_banco / float(prod.fator_conversao or 1)

                subtotal_calc = qtd_nec * custo_unitario_tela

                lista.append({
                    "id": item.id, 
                    "codigo": prod.codigo_interno, 
                    "descricao": prod.descricao,
                    "unidade": prod.unidade_consumo, 
                    "quantidade_necessaria": round(qtd_nec, 4),
                    "largura_mm": float(item.largura_mm or 0.0),
                    "comprimento_mm": float(item.comprimento_mm or 0.0),
                    "quantidade_pecas": int(item.quantidade_pecas or 1),
                    "perda_estimada": float(item.perda_estimada or 0.0), 
                    "custo_unitario": round(custo_banco, 2),
                    "subtotal": round(subtotal_calc, 2),
                    "observacao": item.observacao or '',
                    "material": prod.material if hasattr(prod, 'material') else None,
                    "espessura": float(prod.espessura) if (hasattr(prod, 'espessura') and prod.espessura is not None) else None
                })
            except Exception as item_error:
                print(f"Erro ao processar item_id {item.id}: {str(item_error)}")
                continue

        return jsonify(lista), 200
    except Exception as e:
        print(f"Erro crítico na rota obter_estrutura: {str(e)}")
        return jsonify({"error": f"Erro na valorização da estrutura: {str(e)}"}), 500

@engenharia_bp.route('/api/produtos/filhos', methods=['GET'])
def listar_produtos_filhos():
    try:
        produtos = Produto.query.filter(Produto.tipo_produto != 'PA').all()
        return jsonify([{
            "id": p.id, 
            "codigo": p.codigo_interno, 
            "descricao": p.descricao, 
            "tipo_produto": p.tipo_produto,
            "unidade_consumo": p.unidade_consumo or 'UN',
            "custo_medio": float(p.custo_medio_compra or 0)
        } for p in produtos]), 200
    except Exception as e:
        print(f"ERRO AO LISTAR PRODUTOS FILHOS: {str(e)}")
        return jsonify({"error": str(e)}), 500

# --- RELATÓRIO PDF ---
@engenharia_bp.route('/api/estrutura/<int:pai_id>/pdf', methods=['GET'])
def gerar_pdf_estrutura(pai_id):
    try:
        produto_pai = db.session.get(Produto, pai_id)
        itens_estrutura = StructuralProduto.query.filter_by(produto_pai_id=pai_id).all()
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25)
        story = []
        styles = getSampleStyleSheet()
        
        style_titulo = ParagraphStyle('Tit', parent=styles['Title'], fontSize=16, leading=20, textColor=colors.HexColor('#1A365D'), alignment=0)
        story.append(Paragraph("<b>MH INDÚSTRIA E COMÉRCIO</b>", style_titulo))
        story.append(Paragraph(f"Relatório de Engenharia Valorizado - {produto_pai.descricao}", styles['Heading3']))
        story.append(Spacer(1, 15))
        
        dados_tabela = [["Cód. Insumo", "Descrição", "Dimensões", "Qtd. Req.", "Custo Unit.", "Subtotal", "Obs"]]
        custo_total_bom = 0.0

        for item in itens_estrutura:
            comp = db.session.get(Produto, item.componente_id)
            if comp:
                dim = "-"
                if (item.largura_mm or 0) > 0 and (item.comprimento_mm or 0) > 0:
                    dim = f"{int(item.largura_mm)}x{int(item.comprimento_mm)}"
                elif (item.comprimento_mm or 0) > 0:
                    dim = f"{int(item.comprimento_mm)} m"

                custo_banco = float(comp.custo_medio_compra) if comp.custo_medio_compra is not None else 0.0
                peso_m2_banco = float(comp.peso_m2) if comp.peso_m2 is not None else 1.0000
                u_consumo = str(comp.unidade_consumo or '').strip().upper()
                u_compra = str(comp.unidade_compra or '').strip().upper()
                
                qtd_nec = float(item.quantidade_necessaria) if item.quantidade_necessaria is not None else 0.0
                custo_unitario_correto = custo_banco

                if 'M2' in u_consumo or 'M²' in u_consumo:
                    if u_compra == 'KG':
                        custo_unitario_correto = custo_banco * peso_m2_banco
                elif 'METRO' in u_consumo or u_consumo == 'M':
                    if u_compra == 'UN':
                        custo_unitario_correto = custo_banco

                subtotal_calc = qtd_nec * custo_unitario_correto
                custo_total_bom += subtotal_calc

                dados_tabela.append([
                    comp.codigo_interno, 
                    comp.descricao, 
                    dim, 
                    f"{qtd_nec:.4f} {comp.unidade_consumo}", 
                    f"R$ {custo_unitario_correto:.2f}",
                    f"R$ {subtotal_calc:.2f}",
                    item.observacao or ''
                ])
        
        dados_tabela.append(["", "", "", "", "TOTAL BOM:", f"R$ {custo_total_bom:.2f}", ""])
                
        tabela = Table(dados_tabela, colWidths=[65, 150, 65, 75, 65, 65, 75])
        tabela.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2B6CB0')), 
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')), 
            ('ALIGN', (2, 1), (5, -1), 'RIGHT'), 
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, -1), (-1, -1), 1.5, colors.HexColor('#1A365D')),
            ('FONTNAME', (4, -1), (5, -1), 'Helvetica-Bold')
        ]))
        story.append(tabela)
        doc.build(story)
        buffer.seek(0)
        return send_file(buffer, as_attachment=False, mimetype='application/pdf', download_name=f"BOM_{produto_pai.codigo_interno}.pdf")
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@engenharia_bp.route('/pcp/simulador', methods=['GET'])
def tela_simulador():
    """Renderiza a página visual do simulador de retalhos"""
    return render_template('simulador.html')

@engenharia_bp.route('/api/pcp/simular-aproveitamento', methods=['GET'])
def simular_aproveitamento():
    try:
        retalhos_disponiveis = CadastroRetalhos.query.filter(CadastroRetalhos.quantidade_saldo > 0).all()
        sugestoes = []
        
        todas_pecas_bom = db.session.query(StructuralProduto, Produto)\
            .join(Produto, StructuralProduto.componente_id == Produto.id)\
            .filter(Produto.tipo_produto != 'PA').all()
        
        for retalho in retalhos_disponiveis:
            material_retalho = retalho.material.strip().upper() if retalho.material else ""
            esp_ret = float(retalho.espessura) if retalho.espessura else 0.0
            
            for estrutura, produto in todas_pecas_bom:
                material_produto = produto.material.strip().upper() if produto.material else ""
                esp_prod = float(produto.espessura) if produto.espessura else 0.0
                
                if (material_produto in material_retalho or material_retalho in material_produto) and (esp_prod == esp_ret):
                    if estrutura.largura_mm <= (retalho.largura - 5) and estrutura.comprimento_mm <= (retalho.comprimento - 5):
                        produto_pai = Produto.query.get(estrutura.produto_pai_id)
                        
                        area_retalho = retalho.largura * retalho.comprimento
                        area_peca = estrutura.largura_mm * estrutura.comprimento_mm
                        qtd_max_teorica = int(area_retalho // area_peca) if area_peca > 0 else 1
                        
                        sugestoes.append({
                            "retalho_codigo": retalho.codigo_retalho,
                            "retalho_info": f"{retalho.material} {float(retalho.espessura)}mm ({retalho.acabamento})",
                            "retalho_dimensoes": f"{retalho.largura}x{retalho.comprimento} mm",
                            "retalho_saldo": retalho.quantidade_saldo,
                            "produto_final": produto_pai.descricao if produto_pai else "Produto Não Identificado",
                            "peca_componente": produto.descricao,
                            "peca_dimensoes": f"{int(estrutura.largura_mm)}x{int(estrutura.comprimento_mm)} mm",
                            "qtd_estrutura": estrutura.quantidade_pecas,
                            "aproveitamento_estimado": qtd_max_teorica
                        })
                        
        return jsonify(sugestoes), 200
    except Exception as e:
        print(f"ERRO CRÍTICO NA SIMULAÇÃO: {str(e)}")
        return jsonify({"error": str(e)}), 500

# --- PCP & LISTAR E FILTRAR FORNECEDORES ---
@engenharia_bp.route('/api/fornecedores', methods=['GET'])
def listar_fornecedores():
    try:
        busca = request.args.get('busca', '').strip()
        query = Fornecedor.query
        
        if busca:
            query = query.filter(
                (Fornecedor.razao_social.ilike(f"%{busca}%")) | 
                (Fornecedor.cnpj.like(f"%{busca}%"))
            )
        
        fornecedores = query.order_by(Fornecedor.razao_social).all()
        
        return jsonify([{
            "id": f.id,
            "razao_social": f.razao_social,
            "cnpj": f.cnpj,
            "telefone": f.telefone or '',
            "email": f.email or ''
        } for f in fornecedores]), 200
        
    except Exception as e:
        print(f"❌ ERRO AO LISTAR FORNECEDORES: {str(e)}")
        return jsonify({"error": "Erro interno ao listar fornecedores."}), 500