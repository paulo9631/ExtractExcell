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
    detectar_matricula_por_contornos,
    detectar_matricula_por_hough,
    pre_processar_imagem
)
from modules.core.text_extractor import extrair_info_ocr, extrair_matricula, extrair_matricula_avancado
from modules.core.student_api import buscar_estudante
from modules.core.detector_matricula import DetectorMatricula
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
    
    # Aplica blur para reduzir ruído
    roi_gray = cv2.GaussianBlur(roi_gray, (3, 3), 0)
    
    # Equalização de histograma
    roi_eq = cv2.equalizeHist(roi_gray)
    
    # CLAHE para melhorar ainda mais o contraste
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    roi_eq = clahe.apply(roi_eq)
    
    # Threshold adaptativo
    roi_bin = cv2.adaptiveThreshold(
        roi_eq, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    return Image.fromarray(roi_bin)

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
    # Converte para escala de cinza
    roi_gray = np.array(roi_pil.convert("L"))
    
    # Versão 1: Equalização de histograma + blur
    roi_eq = cv2.equalizeHist(roi_gray)
    roi_eq = cv2.GaussianBlur(roi_eq, (3, 3), 0)
    
    # Versão 2: CLAHE para melhorar o contraste local
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    roi_clahe = clahe.apply(roi_gray)
    
    # Versão 3: Binarização com Otsu
    _, roi_bin = cv2.threshold(roi_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Versão 4: Binarização adaptativa
    roi_bin_adapt = cv2.adaptiveThreshold(
        roi_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    # Versão 5: Binarização adaptativa + operações morfológicas
    kernel = np.ones((2, 2), np.uint8)
    roi_morph = cv2.morphologyEx(roi_bin_adapt, cv2.MORPH_CLOSE, kernel)
    roi_morph = cv2.morphologyEx(roi_morph, cv2.MORPH_OPEN, kernel)
    
    # Salva as versões para debug
    if debug_folder:
        cv2.imwrite(os.path.join(debug_folder, f"matricula_eq_{idx}.png"), roi_eq)
        cv2.imwrite(os.path.join(debug_folder, f"matricula_clahe_{idx}.png"), roi_clahe)
        cv2.imwrite(os.path.join(debug_folder, f"matricula_bin_{idx}.png"), roi_bin)
        cv2.imwrite(os.path.join(debug_folder, f"matricula_bin_adapt_{idx}.png"), roi_bin_adapt)
        cv2.imwrite(os.path.join(debug_folder, f"matricula_morph_{idx}.png"), roi_morph)
    
    # Retorna a versão que geralmente funciona melhor para OCR de dígitos
    return Image.fromarray(roi_morph)

class ProcessWorker(QRunnable):
    def __init__(self, pdf_paths, config, n_alternativas, dpi_escolhido):
        super().__init__()
        self.pdf_paths = pdf_paths
        self.config = config
        self.n_alternativas = n_alternativas
        self.dpi_escolhido = dpi_escolhido
        self.signals = WorkerSignals()
        # Inicializa o detector de matrículas
        self.detector_matricula = DetectorMatricula(config)

    def extrair_matricula_com_multiplas_estrategias(self, imagem_original, debug_subdir):
        """
        Tenta extrair a matrícula usando o DetectorMatricula melhorado.
        
        Args:
            imagem_original: Imagem PIL original
            debug_subdir: Diretório para salvar imagens de debug
            
        Returns:
            Texto da matrícula extraído
        """
        # Usa o detector de matrículas melhorado
        if self.config.get("scanned_by_printer", False):
            # Para documentos escaneados, usa o método especializado
            matricula, confianca = self.detector_matricula.extrair_matricula_scaneada(imagem_original, debug_subdir)
            if matricula:
                logger.info(f"[Worker] Matrícula (scanner especializado) lida: '{matricula}' (conf: {confianca:.2f})")
                return matricula
        
        # Método padrão para outros tipos de documentos
        resultado = self.detector_matricula.processar_documento(imagem_original, debug_subdir)
        matricula = resultado["matricula"]
        
        if matricula:
            logger.info(f"[Worker] Matrícula (detector) lida: '{matricula}' (conf: {resultado['confianca']:.2f}, tipo: {resultado['tipo']})")
            return matricula
        
        # Fallback para o método antigo se o detector não encontrou nada
        logger.info("[Worker] Detector não encontrou matrícula, tentando método antigo...")
        
        from pytesseract import image_to_string, Output
        
        resultados = []
        
        # Estratégia 1: Usar ROI fixa se configurada
        if "matricula_roi" in self.config:
            try:
                x, y, w, h = self.config["matricula_roi"].values()
                roi_matricula = imagem_original.crop((x, y, x+w, y+h))
                
                # Aplica pré-processamento avançado
                roi_processada = preprocess_roi_avancado(roi_matricula, debug_subdir, 1)
                
                # Salva a ROI processada para debug
                roi_processada.save(os.path.join(debug_subdir, "matricula_roi_processada_1.png"))
                
                # Configuração específica para dígitos
                config_tess = r"--psm 7 -c tessedit_char_whitelist=0123456789"
                matricula = image_to_string(roi_processada, config=config_tess, output_type=Output.STRING).strip()
                matricula = ''.join(c for c in matricula if c.isdigit())
                
                logger.info(f"[Worker] Matrícula (ROI fixa) lida: '{matricula}'")
                if matricula.isdigit() and len(matricula) >= 5:
                    resultados.append((matricula, 0.9))  # Alta confiança para ROI fixa
            except Exception as e:
                logger.error(f"Erro na extração da matrícula (ROI fixa): {e}")
        
        # Estratégia 2: Usar template matching
        if "matricula_template_path" in self.config:
            try:
                temp_cab = Image.open(self.config["matricula_template_path"])
                
                # Pré-processa a imagem para melhorar a detecção
                pil_img_proc = pre_processar_imagem(imagem_original, equalizar=True, ajustar_contraste=True)
                
                # Detecta o template com multi-escala e rotações
                pts_cab, score_cab = detectar_area_cabecalho_template(
                    pil_img_proc, temp_cab, 
                    pre_processar=True, 
                    multi_escala=True,
                    rotacoes=True
                )
                
                logger.debug(f"[DEBUG] Score do template matching do cabeçalho: {score_cab:.2f}")
                
                thr_cab = self.config.get("matricula_template_threshold", 0.25)
                
                if score_cab >= thr_cab and pts_cab:
                    xs = [p[0] for p in pts_cab]
                    ys = [p[1] for p in pts_cab]
                    x_min, x_max = min(xs), max(xs)
                    y_min, y_max = min(ys), max(ys)
                    
                    # Salva a ROI detectada para debug
                    debug_roi_path = os.path.join(debug_subdir, "debug_matricula_roi_template.png")
                    imagem_original.crop((x_min, y_min, x_max, y_max)).save(debug_roi_path)
                    
                    # Extrai a matrícula da ROI detectada
                    roi_matricula = imagem_original.crop((x_min, y_min, x_max, y_max))
                    roi_processada = preprocess_roi_avancado(roi_matricula, debug_subdir, 2)
                    
                    # Salva a ROI processada para debug
                    debug_roi_ocr_path = os.path.join(debug_subdir, "debug_matricula_roi_used_2.png")
                    roi_processada.save(debug_roi_ocr_path)
                    
                    # Configuração específica para dígitos
                    config_tess = r"--psm 7 -c tessedit_char_whitelist=0123456789"
                    matricula = image_to_string(roi_processada, config=config_tess, output_type=Output.STRING).strip()
                    matricula = ''.join(c for c in matricula if c.isdigit())
                    
                    logger.info(f"[Worker] Matrícula (template-cabeçalho) lida: '{matricula}'")
                    if matricula.isdigit() and len(matricula) >= 5:
                        resultados.append((matricula, score_cab))
            except Exception as e:
                logger.error(f"Erro no template de cabeçalho/matrícula: {e}")
        
        # Escolhe o melhor resultado com base na confiança
        if resultados:
            # Ordena por confiança (maior primeiro)
            resultados.sort(key=lambda x: x[1], reverse=True)
            return resultados[0][0]
        
        return ""

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
                        
                        # Pré-processa a imagem para melhorar a detecção
                        imagem_proc = pre_processar_imagem(imagens[0], equalizar=True, ajustar_contraste=True)
                        
                        # Detecta o template com multi-escala e rotações
                        pts_ref, score = detectar_area_gabarito_template(
                            imagem_proc, template, 
                            pre_processar=True, 
                            multi_escala=True,
                            rotacoes=True
                        )
                        
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
                        debug=True, 
                        debug_folder=debug_subdir
                    )
                    respostas_ordenadas = {}
                    questoes_sorted = sorted(respostas.keys(), key=lambda x: int(x.split()[1]))
                    for q in questoes_sorted:
                        respostas_ordenadas[q] = respostas[q]

                    info_ocr = extrair_info_ocr(pil_img_corrigida)

                    pil_img_original = imagens_originais[i]
                    
                    # Usa a nova função para extrair matrícula com múltiplas estratégias
                    matricula_texto = self.extrair_matricula_com_multiplas_estrategias(
                        pil_img_original, debug_subdir
                    )
                    
                    dados_api = {}
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
