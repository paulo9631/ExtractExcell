# modules/ui/pdf_preview.py

import os
import gc
import sys
import time
import traceback
import logging
import io
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QScrollArea, QWidget, QLabel,
    QGridLayout, QHBoxLayout, QToolButton, QSpinBox,
    QComboBox, QFrame, QSizePolicy, QPushButton, QProgressBar,
    QMessageBox, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QSize, QTimer, QThread, pyqtSignal, QObject, QRunnable, QThreadPool, QByteArray, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPixmap, QImage, QColor, QFont, QPalette, QIcon
from modules.core.converter import converter_pdf_em_imagens
from modules.ui.icon_provider import IconProvider
from PIL import Image, ImageOps
from PIL.ImageQt import ImageQt

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('PDFViewer')

# Tentativa de usar visualização nativa
PDF_VIEW_AVAILABLE = False
try:
    from PyQt6.QtPdf import QPdfDocument
    from PyQt6.QtPdfWidgets import QPdfView
    PDF_VIEW_AVAILABLE = True
    logger.info("QPdfView está disponível e será usado se possível")
except ImportError:
    logger.warning("QPdfView não está disponível, usando visualizador personalizado")
    PDF_VIEW_AVAILABLE = False


# Definições de cores e estilos
class AppStyles:
    # Cores principais
    PRIMARY = "#4f46e5"  # Indigo-600
    PRIMARY_DARK = "#4338ca"  # Indigo-700
    PRIMARY_LIGHT = "#818cf8"  # Indigo-400
    
    SECONDARY = "#0ea5e9"  # Sky-500
    SECONDARY_DARK = "#0284c7"  # Sky-600
    
    NEUTRAL_50 = "#f8fafc"  # Slate-50
    NEUTRAL_100 = "#f1f5f9"  # Slate-100
    NEUTRAL_200 = "#e2e8f0"  # Slate-200
    NEUTRAL_300 = "#cbd5e1"  # Slate-300
    NEUTRAL_400 = "#94a3b8"  # Slate-400
    NEUTRAL_500 = "#64748b"  # Slate-500
    NEUTRAL_600 = "#475569"  # Slate-600
    NEUTRAL_700 = "#334155"  # Slate-700
    NEUTRAL_800 = "#1e293b"  # Slate-800
    NEUTRAL_900 = "#0f172a"  # Slate-900
    
    SUCCESS = "#10b981"  # Emerald-500
    WARNING = "#f59e0b"  # Amber-500
    ERROR = "#ef4444"  # Red-500
    
    # Estilos de componentes
    BUTTON_STYLE = f"""
        QPushButton {{
            background-color: {PRIMARY};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {PRIMARY_DARK};
        }}
        QPushButton:pressed {{
            background-color: {PRIMARY_DARK};
        }}
        QPushButton:disabled {{
            background-color: {NEUTRAL_300};
            color: {NEUTRAL_500};
        }}
    """
    
    SECONDARY_BUTTON_STYLE = f"""
        QPushButton {{
            background-color: {NEUTRAL_100};
            color: {NEUTRAL_700};
            border: 1px solid {NEUTRAL_300};
            border-radius: 6px;
            padding: 8px 16px;
        }}
        QPushButton:hover {{
            background-color: {NEUTRAL_200};
        }}
        QPushButton:pressed {{
            background-color: {NEUTRAL_300};
        }}
        QPushButton:disabled {{
            background-color: {NEUTRAL_100};
            color: {NEUTRAL_400};
            border: 1px solid {NEUTRAL_200};
        }}
    """
    
    TOOL_BUTTON_STYLE = f"""
        QToolButton {{
            border: none;
            padding: 6px;
            border-radius: 6px;
            background-color: transparent;
        }}
        QToolButton:hover {{
            background-color: {NEUTRAL_200};
        }}
        QToolButton:pressed {{
            background-color: {NEUTRAL_300};
        }}
        QToolButton:disabled {{
            opacity: 0.5;
        }}
    """
    
    SPIN_BOX_STYLE = f"""
        QSpinBox {{
            border: 1px solid {NEUTRAL_300};
            border-radius: 6px;
            padding: 4px 8px;
            background-color: white;
            min-height: 24px;
        }}
        QSpinBox:focus {{
            border: 1px solid {PRIMARY};
        }}
        QSpinBox::up-button, QSpinBox::down-button {{
            width: 16px;
            border-radius: 4px;
            background-color: {NEUTRAL_100};
        }}
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
            background-color: {NEUTRAL_200};
        }}
    """
    
    COMBO_BOX_STYLE = f"""
        QComboBox {{
            border: 1px solid {NEUTRAL_300};
            border-radius: 6px;
            padding: 4px 8px;
            background-color: white;
            min-height: 24px;
        }}
        QComboBox:focus {{
            border: 1px solid {PRIMARY};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        QComboBox QAbstractItemView {{
            border: 1px solid {NEUTRAL_300};
            border-radius: 6px;
            background-color: white;
            selection-background-color: {PRIMARY_LIGHT};
        }}
    """
    
    PROGRESS_BAR_STYLE = f"""
        QProgressBar {{
            border: 1px solid {NEUTRAL_300};
            border-radius: 6px;
            text-align: center;
            background-color: {NEUTRAL_100};
            height: 20px;
            margin: 0px 10px;
            font-weight: bold;
        }}
        QProgressBar::chunk {{
            background-color: {SUCCESS};
            border-radius: 5px;
        }}
    """
    
    SCROLL_AREA_STYLE = f"""
        QScrollArea {{
            border: none;
            background-color: {NEUTRAL_200};
        }}
        QScrollBar:vertical {{
            border: none;
            background-color: {NEUTRAL_200};
            width: 12px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {NEUTRAL_400};
            border-radius: 6px;
            min-height: 20px;
            margin: 2px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {NEUTRAL_500};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            border: none;
            background-color: {NEUTRAL_200};
            height: 12px;
            margin: 0px;
        }}
        QScrollBar::handle:horizontal {{
            background-color: {NEUTRAL_400};
            border-radius: 6px;
            min-width: 20px;
            margin: 2px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background-color: {NEUTRAL_500};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
    """
    
    HEADER_STYLE = f"""
        background-color: {NEUTRAL_50}; 
        color: {NEUTRAL_700}; 
        font-weight: bold; 
        padding: 12px 16px; 
        border-bottom: 1px solid {NEUTRAL_200};
    """
    
    FOOTER_STYLE = f"""
        background-color: {NEUTRAL_50}; 
        border-top: 1px solid {NEUTRAL_200};
        padding: 8px;
    """
    
    CONTROL_BAR_STYLE = f"""
        background-color: {NEUTRAL_100};
        border-bottom: 1px solid {NEUTRAL_200};
        padding: 8px;
    """
    
    PAGE_FRAME_STYLE = f"""
        background-color: white;
        border: 1px solid {NEUTRAL_300};
        border-radius: 4px;
    """


class PDFLoaderSignals(QObject):
    """Sinais para o carregador de PDF."""
    progress = pyqtSignal(int)
    page_loaded = pyqtSignal(int, object)  # Envia o índice e a imagem PIL
    finished = pyqtSignal()
    error = pyqtSignal(str)


class PDFLoaderThread(QThread):
    """Thread para carregar PDFs sem bloquear a interface."""
    
    def __init__(self, pdf_path, dpi=72, parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.dpi = dpi
        self.signals = PDFLoaderSignals()
        self._abort = False
        logger.info(f"Inicializando carregador de PDF: {pdf_path}, DPI: {dpi}")
    
    def run(self):
        try:
            logger.info(f"Iniciando carregamento do PDF: {self.pdf_path}")
            start_time = time.time()
            
            # Carregar o PDF
            pages = converter_pdf_em_imagens(self.pdf_path, dpi=self.dpi)
            
            if not pages:
                logger.error(f"Falha ao carregar o PDF: {self.pdf_path}")
                self.signals.error.emit("Não foi possível carregar o PDF.")
                return
            
            logger.info(f"PDF carregado com {len(pages)} páginas em {time.time() - start_time:.2f} segundos")
            
            # Processar cada página
            total_pages = len(pages)
            for i, page in enumerate(pages):
                if self._abort:
                    logger.info("Carregamento de PDF abortado")
                    return
                
                page_start = time.time()
                logger.debug(f"Processando página {i+1}/{total_pages}")
                
                # Verificar se a imagem está muito escura ou preta
                try:
                    # Verificar se a imagem está muito escura
                    extrema = page.getextrema()
                    logger.debug(f"Valores extremos da imagem: {extrema}")
                    
                    # Se for uma imagem RGB/RGBA, verificar cada canal
                    if isinstance(extrema, tuple) and len(extrema) > 1:
                        is_dark = all(ex[1] < 200 for ex in extrema)  # Verificar valor máximo em cada canal
                    else:
                        is_dark = extrema[1] < 200  # Para imagens em escala de cinza
                    
                    # Se a imagem estiver muito escura, tentar melhorar o contraste
                    if is_dark:
                        logger.info(f"Imagem da página {i+1} está escura, aplicando correção de contraste")
                        page = ImageOps.autocontrast(page, cutoff=0.5)
                        
                        # Verificar novamente após o ajuste
                        extrema_after = page.getextrema()
                        logger.debug(f"Valores extremos após ajuste: {extrema_after}")
                except Exception as e:
                    logger.warning(f"Erro ao analisar luminosidade da imagem: {e}")
                
                # Atualizar progresso
                progress = int((i / total_pages) * 100)
                self.signals.progress.emit(progress)
                
                # Emitir sinal com a página carregada (imagem PIL)
                self.signals.page_loaded.emit(i, page)
                
                logger.debug(f"Página {i+1} processada em {time.time() - page_start:.2f} segundos")
                
                # Pequena pausa para permitir que a UI responda
                QThread.msleep(10)
            
            self.signals.progress.emit(100)
            self.signals.finished.emit()
            logger.info(f"Carregamento completo do PDF em {time.time() - start_time:.2f} segundos")
            
        except Exception as e:
            logger.error(f"Erro ao carregar o PDF: {str(e)}")
            logger.error(traceback.format_exc())
            self.signals.error.emit(f"Erro ao carregar o PDF: {str(e)}")
    
    def abort(self):
        """Aborta o carregamento."""
        logger.info("Solicitação para abortar o carregamento do PDF")
        self._abort = True


class ZoomWorkerSignals(QObject):
    """Sinais para o worker de zoom."""
    finished = pyqtSignal(int, float, QPixmap)  # página, fator de zoom, pixmap
    error = pyqtSignal(str)


class ZoomWorker(QRunnable):
    """Worker para aplicar zoom em uma página sem bloquear a interface."""
    
    def __init__(self, page_index, pil_image, zoom_factor):
        super().__init__()
        self.page_index = page_index
        self.pil_image = pil_image
        self.zoom_factor = zoom_factor
        self.signals = ZoomWorkerSignals()
        logger.debug(f"Inicializando worker de zoom: página {page_index+1}, fator {zoom_factor}")
    
    def run(self):
        try:
            start_time = time.time()
            logger.debug(f"Aplicando zoom na página {self.page_index+1}, fator: {self.zoom_factor}")
            
            # Redimensionar a imagem PIL
            if self.zoom_factor != 1.0:
                w, h = self.pil_image.size
                new_w = int(w * self.zoom_factor)
                new_h = int(h * self.zoom_factor)
                
                logger.debug(f"Redimensionando imagem de {w}x{h} para {new_w}x{new_h}")
                
                # Usar LANCZOS para melhor qualidade em redimensionamento
                resized_img = self.pil_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
            else:
                resized_img = self.pil_image
            
            # Verificar se a imagem está no modo correto para exibição
            if resized_img.mode not in ['RGB', 'RGBA']:
                logger.debug(f"Convertendo imagem do modo {resized_img.mode} para RGB")
                resized_img = resized_img.convert('RGB')
            
            # Método alternativo de conversão para QPixmap
            logger.debug("Convertendo imagem PIL para QPixmap (método alternativo)")
            
            # Método 1: Usando QImage diretamente
            try:
                # Converter para bytes
                img_byte_arr = io.BytesIO()
                resized_img.save(img_byte_arr, format='PNG')
                img_bytes = img_byte_arr.getvalue()
                
                # Criar QImage a partir dos bytes
                q_image = QImage()
                q_image.loadFromData(QByteArray(img_bytes))
                
                if q_image.isNull():
                    raise Exception("QImage está vazia após conversão")
                
                # Converter para QPixmap
                pixmap = QPixmap.fromImage(q_image)
                logger.debug(f"Pixmap criado com tamanho: {pixmap.width()}x{pixmap.height()}")
                
            except Exception as e:
                logger.warning(f"Método 1 falhou: {e}, tentando método 2")
                
                # Método 2: Usando ImageQt
                try:
                    qimg = ImageQt(resized_img)
                    pixmap = QPixmap.fromImage(qimg)
                    logger.debug(f"Pixmap criado com método 2, tamanho: {pixmap.width()}x{pixmap.height()}")
                    
                except Exception as e2:
                    logger.warning(f"Método 2 falhou: {e2}, tentando método 3")
                    
                    # Método 3: Salvar temporariamente e carregar
                    try:
                        temp_path = f"temp_page_{self.page_index}.png"
                        resized_img.save(temp_path)
                        pixmap = QPixmap(temp_path)
                        os.remove(temp_path)
                        logger.debug(f"Pixmap criado com método 3, tamanho: {pixmap.width()}x{pixmap.height()}")
                        
                    except Exception as e3:
                        raise Exception(f"Todos os métodos de conversão falharam: {e}, {e2}, {e3}")
            
            # Verificar se o pixmap é válido
            if pixmap.isNull():
                raise Exception("Pixmap está vazio após conversão")
            
            # Emitir sinal com o resultado
            logger.debug(f"Zoom concluído em {time.time() - start_time:.2f} segundos")
            self.signals.finished.emit(self.page_index, self.zoom_factor, pixmap)
            
        except Exception as e:
            logger.error(f"Erro ao aplicar zoom: {str(e)}")
            logger.error(traceback.format_exc())
            self.signals.error.emit(f"Erro ao aplicar zoom: {str(e)}")


class PDFPreviewDialog(QDialog):
    """
    Diálogo de preview das páginas de um PDF.
    Usa QPdfDocument/QPdfView quando disponível;
    caso contrário, faz fallback para visualização de página inteira.
    """
    def __init__(self, pdf_path, parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.setWindowTitle(f"Visualização — {os.path.basename(pdf_path)}")
        self.resize(1000, 800)
        
        # Configurar fonte e estilo da janela
        self.setFont(QFont("Segoe UI", 10))
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {AppStyles.NEUTRAL_100};
            }}
            QLabel {{
                color: {AppStyles.NEUTRAL_700};
            }}
        """)
        
        logger.info(f"Inicializando diálogo de visualização para: {pdf_path}")
        
        # Armazenamento de páginas e cache
        self.pil_pages = {}  # Armazena as imagens PIL originais
        self.pixmap_cache = {}  # Cache de pixmaps com zoom: {(page_index, zoom_factor): pixmap}
        
        self.current_page = 0
        self.zoom_levels = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
        self.current_zoom = 2  # Índice para zoom_levels[2] = 1.0 (100%)
        
        self.loader_thread = None
        self.threadpool = QThreadPool()
        logger.info(f"Número máximo de threads disponíveis: {self.threadpool.maxThreadCount()}")
        
        # Configurar a interface
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Cabeçalho
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_frame.setStyleSheet(f"QFrame#headerFrame {{ {AppStyles.HEADER_STYLE} }}")
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 12, 16, 12)
        
        # Ícone de PDF
        pdf_icon_label = QLabel()
        pdf_icon = IconProvider.get_icon("file-text", AppStyles.PRIMARY, 24)
        pdf_icon_label.setPixmap(pdf_icon.pixmap(24, 24))
        
        # Título do PDF
        header_title = QLabel(f"Visualizando: {os.path.basename(pdf_path)}")
        header_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        
        header_layout.addWidget(pdf_icon_label)
        header_layout.addWidget(header_title)
        header_layout.addStretch()
        
        layout.addWidget(header_frame)

        # Se PDF_VIEW_AVAILABLE, tenta carregar com QPdfView
        if PDF_VIEW_AVAILABLE:
            try:
                logger.info("Tentando usar QPdfView")
                doc = QPdfDocument(self)
                status = doc.load(pdf_path)
                if status == QPdfDocument.Status.Ready:
                    logger.info("QPdfView carregado com sucesso")
                    view = QPdfView(self)
                    view.setDocument(doc)
                    view.setZoomMode(QPdfView.ZoomMode.FitInView)
                    layout.addWidget(view)
                    
                    # Botões de ação
                    button_box = QHBoxLayout()
                    button_box.setContentsMargins(16, 12, 16, 12)
                    
                    close_button = QPushButton("Fechar")
                    close_button.setStyleSheet(AppStyles.SECONDARY_BUTTON_STYLE)
                    close_button.clicked.connect(self.reject)
                    button_box.addStretch()
                    button_box.addWidget(close_button)
                    
                    footer = QFrame()
                    footer.setLayout(button_box)
                    footer.setStyleSheet(f"QFrame {{ {AppStyles.FOOTER_STYLE} }}")
                    layout.addWidget(footer)
                    return
                else:
                    logger.warning(f"QPdfView não conseguiu carregar o PDF, status: {status}")
            except Exception as e:
                logger.error(f"Erro ao usar QPdfView: {e}")
                logger.error(traceback.format_exc())
                # Continua para o fallback
        
        # Fallback: criar nossa própria visualização de página inteira
        logger.info("Usando visualizador personalizado")
        self._create_full_page_viewer(layout)
        
        # Iniciar o carregamento do PDF em uma thread separada
        self._start_pdf_loading()
    
    def closeEvent(self, event):
        """Manipula o evento de fechamento do diálogo."""
        logger.info("Fechando diálogo de visualização")
        
        # Abortar o carregamento se estiver em andamento
        if self.loader_thread and self.loader_thread.isRunning():
            logger.info("Abortando thread de carregamento")
            self.loader_thread.abort()
            self.loader_thread.wait()
        
        # Limpar cache e liberar memória
        logger.info(f"Limpando cache: {len(self.pixmap_cache)} pixmaps, {len(self.pil_pages)} imagens PIL")
        self.pixmap_cache.clear()
        self.pil_pages.clear()
        gc.collect()
        
        logger.info("Diálogo fechado")
        super().closeEvent(event)
    
    def _create_full_page_viewer(self, parent_layout):
        """Cria a interface de visualização de página inteira"""
        logger.info("Criando interface de visualização de página inteira")
        
        # Barra de controles
        control_bar = QFrame()
        control_bar.setObjectName("controlBar")
        control_bar.setStyleSheet(f"QFrame#controlBar {{ {AppStyles.CONTROL_BAR_STYLE} }}")
        
        # Adicionar sombra à barra de controle
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 2)
        control_bar.setGraphicsEffect(shadow)
        
        control_layout = QHBoxLayout(control_bar)
        control_layout.setContentsMargins(16, 8, 16, 8)
        
        # Navegação de páginas
        nav_frame = QFrame()
        nav_frame.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1px solid {AppStyles.NEUTRAL_300};
                border-radius: 8px;
            }}
        """)
        nav_layout = QHBoxLayout(nav_frame)
        nav_layout.setContentsMargins(4, 4, 4, 4)
        nav_layout.setSpacing(2)
        
        self.btn_prev = QToolButton()
        self.btn_prev.setIcon(IconProvider.get_icon("chevron-left", AppStyles.NEUTRAL_600, 20))
        self.btn_prev.setIconSize(QSize(20, 20))
        self.btn_prev.setToolTip("Página anterior")
        self.btn_prev.clicked.connect(self.previous_page)
        self.btn_prev.setStyleSheet(AppStyles.TOOL_BUTTON_STYLE)
        
        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.setMaximum(1)
        self.page_spin.setValue(1)
        self.page_spin.valueChanged.connect(self.on_page_spin_changed)
        self.page_spin.setFixedWidth(60)
        self.page_spin.setStyleSheet(AppStyles.SPIN_BOX_STYLE)
        self.page_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.page_count_label = QLabel("de 1")
        self.page_count_label.setStyleSheet(f"color: {AppStyles.NEUTRAL_600}; margin: 0 4px;")
        
        self.btn_next = QToolButton()
        self.btn_next.setIcon(IconProvider.get_icon("chevron-right", AppStyles.NEUTRAL_600, 20))
        self.btn_next.setIconSize(QSize(20, 20))
        self.btn_next.setToolTip("Próxima página")
        self.btn_next.clicked.connect(self.next_page)
        self.btn_next.setStyleSheet(AppStyles.TOOL_BUTTON_STYLE)
        
        nav_layout.addWidget(self.btn_prev)
        nav_layout.addWidget(self.page_spin)
        nav_layout.addWidget(self.page_count_label)
        nav_layout.addWidget(self.btn_next)
        
        # Controle de zoom
        zoom_frame = QFrame()
        zoom_frame.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1px solid {AppStyles.NEUTRAL_300};
                border-radius: 8px;
            }}
        """)
        zoom_layout = QHBoxLayout(zoom_frame)
        zoom_layout.setContentsMargins(8, 4, 8, 4)
        zoom_layout.setSpacing(8)
        
        zoom_icon_label = QLabel()
        zoom_icon = IconProvider.get_icon("zoom-in", AppStyles.NEUTRAL_600, 18)
        zoom_icon_label.setPixmap(zoom_icon.pixmap(18, 18))
        
        self.zoom_combo = QComboBox()
        self.zoom_combo.addItems(["50%", "75%", "100%", "125%", "150%", "200%"])
        self.zoom_combo.setCurrentIndex(2)  # 100% por padrão
        self.zoom_combo.currentIndexChanged.connect(self.on_zoom_changed)
        self.zoom_combo.setFixedWidth(100)
        self.zoom_combo.setStyleSheet(AppStyles.COMBO_BOX_STYLE)
        
        zoom_layout.addWidget(zoom_icon_label)
        zoom_layout.addWidget(self.zoom_combo)
        
        # Adicionar widgets à barra de controle
        control_layout.addWidget(nav_frame)
        control_layout.addStretch()
        control_layout.addWidget(zoom_frame)
        
        # Área de visualização da página
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setStyleSheet(AppStyles.SCROLL_AREA_STYLE)
        
        self.page_container = QWidget()
        self.page_container.setStyleSheet(f"background-color: {AppStyles.NEUTRAL_200};")
        self.page_layout = QVBoxLayout(self.page_container)
        self.page_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_layout.setContentsMargins(20, 20, 20, 20)
        self.page_layout.setSpacing(0)
        
        self.page_frame = QFrame()
        self.page_frame.setObjectName("pageFrame")
        self.page_frame.setStyleSheet(f"QFrame#pageFrame {{ {AppStyles.PAGE_FRAME_STYLE} }}")
        
        # Adicionar sombra ao frame da página
        page_shadow = QGraphicsDropShadowEffect()
        page_shadow.setBlurRadius(15)
        page_shadow.setColor(QColor(0, 0, 0, 40))
        page_shadow.setOffset(0, 3)
        self.page_frame.setGraphicsEffect(page_shadow)
        
        self.page_frame_layout = QVBoxLayout(self.page_frame)
        self.page_frame_layout.setContentsMargins(0, 0, 0, 0)
        
        self.page_label = QLabel("Carregando PDF...")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.page_label.setStyleSheet(f"color: {AppStyles.NEUTRAL_600}; font-size: 14px;")
        self.page_frame_layout.addWidget(self.page_label)
        
        self.page_layout.addWidget(self.page_frame)
        self.scroll_area.setWidget(self.page_container)
        
        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Carregando PDF: %p%")
        self.progress_bar.setStyleSheet(AppStyles.PROGRESS_BAR_STYLE)
        self.progress_bar.setFixedHeight(24)
        
        # Container para a barra de progresso com margens
        progress_container = QWidget()
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(16, 8, 16, 8)
        progress_layout.addWidget(self.progress_bar)
        
        # Adicionar componentes ao layout principal
        parent_layout.addWidget(control_bar)
        parent_layout.addWidget(self.scroll_area, 1)
        parent_layout.addWidget(progress_container)
        
        # Botões de ação
        footer = QFrame()
        footer.setObjectName("footerFrame")
        footer.setStyleSheet(f"QFrame#footerFrame {{ {AppStyles.FOOTER_STYLE} }}")
        
        button_layout = QHBoxLayout(footer)
        button_layout.setContentsMargins(16, 12, 16, 12)
        
        self.close_button = QPushButton("Fechar")
        self.close_button.setIcon(IconProvider.get_icon("x", "white", 16))
        self.close_button.clicked.connect(self.reject)
        self.close_button.setStyleSheet(AppStyles.BUTTON_STYLE)
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        
        parent_layout.addWidget(footer)
        
        # Inicialmente, desabilitar controles de navegação
        self.btn_prev.setEnabled(False)
        self.btn_next.setEnabled(False)
        self.page_spin.setEnabled(False)
        self.zoom_combo.setEnabled(False)
        
        logger.info("Interface de visualização criada")

    def _start_pdf_loading(self):
        """Inicia o carregamento do PDF em uma thread separada."""
        logger.info("Iniciando carregamento do PDF em thread separada")
        
        # Usar DPI mais alto para melhor qualidade
        self.loader_thread = PDFLoaderThread(self.pdf_path, dpi=120, parent=self)
        self.loader_thread.signals.progress.connect(self.progress_bar.setValue)
        self.loader_thread.signals.page_loaded.connect(self._on_page_loaded)
        self.loader_thread.signals.finished.connect(self._on_loading_finished)
        self.loader_thread.signals.error.connect(self._on_loading_error)
        self.loader_thread.start()
        
        # Animação de carregamento
        self.page_label.setText("Carregando PDF...")
        self.page_label.setStyleSheet(f"""
            color: {AppStyles.NEUTRAL_600}; 
            font-size: 14px;
            background-image: url(':/icons/loading.gif');
            background-position: center bottom;
            background-repeat: no-repeat;
            padding-bottom: 40px;
        """)
        
        logger.info("Thread de carregamento iniciada")
    
    def _on_page_loaded(self, page_index, pil_image):
        """Manipula o evento de página carregada."""
        logger.debug(f"Página {page_index+1} carregada, tamanho: {pil_image.size}, modo: {pil_image.mode}")
        
        try:
            # Verificar se a imagem está em um formato adequado
            if pil_image.mode not in ['RGB', 'RGBA']:
                logger.debug(f"Convertendo imagem do modo {pil_image.mode} para RGB")
                pil_image = pil_image.convert('RGB')
            
            # Verificar se a imagem tem conteúdo (não é toda preta)
            extrema = pil_image.getextrema()
            logger.debug(f"Valores extremos da imagem: {extrema}")
            
            # Armazenar a imagem PIL
            self.pil_pages[page_index] = pil_image
            
            # Se for a primeira página, processar e mostrar imediatamente
            if page_index == 0 and self.current_page == 0:
                logger.debug("Processando primeira página para exibição")
                self._process_and_show_page(0)
            
            # Atualizar o contador de páginas
            total_pages = max(page_index + 1, len(self.pil_pages))
            self.page_count_label.setText(f"de {total_pages}")
            self.page_spin.setMaximum(total_pages)
            
            # Habilitar controles se necessário
            if not self.page_spin.isEnabled():
                logger.debug("Habilitando controles de navegação")
                self.page_spin.setEnabled(True)
                self.zoom_combo.setEnabled(True)
            
            # Atualizar botões de navegação
            self._update_navigation_buttons()
            
        except Exception as e:
            logger.error(f"Erro ao processar página carregada: {str(e)}")
            logger.error(traceback.format_exc())
    
    def _on_loading_finished(self):
        """Manipula o evento de carregamento concluído."""
        logger.info("Carregamento do PDF concluído")
        
        try:
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat("Carregamento concluído")
            
            # Animar a barra de progresso para desaparecer
            def hide_progress():
                self.progress_bar.setVisible(False)
                self.progress_bar.parentWidget().setFixedHeight(0)
            
            QTimer.singleShot(1500, hide_progress)
            
            # Garantir que os controles estejam habilitados
            self.page_spin.setEnabled(True)
            self.zoom_combo.setEnabled(True)
            
            # Atualizar botões de navegação
            self._update_navigation_buttons()
            
            logger.info(f"PDF carregado com {len(self.pil_pages)} páginas")
            
        except Exception as e:
            logger.error(f"Erro ao finalizar carregamento: {str(e)}")
            logger.error(traceback.format_exc())
    
    def _on_loading_error(self, error_message):
        """Manipula o evento de erro no carregamento."""
        logger.error(f"Erro no carregamento do PDF: {error_message}")
        
        self.page_label.setText(error_message)
        self.page_label.setStyleSheet(f"color: {AppStyles.ERROR}; font-size: 14px;")
        self.progress_bar.setFormat("Erro no carregamento")
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {AppStyles.NEUTRAL_300};
                border-radius: 6px;
                text-align: center;
                background-color: {AppStyles.NEUTRAL_100};
                height: 20px;
                margin: 0px 10px;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {AppStyles.ERROR};
                border-radius: 5px;
            }}
        """)
        
        # Mostrar mensagem de erro
        QMessageBox.critical(self, "Erro de Carregamento", 
                            f"Ocorreu um erro ao carregar o PDF:\n{error_message}")
    
    def _process_and_show_page(self, page_index):
        """Processa e exibe a página especificada."""
        logger.debug(f"Processando página {page_index+1} para exibição")
        
        if page_index not in self.pil_pages:
            logger.warning(f"Página {page_index+1} não está disponível")
            return
        
        try:
            # Verificar se já temos esta página com este zoom no cache
            zoom_factor = self.zoom_levels[self.current_zoom]
            cache_key = (page_index, zoom_factor)
            
            if cache_key in self.pixmap_cache:
                # Usar a versão em cache
                logger.debug(f"Usando versão em cache para página {page_index+1}, zoom {zoom_factor}")
                pixmap = self.pixmap_cache[cache_key]
                
                # Verificar se o pixmap é válido
                if pixmap.isNull() or pixmap.width() == 0 or pixmap.height() == 0:
                    logger.warning("Pixmap em cache é inválido, recriando")
                    del self.pixmap_cache[cache_key]
                    # Reprocessar a página
                    self._process_and_show_page(page_index)
                    return
                
                self.page_label.setPixmap(pixmap)
                self.current_page = page_index
                self._update_navigation_buttons()
                return
            
            # Mostrar indicador de carregamento
            self.page_label.setText(f"Aplicando zoom na página {page_index+1}...")
            self.page_label.setStyleSheet(f"color: {AppStyles.NEUTRAL_600}; font-size: 14px;")
            
            # Processar a página em uma thread separada
            logger.debug(f"Iniciando worker para aplicar zoom na página {page_index+1}")
            worker = ZoomWorker(page_index, self.pil_pages[page_index], zoom_factor)
            worker.signals.finished.connect(self._on_zoom_finished)
            worker.signals.error.connect(self._on_zoom_error)
            
            # Iniciar o worker
            self.threadpool.start(worker)
            
        except Exception as e:
            logger.error(f"Erro ao processar página {page_index+1}: {str(e)}")
            logger.error(traceback.format_exc())
            self.page_label.setText(f"Erro ao processar página {page_index+1}: {str(e)}")
            self.page_label.setStyleSheet(f"color: {AppStyles.ERROR}; font-size: 14px;")
    
    def _on_zoom_finished(self, page_index, zoom_factor, pixmap):
        """Manipula o evento de zoom concluído."""
        logger.debug(f"Zoom concluído para página {page_index+1}, fator {zoom_factor}")
        
        try:
            # Verificar se o pixmap é válido
            if pixmap.isNull() or pixmap.width() == 0 or pixmap.height() == 0:
                logger.error("Pixmap resultante é inválido")
                self.page_label.setText("Erro: A imagem não pôde ser processada corretamente")
                self.page_label.setStyleSheet(f"color: {AppStyles.ERROR}; font-size: 14px;")
                return
                
            # Armazenar no cache
            cache_key = (page_index, zoom_factor)
            self.pixmap_cache[cache_key] = pixmap
            
            # Se esta for a página atual e o zoom atual, exibir
            if page_index == self.current_page and zoom_factor == self.zoom_levels[self.current_zoom]:
                logger.debug(f"Exibindo página {page_index+1} com zoom {zoom_factor}")
                self.page_label.setPixmap(pixmap)
                self.page_label.setStyleSheet("")  # Limpar estilo
            
            # Limitar o tamanho do cache (manter apenas as últimas 3 páginas com zoom)
            if len(self.pixmap_cache) > 3:
                # Remover a entrada mais antiga que não seja a atual
                keys_to_remove = [k for k in self.pixmap_cache.keys() if k != cache_key]
                if keys_to_remove:
                    oldest_key = keys_to_remove[0]
                    logger.debug(f"Removendo do cache: página {oldest_key[0]+1}, zoom {oldest_key[1]}")
                    del self.pixmap_cache[oldest_key]
                    # Forçar coleta de lixo para liberar memória
                    gc.collect()
            
        except Exception as e:
            logger.error(f"Erro ao finalizar zoom: {str(e)}")
            logger.error(traceback.format_exc())
    
    def _on_zoom_error(self, error_message):
        """Manipula erros no processamento de zoom."""
        logger.error(f"Erro ao aplicar zoom: {error_message}")
        self.page_label.setText(f"Erro ao aplicar zoom: {error_message}")
        self.page_label.setStyleSheet(f"color: {AppStyles.ERROR}; font-size: 14px;")
        
        # Tentar fallback para zoom 100%
        if self.current_zoom != 2:  # 2 = 100%
            logger.info("Tentando fallback para zoom 100%")
            self.zoom_combo.setCurrentIndex(2)
    
    def _update_navigation_buttons(self):
        """Atualiza o estado dos botões de navegação."""
        try:
            self.btn_prev.setEnabled(self.current_page > 0)
            self.btn_next.setEnabled(self.current_page < len(self.pil_pages) - 1)
            
            # Atualizar o spin box
            self.page_spin.blockSignals(True)
            self.page_spin.setValue(self.current_page + 1)
            self.page_spin.blockSignals(False)
            
            logger.debug(f"Botões de navegação atualizados: prev={self.btn_prev.isEnabled()}, next={self.btn_next.isEnabled()}")
            
        except Exception as e:
            logger.error(f"Erro ao atualizar botões de navegação: {str(e)}")
    
    def show_page(self, page_index):
        """Exibe a página especificada."""
        logger.info(f"Solicitação para mostrar página {page_index+1}")
        
        try:
            if page_index < 0 or page_index >= len(self.pil_pages):
                logger.warning(f"Índice de página inválido: {page_index+1}")
                return
            
            if self.current_page != page_index:
                self.current_page = page_index
                self._process_and_show_page(page_index)
                
        except Exception as e:
            logger.error(f"Erro ao mostrar página {page_index+1}: {str(e)}")
            logger.error(traceback.format_exc())
    
    def previous_page(self):
        """Navega para a página anterior."""
        logger.debug("Solicitação para página anterior")
        try:
            if self.current_page > 0:
                self.show_page(self.current_page - 1)
        except Exception as e:
            logger.error(f"Erro ao navegar para página anterior: {str(e)}")
            logger.error(traceback.format_exc())
    
    def next_page(self):
        """Navega para a próxima página."""
        logger.debug("Solicitação para próxima página")
        try:
            if self.current_page < len(self.pil_pages) - 1:
                self.show_page(self.current_page + 1)
        except Exception as e:
            logger.error(f"Erro ao navegar para próxima página: {str(e)}")
            logger.error(traceback.format_exc())
    
    def on_page_spin_changed(self, value):
        """Manipula a mudança de valor no controle de página."""
        logger.debug(f"Spin box de página alterado para {value}")
        try:
            # Converter de número de página amigável (1-based) para índice (0-based)
            page_index = value - 1
            if 0 <= page_index < len(self.pil_pages):
                self.show_page(page_index)
        except Exception as e:
            logger.error(f"Erro ao mudar página via spin box: {str(e)}")
            logger.error(traceback.format_exc())
    
    def on_zoom_changed(self, index):
        """Manipula a mudança de nível de zoom."""
        logger.debug(f"Nível de zoom alterado para índice {index}")
        try:
            if 0 <= index < len(self.zoom_levels):
                old_zoom = self.current_zoom
                self.current_zoom = index
                
                # Reprocessar a página atual com o novo zoom
                logger.info(f"Alterando zoom de {self.zoom_levels[old_zoom]} para {self.zoom_levels[index]}")
                self._process_and_show_page(self.current_page)
        except Exception as e:
            logger.error(f"Erro ao mudar nível de zoom: {str(e)}")
            logger.error(traceback.format_exc())