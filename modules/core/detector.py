import cv2
import numpy as np
from PIL import Image, ImageDraw
import os

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

def detectar_area_gabarito_template(imagem, template):
    """
    Localiza o template do gabarito e retorna (pts, score).
    pts são os 4 pontos do retângulo [top-left, top-right, bottom-right, bottom-left].
    """
    img_gray = np.array(imagem.convert("L"))
    template_gray = np.array(template.convert("L"))
    res = cv2.matchTemplate(img_gray, template_gray, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    h, w = template_gray.shape
    top_left = max_loc
    bottom_right = (top_left[0] + w, top_left[1] + h)
    pts = [
        top_left,
        (bottom_right[0], top_left[1]),
        bottom_right,
        (top_left[0], bottom_right[1])
    ]
    return pts, max_val

def detectar_area_cabecalho_template(imagem, template):
    """
    Localiza o template do cabeçalho (matrícula) e retorna (pts, score).
    A lógica é igual à do gabarito, só muda o nome para ficar claro.
    """
    img_gray = np.array(imagem.convert("L"))
    template_gray = np.array(template.convert("L"))
    res = cv2.matchTemplate(img_gray, template_gray, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    h, w = template_gray.shape
    top_left = max_loc
    bottom_right = (top_left[0] + w, top_left[1] + h)
    pts = [
        top_left,
        (bottom_right[0], top_left[1]),
        bottom_right,
        (top_left[0], bottom_right[1])
    ]
    return pts, max_val

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
    """
    if num_alternativas == 4:
        alternativas = ['A','B','C','D']
    else:
        alternativas = ['A','B','C','D','E']
    
    if debug and debug_folder:
        os.makedirs(debug_folder, exist_ok=True)
        debug_bin_dir = os.path.join(debug_folder, "bin")
        debug_rois_dir = os.path.join(debug_folder, "rois")
        debug_subrois_dir = os.path.join(debug_folder, "subrois")
        os.makedirs(debug_bin_dir, exist_ok=True)
        os.makedirs(debug_rois_dir, exist_ok=True)
        os.makedirs(debug_subrois_dir, exist_ok=True)
    
    imagem_gray = imagem.convert("L")
    imagem_np = np.array(imagem_gray)
    _, imagem_bin = cv2.threshold(imagem_np, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

    kernel = np.ones((3,3), np.uint8)
    imagem_bin = cv2.morphologyEx(imagem_bin, cv2.MORPH_CLOSE, kernel, iterations=1)
    imagem_bin = cv2.morphologyEx(imagem_bin, cv2.MORPH_OPEN, kernel, iterations=1)
    
    if debug and debug_folder:
        bin_filename = os.path.join(debug_bin_dir, "debug_imagem_bin_grid.png")
        cv2.imwrite(bin_filename, imagem_bin)
    
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
                
            marcadas = [i for i, r in enumerate(fill_ratios) if r >= threshold_fill]
            if len(marcadas) == 0:
                resultado = f"Não marcado (max fill: {max(fill_ratios):.2f})"
            elif len(marcadas) > 1:
                resultado = "N"
            else:
                resultado = alternativas[marcadas[0]]
            
            resultados[questao_nome] = resultado
            questao_num += 1
    
    return resultados
