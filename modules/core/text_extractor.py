import cv2
import numpy as np
from PIL import Image
import pytesseract
import logging

logger = logging.getLogger('GabaritoApp.TextExtractor')

def pre_processar_imagem_ocr(imagem_pil, equalizar=True, remover_ruido=True, binarizar=True):
    """
    Pré-processa a imagem para melhorar a extração de texto via OCR.
    
    Args:
        imagem_pil: Imagem PIL
        equalizar: Se True, aplica equalização de histograma
        remover_ruido: Se True, aplica filtro para remoção de ruído
        binarizar: Se True, aplica binarização
        
    Returns:
        Imagem PIL pré-processada
    """
    # Converte para escala de cinza
    img_gray = np.array(imagem_pil.convert("L"))
    
    # Remoção de ruído
    if remover_ruido:
        img_gray = cv2.GaussianBlur(img_gray, (3, 3), 0)
    
    # Equalização de histograma
    if equalizar:
        img_gray = cv2.equalizeHist(img_gray)
    
    # Binarização
    if binarizar:
        # Usa threshold adaptativo para lidar melhor com variações de iluminação
        img_gray = cv2.adaptiveThreshold(
            img_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
    
    return Image.fromarray(img_gray)

def pre_processar_imagem_ocr_avancado(imagem_pil, equalizar=True, remover_ruido=True, binarizar=True, deskew=True):
    """
    Pré-processamento avançado para melhorar a extração de texto via OCR.
    
    Args:
        imagem_pil: Imagem PIL
        equalizar: Se True, aplica equalização de histograma
        remover_ruido: Se True, aplica filtro para remoção de ruído
        binarizar: Se True, aplica binarização
        deskew: Se True, corrige a inclinação do texto
        
    Returns:
        Imagem PIL pré-processada
    """
    # Converte para escala de cinza
    img_gray = np.array(imagem_pil.convert("L"))
    
    # Remoção de ruído
    if remover_ruido:
        # Usa filtro bilateral para preservar bordas enquanto remove ruído
        img_gray = cv2.bilateralFilter(img_gray, 9, 75, 75)
    
    # Equalização de histograma
    if equalizar:
        # Usa CLAHE para melhorar o contraste local
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        img_gray = clahe.apply(img_gray)
    
    # Correção de inclinação (deskew)
    if deskew:
        # Detecta a inclinação do texto e corrige
        coords = np.column_stack(np.where(img_gray > 0))
        if len(coords) > 0:  # Verifica se há pontos para calcular
            angle = cv2.minAreaRect(coords)[-1]
            
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
                
            # Apenas corrige se a inclinação for significativa
            if abs(angle) > 0.5:
                (h, w) = img_gray.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                img_gray = cv2.warpAffine(img_gray, M, (w, h), 
                                        flags=cv2.INTER_CUBIC, 
                                        borderMode=cv2.BORDER_REPLICATE)
    
    # Binarização
    if binarizar:
        # Usa Otsu para determinar o threshold automaticamente
        _, img_bin = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Aplica operações morfológicas para limpar a imagem
        kernel = np.ones((2, 2), np.uint8)
        img_bin = cv2.morphologyEx(img_bin, cv2.MORPH_CLOSE, kernel)
        img_bin = cv2.morphologyEx(img_bin, cv2.MORPH_OPEN, kernel)
        
        return Image.fromarray(img_bin)
    
    return Image.fromarray(img_gray)

def extrair_texto_roi(imagem_pil, roi, pre_processar=True, config=''):
    """
    Extrai texto de uma região de interesse (ROI) específica.
    
    Args:
        imagem_pil: Imagem PIL
        roi: Dicionário com x, y, width, height
        pre_processar: Se True, aplica pré-processamento
        config: Configuração do Tesseract
        
    Returns:
        Texto extraído
    """
    x, y, w, h = roi['x'], roi['y'], roi['width'], roi['height']
    roi_img = imagem_pil.crop((x, y, x+w, y+h))
    
    if pre_processar:
        roi_img = pre_processar_imagem_ocr(roi_img)
    
    texto = pytesseract.image_to_string(roi_img, config=config).strip()
    return texto

def extrair_matricula(imagem_pil, roi=None, pre_processar=True):
    """
    Extrai o número de matrícula de uma imagem.
    
    Args:
        imagem_pil: Imagem PIL
        roi: Região de interesse (opcional)
        pre_processar: Se True, aplica pré-processamento
        
    Returns:
        Número de matrícula extraído
    """
    if roi:
        roi_img = imagem_pil.crop((roi['x'], roi['y'], roi['x']+roi['width'], roi['y']+roi['height']))
    else:
        roi_img = imagem_pil
    
    if pre_processar:
        # Pré-processamento específico para números
        roi_img_np = np.array(roi_img.convert("L"))
        
        # Aumenta o contraste
        roi_img_np = cv2.equalizeHist(roi_img_np)
        
        # Aplica threshold adaptativo
        roi_img_np = cv2.adaptiveThreshold(
            roi_img_np, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Operações morfológicas para limpar a imagem
        kernel = np.ones((2, 2), np.uint8)
        roi_img_np = cv2.morphologyEx(roi_img_np, cv2.MORPH_CLOSE, kernel)
        
        roi_img = Image.fromarray(roi_img_np)
    
    # Configuração específica para números
    config = r'--psm 7 -c tessedit_char_whitelist=0123456789'
    
    # Extrai o texto
    matricula = pytesseract.image_to_string(roi_img, config=config).strip()
    
    # Limpa o resultado (remove caracteres não numéricos)
    matricula = ''.join(c for c in matricula if c.isdigit())
    
    return matricula

def extrair_matricula_avancado(imagem_pil, roi=None, pre_processar=True, tentativas_multiplas=True):
    """
    Extrai o número de matrícula de uma imagem com técnicas avançadas.
    
    Args:
        imagem_pil: Imagem PIL
        roi: Região de interesse (opcional)
        pre_processar: Se True, aplica pré-processamento
        tentativas_multiplas: Se True, tenta várias configurações de OCR
        
    Returns:
        Número de matrícula extraído
    """
    if roi:
        roi_img = imagem_pil.crop((roi['x'], roi['y'], roi['x']+roi['width'], roi['y']+roi['height']))
    else:
        roi_img = imagem_pil
    
    # Lista para armazenar resultados de diferentes tentativas
    resultados = []
    
    if pre_processar:
        # Pré-processamento padrão
        roi_proc = pre_processar_imagem_ocr_avancado(roi_img)
        
        # Configuração específica para números
        config = r'--psm 7 -c tessedit_char_whitelist=0123456789'
        
        # Primeira tentativa com pré-processamento padrão
        matricula = pytesseract.image_to_string(roi_proc, config=config).strip()
        matricula = ''.join(c for c in matricula if c.isdigit())
        
        if matricula.isdigit() and len(matricula) >= 5:
            return matricula
        
        resultados.append(matricula)
        
        if tentativas_multiplas:
            # Segunda tentativa: inversão de cores
            roi_inv = Image.fromarray(255 - np.array(roi_proc))
            matricula = pytesseract.image_to_string(roi_inv, config=config).strip()
            matricula = ''.join(c for c in matricula if c.isdigit())
            resultados.append(matricula)
            
            # Terceira tentativa: dilatação para conectar caracteres quebrados
            roi_np = np.array(roi_proc)
            kernel = np.ones((2, 2), np.uint8)
            roi_dilated = cv2.dilate(roi_np, kernel, iterations=1)
            matricula = pytesseract.image_to_string(Image.fromarray(roi_dilated), config=config).strip()
            matricula = ''.join(c for c in matricula if c.isdigit())
            resultados.append(matricula)
            
            # Quarta tentativa: erosão para separar caracteres juntos
            roi_eroded = cv2.erode(roi_np, kernel, iterations=1)
            matricula = pytesseract.image_to_string(Image.fromarray(roi_eroded), config=config).strip()
            matricula = ''.join(c for c in matricula if c.isdigit())
            resultados.append(matricula)
            
            # Quinta tentativa: PSM diferente
            config_alt = r'--psm 8 -c tessedit_char_whitelist=0123456789'
            matricula = pytesseract.image_to_string(roi_proc, config=config_alt).strip()
            matricula = ''.join(c for c in matricula if c.isdigit())
            resultados.append(matricula)
    else:
        # Sem pré-processamento
        config = r'--psm 7 -c tessedit_char_whitelist=0123456789'
        matricula = pytesseract.image_to_string(roi_img, config=config).strip()
        matricula = ''.join(c for c in matricula if c.isdigit())
        resultados.append(matricula)
    
    # Escolhe o melhor resultado (o mais longo que seja um número)
    resultados = [r for r in resultados if r.isdigit()]
    if resultados:
        return max(resultados, key=len)
    
    return ""

def extrair_info_ocr(imagem_pil):
    """
    Extrai informações gerais via OCR da imagem.
    
    Returns:
        Dicionário com informações extraídas
    """
    # Implementação básica - pode ser expandida conforme necessário
    info = {
        "nome_aluno": "",
        "escola": "",
        "turma": ""
    }
    
    # Aqui você pode adicionar lógica para extrair outras informações
    # como nome do aluno, escola, etc.
    
    return info