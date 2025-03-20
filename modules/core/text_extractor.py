import pytesseract
import re
from PIL import Image

def extrair_info_ocr(imagem):
    """
    Extrai informações via OCR. (Exemplo simplificado)
    """
    texto = pytesseract.image_to_string(imagem, lang='por')
    nome_aluno = ""
    escola = ""
    turma = ""

    match_matricula = re.search(r"MATRÍCULA\s*[:\-]?\s*(\d+)", texto, re.IGNORECASE)
    if match_matricula:
        matricula = match_matricula.group(1).strip()
    
    match_nome = re.search(r"NOME\s*[:\-]?\s*(.*)", texto, re.IGNORECASE)
    if match_nome:
        nome_aluno = match_nome.group(1).strip()
    
    match_escola = re.search(r"ESCOLA\s*[:\-]?\s*(.*)", texto, re.IGNORECASE)
    if match_escola:
        escola = match_escola.group(1).strip()
    
    match_turma = re.search(r"TURMA\s*[:\-]?\s*(.*)", texto, re.IGNORECASE)
    if match_turma:
        turma = match_turma.group(1).strip()
    
    return {
        "nome_aluno": nome_aluno,
        "escola": escola,
        "turma": turma
    }
