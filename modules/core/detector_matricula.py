import os
import cv2
import numpy as np
from PIL import Image
import logging
import pytesseract
import re

logger = logging.getLogger('DetectorMatricula')

class DetectorMatricula:
    """
    Classe para detecção e reconhecimento de matrículas em documentos,
    usando OCR tradicional e múltiplas técnicas de pré-processamento.
    """

    def __init__(self, config=None):
        self.config = config or {}
        self.tesseract_configs = [
            '--psm 7 -c tessedit_char_whitelist=0123456789',
            '--psm 8 -c tessedit_char_whitelist=0123456789',
            '--psm 6 -c tessedit_char_whitelist=0123456789',
            '--psm 10 -c tessedit_char_whitelist=0123456789',
            '--psm 13 -c tessedit_char_whitelist=0123456789'
        ]
        self.min_length = self.config.get('matricula_min_length', 5)
        self.max_length = self.config.get('matricula_max_length', 10)

    def processar_documento(self, imagem, debug_folder=None):
        if isinstance(imagem, np.ndarray):
            imagem_pil = Image.fromarray(imagem)
        else:
            imagem_pil = imagem

        matricula, confianca = self.extrair_matricula_scaneada(imagem_pil, debug_folder)

        resultado = {
            "matricula": matricula,
            "confianca": confianca,
            "valido": bool(matricula and self._validar_matricula(matricula))
        }
        return resultado

    def extrair_matricula_scaneada(self, imagem, debug_folder=None):
        if isinstance(imagem, np.ndarray):
            imagem_pil = Image.fromarray(imagem)
        else:
            imagem_pil = imagem

        roi_pil = self._extrair_roi_matricula(imagem_pil, debug_folder)

        if roi_pil is None:
            logger.error("Não foi possível extrair ROI da matrícula")
            return "", 0.0

        processed_images = self._aplicar_tecnicas_pre_processamento(roi_pil)

        resultados = []

        for technique, img in processed_images:
            img_morph = self._aplicar_morfologia_adaptativa(img)

            for config in self.tesseract_configs:
                try:
                    texto = pytesseract.image_to_string(
                        img_morph, config=config
                    ).strip()

                    texto = self._corrigir_erros_comuns(texto)

                    if texto and self._validar_matricula(texto):
                        resultados.append((texto, 0.8))
                except Exception as e:
                    logger.error(f"Erro OCR {technique}: {e}")

        if not resultados:
            logger.warning("Não foi possível reconhecer matrícula válida")
            return "", 0.0

        resultados.sort(key=lambda x: x[1], reverse=True)
        melhor_texto, melhor_confianca = resultados[0]

        logger.info(f"Matrícula reconhecida: '{melhor_texto}' (confiança: {melhor_confianca})")
        return melhor_texto, melhor_confianca

    def _extrair_roi_matricula(self, imagem_pil, debug_folder=None):
        if "matricula_roi" in self.config:
            try:
                x, y, w, h = self.config["matricula_roi"].values()
                roi = imagem_pil.crop((x, y, x+w, y+h))
                if debug_folder:
                    os.makedirs(debug_folder, exist_ok=True)
                    roi.save(os.path.join(debug_folder, "matricula_roi.png"))
                return roi
            except Exception as e:
                logger.error(f"Erro ao extrair ROI fixa: {e}")

        if "matricula_template_path" in self.config:
            try:
                from modules.core.detector import detectar_area_cabecalho_template, pre_processar_imagem
                template_path = self.config["matricula_template_path"]
                if os.path.exists(template_path):
                    template = Image.open(template_path)
                    img_proc = pre_processar_imagem(imagem_pil)
                    pts, score = detectar_area_cabecalho_template(img_proc, template)
                    if score >= self.config.get("matricula_template_threshold", 0.25):
                        xs = [p[0] for p in pts]
                        ys = [p[1] for p in pts]
                        x_min, x_max = min(xs), max(xs)
                        y_min, y_max = min(ys), max(ys)
                        roi = imagem_pil.crop((x_min, y_min, x_max, y_max))
                        if debug_folder:
                            roi.save(os.path.join(debug_folder, "matricula_roi_template.png"))
                        return roi
            except Exception as e:
                logger.error(f"Erro no template matching: {e}")

        try:
            from modules.core.detector import detectar_matricula_por_contornos
            roi_coords = detectar_matricula_por_contornos(imagem_pil)
            if roi_coords:
                x, y, w, h = roi_coords
                roi = imagem_pil.crop((x, y, x+w, y+h))
                if debug_folder:
                    roi.save(os.path.join(debug_folder, "matricula_roi_contornos.png"))
                return roi
        except Exception as e:
            logger.error(f"Erro na detecção por contornos: {e}")

        try:
            from modules.core.detector import detectar_matricula_por_hough
            roi_coords = detectar_matricula_por_hough(imagem_pil)
            if roi_coords:
                x, y, w, h = roi_coords
                roi = imagem_pil.crop((x, y, x+w, y+h))
                if debug_folder:
                    roi.save(os.path.join(debug_folder, "matricula_roi_hough.png"))
                return roi
        except Exception as e:
            logger.error(f"Erro na detecção por Hough: {e}")

        logger.warning("Não foi possível detectar ROI específica, usando imagem completa")
        return imagem_pil

    def _aplicar_tecnicas_pre_processamento(self, imagem_pil):
        img_np = np.array(imagem_pil.convert("L"))
        processed_images = []

        img_eq = cv2.equalizeHist(img_np)
        _, img_otsu = cv2.threshold(img_eq, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        processed_images.append(("otsu", img_otsu))

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        img_clahe = clahe.apply(img_np)
        _, img_clahe_bin = cv2.threshold(img_clahe, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        processed_images.append(("clahe", img_clahe_bin))

        img_adaptive = cv2.adaptiveThreshold(
            img_np, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        processed_images.append(("adaptive", img_adaptive))

        return processed_images

    def _aplicar_morfologia_adaptativa(self, imagem_bin):
        result = imagem_bin.copy()

        white_pixels = cv2.countNonZero(imagem_bin)
        total_pixels = imagem_bin.size
        white_ratio = white_pixels / total_pixels

        if white_ratio > 0.5:
            kernel = np.ones((2, 2), np.uint8)
            result = cv2.morphologyEx(result, cv2.MORPH_OPEN, kernel, iterations=1)
        elif white_ratio < 0.2:
            kernel = np.ones((2, 1), np.uint8)
            result = cv2.morphologyEx(result, cv2.MORPH_CLOSE, kernel, iterations=1)

        return result

    def _corrigir_erros_comuns(self, texto):
        substituicoes = {
            'l': '1', 'I': '1', 'i': '1',
            'o': '0', 'O': '0', 'Q': '0',
            'S': '5', 's': '5',
            'Z': '2', 'z': '2',
            'G': '6', 'B': '8',
            'A': '4', 'T': '7'
        }
        for char, corr in substituicoes.items():
            texto = texto.replace(char, corr)
        return re.sub(r'\D', '', texto)

    def _validar_matricula(self, texto):
        if not texto.isdigit():
            return False
        if not (self.min_length <= len(texto) <= self.max_length):
            return False
        return True
