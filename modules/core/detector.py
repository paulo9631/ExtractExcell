import cv2
import numpy as np
from PIL import Image, ImageDraw
import os
import logging

logger = logging.getLogger('GabaritoApp.Detector')

def corrigir_perspectiva(imagem_np, pts_ref, largura_dest, altura_dest):
    pts_ref = np.array(pts_ref, dtype="float32")
    pts_dest = np.array([
        [0, 0],
        [largura_dest - 1, 0],
        [largura_dest - 1, altura_dest - 1],
        [0, altura_dest - 1]
    ], dtype="float32")
    M = cv2.getPerspectiveTransform(pts_ref, pts_dest)
    imagem_corrigida = cv2.warpPerspective(imagem_np, M, (largura_dest, altura_dest))
    return imagem_corrigida

def desenhar_rois_em_imagem(imagem, grid_rois, color=(255, 0, 0), width=2):
    draw = ImageDraw.Draw(imagem)
    for coluna in grid_rois:
        for roi in coluna:
            x = roi["x"]
            y = roi["y"]
            w = roi["width"]
            h = roi["height"]
            draw.rectangle([x, y, x + w, y + h], outline=color, width=width)
    return imagem

def pre_processar_imagem(imagem_pil, equalizar=True, ajustar_contraste=True, remover_ruido=True):
    """
    Aplica técnicas de pré-processamento para melhorar a qualidade da imagem antes da detecção.
    
    Args:
        imagem_pil: Imagem PIL
        equalizar: Se True, aplica equalização de histograma
        ajustar_contraste: Se True, aplica ajuste de contraste
        remover_ruido: Se True, aplica filtro para remoção de ruído
        
    Returns:
        Imagem PIL pré-processada
    """
    # Converte para escala de cinza e depois para numpy array
    img_gray = np.array(imagem_pil.convert("L"))
    
    # Remoção de ruído (opcional)
    if remover_ruido:
        img_gray = cv2.GaussianBlur(img_gray, (3, 3), 0)
    
    # Equalização de histograma (melhora o contraste)
    if equalizar:
        img_gray = cv2.equalizeHist(img_gray)
    
    # Ajuste de contraste (CLAHE - Contrast Limited Adaptive Histogram Equalization)
    if ajustar_contraste:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        img_gray = clahe.apply(img_gray)
    
    # Converte de volta para PIL
    return Image.fromarray(img_gray)

def detectar_area_gabarito_template(imagem, template, metodo=cv2.TM_CCOEFF_NORMED, pre_processar=True, multi_escala=True, rotacoes=True):
    """
    Localiza o template do gabarito usando template matching com suporte a múltiplas escalas e rotações.
    
    Args:
        imagem: Imagem PIL
        template: Template PIL
        metodo: Método de template matching
        pre_processar: Se True, aplica pré-processamento na imagem
        multi_escala: Se True, tenta várias escalas para melhorar a detecção
        rotacoes: Se True, tenta várias rotações para melhorar a detecção
        
    Returns:
        (pts, score): Pontos detectados e score de confiança
    """
    # Pré-processamento para melhorar a detecção
    if pre_processar:
        imagem_proc = pre_processar_imagem(imagem)
    else:
        imagem_proc = imagem.convert("L")
    
    template_gray = np.array(template.convert("L"))
    img_gray = np.array(imagem_proc)
    
    # CORREÇÃO: Verifica se o template é maior que a imagem e redimensiona se necessário
    # Isso deve ser feito ANTES de qualquer tentativa de template matching
    if template_gray.shape[0] >= img_gray.shape[0] or template_gray.shape[1] >= img_gray.shape[1]:
        logger.debug(f"Template maior que a imagem. Redimensionando template.")
        # Calcula a escala para garantir que o template seja menor que a imagem
        scale = min(img_gray.shape[0] / template_gray.shape[0], 
                    img_gray.shape[1] / template_gray.shape[1]) * 0.9
        new_width = int(template_gray.shape[1] * scale)
        new_height = int(template_gray.shape[0] * scale)
        template_gray = cv2.resize(template_gray, (new_width, new_height))
        logger.debug(f"Template redimensionado para {new_width}x{new_height}")
    
    # Verifica novamente se o template ainda é maior que a imagem após o redimensionamento
    if template_gray.shape[0] >= img_gray.shape[0] or template_gray.shape[1] >= img_gray.shape[1]:
        logger.error("Template ainda é maior que a imagem após redimensionamento!")
        # Se ainda for maior, redimensiona a imagem para ser maior que o template
        scale_img = max(template_gray.shape[0] / img_gray.shape[0], 
                        template_gray.shape[1] / img_gray.shape[1]) * 1.1
        new_width_img = int(img_gray.shape[1] * scale_img)
        new_height_img = int(img_gray.shape[0] * scale_img)
        img_gray = cv2.resize(img_gray, (new_width_img, new_height_img))
        logger.debug(f"Imagem redimensionada para {new_width_img}x{new_height_img}")
    
    best_score = -1
    best_pts = None
    
    # Se multi_escala, tenta várias escalas para melhorar a detecção
    if multi_escala:
        scales = [0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3]
    else:
        scales = [1.0]
    
    # Se rotacoes, tenta várias rotações para melhorar a detecção
    if rotacoes:
        angles = [-2, -1, 0, 1, 2]
    else:
        angles = [0]
    
    for scale in scales:
        for angle in angles:
            try:
                if scale != 1.0 or angle != 0:
                    # Redimensiona a imagem
                    if scale != 1.0:
                        width = int(img_gray.shape[1] * scale)
                        height = int(img_gray.shape[0] * scale)
                        img_resized = cv2.resize(img_gray, (width, height), interpolation=cv2.INTER_AREA)
                    else:
                        img_resized = img_gray.copy()
                    
                    # Rotaciona a imagem
                    if angle != 0:
                        center = (img_resized.shape[1] // 2, img_resized.shape[0] // 2)
                        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
                        img_resized = cv2.warpAffine(img_resized, rotation_matrix, 
                                                    (img_resized.shape[1], img_resized.shape[0]),
                                                    flags=cv2.INTER_LINEAR)
                else:
                    img_resized = img_gray
                
                # Verifica novamente se o template é maior que a imagem redimensionada
                if template_gray.shape[0] >= img_resized.shape[0] or template_gray.shape[1] >= img_resized.shape[1]:
                    logger.debug(f"Template maior que a imagem redimensionada. Pulando escala {scale} e ângulo {angle}.")
                    continue
                
                # Aplica template matching
                res = cv2.matchTemplate(img_resized, template_gray, metodo)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                
                if max_val > best_score:
                    best_score = max_val
                    h, w = template_gray.shape
                    
                    # Ajusta as coordenadas para a escala e rotação originais
                    if scale != 1.0 or angle != 0:
                        # Calcula as coordenadas no espaço original
                        if scale != 1.0:
                            max_loc = (int(max_loc[0] / scale), int(max_loc[1] / scale))
                            h = int(h / scale)
                            w = int(w / scale)
                        
                        # Se houve rotação, precisamos ajustar as coordenadas
                        if angle != 0:
                            # Isso é uma aproximação simplificada
                            center_orig = (img_gray.shape[1] // 2, img_gray.shape[0] // 2)
                            dx = max_loc[0] - center_orig[0]
                            dy = max_loc[1] - center_orig[1]
                            
                            # Rotaciona o deslocamento de volta
                            angle_rad = -angle * np.pi / 180.0
                            dx_rot = dx * np.cos(angle_rad) - dy * np.sin(angle_rad)
                            dy_rot = dx * np.sin(angle_rad) + dy * np.cos(angle_rad)
                            
                            max_loc = (int(center_orig[0] + dx_rot), int(center_orig[1] + dy_rot))
                    
                    top_left = max_loc
                    bottom_right = (top_left[0] + w, top_left[1] + h)
                    best_pts = [
                        top_left,
                        (bottom_right[0], top_left[1]),
                        bottom_right,
                        (top_left[0], bottom_right[1])
                    ]
            except Exception as e:
                logger.error(f"Erro no template matching para escala {scale} e ângulo {angle}: {e}")
                continue
    
    logger.debug(f"Template matching score: {best_score:.4f}")
    return best_pts, best_score

def detectar_area_cabecalho_template(imagem, template, metodo=cv2.TM_CCOEFF_NORMED, pre_processar=True, multi_escala=True, rotacoes=True):
    """
    Localiza o template do cabeçalho (matrícula) com suporte a múltiplas escalas e rotações.
    
    Args:
        imagem: Imagem PIL
        template: Template PIL
        metodo: Método de template matching
        pre_processar: Se True, aplica pré-processamento na imagem
        multi_escala: Se True, tenta várias escalas para melhorar a detecção
        rotacoes: Se True, tenta várias rotações para melhorar a detecção
        
    Returns:
        (pts, score): Pontos detectados e score de confiança
    """
    # Usa a mesma implementação melhorada do detectar_area_gabarito_template
    return detectar_area_gabarito_template(imagem, template, metodo, pre_processar, multi_escala, rotacoes)

def detectar_matricula_por_contornos(imagem_pil, debug_folder=None):
    """
    Método alternativo para detectar a área de matrícula usando detecção de contornos.
    Útil quando o template matching falha.
    
    Args:
        imagem_pil: Imagem PIL
        debug_folder: Pasta para salvar imagens de debug
        
    Returns:
        (x, y, w, h): Coordenadas da região detectada ou None se não encontrada
    """
    # Converte para escala de cinza
    img_gray = np.array(imagem_pil.convert("L"))
    
    # Aplica blur para reduzir ruído
    img_blur = cv2.GaussianBlur(img_gray, (5, 5), 0)
    
    # Aplica threshold adaptativo
    img_thresh = cv2.adaptiveThreshold(
        img_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 11, 2
    )
    
    # Operações morfológicas para melhorar a detecção
    kernel = np.ones((3, 3), np.uint8)
    img_morph = cv2.morphologyEx(img_thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
    
    if debug_folder:
        cv2.imwrite(os.path.join(debug_folder, "matricula_thresh.png"), img_thresh)
        cv2.imwrite(os.path.join(debug_folder, "matricula_morph.png"), img_morph)
    
    # Encontra contornos
    contours, _ = cv2.findContours(img_morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filtra contornos por área e formato (procurando retângulos)
    candidatos = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 1000:  # Ignora contornos muito pequenos
            continue
        
        # Aproxima o contorno para um polígono
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.04 * peri, True)
        
        # Verifica se é um retângulo (4 vértices)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(contour)
            # Verifica proporções típicas de uma caixa de matrícula
            aspect_ratio = w / float(h)
            if 2.0 < aspect_ratio < 6.0:  # Proporção típica de uma caixa de matrícula
                candidatos.append((x, y, w, h, area))
    
    if not candidatos:
        return None
    
    # Ordena por área (maior primeiro)
    candidatos.sort(key=lambda x: x[4], reverse=True)
    
    # Pega o maior candidato
    x, y, w, h, _ = candidatos[0]
    
    if debug_folder:
        debug_img = np.array(imagem_pil)
        cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.imwrite(os.path.join(debug_folder, "matricula_contorno.png"), debug_img)
    
    return (x, y, w, h)

def detectar_matricula_por_hough(imagem_pil, debug_folder=None):
    """
    Método alternativo para detectar a área de matrícula usando transformada de Hough.
    Útil quando o template matching e a detecção por contornos falham.
    
    Args:
        imagem_pil: Imagem PIL
        debug_folder: Pasta para salvar imagens de debug
        
    Returns:
        (x, y, w, h): Coordenadas da região detectada ou None se não encontrada
    """
    # Converte para escala de cinza
    img_gray = np.array(imagem_pil.convert("L"))
    
    # Aplica blur para reduzir ruído
    img_blur = cv2.GaussianBlur(img_gray, (5, 5), 0)
    
    # Detecção de bordas com Canny
    edges = cv2.Canny(img_blur, 50, 150, apertureSize=3)
    
    if debug_folder:
        cv2.imwrite(os.path.join(debug_folder, "matricula_edges.png"), edges)
    
    # Detecta linhas usando a transformada de Hough
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=100, maxLineGap=10)
    
    if lines is None or len(lines) < 4:
        return None
    
    # Filtra linhas horizontais e verticais
    horizontal_lines = []
    vertical_lines = []
    
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if abs(x2 - x1) > abs(y2 - y1):  # Linha horizontal
            if abs(x2 - x1) > img_gray.shape[1] * 0.1:  # Pelo menos 10% da largura da imagem
                horizontal_lines.append((x1, y1, x2, y2))
        else:  # Linha vertical
            if abs(y2 - y1) > img_gray.shape[0] * 0.02:  # Pelo menos 2% da altura da imagem
                vertical_lines.append((x1, y1, x2, y2))
    
    if len(horizontal_lines) < 2 or len(vertical_lines) < 2:
        return None
    
    # Encontra as linhas que formam um retângulo
    # Simplificação: pega as linhas mais extremas
    horizontal_lines.sort(key=lambda line: line[1])  # Ordena por y
    top_line = horizontal_lines[0]
    bottom_line = horizontal_lines[-1]
    
    vertical_lines.sort(key=lambda line: line[0])  # Ordena por x
    left_line = vertical_lines[0]
    right_line = vertical_lines[-1]
    
    # Calcula as coordenadas do retângulo
    x = min(left_line[0], left_line[2])
    y = min(top_line[1], top_line[3])
    w = max(right_line[0], right_line[2]) - x
    h = max(bottom_line[1], bottom_line[3]) - y
    
    # Verifica se as proporções são razoáveis para uma caixa de matrícula
    aspect_ratio = w / float(h)
    if not (2.0 < aspect_ratio < 6.0):
        return None
    
    if debug_folder:
        debug_img = np.array(imagem_pil)
        cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.imwrite(os.path.join(debug_folder, "matricula_hough.png"), debug_img)
    
    return (x, y, w, h)

def detectar_respostas_por_grid(
    imagem,
    grid_rois,
    num_alternativas=4,
    threshold_fill=0.3,
    debug=True,
    debug_folder=None
):
    """
    Detecta as respostas em formato de grade (bubbles).
    Usa threshold Otsu e operações morfológicas (close, open).

    Se num_alternativas=5, as alternativas serão A, B, C, D, E.
    """
    if num_alternativas == 4:
        alternativas = ['A','B','C','D']
    else:
        alternativas = ['A','B','C','D','E']
    
    # Debug dirs
    if debug and debug_folder:
        os.makedirs(debug_folder, exist_ok=True)
        debug_bin_dir = os.path.join(debug_folder, "bin")
        debug_rois_dir = os.path.join(debug_folder, "rois")
        debug_subrois_dir = os.path.join(debug_folder, "subrois")
        os.makedirs(debug_bin_dir, exist_ok=True)
        os.makedirs(debug_rois_dir, exist_ok=True)
        os.makedirs(debug_subrois_dir, exist_ok=True)
        
        # Salva a imagem colorida de entrada
        step1_color = os.path.join(debug_bin_dir, "debug_step1_color.png")
        imagem.save(step1_color)

    # Converte para escala de cinza
    imagem_gray = imagem.convert("L")
    if debug and debug_folder:
        step2_gray = os.path.join(debug_bin_dir, "debug_step2_gray.png")
        imagem_gray.save(step2_gray)

    # Threshold Otsu invertido
    imagem_np = np.array(imagem_gray)
    
    # Aplica CLAHE para melhorar o contraste antes do threshold
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    imagem_np = clahe.apply(imagem_np)
    
    if debug and debug_folder:
        step2_5_clahe = os.path.join(debug_bin_dir, "debug_step2_5_clahe.png")
        cv2.imwrite(step2_5_clahe, imagem_np)
    
    # Threshold Otsu invertido
    _, imagem_bin = cv2.threshold(imagem_np, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    
    if debug and debug_folder:
        step3_thresh = os.path.join(debug_bin_dir, "debug_step3_threshold.png")
        cv2.imwrite(step3_thresh, imagem_bin)

    # Morfologia melhorada
    kernel = np.ones((3,3), np.uint8)
    imagem_bin = cv2.morphologyEx(imagem_bin, cv2.MORPH_CLOSE, kernel, iterations=2)
    imagem_bin = cv2.morphologyEx(imagem_bin, cv2.MORPH_OPEN, kernel, iterations=1)

    if debug and debug_folder:
        step4_morph = os.path.join(debug_bin_dir, "debug_step4_morph.png")
        cv2.imwrite(step4_morph, imagem_bin)

    resultados = {}
    questao_num = 1

    for col_rois in grid_rois:
        for roi in col_rois:
            questao_nome = f"Questao {questao_num}"
            x = roi["x"]
            y = roi["y"]
            w = roi["width"]
            h = roi["height"]
            if w is None or h is None:
                resultados[questao_nome] = "ROI inválido"
                questao_num += 1
                continue
            
            roi_img = imagem_bin[y:y+h, x:x+w]
            if debug and debug_folder:
                roi_filename = os.path.join(debug_rois_dir, f"debug_grid_roi_{questao_num}.png")
                cv2.imwrite(roi_filename, roi_img)

            sub_w = w // num_alternativas
            fill_ratios = []
            for alt_i in range(num_alternativas):
                sub_roi = roi_img[:, alt_i*sub_w:(alt_i+1)*sub_w]
                area_sub = sub_roi.shape[0] * sub_roi.shape[1]
                count_white = cv2.countNonZero(sub_roi)
                ratio = count_white / area_sub if area_sub > 0 else 0
                fill_ratios.append(ratio)
                if debug and debug_folder:
                    alt_filename = f"debug_grid_roi_{questao_num}_alt_{alternativas[alt_i]}.png"
                    alt_file_path = os.path.join(debug_subrois_dir, alt_filename)
                    cv2.imwrite(alt_file_path, sub_roi)
            
            # Algoritmo melhorado para detecção de alternativas marcadas
            max_ratio = max(fill_ratios)
            marcadas = []
            
            # Considera apenas alternativas com preenchimento significativo
            for i, ratio in enumerate(fill_ratios):
                # Se o ratio for pelo menos 70% do máximo, considera como marcado
                if ratio >= threshold_fill and ratio >= max_ratio * 0.7:
                    marcadas.append(i)
            
            if len(marcadas) == 0:
                resultado = f"Não marcado (max fill: {max_ratio:.2f})"
            elif len(marcadas) > 1:
                resultado = "N"
            else:
                resultado = alternativas[marcadas[0]]
            
            resultados[questao_nome] = resultado
            questao_num += 1
    
    return resultados