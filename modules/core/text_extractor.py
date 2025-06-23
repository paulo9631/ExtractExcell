import os
import cv2
import numpy as np
import pytesseract
import re
import logging
from PIL import Image
from scipy import ndimage

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
    img_gray = np.array(imagem_pil.convert("L"))
    
    if remover_ruido:
        img_gray = cv2.GaussianBlur(img_gray, (3, 3), 0)
    
    if equalizar:
        img_gray = cv2.equalizeHist(img_gray)
    
    if binarizar:
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
    img_gray = np.array(imagem_pil.convert("L"))
    
    if remover_ruido:
        img_gray = cv2.bilateralFilter(img_gray, 9, 75, 75)
    
    if equalizar:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        img_gray = clahe.apply(img_gray)
    
    if deskew:
        coords = np.column_stack(np.where(img_gray > 0))
        if len(coords) > 0:  
            angle = cv2.minAreaRect(coords)[-1]
            
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
                
            if abs(angle) > 0.5:
                (h, w) = img_gray.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                img_gray = cv2.warpAffine(img_gray, M, (w, h), 
                                        flags=cv2.INTER_CUBIC, 
                                        borderMode=cv2.BORDER_REPLICATE)
    
    # Binarização
    if binarizar:
        _, img_bin = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        kernel = np.ones((2, 2), np.uint8)
        img_bin = cv2.morphologyEx(img_bin, cv2.MORPH_CLOSE, kernel)
        img_bin = cv2.morphologyEx(img_bin, cv2.MORPH_OPEN, kernel)
        
        return Image.fromarray(img_bin)
    
    return Image.fromarray(img_gray)

def validar_matricula(texto, comprimento_min=4, comprimento_max=10):
    """
    Valida se o texto parece ser uma matrícula válida.
    
    Args:
        texto: String com a matrícula
        comprimento_min: Comprimento mínimo aceitável
        comprimento_max: Comprimento máximo aceitável
        
    Returns:
        Boolean indicando se a matrícula é válida
    """
    if not texto.isdigit():
        return False
    
    if len(texto) < comprimento_min or len(texto) > comprimento_max:
        return False
    
    if any(digito * 4 in texto for digito in "0123456789"):
        return False
    
    if texto.startswith('0') and len(texto) > 5:
        return False
    
    return True

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
        roi_img_np = np.array(roi_img.convert("L"))
        
        roi_img_np = cv2.equalizeHist(roi_img_np)
        
        roi_img_np = cv2.adaptiveThreshold(
            roi_img_np, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        kernel = np.ones((2, 2), np.uint8)
        roi_img_np = cv2.morphologyEx(roi_img_np, cv2.MORPH_CLOSE, kernel)
        
        roi_img = Image.fromarray(roi_img_np)
    
    config = r'--psm 7 -c tessedit_char_whitelist=0123456789'
    
    matricula = pytesseract.image_to_string(roi_img, config=config).strip()
    
    matricula = ''.join(c for c in matricula if c.isdigit())
    
    return matricula

def extrair_matricula_avancado(imagem_pil, roi=None, pre_processar=True, tentativas_multiplas=True, debug_folder=None):
    """
    Extrai o número de matrícula de uma imagem com técnicas avançadas.
    
    Args:
        imagem_pil: Imagem PIL
        roi: Região de interesse (opcional)
        pre_processar: Se True, aplica pré-processamento
        tentativas_multiplas: Se True, tenta várias configurações de OCR
        debug_folder: Pasta para salvar imagens de debug
        
    Returns:
        Número de matrícula extraído
    """
    if roi:
        roi_img = imagem_pil.crop((roi['x'], roi['y'], roi['x']+roi['width'], roi['y']+roi['height']))
    else:
        roi_img = imagem_pil
    
    resultados = []
    
    if pre_processar:
        roi_proc = pre_processar_imagem_ocr_avancado(roi_img)
        
        if debug_folder:
            roi_proc.save(os.path.join(debug_folder, "matricula_proc_padrao.png"))
        config = r'--psm 7 -c tessedit_char_whitelist=0123456789'
        
        matricula = pytesseract.image_to_string(roi_proc, config=config).strip()
        matricula = ''.join(c for c in matricula if c.isdigit())
        
        if matricula.isdigit() and len(matricula) >= 5:
            return matricula
        
        resultados.append(matricula)
        
        if tentativas_multiplas:
            roi_inv = Image.fromarray(255 - np.array(roi_proc))
            if debug_folder:
                roi_inv.save(os.path.join(debug_folder, "matricula_invertida.png"))
            
            matricula = pytesseract.image_to_string(roi_inv, config=config).strip()
            matricula = ''.join(c for c in matricula if c.isdigit())
            resultados.append(matricula)
            
            roi_np = np.array(roi_proc)
            kernel = np.ones((2, 2), np.uint8)
            roi_dilated = cv2.dilate(roi_np, kernel, iterations=1)
            if debug_folder:
                cv2.imwrite(os.path.join(debug_folder, "matricula_dilatada.png"), roi_dilated)
            
            matricula = pytesseract.image_to_string(Image.fromarray(roi_dilated), config=config).strip()
            matricula = ''.join(c for c in matricula if c.isdigit())
            resultados.append(matricula)
            
            roi_eroded = cv2.erode(roi_np, kernel, iterations=1)
            if debug_folder:
                cv2.imwrite(os.path.join(debug_folder, "matricula_erodida.png"), roi_eroded)
            
            matricula = pytesseract.image_to_string(Image.fromarray(roi_eroded), config=config).strip()
            matricula = ''.join(c for c in matricula if c.isdigit())
            resultados.append(matricula)
            
            config_alt = r'--psm 8 -c tessedit_char_whitelist=0123456789'
            matricula = pytesseract.image_to_string(roi_proc, config=config_alt).strip()
            matricula = ''.join(c for c in matricula if c.isdigit())
            resultados.append(matricula)
            
            roi_gray = np.array(roi_img.convert("L"))
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
            roi_clahe = clahe.apply(roi_gray)
            _, roi_bin = cv2.threshold(roi_clahe, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            if debug_folder:
                cv2.imwrite(os.path.join(debug_folder, "matricula_clahe_agressivo.png"), roi_bin)
            
            matricula = pytesseract.image_to_string(Image.fromarray(roi_bin), config=config).strip()
            matricula = ''.join(c for c in matricula if c.isdigit())
            resultados.append(matricula)
            
            roi_gray = np.array(roi_img.convert("L"))
            roi_bilateral = cv2.bilateralFilter(roi_gray, 11, 17, 17)
            roi_adapt = cv2.adaptiveThreshold(
                roi_bilateral, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            if debug_folder:
                cv2.imwrite(os.path.join(debug_folder, "matricula_bilateral_adapt.png"), roi_adapt)
            
            matricula = pytesseract.image_to_string(Image.fromarray(roi_adapt), config=config).strip()
            matricula = ''.join(c for c in matricula if c.isdigit())
            resultados.append(matricula)
    else:
        config = r'--psm 7 -c tessedit_char_whitelist=0123456789'
        matricula = pytesseract.image_to_string(roi_img, config=config).strip()
        matricula = ''.join(c for c in matricula if c.isdigit())
        resultados.append(matricula)
    
    resultados = [r for r in resultados if r.isdigit()]
    if resultados:
        resultados.sort(key=len, reverse=True)  
        resultados_validos = [r for r in resultados if len(r) >= 5]
        if resultados_validos:
            return resultados_validos[0]
        
        return resultados[0]
    
    return ""

def preprocess_roi_avancado(roi_pil, debug_folder=None, idx=0):
    """
    Pré-processamento avançado para ROIs de matrícula.
    Aplica múltiplas técnicas e retorna a melhor versão.
    
    Args:
        roi_pil: Imagem PIL da ROI
        debug_folder: Pasta para salvar imagens de debug
        idx: Índice para nomear arquivos de debug
        
    Returns:
        Imagem PIL pré-processada
    """
    roi_gray = np.array(roi_pil.convert("L"))
    
    roi_eq = cv2.equalizeHist(roi_gray)
    roi_eq = cv2.GaussianBlur(roi_eq, (3, 3), 0)
    
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    roi_clahe = clahe.apply(roi_gray)
    
    _, roi_bin = cv2.threshold(roi_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    roi_bin_adapt = cv2.adaptiveThreshold(
        roi_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    kernel = np.ones((2, 2), np.uint8)
    roi_morph = cv2.morphologyEx(roi_bin_adapt, cv2.MORPH_CLOSE, kernel)
    roi_morph = cv2.morphologyEx(roi_morph, cv2.MORPH_OPEN, kernel)
    
    if debug_folder:
        cv2.imwrite(os.path.join(debug_folder, f"matricula_eq_{idx}.png"), roi_eq)
        cv2.imwrite(os.path.join(debug_folder, f"matricula_clahe_{idx}.png"), roi_clahe)
        cv2.imwrite(os.path.join(debug_folder, f"matricula_bin_{idx}.png"), roi_bin)
        cv2.imwrite(os.path.join(debug_folder, f"matricula_bin_adapt_{idx}.png"), roi_bin_adapt)
        cv2.imwrite(os.path.join(debug_folder, f"matricula_morph_{idx}.png"), roi_morph)
    
    return Image.fromarray(roi_morph)

def extrair_matricula_com_multiplas_estrategias(imagem_original, config, debug_subdir=None):
    """
    Tenta extrair a matrícula usando múltiplas estratégias, retornando o melhor resultado.
    
    Args:
        imagem_original: Imagem PIL original
        config: Dicionário de configuração
        debug_subdir: Diretório para salvar imagens de debug
            
    Returns:
        Texto da matrícula extraído
    """
    from pytesseract import image_to_string, Output
    
    resultados = []
    
    if "matricula_roi" in config:
        try:
            x, y, w, h = config["matricula_roi"].values()
            roi_matricula = imagem_original.crop((x, y, x+w, y+h))
            
            roi_processada = preprocess_roi_avancado(roi_matricula, debug_subdir, 1)
            
            if debug_subdir:
                roi_processada.save(os.path.join(debug_subdir, "matricula_roi_processada_1.png"))
            
            config_tess = r"--psm 7 -c tessedit_char_whitelist=0123456789"
            matricula = image_to_string(roi_processada, config=config_tess, output_type=Output.STRING).strip()
            matricula = ''.join(c for c in matricula if c.isdigit())
            
            logger.info(f"Matrícula (ROI fixa) lida: '{matricula}'")
            if matricula.isdigit() and len(matricula) >= 5:
                resultados.append((matricula, 0.9))
        except Exception as e:
            logger.error(f"Erro na extração da matrícula (ROI fixa): {e}")
    
    if "matricula_template_path" in config:
        try:
            from modules.core.detector import detectar_area_cabecalho_template, pre_processar_imagem
            
            temp_cab = Image.open(config["matricula_template_path"])
            
            pil_img_proc = pre_processar_imagem(imagem_original, equalizar=True, ajustar_contraste=True)
            
            pts_cab, score_cab = detectar_area_cabecalho_template(
                pil_img_proc, temp_cab, 
                pre_processar=True, 
                multi_escala=True,
                rotacoes=True
            )
            
            logger.debug(f"Score do template matching do cabeçalho: {score_cab:.2f}")
            
            thr_cab = config.get("matricula_template_threshold", 0.25)
            
            if score_cab >= thr_cab and pts_cab:
                xs = [p[0] for p in pts_cab]
                ys = [p[1] for p in pts_cab]
                x_min, x_max = min(xs), max(xs)
                y_min, y_max = min(ys), max(ys)
                
                if debug_subdir:
                    debug_roi_path = os.path.join(debug_subdir, "debug_matricula_roi_template.png")
                    imagem_original.crop((x_min, y_min, x_max, y_max)).save(debug_roi_path)
                
                roi_matricula = imagem_original.crop((x_min, y_min, x_max, y_max))
                roi_processada = preprocess_roi_avancado(roi_matricula, debug_subdir, 2)
                
                if debug_subdir:
                    debug_roi_ocr_path = os.path.join(debug_subdir, "debug_matricula_roi_used_2.png")
                    roi_processada.save(debug_roi_ocr_path)
                
                config_tess = r"--psm 7 -c tessedit_char_whitelist=0123456789"
                matricula = image_to_string(roi_processada, config=config_tess, output_type=Output.STRING).strip()
                matricula = ''.join(c for c in matricula if c.isdigit())
                
                logger.info(f"Matrícula (template-cabeçalho) lida: '{matricula}'")
                if matricula.isdigit() and len(matricula) >= 5:
                    resultados.append((matricula, score_cab))
        except Exception as e:
            logger.error(f"Erro no template de cabeçalho/matrícula: {e}")
    
    try:
        from modules.core.detector import detectar_matricula_por_contornos
        
        logger.info("Tentando detecção de matrícula por contornos...")
        roi_coords = detectar_matricula_por_contornos(imagem_original, debug_folder=debug_subdir)
        
        if roi_coords:
            x, y, w, h = roi_coords
            roi_matricula = imagem_original.crop((x, y, x+w, y+h))
            roi_processada = preprocess_roi_avancado(roi_matricula, debug_subdir, 3)
            
            if debug_subdir:
                roi_processada.save(os.path.join(debug_subdir, "matricula_contorno_processada.png"))
            
            config_tess = r"--psm 7 -c tessedit_char_whitelist=0123456789"
            matricula = image_to_string(roi_processada, config=config_tess, output_type=Output.STRING).strip()
            matricula = ''.join(c for c in matricula if c.isdigit())
            
            logger.info(f"Matrícula (contornos) lida: '{matricula}'")
            if matricula.isdigit() and len(matricula) >= 5:
                resultados.append((matricula, 0.7))  
    except Exception as e:
        logger.error(f"Erro na detecção por contornos: {e}")
    
    try:
        from modules.core.detector import detectar_matricula_por_hough
        
        logger.info("Tentando detecção de matrícula por Hough...")
        roi_coords = detectar_matricula_por_hough(imagem_original, debug_folder=debug_subdir)
        
        if roi_coords:
            x, y, w, h = roi_coords
            roi_matricula = imagem_original.crop((x, y, x+w, y+h))
            roi_processada = preprocess_roi_avancado(roi_matricula, debug_subdir, 4)
            
            if debug_subdir:
                roi_processada.save(os.path.join(debug_subdir, "matricula_hough_processada.png"))
            
            config_tess = r"--psm 7 -c tessedit_char_whitelist=0123456789"
            matricula = image_to_string(roi_processada, config=config_tess, output_type=Output.STRING).strip()
            matricula = ''.join(c for c in matricula if c.isdigit())
            
            logger.info(f"Matrícula (Hough) lida: '{matricula}'")
            if matricula.isdigit() and len(matricula) >= 5:
                resultados.append((matricula, 0.6))
    except Exception as e:
        logger.error(f"Erro na detecção por Hough: {e}")
    
    try:
        logger.info("Tentando extração de matrícula com múltiplas técnicas...")
        matricula = extrair_matricula_avancado(imagem_original, pre_processar=True, tentativas_multiplas=True, debug_folder=debug_subdir)
        
        if matricula.isdigit() and len(matricula) >= 5:
            logger.info(f"Matrícula (técnicas múltiplas) lida: '{matricula}'")
            resultados.append((matricula, 0.5))  
    except Exception as e:
        logger.error(f"Erro na extração com múltiplas técnicas: {e}")
    
    if resultados:
        resultados.sort(key=lambda x: x[1], reverse=True)
        return resultados[0][0]
    
    return ""

def extrair_info_ocr(imagem_pil):
    """
    Extrai informações gerais via OCR da imagem.
    
    Args:
        imagem_pil: Imagem PIL
        
    Returns:
        Dicionário com informações extraídas
    """
    info = {
        "nome_aluno": "",
        "escola": "",
        "turma": ""
    }
    
    return info