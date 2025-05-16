import fitz
import os
from typing import List, Dict

def preencher_pdf_com_info(modelo_pdf_path: str, dados_alunos: List[Dict], output_path: str):
    """
    Gera um PDF com uma página para cada aluno, preenchendo suas informações nos locais definidos.

    :param modelo_pdf_path: Caminho do PDF base (modelo).
    :param dados_alunos: Lista de dicionários com os dados dos alunos.
    :param output_path: Caminho final para salvar o PDF combinado.
    """
    if not os.path.exists(modelo_pdf_path):
        raise FileNotFoundError(f"Modelo PDF não encontrado: {modelo_pdf_path}")

    pdf_final = fitz.open()

    for aluno in dados_alunos:
        doc = fitz.open(modelo_pdf_path)
        page = doc[0]


        coordenadas = {
            "escola": (244, 448),       
            "nome": (51, 487),         
            "turno": (311, 486),       
            "turma": (367, 486),       
            "data_nascimento": (855, 163), 
            "matricula": (57, 530),    
        }

        # Configurações de fonte
        fonte = "helv"
        tamanho = 11
        
        # Insere os textos diretamente
        page.insert_text(coordenadas["escola"], aluno.get("escola", ""), fontname=fonte, fontsize=tamanho, color=(0,0,0))
        page.insert_text(coordenadas["nome"], aluno.get("nome", ""), fontname=fonte, fontsize=tamanho, color=(0,0,0))
        page.insert_text(coordenadas["turno"], aluno.get("turno", ""), fontname=fonte, fontsize=tamanho, color=(0,0,0))
        page.insert_text(coordenadas["turma"], aluno.get("turma", ""), fontname=fonte, fontsize=tamanho, color=(0,0,0))
        
        # Para a data de nascimento, podemos formatá-la melhor
        data_nasc = aluno.get("data_nascimento", "")
        if data_nasc and len(data_nasc) >= 10:  # Formato esperado: DD/MM/AAAA
            # Divide a data em dia, mês e ano para posicionar em caixas separadas
            partes = data_nasc.split('/')
            if len(partes) == 3:
                dia, mes, ano = partes
                # Posiciona cada parte da data
                page.insert_text((855, 163), dia, fontname=fonte, fontsize=tamanho, color=(0,0,0))
                page.insert_text((900, 163), mes, fontname=fonte, fontsize=tamanho, color=(0,0,0))
                page.insert_text((945, 163), ano, fontname=fonte, fontsize=tamanho, color=(0,0,0))
        else:
            # Se não estiver no formato esperado, insere como está
            page.insert_text(coordenadas["data_nascimento"], data_nasc, fontname=fonte, fontsize=tamanho, color=(0,0,0))
        
        # Insere a matrícula
        page.insert_text(coordenadas["matricula"], aluno.get("matricula", ""), fontname=fonte, fontsize=tamanho, color=(0,0,0))

        pdf_final.insert_pdf(doc)
        doc.close()

    # Garante que o diretório de saída existe
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    pdf_final.save(output_path)
    pdf_final.close()