import os
from datetime import datetime
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

                # Guarda uma cópia da imagem original para debug e extração da matrícula
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
                        debug=False,  # Não polui o cmd com logs de ROI
                        debug_folder=debug_subdir
                    )
                    respostas_ordenadas = {}
                    questoes_sorted = sorted(respostas.keys(), key=lambda x: int(x.split()[1]))
                    for q in questoes_sorted:
                        respostas_ordenadas[q] = respostas[q]

                    info_ocr = extrair_info_ocr(pil_img_corrigida)

                    pil_img_original = imagens_originais[i]
                    matricula_texto = ""
                    if "matricula_roi" in self.config:
                        from pytesseract import image_to_string, Output
                        try:
                            x, y, w, h = self.config["matricula_roi"].values()
                            roi_matricula = pil_img_original.crop((x, y, x+w, y+h))
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
                            img_gray = np.array(pil_img_original.convert("L"))
                            template_gray = np.array(temp_cab.convert("L"))
                            logger.debug(f"[DEBUG] Original image size: {img_gray.shape}, Template size: {template_gray.shape}")
                            
                            if template_gray.shape[0] > img_gray.shape[0] or template_gray.shape[1] > img_gray.shape[1]:
                                scale = min(img_gray.shape[0] / template_gray.shape[0], img_gray.shape[1] / template_gray.shape[1])
                                new_size = (int(template_gray.shape[1] * scale), int(template_gray.shape[0] * scale))
                                logger.debug(f"[DEBUG] Resizing template to: {new_size}")
                                temp_cab = temp_cab.resize(new_size)
                                template_gray = np.array(temp_cab.convert("L"))
                            
                            pts_cab, score_cab = detectar_area_cabecalho_template(pil_img_original, temp_cab)
                            logger.debug(f"[DEBUG] Template matching score (header): {score_cab:.2f}")
                            logger.debug(f"[DEBUG] Header points: {pts_cab}")
                            
                            xs = [p[0] for p in pts_cab]
                            ys = [p[1] for p in pts_cab]
                            x_min, x_max = min(xs), max(xs)
                            y_min, y_max = min(ys), max(ys)
                            
                            # Salva a ROI calculada para debug
                            debug_roi_path = os.path.join(debug_subdir, "debug_matricula_roi_template.png")
                            pil_img_original.crop((x_min, y_min, x_max, y_max)).save(debug_roi_path)
                            logger.debug(f"[DEBUG] ROI da matrícula (template) saved: {debug_roi_path}")
                            
                            thr_cab = self.config.get("matricula_template_threshold", 0.5)
                            if score_cab >= thr_cab:
                                roi_matricula = pil_img_original.crop((x_min, y_min, x_max, y_max))
                                # Salva a ROI que será utilizada para o OCR
                                debug_roi_ocr_path = os.path.join(debug_subdir, "debug_matricula_roi_used.png")
                                roi_matricula.save(debug_roi_ocr_path)
                                logger.debug(f"[DEBUG] ROI for OCR saved: {debug_roi_ocr_path}")
                                
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
                            "dados_api": {}  # dados_api já processados acima
                        }
                    }
                    all_pages.append(page_dict)

                self.signals.progress.emit((idx+1) * passo)

            self.signals.finished.emit(all_pages)

        except Exception as e:
            logger.error(f"Erro no Worker: {e}", exc_info=True)
            self.signals.error.emit(str(e))
            self.signals.finished.emit([])
