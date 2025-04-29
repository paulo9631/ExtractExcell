import os
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QColor
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QFrame,
    QGraphicsDropShadowEffect
)
from PIL import Image
from PIL.ImageQt import ImageQt

# Módulo interno (mantém import leve – execução pesada ocorre no worker)
from modules.ui.icon_provider import IconProvider

THUMB_SIZE = (180, 250)  # Largura, Altura máximas da miniatura


class _ThumbWorker(QThread):
    """Thread auxiliar para não bloquear a UI ao gerar miniatura."""

    finished = pyqtSignal(QPixmap)
    error = pyqtSignal(str)

    def __init__(self, pdf_path: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._pdf_path = pdf_path

    def run(self):  # noqa: D401  ‑ Qt style
        try:
            # Import pesado aqui (fora da UI‑thread)
            from modules.core.converter import converter_pdf_em_imagens

            pages = converter_pdf_em_imagens(self._pdf_path, dpi=70)
            if not pages:
                self.error.emit("Falha ao converter o PDF em imagem.")
                return

            img = pages[0]
            img.thumbnail(THUMB_SIZE, Image.Resampling.LANCZOS)
            qimg = ImageQt(img)
            pix = QPixmap.fromImage(qimg)
            self.finished.emit(pix)
        except Exception as exc:  # pragma: no cover
            self.error.emit(str(exc))


class PDFThumbnail(QWidget):
    """Miniatura clicável representando um PDF."""

    clicked = pyqtSignal(str)

    def __init__(self, pdf_path: str, index: int, parent: QWidget | None = None):
        super().__init__(parent)
        self._pdf_path = pdf_path
        self._index = index
        self._worker: _ThumbWorker | None = None  # Mantém referência
        self._build_ui()
        self._animate_show()
        QTimer.singleShot(50, self._start_worker)  # gera thumbnail levemente depois

    # ---------------------------------------------------------------------
    # UI helpers
    # ---------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(5, 5, 5, 5)

        frame = QFrame()
        frame.setObjectName("thumbFrame")
        frame.setStyleSheet(
            """
            QFrame#thumbFrame {border:1px solid #e2e8f0; border-radius:12px; background:#ffffff;}
            QFrame#thumbFrame:hover {border-color:#3b82f6; background:#f8fafc;}
            """
        )
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 2)
        frame.setGraphicsEffect(shadow)
        root.addWidget(frame)

        fl = QVBoxLayout(frame)
        fl.setContentsMargins(10, 10, 10, 10)
        fl.setSpacing(8)

        # Ícone PDF
        icon_lbl = QLabel()
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setPixmap(IconProvider.get_icon("pdf", "#3b82f6", 32).pixmap(32, 32))
        fl.addWidget(icon_lbl)

        # Área da miniatura (preenche depois)
        self._thumb_lbl = QLabel("Gerando…")
        self._thumb_lbl.setFixedSize(*THUMB_SIZE)
        self._thumb_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb_lbl.setStyleSheet(
            "border:1px solid #e2e8f0; border-radius:8px; background:#f8fafc; color:#64748b;"
        )
        fl.addWidget(self._thumb_lbl)

        # Nome do arquivo (cortado)
        name = os.path.basename(self._pdf_path)
        name = name if len(name) <= 22 else name[:19] + "…"
        name_lbl = QLabel(name)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setStyleSheet("font-size:13px; font-weight:bold; color:#334155;")
        fl.addWidget(name_lbl)

        # Índice
        idx_lbl = QLabel(f"PDF #{self._index + 1}")
        idx_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        idx_lbl.setStyleSheet("font-size:12px; color:#64748b;")
        fl.addWidget(idx_lbl)

    def _animate_show(self) -> None:
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(450 + self._index * 90)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()

    # ------------------------------------------------------------------
    # Thumbnail generation (threaded)
    # ------------------------------------------------------------------
    def _start_worker(self) -> None:
        """Dispara a geração da miniatura em thread separada."""
        if self._worker is not None:
            return  # já iniciou
        self._worker = _ThumbWorker(self._pdf_path, self)
        self._worker.finished.connect(self._on_thumb_ready)
        self._worker.error.connect(self._on_thumb_error)
        self._worker.start()

    def _on_thumb_ready(self, pix: QPixmap) -> None:
        self._thumb_lbl.setPixmap(pix)
        self._thumb_lbl.setStyleSheet(
            "border:1px solid #e2e8f0; border-radius:8px; background:#ffffff;"
        )
        self._thumb_lbl.setText("")  # remove placeholder

    def _on_thumb_error(self, msg: str) -> None:
        self._thumb_lbl.setText("Erro\nna miniatura")
        print(f"[PDFThumbnail] Falha ao gerar miniatura de '{self._pdf_path}': {msg}")

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    def mousePressEvent(self, event):  # noqa: D401
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._pdf_path)
        super().mousePressEvent(event)
