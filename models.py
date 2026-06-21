from decimal import Decimal
from datetime import datetime
from database import db

class Fornecedor(db.Model):
    __tablename__ = 'fornecedores'
    id = db.Column(db.Integer, primary_key=True)
    razao_social = db.Column(db.String(100), nullable=False)
    cnpj = db.Column(db.String(18), unique=True, nullable=False)
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(100))

class Produto(db.Model):
    __tablename__ = 'produtos'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo_interno = db.Column(db.String(50), unique=True, nullable=False)
    descricao = db.Column(db.String(100), nullable=False)
    tipo_produto = db.Column(db.String(5), default='ME')
    unidade_compra = db.Column(db.String(5), nullable=False)
    unidade_consumo = db.Column(db.String(5), nullable=False)
    fator_conversao = db.Column(db.Numeric(10, 4), default=1.0000)
    estoque_atual_compra = db.Column(db.Numeric(12, 4), default=0.0000)
    estoque_atual_consumo = db.Column(db.Numeric(12, 4), default=0.0000)
    custo_medio_compra = db.Column(db.Numeric(12, 2), default=0.00)
    peso_m2 = db.Column(db.Numeric(10, 4), default=1.0000)
    indice_venda = db.Column(db.Numeric(10, 2), default=1.50)
    material = db.Column(db.String(20), nullable=True)
    espessura = db.Column(db.Numeric(4, 2), nullable=True)
    # 📑 LINHA ADICIONADA: Mapeamento do caminho da foto/desenho técnico
    imagem_url = db.Column(db.String(500), nullable=True)

class StructuralProduto(db.Model):
    __tablename__ = 'estrutura_produto'
    id = db.Column(db.Integer, primary_key=True)
    produto_pai_id = db.Column(db.Integer, db.ForeignKey('produtos.id'))
    componente_id = db.Column(db.Integer, db.ForeignKey('produtos.id'))
    
    # --- NOVOS CAMPOS ADICIONADOS COMO OPCIONAIS (Para não travar outros materiais) ---
    material = db.Column(db.String(20), nullable=True)            # Ex: 'IX304', 'IX430' ou None
    espessura = db.Column(db.Numeric(4, 2), nullable=True)        # Ex: 0.80, 1.20 ou None
    # ---------------------------------------------------------------------------------
    
    largura_mm = db.Column(db.Numeric(10, 2), default=0.00)
    comprimento_mm = db.Column(db.Numeric(10, 2), default=0.00)
    quantidade_pecas = db.Column(db.Integer, default=1)
    quantidade_necessaria = db.Column(db.Numeric(10, 4), nullable=False) 
    perda_estimada = db.Column(db.Numeric(5, 2), default=0.00)
    observacao = db.Column(db.String(255), default='')

class HistoricoEntrada(db.Model):
    __tablename__ = 'historico_entradas'
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'))
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('fornecedores.id'))
    numero_nota = db.Column(db.String(20))
    quantidade = db.Column(db.Numeric(12, 4), nullable=False)
    preco_unitario = db.Column(db.Numeric(12, 2), nullable=False)
    data_entrada = db.Column(db.DateTime, default=datetime.now)

# =============================================================================
# MÓDULO COMERCIAL, USUÁRIOS E GEOLOCALIZAÇÃO
# =============================================================================

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(20), nullable=False) # 'ADMIN', 'VENDEDOR', 'CLIENTE'
    vendedor_vinculado_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)

class Cliente(db.Model):
    __tablename__ = 'clientes'
    id = db.Column(db.Integer, primary_key=True)
    razao_social = db.Column(db.String(100), nullable=False)
    nome_fantasia = db.Column(db.String(100))
    cnpj_cpf = db.Column(db.String(18), unique=True, nullable=False)
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    cidade = db.Column(db.String(50))
    estado = db.Column(db.String(2)) # Ex: BA, SP, PE
    
    latitude = db.Column(db.Numeric(10, 8), nullable=True)
    longitude = db.Column(db.Numeric(11, 8), nullable=True)
    vendedor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    
    vendedor = db.relationship('Usuario', foreign_keys=[vendedor_id])

class PedidoVenda(db.Model):
    __tablename__ = 'pedidos_venda'
    id = db.Column(db.Integer, primary_key=True)
    
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    vendedor_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    data_pedido = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.String(20), default='ORÇAMENTO')  # ORÇAMENTO, APROVADO, FINALIZADO
    
    prazo_pagamento = db.Column(db.String(20), default='A_VISTA') # A_VISTA, 30_DIAS, 30_60_DIAS
    valor_bruto = db.Column(db.Numeric(12, 2), default=0.00)
    desconto_aplicado = db.Column(db.Numeric(12, 2), default=0.00)
    valor_total = db.Column(db.Numeric(12, 2), default=0.00)

    cliente = db.relationship('Cliente', backref='pedidos')
    vendedor = db.relationship('Usuario', foreign_keys=[vendedor_id])

class ItemPedido(db.Model):
    __tablename__ = 'itens_pedido'
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos_venda.id', ondelete='CASCADE'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Numeric(12, 2), nullable=False)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)

# =============================================================================
# [NOVO] MÓDULO PCP - CONTROLE DE RETALHOS DE CHAPA
# =============================================================================

class CadastroRetalhos(db.Model):
    __tablename__ = 'cadastro_retalhos'
    
    codigo_retalho = db.Column(db.String(50), primary_key=True) # Ex: IX304-080-200X500-ESC
    material = db.Column(db.String(20), nullable=False)          # IX304, IX430
    espessura = db.Column(db.Numeric(4, 2), nullable=False)        # 0.80, 1.20, 1.50
    largura = db.Column(db.Integer, nullable=False)               # em mm
    comprimento = db.Column(db.Integer, nullable=False)           # em mm
    acabamento = db.Column(db.String(5), nullable=False)          # ESC, BRI, FOS
    quantidade_saldo = db.Column(db.Integer, default=0)           # Saldo físico atual

class MovimentacaoRetalhos(db.Model):
    __tablename__ = 'movimentacao_retalhos'
    
    id_movimentacao = db.Column(db.Integer, primary_key=True, autoincrement=True)
    codigo_retalho = db.Column(db.String(50), db.ForeignKey('cadastro_retalhos.codigo_retalho', ondelete='CASCADE'), nullable=False)
    tipo_movimentacao = db.Column(db.String(10), nullable=False)   # ENTRADA ou SAIDA
    quantidade = db.Column(db.Integer, nullable=False)
    data_movimento = db.Column(db.DateTime, default=datetime.now)
