import os
import sys
import cv2
import numpy as np
from PIL import Image
import logging
import pytesseract
import re
from pytesseract import image_to_data, Output

logger = logging.getLogger('DetectorMatricula')

def resource_path(relative_path):
    """
    Retorna o caminho absoluto para recursos, considerando o bundle do PyInstaller.
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class DetectorMatricula:
    """
    Classe para detecção e reconhecimento de matrículas em documentos,
    usando OCR tradicional, ROI, fallback heurístico e pré-processamento.
    """

    def __init__(self, config=None, debug=False, debug_dir="debug"):
        self.config = config or {}
        self.tesseract_configs = [
            '--psm 7 -c tessedit_char_whitelist=0123456789',
            '--psm 8 -c tessedit_char_whitelist=0123456789',
            '--psm 6 -c tessedit_char_whitelist=0123456789',
            '--psm 10 -c tessedit_char_whitelist=0123456789',
            '--psm 13 -c tessedit_char_whitelist=0123456789',
        ]
        self.min_length = self.config.get('matricula_min_length', 5)
        self.max_length = self.config.get('matricula_max_length', 10)
        self.debug = debug
        self.debug_dir = debug_dir
        os.makedirs(self.debug_dir, exist_ok=True)

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

        if roi_pil is None or roi_pil.size[0] < 10:
            logger.warning("Não foi possível extrair ROI da matrícula. Tentando OCR geral.")
            return self._ocr_semantico_global(imagem_pil)

        processed_images = self._aplicar_tecnicas_pre_processamento(roi_pil)
        resultados = []

        for technique, img in processed_images:
            img_morph = self._aplicar_morfologia_adaptativa(img)
            for config in self.tesseract_configs:
                try:
                    texto = pytesseract.image_to_string(img_morph, config=config).strip()
                    texto = self._corrigir_erros_comuns(texto)
                    if texto and self._validar_matricula(texto):
                        resultados.append((texto, 0.8))
                except Exception as e:
                    logger.error(f"Erro OCR {technique}: {e}")

        if resultados:
            resultados.sort(key=lambda x: x[1], reverse=True)
            melhor_texto, melhor_confianca = resultados[0]
            return melhor_texto, melhor_confianca

        return self._ocr_semantico_global(imagem_pil)

    def _ocr_semantico_global(self, imagem_pil):
        dados = image_to_data(imagem_pil, output_type=Output.DICT, lang='por')
        melhores = []

        for i, palavra in enumerate(dados['text']):
            texto = palavra.strip().lower()
            conf = float(dados['conf'][i]) if str(dados['conf'][i]).replace('.', '', 1).isdigit() else 0
            top = dados['top'][i]

            if texto in ['matrícula', 'matricula']:
                for j in range(i + 1, min(i + 5, len(dados['text']))):
                    candidato = dados['text'][j].strip()
                    if candidato.isdigit() and self._validar_matricula(candidato):
                        return candidato, conf

            if texto.isdigit() and self._validar_matricula(texto):
                melhores.append((texto, conf, top))

        if melhores:
            melhores.sort(key=lambda x: (x[2], -x[1]))
            melhor = melhores[0]
            return melhor[0], melhor[1]

        return "", 0.0

    def _extrair_roi_matricula(self, imagem_pil, debug_folder=None):
        if "matricula_template_path" in self.config:
            try:
                from modules.core.detector import detectar_area_cabecalho_template, pre_processar_imagem
                template_path = resource_path(self.config["matricula_template_path"])
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

    def detectar_area_matricula(self, imagem, index=0):
        altura, largura = imagem.shape[:2]

        roi_x_inicio = int(0.05 * largura)
        roi_x_fim = int(0.35 * largura)
        roi_y_inicio = int(0.18 * altura)
        roi_y_fim = int(0.30 * altura)

        area_matricula = imagem[roi_y_inicio:roi_y_fim, roi_x_inicio:roi_x_fim]

        area_matricula = cv2.cvtColor(area_matricula, cv2.COLOR_BGR2GRAY)
        area_matricula = cv2.threshold(area_matricula, 0, 255,
                                       cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        area_matricula = cv2.medianBlur(area_matricula, 3)

        if self.debug:
            debug_path = os.path.join(self.debug_dir, f"matricula_roi_{index}.png")
            cv2.imwrite(debug_path, area_matricula)

        return area_matricula

    def detectar_matricula(self, imagem, index=0):
        roi = self.detectar_area_matricula(imagem, index=index)

        header_roi = cv2.equalizeHist(roi)
        header_roi = cv2.adaptiveThreshold(
            header_roi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        if self.debug:
            debug_header = os.path.join(self.debug_dir, f"matricula_header_{index}.png")
            cv2.imwrite(debug_header, header_roi)

        config_tess = "--psm 6"
        data = pytesseract.image_to_data(header_roi, output_type=pytesseract.Output.DICT, config=config_tess)

        matricula = ""
        for i, word in enumerate(data['text']):
            if word.strip().lower() == "matricula":
                if i + 1 < len(data['text']):
                    candidato = data['text'][i + 1].strip()
                    if candidato.isdigit():
                        matricula = candidato
                        break

        if not matricula:
            fallback_text = pytesseract.image_to_string(header_roi, config="--psm 7")
            fallback_text = fallback_text.replace("\n", " ")
            match = re.search(r'\d{5,}', fallback_text)
            if match:
                matricula = match.group(0)

        return matricula.strip()

    def _validar_matricula(self, texto):
        return texto.isdigit() and self.min_length <= len(texto) <= self.max_length
