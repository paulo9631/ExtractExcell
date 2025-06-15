import fitz
import os
import sys
from typing import List, Dict

def resource_path(relative_path):
    """
    Retorna o caminho absoluto para recursos, considerando o bundle do PyInstaller.
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def preencher_pdf_com_info(modelo_pdf_path: str, dados_alunos: List[Dict], output_path: str):
    """
    Gera um PDF com uma página para cada aluno, preenchendo suas informações nos locais definidos.

    :param modelo_pdf_path: Caminho do PDF base (modelo).
    :param dados_alunos: Lista de dicionários com os dados dos alunos.
    :param output_path: Caminho final para salvar o PDF combinado.
    """
    modelo_pdf_path = resource_path(modelo_pdf_path)

    if not os.path.exists(modelo_pdf_path):
        raise FileNotFoundError(f"Modelo PDF não encontrado: {modelo_pdf_path}")

    pdf_final = fitz.open()

    for aluno in dados_alunos:
        doc = fitz.open(modelo_pdf_path)
        page = doc[0]

        coordenadas = {
            "escola": (35, 417),
            "nome": (36, 459),
            "turno": (524, 417),
            "turma": (473, 417),
            "matricula": (319, 417),
            "nasc_d1": (377, 459),
            "nasc_d2": (400, 459),
            "nasc_m1": (424, 459),
            "nasc_m2": (448, 459),
            "nasc_a1": (471, 459),
            "nasc_a2": (495, 459),
            "nasc_a3": (519, 459),
            "nasc_a4": (542, 459),
        }

        fonte = "helv"
        tamanho = 11

        page.insert_text(coordenadas["escola"], aluno.get("escola", ""), fontname=fonte, fontsize=tamanho, color=(0, 0, 0))
        page.insert_text(coordenadas["nome"], aluno.get("nome", ""), fontname=fonte, fontsize=tamanho, color=(0, 0, 0))
        page.insert_text(coordenadas["turno"], aluno.get("turno", ""), fontname=fonte, fontsize=tamanho, color=(0, 0, 0))
        page.insert_text(coordenadas["turma"], aluno.get("turma", ""), fontname=fonte, fontsize=tamanho, color=(0, 0, 0))
        page.insert_text(coordenadas["matricula"], aluno.get("matricula", ""), fontname=fonte, fontsize=tamanho, color=(0, 0, 0))

        data_nasc = aluno.get("data_nascimento", "")
        if data_nasc and len(data_nasc) >= 10:
            partes = data_nasc.split('/')
            if len(partes) == 3:
                dia, mes, ano = partes
                if len(dia) == 2:
                    page.insert_text(coordenadas["nasc_d1"], dia[0], fontname=fonte, fontsize=tamanho, color=(0, 0, 0))
                    page.insert_text(coordenadas["nasc_d2"], dia[1], fontname=fonte, fontsize=tamanho, color=(0, 0, 0))
                if len(mes) == 2:
                    page.insert_text(coordenadas["nasc_m1"], mes[0], fontname=fonte, fontsize=tamanho, color=(0, 0, 0))
                    page.insert_text(coordenadas["nasc_m2"], mes[1], fontname=fonte, fontsize=tamanho, color=(0, 0, 0))
                if len(ano) == 4:
                    page.insert_text(coordenadas["nasc_a3"], ano[2], fontname=fonte, fontsize=tamanho, color=(0, 0, 0))
                    page.insert_text(coordenadas["nasc_a4"], ano[3], fontname=fonte, fontsize=tamanho, color=(0, 0, 0))

        pdf_final.insert_pdf(doc)
        doc.close()

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    pdf_final.save(output_path)
    pdf_final.close()
