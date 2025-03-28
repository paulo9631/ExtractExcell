import os
from datetime import datetime
import cv2
import numpy as np
from PIL import Image, ImageDraw

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from modules.core.converter import converter_pdf_em_imagens
from modules.core.detector import (
    detectar_respostas_por_grid,
    corrigir_perspectiva,
    detectar_area_gabarito_template,
    detectar_area_cabecalho_template  # função para cabeçalho
)
from modules.core.text_extractor import extrair_info_ocr
from modules.core.student_api import buscar_estudante
from modules.utils import logger

class WorkerSignals(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)
    message = pyqtSignal(str)
    error = pyqtSignal(str)

# Função auxiliar para pré-processamento alternativo quando o documento é scaneado por uma impressora
def preprocess_roi(roi_pil):
    """
    Converte a ROI para escala de cinza, aplica equalização e outros ajustes,
    buscando realçar os dígitos para uma melhor extração.
    """
    roi_gray = np.array(roi_pil.convert("L"))
    # (Opcional) Você pode incluir aqui outros filtros se necessário,
    # ex: GaussianBlur, limiarização adaptativa etc.
    roi_eq = cv2.equalizeHist(roi_gray)
    return Image.fromarray(roi_eq)

class ProcessWorker(QRunnable):
    def __init__(self, pdf_paths, config, n_alternativas, dpi_escolhido):
        super().__init__()
        self.pdf_paths = pdf_paths
        self.config = config
        self.n_alternativas = n_alternativas
        self.dpi_escolhido = dpi_escolhido
        self.signals = WorkerSignals()

    def run(self):
        try:
            debug_exec_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_dir = os.path.join("debug", debug_exec_id)
            os.makedirs(debug_dir, exist_ok=True)
            logger.debug(f"[Worker] Debug folder created: {debug_dir}")

            threshold_fill = self.config.get("threshold_fill", 0.3)
            if "grid_rois" not in self.config:
                msg = "Configuração 'grid_rois' não encontrada."
                self.signals.error.emit(msg)
                logger.error(msg)
                self.signals.finished.emit([])
                return

            grid_rois = self.config["grid_rois"]
            pdf_count = len(self.pdf_paths)
            passo = 80 // max(pdf_count, 1)
            all_pages = []

            for idx, pdf_path in enumerate(self.pdf_paths):
                nome_pdf = os.path.basename(pdf_path)
                logger.debug(f"[Worker] Converting {nome_pdf} at DPI {self.dpi_escolhido}")
                imagens = converter_pdf_em_imagens(pdf_path, dpi=self.dpi_escolhido)
                if not imagens:
                    msg = f"Falha ao converter PDF: {nome_pdf}"
                    self.signals.error.emit(msg)
                    logger.error(msg)
                    continue

                # Guarda cópia das imagens originais para debug e extração da matrícula
                imagens_originais = list(imagens)

                pts_ref = None
                if "template_path" in self.config:
                    try:
                        template = Image.open(self.config["template_path"])
                        pts_ref, score = detectar_area_gabarito_template(imagens[0], template)
                        logger.debug(f"[Worker] Template gabarito score: {score:.2f}")
                        if score < 0.5:
                            aviso = f"Baixa confiança no template gabarito (score={score:.2f})"
                            self.signals.message.emit(aviso)
                            logger.debug(aviso)
                    except Exception as e:
                        logger.error(f"Template matching do gabarito failed: {e}")
                        self.signals.message.emit(f"Aviso: falha no template gabarito: {e}")
                elif "pts_ref" in self.config:
                    pts_ref = self.config["pts_ref"]

                if pts_ref:
                    larg = self.config.get("largura_corrigida", 800)
                    alt = self.config.get("altura_corrigida", 1200)
                    imagens_corrigidas = []
                    for pil_img in imagens:
                        np_img = np.array(pil_img)
                        corr = corrigir_perspectiva(np_img, pts_ref, larg, alt)
                        imagens_corrigidas.append(Image.fromarray(corr))
                    imagens = imagens_corrigidas
                    logger.debug(f"[Worker] Perspective corrected for {nome_pdf}")

                for i, pil_img_corrigida in enumerate(imagens):
                    debug_subdir = os.path.join(debug_dir, f"{nome_pdf}_pag_{i+1}")
                    os.makedirs(debug_subdir, exist_ok=True)
                    logger.debug(f"[Worker] Processing page {i+1} of {nome_pdf}")

                    # Salva a página completa original para debug
                    debug_full_page = os.path.join(debug_subdir, "debug_full_page_original.png")
                    imagens_originais[i].save(debug_full_page)
                    logger.debug(f"[Worker] Full original page saved: {debug_full_page}")

                    respostas = detectar_respostas_por_grid(
                        imagem=pil_img_corrigida,
                        grid_rois=grid_rois,
                        num_alternativas=self.n_alternativas,
                        threshold_fill=threshold_fill,
                        debug=False, 
                        debug_folder=debug_subdir
                    )
                    respostas_ordenadas = {}
                    questoes_sorted = sorted(respostas.keys(), key=lambda x: int(x.split()[1]))
                    for q in questoes_sorted:
                        respostas_ordenadas[q] = respostas[q]

                    info_ocr = extrair_info_ocr(pil_img_corrigida)

                    pil_img_original = imagens_originais[i]
                    matricula_texto = ""
                    dados_api = {}
                    if "matricula_roi" in self.config:
                        from pytesseract import image_to_string, Output
                        try:
                            x, y, w, h = self.config["matricula_roi"].values()
                            roi_matricula = pil_img_original.crop((x, y, x+w, y+h))
                            if self.config.get("scanned_by_printer", True):
                                roi_matricula = preprocess_roi(roi_matricula)
                            config_tess = r"--psm 7 -c tessedit_char_whitelist=0123456789"
                            matricula_texto = image_to_string(roi_matricula, config=config_tess, output_type=Output.STRING).strip()
                            logger.info(f"[Worker] Matrícula (ROI fixa) lida: '{matricula_texto}'")
                            if not matricula_texto.isdigit():
                                logger.warning(f"[Worker] Matrícula extraída inválida (ROI fixa): '{matricula_texto}'")
                        except Exception as e:
                            logger.error(f"Erro na extração da matrícula (ROI fixa): {e}")
                            self.signals.message.emit(f"Aviso: falha ao extrair matrícula da ROI fixa: {e}")
                    elif "matricula_template_path" in self.config:
                        from pytesseract import image_to_string, Output
                        from modules.core.detector import detectar_area_cabecalho_template
                        try:
                            temp_cab = Image.open(self.config["matricula_template_path"])
                            pil_img_gray = pil_img_original.convert("L")
                            img_gray_np = np.array(pil_img_gray)
                            img_gray_eq = cv2.equalizeHist(img_gray_np)
                            pil_img_eq = Image.fromarray(img_gray_eq)

                            template_gray = np.array(temp_cab.convert("L"))
                            logger.debug(f"[DEBUG] Tamanho da imagem equalizada: {img_gray_eq.shape}, tamanho do template: {template_gray.shape}")
                            
                            if template_gray.shape[0] > img_gray_eq.shape[0] or template_gray.shape[1] > img_gray_eq.shape[1]:
                                scale = min(img_gray_eq.shape[0] / template_gray.shape[0], img_gray_eq.shape[1] / template_gray.shape[1])
                                new_size = (int(template_gray.shape[1] * scale), int(template_gray.shape[0] * scale))
                                logger.debug(f"[DEBUG] Redimensionando template para: {new_size}")
                                temp_cab = temp_cab.resize(new_size)
                                template_gray = np.array(temp_cab.convert("L"))
                            
                            pts_cab, score_cab = detectar_area_cabecalho_template(pil_img_eq, temp_cab)
                            logger.debug(f"[DEBUG] Score do template matching do cabeçalho: {score_cab:.2f}")
                            logger.debug(f"[DEBUG] Pontos do cabeçalho encontrados: {pts_cab}")
                            
                            xs = [p[0] for p in pts_cab]
                            ys = [p[1] for p in pts_cab]
                            x_min, x_max = min(xs), max(xs)
                            y_min, y_max = min(ys), max(ys)
                            
                            debug_roi_path = os.path.join(debug_subdir, "debug_matricula_roi_template.png")
                            pil_img_original.crop((x_min, y_min, x_max, y_max)).save(debug_roi_path)
                            logger.debug(f"[DEBUG] ROI da matrícula (template) salva: {debug_roi_path}")
                            
                            thr_cab = self.config.get("matricula_template_threshold", 0.5)
                            if score_cab >= thr_cab:
                                roi_matricula = pil_img_original.crop((x_min, y_min, x_max, y_max))
                                debug_roi_ocr_path = os.path.join(debug_subdir, "debug_matricula_roi_used.png")
                                roi_matricula.save(debug_roi_ocr_path)
                                logger.debug(f"[DEBUG] ROI for OCR saved: {debug_roi_ocr_path}")
                                
                                if self.config.get("scanned_by_printer", False):
                                    roi_matricula = preprocess_roi(roi_matricula)
                                config_tess = r"--psm 7 -c tessedit_char_whitelist=0123456789"
                                matricula_texto = image_to_string(roi_matricula, config=config_tess, output_type=Output.STRING).strip()
                                logger.info(f"[Worker] Matrícula (template-cabeçalho) lida: '{matricula_texto}'")
                                if not matricula_texto.isdigit():
                                    logger.warning(f"[Worker] Matrícula extraída inválida (template-cabeçalho): '{matricula_texto}'")
                            else:
                                aviso = f"Cabeçalho (matrícula) não encontrado (score={score_cab:.2f})"
                                self.signals.message.emit(aviso)
                                logger.warning(aviso)
                        except Exception as e:
                            logger.error(f"Erro no template de cabeçalho/matrícula: {e}")
                            self.signals.message.emit(f"Aviso: falha ao usar template_cabecalho: {e}")

                    if matricula_texto.isdigit():
                        logger.info(f"[Worker] Buscando estudante para matrícula {matricula_texto}")
                        try:
                            dados_api = buscar_estudante(matricula_texto)
                            logger.info(f"[Worker] API returned for {matricula_texto}: {dados_api}")
                            if dados_api:
                                info_ocr["nome_aluno"] = dados_api.get("name", info_ocr.get("nome_aluno", ""))
                                info_ocr["escola"] = dados_api.get("school", info_ocr.get("escola", ""))
                                info_ocr["turma"] = dados_api.get("class", info_ocr.get("turma", ""))
                            else:
                                logger.debug(f"[Worker] API não retornou dados para matrícula {matricula_texto}")
                        except Exception as e:
                            logger.error(f"Erro na busca do estudante: {e}")
                            self.signals.message.emit(f"Aviso: falha ao buscar estudante: {e}")

                    page_dict = {
                        "Página": f"PDF {idx+1} Pag {i+1}",
                        "Arquivo": nome_pdf,
                        "PreviewImage": pil_img_corrigida,
                        "Respostas": respostas_ordenadas,
                        "OCR": {
                            "nome_aluno": info_ocr.get("nome_aluno", ""),
                            "escola": info_ocr.get("escola", ""),
                            "turma": info_ocr.get("turma", ""),
                            "matricula": matricula_texto,
                            "dados_api": dados_api
                        }
                    }
                    all_pages.append(page_dict)

                self.signals.progress.emit((idx+1) * passo)

            self.signals.finished.emit(all_pages)

        except Exception as e:
            logger.error(f"Erro no Worker: {e}", exc_info=True)
            self.signals.error.emit(str(e))
            self.signals.finished.emit([])
