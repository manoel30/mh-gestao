import pandas as pd
from database import db
from models import CadastroRetalhos
# Supondo que você tenha uma tabela/modelo para a Estrutura de Produtos
# Caso não tenha, simularemos com um dicionário/lista de busca abaixo

def analisar_aproveitamento_retalhos():
    # 1. Puxa todos os retalhos que têm saldo disponível no Postgres
    retalhos_disponiveis = CadastroRetalhos.query.filter(CadastroRetalhos.quantidade_saldo > 0).all()
    
    # 2. Simulação da sua Estrutura de Produtos (Isso pode vir do seu ERP/Banco)
    # Aqui cadastramos as peças que compõem os seus produtos padronizados (ex: Armários, Pias)
    estrutura_produtos = [
        {
            "produto_pai": "ARM-PA-304-01",
            "componente": "Lateral Direita",
            "material": "IX304",
            "espessura": 0.80,
            "acabamento": "ESC",
            "largura_necessaria": 450,
            "comprimento_necessario": 580
        },
        {
            "produto_pai": "ARM-PA-304-01",
            "componente": "Prateleira Interna",
            "material": "IX304",
            "espessura": 0.80,
            "acabamento": "ESC",
            "largura_necessaria": 400,
            "comprimento_necessario": 500
        },
        {
            "produto_pai": "PIA-INOX-430",
            "componente": "Espelho Traseiro",
            "material": "IX430",
            "espessura": 1.00,
            "acabamento": "BRI",
            "largura_necessaria": 150,
            "comprimento_necessario": 1100
        }
    ]
    
    sugestoes = []
    
    # 3. O "Cérebro" do Cruzamento
    for retalho in retalhos_disponiveis:
        for peca in estrutura_produtos:
            # Valida Material, Espessura e Acabamento
            if (retalho.material == peca["material"] and 
                retalho.espessura == peca["espessura"] and 
                retalho.acabamento == peca["acabamento"]):
                
                # Valida se a peça cabe dentro do retalho (comprimento e largura)
                # Adicionamos a lógica de rotação (se cabe virando a peça em 90°)
                cabe_normal = (retalho.largura >= peca["largura_necessaria"] and retalho.comprimento >= peca["comprimento_necessario"])
                cabe_rotacionado = (retalho.largura >= peca["comprimento_necessario"] and retalho.comprimento >= peca["largura_necessaria"])
                
                if cabe_normal or cabe_rotacionado:
                    sugestoes.append({
                        "Código do Retalho": retalho.codigo_retalho,
                        "Dimensões Retalho (mm)": f"{retalho.largura}x{retalho.comprimento}",
                        "Saldo Disp.": retalho.quantidade_saldo,
                        "Produto Destino": peca["produto_pai"],
                        "Componente": peca["componente"],
                        "Medidas da Peça (mm)": f"{peca['largura_necessaria']}x{peca['comprimento_necessario']}",
                        "Status": "🔥 Uso Recomendado" if retalho.largura - peca["largura_necessaria"] <= 50 else "Aproveitamento Parcial"
                    })
                    
    # 4. Transforma o resultado em uma Planilha Excel formatada
    df = pd.DataFrame(sugestoes)
    nome_arquivo = "sugestao_aproveitamento_retalhos.xlsx"
    df.to_excel(nome_arquivo, index=False)
    
    print(f"✓ Planilha '{nome_arquivo}' gerada com sucesso com as sugestões de corte!")
    return nome_arquivo