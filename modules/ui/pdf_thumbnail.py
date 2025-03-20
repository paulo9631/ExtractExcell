import os
from PyQt6.QtCore import QTimer, Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QFrame, QGraphicsDropShadowEffect
from PyQt6.QtGui import QPixmap, QColor
from PIL import Image
from PIL.ImageQt import ImageQt

from modules.core.converter import converter_pdf_em_imagens
from modules.ui.icon_provider import IconProvider

class PDFThumbnail(QWidget):
    """Exibe thumbnail + nome do PDF + índice."""
    def __init__(self, pdf_path, index, parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.index = index
        self.dark_mode = False
        self.initUI()
                
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(500 + index * 100)  # Atraso baseado no índice
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.start()

    def initUI(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)

        self.frame = QFrame()
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(15)
        self.shadow.setColor(QColor(0, 0, 0, 30))
        self.shadow.setOffset(0, 2)
        self.frame.setGraphicsEffect(self.shadow)
        
        self.frame.setStyleSheet("""
            QFrame {
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                background-color: #ffffff;
            }
            QFrame:hover {
                border-color: #3b82f6;
                background-color: #f8fafc;
            }
        """)
        self.frm_layout = QVBoxLayout(self.frame)
        self.frm_layout.setContentsMargins(10, 10, 10, 10)
        self.frm_layout.setSpacing(10)

        self.pdf_icon_label = QLabel()
        pdf_icon = IconProvider.get_icon("pdf", "#3b82f6", 32)
        self.pdf_icon_label.setPixmap(pdf_icon.pixmap(32, 32))
        self.pdf_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.frm_layout.addWidget(self.pdf_icon_label)

        self.lbl_thumb = QLabel()
        self.lbl_thumb.setFixedSize(180, 250)
        self.lbl_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_thumb.setStyleSheet("""
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            background-color: #f8fafc;
            padding: 5px;
        """)
        self.frm_layout.addWidget(self.lbl_thumb)

        base_name = os.path.basename(self.pdf_path)
        if len(base_name) > 20:
            base_name = base_name[:17] + "..."

        self.lbl_filename = QLabel(base_name)
        self.lbl_filename.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_filename.setStyleSheet("font-size: 13px; font-weight: bold; color: #334155;")
        self.frm_layout.addWidget(self.lbl_filename)

        self.lbl_index = QLabel(f"PDF #{self.index+1}")
        self.lbl_index.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_index.setStyleSheet("font-size: 12px; color: #64748b;")
        self.frm_layout.addWidget(self.lbl_index)

        self.layout.addWidget(self.frame)

        QTimer.singleShot(100, self.gerar_thumbnail)

    def set_dark_mode(self, dark):
        """Atualiza o thumbnail para o modo escuro ou claro."""
        self.dark_mode = dark
        
        if dark:
            self.frame.setStyleSheet("""
                QFrame {
                    border: 1px solid #334155;
                    border-radius: 12px;
                    background-color: #1e293b;
                }
                QFrame:hover {
                    border-color: #60a5fa;
                    background-color: #0f172a;
                }
            """)
            
            self.lbl_thumb.setStyleSheet("""
                border: 1px solid #334155;
                border-radius: 8px;
                background-color: #0f172a;
                padding: 5px;
            """)
            
            self.lbl_filename.setStyleSheet("font-size: 13px; font-weight: bold; color: #e2e8f0;")
            self.lbl_index.setStyleSheet("font-size: 12px; color: #94a3b8;")
            
            pdf_icon = IconProvider.get_icon("pdf", "#60a5fa", 32)
            self.pdf_icon_label.setPixmap(pdf_icon.pixmap(32, 32))
            
            self.shadow.setColor(QColor(0, 0, 0, 50))
        else:
            self.frame.setStyleSheet("""
                QFrame {
                    border: 1px solid #e2e8f0;
                    border-radius: 12px;
                    background-color: #ffffff;
                }
                QFrame:hover {
                    border-color: #3b82f6;
                    background-color: #f8fafc;
                }
            """)
            
            self.lbl_thumb.setStyleSheet("""
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                background-color: #f8fafc;
                padding: 5px;
            """)
            
            self.lbl_filename.setStyleSheet("font-size: 13px; font-weight: bold; color: #334155;")
            self.lbl_index.setStyleSheet("font-size: 12px; color: #64748b;")
            
            pdf_icon = IconProvider.get_icon("pdf", "#3b82f6", 32)
            self.pdf_icon_label.setPixmap(pdf_icon.pixmap(32, 32))
            
            self.shadow.setColor(QColor(0, 0, 0, 30))

    def gerar_thumbnail(self):
        """Converte apenas a 1ª página do PDF em baixa DPI e exibe."""
        try:
            thumbs = converter_pdf_em_imagens(self.pdf_path, dpi=40)
            if thumbs:
                img_pil = thumbs[0]
                img_pil.thumbnail((180, 250), Image.Resampling.LANCZOS)
                qt_img = ImageQt(img_pil)
                pixmap = QPixmap.fromImage(qt_img)
                self.lbl_thumb.setPixmap(pixmap)
            else:
                self.lbl_thumb.setText("Falha ao carregar")
                if self.dark_mode:
                    self.lbl_thumb.setStyleSheet("""
                        border: 1px solid #334155;
                        border-radius: 8px;
                        background-color: #0f172a;
                        padding: 5px;
                        color: #ef4444;
                        font-weight: bold;
                    """)
                else:
                    self.lbl_thumb.setStyleSheet("""
                        border: 1px solid #e2e8f0;
                        border-radius: 8px;
                        background-color: #f8fafc;
                        padding: 5px;
                        color: #ef4444;
                        font-weight: bold;
                    """)
        except Exception as e:
            self.lbl_thumb.setText("Erro ao carregar")
            if self.dark_mode:
                self.lbl_thumb.setStyleSheet("""
                    border: 1px solid #334155;
                    border-radius: 8px;
                    background-color: #0f172a;
                    padding: 5px;
                    color: #ef4444;
                    font-weight: bold;
                """)
            else:
                self.lbl_thumb.setStyleSheet("""
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    background-color: #f8fafc;
                    padding: 5px;
                    color: #ef4444;
                    font-weight: bold;
                """)