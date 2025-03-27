import pandas as pd
from openpyxl import load_workbook

def encontrar_proxima_linha_vazia(ws, linha_inicial=30):
    # Colunas de respostas (I até AH)
    resposta_cols = ["I", "J", "K", "L", "M", "N", "O", "P", "Q", "R",
                     "S", "T", "U", "V", "W", "X", "Y", "Z", "AA", "AB",
                     "AC", "AD", "AE", "AF", "AG", "AH"]
    linha = linha_inicial
    while True:
        preenchido = False
        for col in resposta_cols:
            valor = ws[f"{col}{linha}"].value
            if valor is not None and str(valor).strip() != "":
                preenchido = True
                break
        if not preenchido:
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

    map_info_coluna = {
       "matricula": "D",
       "nome_aluno": "E",
       "escola": "G",
       "turma": "H" 
    }

    map_questao_coluna = {
        1: 'I', 2: 'J', 3: 'K', 4: 'L', 5: 'M',
        6: 'N', 7: 'O', 8: 'P', 9: 'Q', 10: 'R',
        11: 'S', 12: 'T', 13: 'U', 14: 'V', 15: 'W',
        16: 'X', 17: 'Y', 18: 'Z', 19: 'AA', 20: 'AB',
        21: 'AC', 22: 'AD', 23: 'AE', 24: 'AF', 25: 'AG',
        26: 'AH'
    }
    
    for idx, item in enumerate(dados):
        respostas = item.get("Respostas", {})
        ocr_info = item.get("OCR", {})
        
        # Busca a primeira linha com as colunas de respostas vazias (I até AH)
        row_inicial = encontrar_proxima_linha_vazia(ws, linha_inicial=30)

        matricula_val = ocr_info.get("matricula", "N/A")
        nome_val = ocr_info.get("nome_aluno", "N/A")
        escola_val = ocr_info.get("escola", "N/A")
        turma_val = ocr_info.get("turma", "N/A") 

        ws[f"{map_info_coluna['matricula']}{row_inicial}"] = matricula_val
        ws[f"{map_info_coluna['nome_aluno']}{row_inicial}"] = nome_val
        ws[f"{map_info_coluna['escola']}{row_inicial}"] = escola_val
        ws[f"{map_info_coluna['turma']}{row_inicial}"] = turma_val

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
