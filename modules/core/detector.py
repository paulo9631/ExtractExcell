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
    img_gray = np.array(imagem_pil.convert("L"))
    if remover_ruido:
        img_gray = cv2.GaussianBlur(img_gray, (3, 3), 0)
    if equalizar:
        img_gray = cv2.equalizeHist(img_gray)
    if ajustar_contraste:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        img_gray = clahe.apply(img_gray)
    return Image.fromarray(img_gray)

def detectar_area_gabarito_template(imagem, template, metodo=cv2.TM_CCOEFF_NORMED, pre_processar=True, multi_escala=True, rotacoes=True):
    if pre_processar:
        imagem_proc = pre_processar_imagem(imagem)
    else:
        imagem_proc = imagem.convert("L")
    template_gray = np.array(template.convert("L"))
    img_gray = np.array(imagem_proc)
    if template_gray.shape[0] >= img_gray.shape[0] or template_gray.shape[1] >= img_gray.shape[1]:
        logger.debug(f"Template maior que a imagem. Redimensionando template.")
        scale = min(img_gray.shape[0] / template_gray.shape[0], 
                    img_gray.shape[1] / template_gray.shape[1]) * 0.9
        new_width = int(template_gray.shape[1] * scale)
        new_height = int(template_gray.shape[0] * scale)
        template_gray = cv2.resize(template_gray, (new_width, new_height))
        logger.debug(f"Template redimensionado para {new_width}x{new_height}")
    if template_gray.shape[0] >= img_gray.shape[0] or template_gray.shape[1] >= img_gray.shape[1]:
        logger.error("Template ainda é maior que a imagem após redimensionamento!")
        scale_img = max(template_gray.shape[0] / img_gray.shape[0], 
                        template_gray.shape[1] / img_gray.shape[1]) * 1.1
        new_width_img = int(img_gray.shape[1] * scale_img)
        new_height_img = int(img_gray.shape[0] * scale_img)
        img_gray = cv2.resize(img_gray, (new_width_img, new_height_img))
        logger.debug(f"Imagem redimensionada para {new_width_img}x{new_height_img}")
    best_score = -1
    best_pts = None
    if multi_escala:
        scales = [0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3]
    else:
        scales = [1.0]
    if rotacoes:
        angles = [-2, -1, 0, 1, 2]
    else:
        angles = [0]
    for scale in scales:
        for angle in angles:
            try:
                if scale != 1.0 or angle != 0:
                    if scale != 1.0:
                        width = int(img_gray.shape[1] * scale)
                        height = int(img_gray.shape[0] * scale)
                        img_resized = cv2.resize(img_gray, (width, height), interpolation=cv2.INTER_AREA)
                    else:
                        img_resized = img_gray.copy()
                    if angle != 0:
                        center = (img_resized.shape[1] // 2, img_resized.shape[0] // 2)
                        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
                        img_resized = cv2.warpAffine(img_resized, rotation_matrix, 
                                                    (img_resized.shape[1], img_resized.shape[0]),
                                                    flags=cv2.INTER_LINEAR)
                else:
                    img_resized = img_gray
                if template_gray.shape[0] >= img_resized.shape[0] or template_gray.shape[1] >= img_resized.shape[1]:
                    logger.debug(f"Template maior que a imagem redimensionada. Pulando escala {scale} e ângulo {angle}.")
                    continue
                res = cv2.matchTemplate(img_resized, template_gray, metodo)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                if max_val > best_score:
                    best_score = max_val
                    h, w = template_gray.shape
                    if scale != 1.0 or angle != 0:
                        if scale != 1.0:
                            max_loc = (int(max_loc[0] / scale), int(max_loc[1] / scale))
                            h = int(h / scale)
                            w = int(w / scale)
                        if angle != 0:
                            center_orig = (img_gray.shape[1] // 2, img_gray.shape[0] // 2)
                            dx = max_loc[0] - center_orig[0]
                            dy = max_loc[1] - center_orig[1]
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
    return detectar_area_gabarito_template(imagem, template, metodo, pre_processar, multi_escala, rotacoes)

def detectar_matricula_por_contornos(imagem_pil, debug_folder=None):
    img_gray = np.array(imagem_pil.convert("L"))
    img_blur = cv2.GaussianBlur(img_gray, (5, 5), 0)
    img_thresh = cv2.adaptiveThreshold(
        img_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 11, 2
    )
    kernel = np.ones((3, 3), np.uint8)
    img_morph = cv2.morphologyEx(img_thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
    if debug_folder:
        cv2.imwrite(os.path.join(debug_folder, "matricula_thresh.png"), img_thresh)
        cv2.imwrite(os.path.join(debug_folder, "matricula_morph.png"), img_morph)
    contours, _ = cv2.findContours(img_morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidatos = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 1000:
            continue
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.04 * peri, True)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / float(h)
            if 2.0 < aspect_ratio < 6.0:
                candidatos.append((x, y, w, h, area))
    if not candidatos:
        return None
    candidatos.sort(key=lambda x: x[4], reverse=True)
    x, y, w, h, _ = candidatos[0]
    if debug_folder:
        debug_img = np.array(imagem_pil)
        cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.imwrite(os.path.join(debug_folder, "matricula_contorno.png"), debug_img)
    return (x, y, w, h)

def detectar_matricula_por_hough(imagem_pil, debug_folder=None):
    img_gray = np.array(imagem_pil.convert("L"))
    img_blur = cv2.GaussianBlur(img_gray, (5, 5), 0)
    edges = cv2.Canny(img_blur, 50, 150, apertureSize=3)
    if debug_folder:
        cv2.imwrite(os.path.join(debug_folder, "matricula_edges.png"), edges)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=100, maxLineGap=10)
    if lines is None or len(lines) < 4:
        return None
    horizontal_lines = []
    vertical_lines = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if abs(x2 - x1) > abs(y2 - y1):
            if abs(x2 - x1) > img_gray.shape[1] * 0.1:
                horizontal_lines.append((x1, y1, x2, y2))
        else:
            if abs(y2 - y1) > img_gray.shape[0] * 0.02:
                vertical_lines.append((x1, y1, x2, y2))
    if len(horizontal_lines) < 2 or len(vertical_lines) < 2:
        return None
    horizontal_lines.sort(key=lambda line: line[1])
    top_line = horizontal_lines[0]
    bottom_line = horizontal_lines[-1]
    vertical_lines.sort(key=lambda line: line[0])
    left_line = vertical_lines[0]
    right_line = vertical_lines[-1]
    x = min(left_line[0], left_line[2])
    y = min(top_line[1], top_line[3])
    w = max(right_line[0], right_line[2]) - x
    h = max(bottom_line[1], bottom_line[3]) - y
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
        imagem.save(os.path.join(debug_bin_dir, "debug_original.png"))
    imagem_gray = imagem.convert("L")
    imagem_np = np.array(imagem_gray)
    if debug and debug_folder:
        cv2.imwrite(os.path.join(debug_bin_dir, "debug_gray.png"), imagem_np)
    imagem_np = cv2.bilateralFilter(imagem_np, 5, 50, 50)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    imagem_np = clahe.apply(imagem_np)
    if debug and debug_folder:
        cv2.imwrite(os.path.join(debug_bin_dir, "debug_clahe.png"), imagem_np)
    _, thresh_otsu = cv2.threshold(imagem_np, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    thresh_adaptive = cv2.adaptiveThreshold(
        imagem_np, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 11, 2
    )
    imagem_bin = cv2.addWeighted(thresh_otsu, 0.5, thresh_adaptive, 0.5, 0)
    _, imagem_bin = cv2.threshold(imagem_bin, 127, 255, cv2.THRESH_BINARY)
    if debug and debug_folder:
        cv2.imwrite(os.path.join(debug_bin_dir, "debug_otsu.png"), thresh_otsu)
        cv2.imwrite(os.path.join(debug_bin_dir, "debug_adaptive.png"), thresh_adaptive)
        cv2.imwrite(os.path.join(debug_bin_dir, "debug_combined.png"), imagem_bin)
    kernel_noise = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    imagem_bin = cv2.morphologyEx(imagem_bin, cv2.MORPH_OPEN, kernel_noise, iterations=1)
    kernel_connect = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    imagem_bin = cv2.morphologyEx(imagem_bin, cv2.MORPH_CLOSE, kernel_connect, iterations=1)
    if debug and debug_folder:
        cv2.imwrite(os.path.join(debug_bin_dir, "debug_final_binary.png"), imagem_bin)
    resultados = {}
    questao_num = 1
    for col_rois in grid_rois:
        for roi in col_rois:
            questao_nome = f"Questao {questao_num}"
            x = roi["x"]
            y = roi["y"]
            w = roi["width"]
            h = roi["height"]
            if w is None or h is None or w <= 0 or h <= 0:
                resultados[questao_nome] = "ROI inválido"
                questao_num += 1
                continue
            x = max(0, x)
            y = max(0, y)
            w = min(w, imagem_bin.shape[1] - x)
            h = min(h, imagem_bin.shape[0] - y)
            if w <= 0 or h <= 0:
                resultados[questao_nome] = "ROI fora dos limites"
                questao_num += 1
                continue
            roi_img = imagem_bin[y:y+h, x:x+w]
            if debug and debug_folder:
                cv2.imwrite(os.path.join(debug_rois_dir, f"debug_roi_{questao_num}.png"), roi_img)
            sub_w = w // num_alternativas
            fill_ratios = []
            for alt_i in range(num_alternativas):
                start_x = alt_i * sub_w
                end_x = (alt_i + 1) * sub_w if alt_i < num_alternativas - 1 else w
                end_x = min(end_x, w)
                if start_x >= end_x:
                    fill_ratios.append(0.0)
                    continue
                sub_roi = roi_img[:, start_x:end_x]
                if sub_roi.size == 0:
                    fill_ratios.append(0.0)
                    continue
                area_sub = sub_roi.shape[0] * sub_roi.shape[1]
                count_white = cv2.countNonZero(sub_roi)
                ratio = count_white / area_sub if area_sub > 0 else 0
                fill_ratios.append(ratio)
                if debug and debug_folder:
                    alt_filename = f"debug_roi_{questao_num}_alt_{alternativas[alt_i]}_ratio_{ratio:.3f}.png"
                    alt_file_path = os.path.join(debug_subrois_dir, alt_filename)
                    cv2.imwrite(alt_file_path, sub_roi)
            max_ratio = max(fill_ratios) if fill_ratios else 0
            dynamic_threshold = threshold_fill
            if max_ratio < threshold_fill * 0.5:
                dynamic_threshold = threshold_fill * 0.6
            elif max_ratio > threshold_fill * 3:
                dynamic_threshold = threshold_fill * 1.5
            marcadas = []
            for i, ratio in enumerate(fill_ratios):
                if ratio >= dynamic_threshold and ratio >= max_ratio * 0.6:
                    marcadas.append(i)
            if len(marcadas) == 0:
                if max_ratio > threshold_fill * 0.3:
                    best_alt = fill_ratios.index(max_ratio)
                    if max_ratio >= threshold_fill * 0.5:
                        resultado = f"{alternativas[best_alt]} (fraco)"
                    else:
                        resultado = f"Não marcado (max: {max_ratio:.2f})"
                else:
                    resultado = "Não marcado"
            elif len(marcadas) == 1:
                resultado = alternativas[marcadas[0]]
            else:
                marked_ratios = [fill_ratios[i] for i in marcadas]
                max_marked = max(marked_ratios)
                strong_marks = [i for i in marcadas if fill_ratios[i] >= max_marked * 0.85]
                if len(strong_marks) == 1:
                    resultado = f"{alternativas[strong_marks[0]]} (múltiplo)"
                else:
                    resultado = "N"
            resultados[questao_nome] = resultado
            if debug:
                logger.debug(f"{questao_nome}: ratios={[f'{r:.3f}' for r in fill_ratios]}, "
                           f"max={max_ratio:.3f}, threshold={dynamic_threshold:.3f}, "
                           f"marcadas={marcadas}, resultado='{resultado}'")
            questao_num += 1
    return resultados
