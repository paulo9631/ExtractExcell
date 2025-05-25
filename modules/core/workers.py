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
    detectar_area_cabecalho_template,
    pre_processar_imagem
)
from modules.core.text_extractor import extrair_info_ocr, extrair_matricula, extrair_matricula_avancado
from modules.core.student_api import StudentAPIClient
from modules.core.detector_matricula import DetectorMatricula
from modules.utils import logger
from modules.DB.operations import buscar_por_matricula_excel


class WorkerSignals(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)
    message = pyqtSignal(str)
    error = pyqtSignal(str)

def preprocess_roi(roi_pil):
    """
    Enhanced ROI preprocessing specifically optimized for printer-scanned documents.
    Applies multiple techniques to improve digit recognition accuracy.
    """
    roi_gray = np.array(roi_pil.convert("L"))
    
    # Step 1: Advanced noise reduction for printer artifacts
    # Bilateral filter to preserve edges while removing noise
    roi_gray = cv2.bilateralFilter(roi_gray, 9, 75, 75)
    
    # Non-local means denoising for repetitive printer patterns
    roi_gray = cv2.fastNlMeansDenoising(roi_gray, None, 10, 7, 21)
    
    # Step 2: Enhanced contrast improvement
    # Multi-scale CLAHE for better local contrast
    clahe1 = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    clahe2 = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
    
    roi_clahe1 = clahe1.apply(roi_gray)
    roi_clahe2 = clahe2.apply(roi_gray)
    
    # Combine different CLAHE results
    roi_enhanced = cv2.addWeighted(roi_clahe1, 0.7, roi_clahe2, 0.3, 0)
    
    # Step 3: Sharpening to improve digit clarity
    kernel_sharpen = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    roi_enhanced = cv2.filter2D(roi_enhanced, -1, kernel_sharpen)
    
    # Step 4: Advanced binarization
    # Multiple threshold methods
    _, thresh_otsu = cv2.threshold(roi_enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    thresh_adaptive = cv2.adaptiveThreshold(
        roi_enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    # Triangle method (good for printer scans)
    _, thresh_triangle = cv2.threshold(roi_enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_TRIANGLE)
    
    # Combine thresholding methods using weighted average
    combined = cv2.addWeighted(thresh_otsu, 0.4, thresh_adaptive, 0.4, 0)
    combined = cv2.addWeighted(combined, 0.8, thresh_triangle, 0.2, 0)
    
    # Step 5: Enhanced morphological operations
    # Remove small noise
    kernel_noise = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel_noise)
    
    # Connect broken characters (common in printer scans)
    kernel_connect_h = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 1))
    kernel_connect_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 2))
    
    combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel_connect_h)
    combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel_connect_v)
    
    # Fill small holes in digits
    kernel_fill = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel_fill)
    
    return Image.fromarray(combined)

def preprocess_roi_avancado(roi_pil, debug_folder=None, idx=0):
    """
    Advanced ROI preprocessing with multiple enhancement techniques.
    Specifically designed for challenging printer-scanned documents.
    """
    # Convert to grayscale
    roi_gray = np.array(roi_pil.convert("L"))
    
    # Enhanced preprocessing pipeline with multiple approaches
    processed_versions = {}
    
    # Version 1: Standard enhanced processing
    roi_standard = roi_gray.copy()
    
    # Noise reduction
    roi_standard = cv2.bilateralFilter(roi_standard, 11, 17, 17)
    roi_standard = cv2.fastNlMeansDenoising(roi_standard, None, 10, 7, 21)
    
    # Contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
    roi_standard = clahe.apply(roi_standard)
    
    # Binarization
    _, roi_standard_bin = cv2.threshold(roi_standard, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    processed_versions['standard'] = roi_standard_bin
    
    # Version 2: High contrast processing
    roi_high_contrast = roi_gray.copy()
    
    # Extreme contrast enhancement
    clahe_extreme = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(2, 2))
    roi_high_contrast = clahe_extreme.apply(roi_high_contrast)
    
    # Aggressive sharpening
    kernel_sharp = np.array([[-1,-1,-1,-1,-1],
                            [-1,2,2,2,-1],
                            [-1,2,8,2,-1],
                            [-1,2,2,2,-1],
                            [-1,-1,-1,-1,-1]]) / 8.0
    roi_high_contrast = cv2.filter2D(roi_high_contrast, -1, kernel_sharp)
    
    # Binarization
    _, roi_high_contrast_bin = cv2.threshold(roi_high_contrast, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    processed_versions['high_contrast'] = roi_high_contrast_bin
    
    # Version 3: Morphological enhancement
    roi_morph = processed_versions['high_contrast'].copy()
    
    # Connect broken digits
    kernel_connect_h = cv2.getStructuringElement(cv2.MORPH_RECT, (4, 1))
    kernel_connect_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3))
    
    roi_morph = cv2.morphologyEx(roi_morph, cv2.MORPH_CLOSE, kernel_connect_h)
    roi_morph = cv2.morphologyEx(roi_morph, cv2.MORPH_CLOSE, kernel_connect_v)
    
    # Fill holes in digits
    kernel_fill = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    roi_morph = cv2.morphologyEx(roi_morph, cv2.MORPH_CLOSE, kernel_fill)
    
    # Clean up noise
    kernel_clean = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    roi_morph = cv2.morphologyEx(roi_morph, cv2.MORPH_OPEN, kernel_clean)
    
    processed_versions['morphological'] = roi_morph
    
    # Version 4: Edge-enhanced processing
    roi_edges = cv2.Canny(roi_gray, 30, 100)
    roi_edges_dilated = cv2.dilate(roi_edges, np.ones((2,2), np.uint8), iterations=1)
    roi_edge_enhanced = cv2.bitwise_or(processed_versions['high_contrast'], roi_edges_dilated)
    processed_versions['edge_enhanced'] = roi_edge_enhanced
    
    # Version 5: Combined approach
    # Combine the best aspects of different methods
    combined = cv2.bitwise_and(processed_versions['standard'], processed_versions['high_contrast'])
    
    # Apply final morphological operations
    kernel_final = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel_final)
    combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel_final)
    
    processed_versions['combined'] = combined
    
    # Save debug versions if requested
    if debug_folder:
        os.makedirs(debug_folder, exist_ok=True)
        for name, img in processed_versions.items():
            debug_path = os.path.join(debug_folder, f"matricula_{name}_{idx}.png")
            cv2.imwrite(debug_path, img)
    
    # Return the combined version as it typically performs best
    return Image.fromarray(processed_versions['combined'])

class ProcessWorker(QRunnable):
    def __init__(self, pdf_paths, config, n_alternativas, dpi_escolhido, client: StudentAPIClient):
        super().__init__()
        self.pdf_paths = pdf_paths
        self.config = config
        self.n_alternativas = n_alternativas
        self.dpi_escolhido = dpi_escolhido
        self.client = client
        self.signals = WorkerSignals()
        self.detector_matricula = DetectorMatricula(config)

    def extrair_matricula_com_multiplas_estrategias(self, imagem_original, debug_subdir):
        """
        Enhanced multi-strategy student ID extraction with improved accuracy for printer scans.
        """
        # Use the enhanced DetectorMatricula for better accuracy
        if self.config.get("scanned_by_printer", False):
            # For printer-scanned documents, use specialized method
            matricula, confianca = self.detector_matricula.extrair_matricula_scaneada(imagem_original, debug_subdir)
            if matricula:
                logger.info(f"[Worker] Matrícula (scanner especializado enhanced) lida: '{matricula}' (conf: {confianca:.2f})")
                return matricula
        
        # Enhanced standard method
        resultado = self.detector_matricula.processar_documento(imagem_original, debug_subdir)
        matricula = resultado["matricula"]
        
        if matricula:
            logger.info(f"[Worker] Matrícula (detector enhanced) lida: '{matricula}' (conf: {resultado['confianca']:.2f})")
            return matricula
        
        # Enhanced fallback methods
        logger.info("[Worker] Detector não encontrou matrícula, tentando métodos enhanced...")
        
        from modules.core.text_extractor import extrair_matricula_com_multiplas_estrategias
        
        # Use the enhanced multi-strategy extraction
        matricula_enhanced = extrair_matricula_com_multiplas_estrategias(
            imagem_original, self.config, debug_subdir
        )
        
        if matricula_enhanced:
            logger.info(f"[Worker] Matrícula (estratégias enhanced) lida: '{matricula_enhanced}'")
            return matricula_enhanced
        
        # Final fallback with advanced preprocessing
        logger.info("[Worker] Tentando fallback final com pré-processamento avançado...")
        
        try:
            # Apply advanced preprocessing to entire image
            from modules.core.text_extractor import pre_processar_imagem_ocr_avancado
            img_processed = pre_processar_imagem_ocr_avancado(imagem_original)
            
            if debug_subdir:
                img_processed.save(os.path.join(debug_subdir, "fallback_processed.png"))
            
            # Try advanced extraction on processed image
            matricula_fallback = extrair_matricula_avancado(
                img_processed, 
                pre_processar=False,  # Already preprocessed
                tentativas_multiplas=True, 
                debug_folder=debug_subdir
            )
            
            if matricula_fallback:
                logger.info(f"[Worker] Matrícula (fallback avançado) lida: '{matricula_fallback}'")
                return matricula_fallback
                
        except Exception as e:
            logger.error(f"Erro no fallback avançado: {e}")
        
        return ""

    def run(self):
        try:
            # Enhanced debug setup
            debug_exec_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_dir = os.path.join("debug", debug_exec_id)
            os.makedirs(debug_dir, exist_ok=True)
            logger.debug(f"[Worker] Enhanced debug folder created: {debug_dir}")

            # Enhanced threshold for printer scans
            threshold_fill = self.config.get("threshold_fill", 0.25)  # Lower threshold for printer scans
            
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
                logger.debug(f"[Worker] Converting {nome_pdf} at enhanced DPI {self.dpi_escolhido}")
                
                # Enhanced DPI for better quality if printer scan detected
                dpi_used = self.dpi_escolhido
                if self.config.get("scanned_by_printer", False):
                    dpi_used = max(self.dpi_escolhido, 200)  # Minimum 200 DPI for printer scans
                    logger.debug(f"[Worker] Using enhanced DPI {dpi_used} for printer scan")
                
                imagens = converter_pdf_em_imagens(pdf_path, dpi=dpi_used)
                if not imagens:
                    msg = f"Falha ao converter PDF: {nome_pdf}"
                    self.signals.error.emit(msg)
                    logger.error(msg)
                    continue

                # Store original images for debug and student ID extraction
                imagens_originais = list(imagens)

                # Enhanced template matching
                pts_ref = None
                if "template_path" in self.config:
                    try:
                        template = Image.open(self.config["template_path"])
                        
                        # Enhanced preprocessing for template matching
                        imagem_proc = pre_processar_imagem(
                            imagens[0], 
                            equalizar=True, 
                            ajustar_contraste=True, 
                            remover_ruido=True
                        )
                        
                        # Enhanced template detection with multiple scales and rotations
                        pts_ref, score = detectar_area_gabarito_template(
                            imagem_proc, template, 
                            pre_processar=True, 
                            multi_escala=True,
                            rotacoes=True
                        )
                        
                        logger.debug(f"[Worker] Enhanced template gabarito score: {score:.2f}")
                        
                        # Lower threshold for printer scans
                        min_score = 0.4 if self.config.get("scanned_by_printer", False) else 0.5
                        
                        if score < min_score:
                            aviso = f"Baixa confiança no template gabarito (score={score:.2f})"
                            self.signals.message.emit(aviso)
                            logger.debug(aviso)
                            
                    except Exception as e:
                        logger.error(f"Enhanced template matching failed: {e}")
                        self.signals.message.emit(f"Aviso: falha no template gabarito enhanced: {e}")
                        
                elif "pts_ref" in self.config:
                    pts_ref = self.config["pts_ref"]

                # Enhanced perspective correction
                if pts_ref:
                    larg = self.config.get("largura_corrigida", 800)
                    alt = self.config.get("altura_corrigida", 1200)
                    imagens_corrigidas = []
                    
                    for pil_img in imagens:
                        np_img = np.array(pil_img)
                        
                        # Enhanced perspective correction with interpolation
                        corr = corrigir_perspectiva(np_img, pts_ref, larg, alt)
                        
                        # Apply additional enhancement for printer scans
                        if self.config.get("scanned_by_printer", False):
                            # Additional sharpening after perspective correction
                            kernel_sharpen = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
                            corr = cv2.filter2D(corr, -1, kernel_sharpen)
                            
                            # Noise reduction
                            corr = cv2.bilateralFilter(corr, 5, 50, 50)
                        
                        imagens_corrigidas.append(Image.fromarray(corr))
                        
                    imagens = imagens_corrigidas
                    logger.debug(f"[Worker] Enhanced perspective correction applied for {nome_pdf}")

                # Process each page with enhanced methods
                for i, pil_img_corrigida in enumerate(imagens):
                    debug_subdir = os.path.join(debug_dir, f"{nome_pdf}_pag_{i+1}")
                    os.makedirs(debug_subdir, exist_ok=True)
                    logger.debug(f"[Worker] Processing page {i+1} of {nome_pdf} with enhanced methods")

                    # Save enhanced debug images
                    debug_full_page = os.path.join(debug_subdir, "debug_full_page_original.png")
                    imagens_originais[i].save(debug_full_page)
                    
                    debug_corrected_page = os.path.join(debug_subdir, "debug_full_page_corrected.png")
                    pil_img_corrigida.save(debug_corrected_page)
                    
                    logger.debug(f"[Worker] Enhanced debug images saved for page {i+1}")

                    # Enhanced answer detection
                    respostas = detectar_respostas_por_grid(
                        imagem=pil_img_corrigida,
                        grid_rois=grid_rois,
                        num_alternativas=self.n_alternativas,
                        threshold_fill=threshold_fill,
                        debug=True, 
                        debug_folder=debug_subdir
                    )
                    
                    # Sort answers
                    respostas_ordenadas = {}
                    questoes_sorted = sorted(respostas.keys(), key=lambda x: int(x.split()[1]))
                    for q in questoes_sorted:
                        respostas_ordenadas[q] = respostas[q]

                    # Enhanced OCR information extraction
                    info_ocr = extrair_info_ocr(pil_img_corrigida)

                    # Enhanced student ID extraction using original image
                    pil_img_original = imagens_originais[i]
                    
                    # Use enhanced multi-strategy extraction
                    matricula_texto = self.extrair_matricula_com_multiplas_estrategias(
                        pil_img_original, debug_subdir
                    )
                    
                    # Enhanced API and database lookup
                    dados_api = {}
                    if matricula_texto.isdigit():
                        logger.info(f"[Worker] Buscando estudante para matrícula {matricula_texto} (enhanced)")
                        try:
                            # Enhanced API search with retry mechanism
                            resultado = self.client.buscar_por_matriculas([matricula_texto])
                            dados_api = resultado[0] if resultado else {}
                            
                            if dados_api:
                                logger.info(f"[Worker] Dados API encontrados: {dados_api}")
                            else:
                                logger.info(f"[Worker] API não retornou dados para matrícula {matricula_texto}")
                                
                        except Exception as e:
                            logger.warning(f"[Worker] Erro ao buscar na API: {e}")
                            dados_api = {}

                        # Enhanced local database fallback
                        if not dados_api:
                            logger.info(f"[Worker] API não encontrou matrícula {matricula_texto}. Buscando localmente...")
                            try:
                                aluno_local = buscar_por_matricula_excel(matricula_texto)
                                if aluno_local:
                                    dados_api = {
                                        "name": aluno_local.nome,
                                        "school": aluno_local.escola,
                                        "class": aluno_local.turma,
                                        "turn": aluno_local.turno,
                                        "birthDate": aluno_local.data_nascimento
                                    }
                                    logger.info(f"[Worker] Dados locais encontrados: {dados_api}")
                                else:
                                    logger.info(f"[Worker] Matrícula {matricula_texto} não encontrada localmente")
                            except Exception as e:
                                logger.error(f"[Worker] Erro ao buscar localmente: {e}")

                        # Enhanced data integration
                        if dados_api:
                            info_ocr["nome_aluno"] = dados_api.get("name", info_ocr.get("nome_aluno", ""))
                            info_ocr["escola"] = dados_api.get("school", info_ocr.get("escola", ""))
                            info_ocr["turma"] = dados_api.get("class", info_ocr.get("turma", ""))
                            info_ocr["turno"] = dados_api.get("turn", "")
                            info_ocr["data_nascimento"] = dados_api.get("birthDate", "")
                    else:
                        logger.warning(f"[Worker] Matrícula inválida ou não encontrada: '{matricula_texto}'")

                    # Enhanced page data structure
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
                        },
                        "ProcessingInfo": {
                            "dpi_used": dpi_used,
                            "threshold_fill": threshold_fill,
                            "template_score": score if 'score' in locals() else 0.0,
                            "printer_scan_mode": self.config.get("scanned_by_printer", False)
                        }
                    }
                    all_pages.append(page_dict)
                    
                    logger.debug(f"[Worker] Page {i+1} processing completed successfully")

                # Update progress
                self.signals.progress.emit((idx+1) * passo)
                logger.debug(f"[Worker] PDF {idx+1}/{pdf_count} completed")

            # Final processing summary
            logger.info(f"[Worker] Enhanced processing completed. Total pages: {len(all_pages)}")
            self.signals.finished.emit(all_pages)

        except Exception as e:
            logger.error(f"Enhanced Worker error: {e}", exc_info=True)
            self.signals.error.emit(str(e))
            self.signals.finished.emit([])
