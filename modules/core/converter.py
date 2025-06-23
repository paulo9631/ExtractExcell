import io
import fitz  # PyMuPDF
import numpy as np
import cv2
from PIL import Image, ImageEnhance
from pytesseract import image_to_string
from pytesseract import Output




def converter_pdf_em_imagens(pdf_path, dpi=300):
    """
    Converte um PDF em uma lista de imagens PIL de alta qualidade.
    Aplica filtros de contraste, binarização e remoção de ruído.
    """
    imagens = []

    # Abrir PDF com PyMuPDF
    pdf_document = fitz.open(pdf_path)
    zoom = dpi / 72  # PyMuPDF usa 72dpi como base
    mat = fitz.Matrix(zoom, zoom)

    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]

        # Renderizar página como imagem
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_data = pix.tobytes("png")
        pil_img = Image.open(io.BytesIO(img_data)).convert("L")  # escala de cinza

        # Melhorar contraste
        pil_img = ajustar_contraste(pil_img)

        # Remover ruído e binarizar
        pil_img = remover_ruido_e_binarizar(pil_img)

        imagens.append(pil_img)

    pdf_document.close()
    return imagens


def ajustar_contraste(pil_img, fator=1.5):
    """
    Aumenta o contraste da imagem PIL.
    """
    enhancer = ImageEnhance.Contrast(pil_img)
    return enhancer.enhance(fator)


def remover_ruido_e_binarizar(pil_img):
    """
    Remove ruídos usando mediana + aplica binarização Otsu.
    """
    img_np = np.array(pil_img)
    # Filtro de mediana
    img_np = cv2.medianBlur(img_np, 3)
    # Binarização Otsu
    _, img_bin = cv2.threshold(img_np, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return Image.fromarray(img_bin)
