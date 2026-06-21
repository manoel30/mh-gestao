from flask import Flask, render_template, request, jsonify, redirect
from database import db
from datetime import datetime
import os 

# 1. IMPORTE TODOS OS SEUS MODELOS AQUI PARA O SQLALCHEMY CONHECÊ-LOS
import models
from models import CadastroRetalhos, MovimentacaoRetalhos  # Seus modelos de retalhos

# ⚠️ AJUSTE AQUI: Se os modelos do comercial estiverem em outro arquivo, importe-o também!
# Exemplo: de onde vem a tabela de pedidos ou clientes? 
# Se estiver no mesmo arquivo: ótimo. Se estiver em outro, adicione a linha abaixo:
# from models_comercial import Cliente, PedidoVenda 

# Importação dos Blueprints Modulares das APIs
from routes.engenharia import engenharia_bp
from routes.comercial import comercial_bp

app = Flask(__name__)

# =============================================================================
# 1. CONFIGURAÇÃO DINÂMICA DO BANCO DE DADOS (LOCAL VS PRODUCTION)
# =============================================================================
# O Render fornece a URL na variável DATABASE_URL. Se não existir, usa o seu localhost.
db_uri = os.environ.get('DATABASE_URL', 'postgresql://postgres:1234@localhost:5432/PLM_GESTA_1')

# Segurança para o SQLAlchemy 2.0: o Render costuma enviar "postgres://", mas o driver exige "postgresql://"
if db_uri and db_uri.startswith("postgres://"):
    db_uri = db_uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 2. Inicializa o Banco conectado ao App
db.init_app(app)

# 3. Registra os Módulos Separados de APIs no App Principal (Apenas uma vez)
app.register_blueprint(engenharia_bp)
app.register_blueprint(comercial_bp)

# 4. Sincronização Automática com Proteção contra Delays de Inicialização
with app.app_context():
    try:
        print("🔄 Forçando limpeza e recriação das tabelas para alinhar colunas...")
        db.drop_all()   # <-- ATIVADO: Apaga as tabelas antigas e erradas do Render
        db.create_all()  # Criará tudo do zero perfeitamente alinhado com o seu models.py
        print("✓ Sucesso: Banco e Tabelas de Venda/Estoque/Retalhos 100% sincronizados!")
    except Exception as e:
        print(f"⚠️ Alerta na sincronização do banco: {e}")
        print("Tentando seguir com a inicialização do servidor...")
# =============================================================================
# ROTAS DAS TELAS HTML (INTERFACE VISUAL)
# =============================================================================

@app.route('/')
def index():
    """Menu Principal de Acesso Fácil para o Pátio e Escritório"""
    return """
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 40px auto; padding: 20px; border: 1px solid #cbd5e0; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h2 style="color: #1a365d; border-bottom: 2px solid #2b6cb0; padding-bottom: 10px;">MH Indústria - Painel PCP & Comercial</h2>
        <p style="color: #4a5568;">Selecione o módulo que deseja acessar:</p>
        
        <h3 style="color: #2b6cb0; margin-top: 20px;">🏭 Engenharia, Fábrica e PCP</h3>
        <ul style="line-height: 2;">
            <li><a href="/produto" style="text-decoration: none; color: #2d3748; font-weight: bold;">1. Cadastro de Insumos e Produtos (PA/MP)</a></li>
            <li><a href="/fornecedor" style="text-decoration: none; color: #2d3748; font-weight: bold;">2. Cadastro de Fornecedores</a></li>
            <li><a href="/entrada" style="text-decoration: none; color: #2d3748; font-weight: bold;">3. Entrada de Notas Fiscais (Alimentar Estoque)</a></li>
            <li><a href="/estrutura" style="text-decoration: none; color: #2d3748; font-weight: bold;">4. Engenharia de Produto (Estrutura BOM / M²)</a></li>
            <li><a href="/pcp/retalhos" style="text-decoration: none; color: #0f172a; font-weight: bold;">📊 [NOVO] Módulo PCP: Controle e Aproveitamento de Retalhos</a></li>
            <li><a href="/pcp/simulador" style="text-decoration: none; color: #2b6cb0; font-weight: bold;">🔍 [NOVO] Simulador: Cruzar Retalhos x Estruturas (BOM)</a></li>
        </ul>
        
        <h3 style="color: #c53030; margin-top: 20px;">💼 Comercial e Logística</h3>
        <ul style="line-height: 2;">
            <li><a href="/cliente" style="text-decoration: none; color: #c53030; font-weight: bold;">5. [NOVO] Cadastro de Clientes (Lojas de Varejo)</a></li>
            <li><a href="/comercial" style="text-decoration: none; color: #c53030; font-weight: bold;">6. [NOVO] Painel Comercial (Pedidos de Venda & Baixa Automática)</a></li>
        </ul>
    </div>
    """

# --- ROTAS NOVAS: CONTROLE DE RETALHOS COMPATÍVEL COM ORM ---

@app.route('/pcp/retalhos', methods=['GET'])
def tela_retalhos():
    """Lista os retalhos e calcula os indicadores dinâmicos de saldo"""
    retalhos = CadastroRetalhos.query.order_by(CadastroRetalhos.codigo_retalho).all()
    
    # Calcula os saldos somando as colunas no Postgres via SQLAlchemy
    saldo_esc = db.session.query(db.func.sum(CadastroRetalhos.quantidade_saldo)).filter(CadastroRetalhos.acabamento == 'ESC').scalar() or 0
    saldo_bri = db.session.query(db.func.sum(CadastroRetalhos.quantidade_saldo)).filter(CadastroRetalhos.acabamento == 'BRI').scalar() or 0
    saldo_fos = db.session.query(db.func.sum(CadastroRetalhos.quantidade_saldo)).filter(CadastroRetalhos.acabamento == 'FOS').scalar() or 0
    
    return render_template('pcp_retalhos.html', 
                           retalhos=retalhos, 
                           saldo_escovado=saldo_esc, 
                           saldo_brilhante=saldo_bri, 
                           saldo_fosco=saldo_fos)

@app.route('/api/pcp/retalhos', methods=['POST'])
def movimentar_retalho():
    """Processa a Entrada ou Saída de chapas e atualiza saldos"""
    codigo = request.form.get('codigo_retalho')
    tipo_mov = request.form.get('tipo_movimentacao')
    qtd = int(request.form.get('quantidade', 1))
    
    retalho = CadastroRetalhos.query.filter_by(codigo_retalho=codigo).first()
    multiplicador = 1 if tipo_mov == 'ENTRADA' else -1
    
    if retalho:
        retalho.quantidade_saldo += (qtd * multiplicador)
    else:
        if tipo_mov == 'ENTRADA':
            retalho = CadastroRetalhos(
                codigo_retalho=codigo,
                material=request.form.get('material'),
                espessura=float(request.form.get('espessura')),
                largura=int(request.form.get('largura')),
                comprimento=int(request.form.get('comprimento')),
                acabamento=request.form.get('acabamento'),
                quantidade_saldo=qtd
            )
            db.session.add(retalho)
        else:
            return "Erro: Não há saldo deste retalho registrado.", 400
            
    # Salva o log de movimentação histórica
    historico = MovimentacaoRetalhos(codigo_retalho=codigo, tipo_movimentacao=tipo_mov, quantidade=qtd)
    db.session.add(historico)
    
    db.session.commit()
    return redirect('/pcp/retalhos')

@app.route('/api/pcp/retalhos/editar', methods=['PUT'])
def editar_retalho():
    dados = request.get_json()
    retalho = CadastroRetalhos.query.filter_by(codigo_retalho=dados.get('codigo')).first()
    if retalho:
        retalho.quantidade_saldo = int(dados.get('novo_saldo'))
        db.session.commit()
        return jsonify({"status": "sucesso"})
    return jsonify({"status": "erro", "message": "Não encontrado"}), 404

@app.route('/api/pcp/retalhos/deletar', methods=['POST'])
def deletar_retalho():
    dados = request.get_json()
    retalho = CadastroRetalhos.query.filter_by(codigo_retalho=dados.get('codigo')).first()
    if retalho:
        db.session.delete(retalho)
        db.session.commit()
        return jsonify({"status": "sucesso"})
    return jsonify({"status": "erro", "message": "Não encontrado"}), 404

# --- ROTAS ANTIGAS DO SEU PROJETO ---

@app.route('/produto')
def tela_produto(): 
    return render_template('produto.html')

@app.route('/fornecedor')
def tela_fornecedor(): 
    return render_template('fornecedor.html')

@app.route('/entrada')
def tela_entrada(): 
    return render_template('entrada.html')

@app.route('/estrutura')
def tela_estrutura(): 
    return render_template('estrutura.html')

@app.route('/cliente')
def tela_cliente(): 
    return render_template('cliente.html')

@app.route('/comercial')
def tela_comercial(): 
    return render_template('comercial.html')

# =============================================================================
# INICIALIZAÇÃO DO SERVIDOR
# =============================================================================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
