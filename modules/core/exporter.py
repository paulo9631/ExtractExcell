import pandas as pd
from openpyxl import load_workbook

def encontrar_proxima_linha_vazia(ws, linha_inicial=30, coluna_verificacao='H'):
    linha = linha_inicial
    while True:
        valor_celula = ws[f"{coluna_verificacao}{linha}"].value
        if valor_celula is None or str(valor_celula).strip() == "":
            return linha
        linha += 1

def importar_para_planilha(dados, caminho_template):
    print(f"[LOG] Função importar_para_planilha chamada para o arquivo '{caminho_template}'. Número de registros a importar: {len(dados)}")
    
    try:
        book = load_workbook(caminho_template)
        print(f"[LOG] Planilha '{caminho_template}' carregada com sucesso.")
    except Exception as e:
        print(f"[ERRO] Falha ao carregar '{caminho_template}': {e}")
        return
    
    sheet_name = "GERAL"
    if sheet_name not in book.sheetnames:
        print(f"[ERRO] Aba '{sheet_name}' não encontrada na planilha.")
        return
    
    ws = book[sheet_name]
    print(f"[LOG] Usando aba '{sheet_name}'.")

    map_questao_coluna = {
        1: 'H', 2: 'I', 3: 'J', 4: 'K', 5: 'L',
        6: 'M', 7: 'N', 8: 'O', 9: 'P', 10: 'Q',
        11: 'R', 12: 'S', 13: 'T', 14: 'U', 15: 'V',
        16: 'W', 17: 'X', 18: 'Y', 19: 'Z', 20: 'AA',
        21: 'AB', 22: 'AC', 23: 'AD', 24: 'AE', 25: 'AF',
        26: 'AG'
    }
    
    for idx, item in enumerate(dados):
        respostas = item.get("Respostas", {})
        row_inicial = encontrar_proxima_linha_vazia(ws, linha_inicial=30, coluna_verificacao='H')
        
        for questao_nome, resposta in respostas.items():
            try:
                numero = int(questao_nome.replace("Questao ", ""))
            except ValueError:
                print(f"[ERRO] Não foi possível extrair número de '{questao_nome}'")
                continue
            col_letra = map_questao_coluna.get(numero)
            if col_letra:
                ws[f"{col_letra}{row_inicial}"] = resposta
                print(f"[LOG] Inserindo {questao_nome}='{resposta}' na célula {col_letra}{row_inicial}")
        
        print(f"[LOG] Inserido registro {idx+1} na linha {row_inicial}")

    try:
        book.save(caminho_template)
        print(f"[LOG] Dados salvos na planilha '{caminho_template}'.")
    except Exception as e:
        print(f"[ERRO] Falha ao salvar '{caminho_template}': {e}")
