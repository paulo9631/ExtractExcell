import os
from datetime import datetime
import numpy as np
from PIL import Image

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from modules.core.converter import converter_pdf_em_imagens
from modules.core.detector import (
    detectar_respostas_por_grid,
    corrigir_perspectiva,
    detectar_area_gabarito_template
)
from .text_extractor import extrair_info_ocr
from ..utils import logger


class WorkerSignals(QObject):
    """Sinais para comunicar progresso/resultado/erros do worker."""
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)
    message = pyqtSignal(str)
    error = pyqtSignal(str)


class ProcessWorker(QRunnable):
    """
    Faz o processamento em background, incluindo:
     - Converter PDFs em imagens
     - (Opcional) Template matching e correção de perspectiva
     - Detecção das respostas e OCR
     - Ordena e retorna
    """
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
            logger.info(f"[Worker] Pasta debug: {debug_dir}")

            threshold_fill = self.config.get("threshold_fill", 0.3)
            if "grid_rois" not in self.config:
                self.signals.error.emit("Configuração 'grid_rois' não encontrada.")
                self.signals.finished.emit([])
                return

            grid_rois = self.config["grid_rois"]
            pdf_count = len(self.pdf_paths)
            passo = 80 // max(pdf_count, 1)

            all_pages = []

            for idx, pdf_path in enumerate(self.pdf_paths):
                self.signals.message.emit(
                    f"Processando PDF {idx+1}/{pdf_count}: {os.path.basename(pdf_path)}"
                )
                imagens = converter_pdf_em_imagens(pdf_path, dpi=self.dpi_escolhido)
                if not imagens:
                    self.signals.error.emit(f"Falha ao converter PDF: {os.path.basename(pdf_path)}")
                    continue

                # Tentar template matching
                pts_ref = None
                if "template_path" in self.config:
                    try:
                        template = Image.open(self.config["template_path"])
                        pts_ref, score = detectar_area_gabarito_template(imagens[0], template)
                        logger.info(f"Template matching: pts_ref={pts_ref}, score={score:.2f}")
                        if score < 0.5:
                            self.signals.message.emit(
                                f"Aviso: Baixa confiança no template (score={score:.2f})"
                            )
                    except Exception as e:
                        logger.error(f"Template matching falhou: {e}")
                        self.signals.message.emit("Aviso: falha no template matching")
                elif "pts_ref" in self.config:
                    pts_ref = self.config["pts_ref"]

                # Corrigir perspectiva (se houver)
                if pts_ref:
                    larg = self.config.get("largura_corrigida", 800)
                    alt = self.config.get("altura_corrigida", 1200)
                    novas = []
                    for i, pil_img in enumerate(imagens):
                        np_img = np.array(pil_img)
                        corr = corrigir_perspectiva(np_img, pts_ref, larg, alt)
                        pil_corr = Image.fromarray(corr)
                        novas.append(pil_corr)
                    imagens = novas

                # Processar cada página
                for i, pil_img in enumerate(imagens):
                    debug_subdir = os.path.join(debug_dir, f"pdf_{idx+1}_pagina_{i+1}")
                    os.makedirs(debug_subdir, exist_ok=True)

                    respostas = detectar_respostas_por_grid(
                        imagem=pil_img,
                        grid_rois=grid_rois,
                        num_alternativas=self.n_alternativas,
                        threshold_fill=threshold_fill,
                        debug=False,
                        debug_folder=debug_subdir
                    )

                    # Ordenar as chaves "Questao X" por número X
                    respostas_ordenadas = {}
                    questoes_sorted = sorted(respostas.keys(),
                                             key=lambda x: int(x.split()[1]))
                    for q in questoes_sorted:
                        respostas_ordenadas[q] = respostas[q]

                    info_ocr = extrair_info_ocr(pil_img)

                    page_dict = {
                        "Página": f"PDF {idx+1} Pag {i+1}",
                        "Arquivo": os.path.basename(pdf_path),
                        "PreviewImage": pil_img,
                        "Respostas": respostas_ordenadas,
                        "OCR": info_ocr
                    }
                    all_pages.append(page_dict)

                self.signals.progress.emit((idx+1)*passo)

            self.signals.finished.emit(all_pages)

        except Exception as e:
            logger.error(f"Erro no Worker: {e}", exc_info=True)
            self.signals.error.emit(str(e))
            self.signals.finished.emit([])
