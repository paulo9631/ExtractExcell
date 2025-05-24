import sys
import os
from PyQt6.QtCore import (
    Qt, QSize, QPropertyAnimation, QEasingCurve,
    QThreadPool, QRunnable, pyqtSignal, QObject
)
from PyQt6.QtGui import QFont, QPixmap, QColor, QPalette, QIcon, QFontDatabase
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QStatusBar, QFileDialog,
    QWidget, QVBoxLayout, QLabel, QScrollArea, QGroupBox, QGridLayout,
    QSplitter, QFormLayout, QComboBox, QSlider, QHBoxLayout, QMessageBox,
    QToolButton, QGraphicsOpacityEffect, QSpacerItem, QSizePolicy,
    QDialog, QPushButton, QFrame, QStackedWidget
)

from modules.core.converter import converter_pdf_em_imagens
from modules.core.workers import ProcessWorker
from modules.core.dialogs import ResultadoDialog
from modules.core.exporter import importar_para_planilha
from modules.ui.pdf_thumbnail import PDFThumbnail
from modules.ui.pdf_preview import PDFPreviewDialog
from modules.ui.modern_widgets import ModernButton, ModernProgressBar, InfoCard, GlassCard
from modules.ui.icon_provider import IconProvider
from modules.ui.pdf_filler_window import PDFFillerWindow



class PDFLoaderSignals(QObject):
    finished = pyqtSignal(str, int)
    error = pyqtSignal(str)


class PDFLoaderWorker(QRunnable):
    def __init__(self, config, pdf_path, client=None):
        super().__init__()
        self.client = client
        self.pdf_path = pdf_path
        self.signals = PDFLoaderSignals()

    def run(self):
        try:
            imagens = converter_pdf_em_imagens(self.pdf_path, dpi=50)
            num_paginas = len(imagens)
            self.signals.finished.emit(self.pdf_path, num_paginas)
        except Exception as e:
            self.signals.error.emit(f"Falha ao carregar '{self.pdf_path}': {e}")


class SelectedPDFsDialog(QDialog):
    def __init__(self, pdf_paths, parent=None):
        super().__init__(parent)
        self.pdf_paths = pdf_paths
        self.setWindowTitle("PDFs Selecionados")
        self.resize(800, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #f8fafc;
                border-radius: 10px;
            }
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QScrollArea {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                background-color: white;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        icon_label = QLabel()
        icon_label.setPixmap(IconProvider.get_icon("file-text", "#3b82f6", 24).pixmap(24, 24))
        
        title_label = QLabel("PDFs Selecionados")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e293b;")
        
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addWidget(header)

        # PDF Grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(15)

        for idx, path in enumerate(pdf_paths):
            thumb = PDFThumbnail(path, idx, parent=self)
            thumb.clicked.connect(lambda p=path: self.open_preview(p))
            row, col = divmod(idx, 4)
            grid.addWidget(thumb, row, col)

        scroll.setWidget(container)
        layout.addWidget(scroll)

        # Footer
        btn_close = ModernButton("Fechar", "x-circle", False)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignCenter)

    def open_preview(self, pdf_path):
        dlg = PDFPreviewDialog(pdf_path, parent=self)
        dlg.exec()


class GabaritoApp(QMainWindow):
    def __init__(self, config, client=None):
        super().__init__()
        self.client = client  # Isso aqui é OBRIGATÓRIO
        self.config = config
        self.pdf_paths = []
        self.threadpool = QThreadPool()
        self.threads_restantes = 0
        self.total_paginas = 0
        self.resultados = None
        
        # Load custom fonts
        self.load_fonts()
        
        self.initUI()
        self.aplicar_tema()
        self.animate_startup()

    def load_fonts(self):
        # This would normally load custom fonts, but we'll use system fonts for compatibility
        pass

    def initUI(self):
        self.setWindowTitle("Leitor de Gabaritos IDEEDUTEC")
        self.setMinimumSize(1200, 800)
        QApplication.instance().setFont(QFont("Segoe UI", 10))

        # Status Bar
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Pronto")
        self.statusbar.setStyleSheet("""
            QStatusBar {
                background-color: #f8fafc;
                color: #64748b;
                border-top: 1px solid #e2e8f0;
                padding: 5px;
            }
        """)

        # Toolbar with modern design
        toolbar = QToolBar("Barra de Ferramentas")
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                           stop:0 #10b981, stop:1 #059669);
                spacing: 10px; 
                padding: 8px 15px; 
                border-bottom: 1px solid #047857;
            }
            QToolButton { 
                background-color: transparent; 
                border: none; 
                border-radius: 6px; 
                padding: 8px; 
                color: white;
            }
            QToolButton:hover { 
                background-color: rgba(255,255,255,0.2); 
            }
            QToolButton:pressed { 
                background-color: rgba(255,255,255,0.3); 
            }
        """)
        self.addToolBar(toolbar)

        # Header with logo and title - MODIFIED SECTION
        header = QWidget()
        hl = QHBoxLayout(header)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(15)
        
        # Logo without circular background
        lbl_logo = QLabel()
        pix = QPixmap("assets/ideedutec_icon.png").scaled(45, 45, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        lbl_logo.setPixmap(pix)
        lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(lbl_logo)
        
        lbl_title = QLabel("Sistema de Avaliação Diagnóstico")
        lbl_title.setStyleSheet("color:white; font-size:20px; font-weight:bold;")
        hl.addWidget(lbl_title)
        
        # PDF Filler button in header
        btn_filler_header = ModernButton("Gabarito Preenchido", "file-text", False)
        btn_filler_header.setFixedHeight(40)
        btn_filler_header.clicked.connect(self.abrir_pdf_filler)
        btn_filler_header.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,0.2);
                color: white;
                border: 1px solid rgba(255,255,255,0.3);
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,0.3);
            }
            QPushButton:pressed {
                background-color: rgba(255,255,255,0.4);
            }
        """)
        
        hl.addStretch()
        hl.addWidget(btn_filler_header)
        toolbar.addWidget(header)

        # Main content area
        main = QWidget()
        main.setStyleSheet("""
            QWidget {
                background-color: #f8fafc;
            }
        """)
        ml = QVBoxLayout(main)
        ml.setContentsMargins(20, 20, 20, 20)
        ml.setSpacing(20)

        # Info cards with modern design
        self.card_pdfs = InfoCard("PDFs Selecionados", "0", "file-text", "#3b82f6")
        self.card_quest = InfoCard("Total de Páginas", "0", "layers", "#10b981")
        self.card_status = InfoCard("Status", "Aguardando", "activity", "#f59e0b")
        
        info_layout = QHBoxLayout()
        info_layout.setSpacing(15)
        info_layout.addWidget(self.card_pdfs)
        info_layout.addWidget(self.card_quest)
        info_layout.addWidget(self.card_status)
        ml.addLayout(info_layout)

        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #e2e8f0;
            }
        """)

        # Left panel - Document selection
        left = QFrame()
        left.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
            }
        """)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(20, 20, 20, 20)
        ll.setSpacing(15)
        
        # Document selection header
        doc_header = QWidget()
        doc_header_layout = QHBoxLayout(doc_header)
        doc_header_layout.setContentsMargins(0, 0, 0, 0)
        
        doc_icon = QLabel()
        doc_icon.setPixmap(IconProvider.get_icon("file-text", "#3b82f6", 24).pixmap(24, 24))
        
        doc_title = QLabel("Documentos Selecionados")
        doc_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e293b;")
        
        doc_header_layout.addWidget(doc_icon)
        doc_header_layout.addWidget(doc_title)
        doc_header_layout.addStretch()
        
        ll.addWidget(doc_header)
        
        # Document scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                background-color: #f8fafc;
            }
            QScrollBar:vertical {
                border: none;
                background: #f1f5f9;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #cbd5e1;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)
        
        cont = QWidget()
        self.thumb_layout = QGridLayout(cont)
        self.thumb_layout.setContentsMargins(15, 15, 15, 15)
        self.thumb_layout.setSpacing(15)
        self.scroll_area.setWidget(cont)
        ll.addWidget(self.scroll_area)
        
        # Document selection buttons
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)
        
        btn_sel = ModernButton("Selecionar PDFs", "file-plus", True)
        btn_sel.clicked.connect(self.selecionar_pdfs)
        
        btn_vis = ModernButton("Visualizar Selecionados", "eye", False)
        btn_vis.clicked.connect(self.open_selected_dialog)
        
        btn_layout.addWidget(btn_sel)
        btn_layout.addWidget(btn_vis)
        
        ll.addWidget(btn_container)

        # Right panel - Processing configuration
        right = QFrame()
        right.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
            }
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: none;
                margin-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #1e293b;
            }
            QComboBox {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 8px 15px;
                background-color: #f8fafc;
                color: #334155;
                min-height: 20px;
            }
            QComboBox:focus {
                border-color: #3b82f6;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: none;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #cbd5e1;
                height: 8px;
                background: #f1f5f9;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #3b82f6;
                border: none;
                width: 18px;
                height: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #2563eb;
            }
            QLabel {
                color: #334155;
            }
        """)
        
        rl = QVBoxLayout(right)
        rl.setContentsMargins(20, 20, 20, 20)
        rl.setSpacing(20)
        
        # Configuration header
        config_header = QWidget()
        config_header_layout = QHBoxLayout(config_header)
        config_header_layout.setContentsMargins(0, 0, 0, 0)
        
        config_icon = QLabel()
        config_icon.setPixmap(IconProvider.get_icon("settings", "#10b981", 24).pixmap(24, 24))
        
        config_title = QLabel("Configurações de Processamento")
        config_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e293b;")
        
        config_header_layout.addWidget(config_icon)
        config_header_layout.addWidget(config_title)
        config_header_layout.addStretch()
        
        rl.addWidget(config_header)
        
        # Configuration form
        form_container = QFrame()
        form_container.setStyleSheet("""
            QFrame {
                background-color: #f8fafc;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        form = QFormLayout(form_container)
        form.setContentsMargins(15, 15, 15, 15)
        form.setSpacing(15)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # Number of alternatives
        alt_label = QLabel("Número de alternativas:")
        alt_label.setStyleSheet("font-weight: bold;")
        
        self.combo_alt = QComboBox()
        self.combo_alt.addItem("4 alternativas (A–D)", 4)
        self.combo_alt.addItem("5 alternativas (A–E)", 5)
        
        form.addRow(alt_label, self.combo_alt)
        
        # Resolution
        res_label = QLabel("Resolução de processamento:")
        res_label.setStyleSheet("font-weight: bold;")
        
        self.res_combo = QComboBox()
        self.res_combo.addItems(["Alta (300 DPI)", "Média (200 DPI)", "Baixa (150 DPI)"])
        
        form.addRow(res_label, self.res_combo)
        
        # Threshold slider
        thr_label = QLabel("Limiar de preenchimento:")
        thr_label.setStyleSheet("font-weight: bold;")
        
        slider_container = QWidget()
        slider_layout = QHBoxLayout(slider_container)
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.setSpacing(10)
        
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(10, 70)
        v = int(self.config.get("threshold_fill", 0.3) * 100)
        self.slider.setValue(v)
        
        self.lbl_thr = QLabel(f"{v / 100:.2f}")
        self.lbl_thr.setStyleSheet("font-weight: bold; color: #3b82f6; min-width: 40px;")
        
        self.slider.valueChanged.connect(lambda x: self.lbl_thr.setText(f"{x / 100:.2f}"))
        
        slider_layout.addWidget(self.slider)
        slider_layout.addWidget(self.lbl_thr)
        
        form.addRow(thr_label, slider_container)
        
        rl.addWidget(form_container)
        
        # Progress section
        progress_container = QFrame()
        progress_container.setStyleSheet("""
            QFrame {
                background-color: #f8fafc;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(15, 15, 15, 15)
        progress_layout.setSpacing(10)
        
        progress_header = QWidget()
        progress_header_layout = QHBoxLayout(progress_header)
        progress_header_layout.setContentsMargins(0, 0, 0, 0)     
        
        progress_title = QLabel("Progresso:")
        progress_title.setStyleSheet("font-weight: bold;")
        
        progress_header_layout.addWidget(progress_title)
        progress_header_layout.addStretch()
        
        progress_layout.addWidget(progress_header)
        
        self.progress = ModernProgressBar()
        self.progress.setValue(0)
        
        progress_layout.addWidget(self.progress)
        
        rl.addWidget(progress_container)
        
        # Process button
        btn_proc = ModernButton("Iniciar Processamento", "play", True)
        btn_proc.clicked.connect(self.processar_gabarito)
        
        rl.addWidget(btn_proc, alignment=Qt.AlignmentFlag.AlignCenter)
        rl.addStretch()

        # Add panels to splitter
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([400, 700])
        ml.addWidget(splitter)

        # Status indicator
        status_bar = QFrame()
        status_bar.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #e2e8f0;
            }
        """)
        
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(15, 10, 15, 10)
        
        status_icon = QLabel()
        status_icon.setPixmap(IconProvider.get_icon("info", "#64748b", 16).pixmap(16, 16))
        
        self.lbl_status = QLabel("Status: Aguardando seleção de PDFs")
        self.lbl_status.setStyleSheet("color: #64748b;")
        
        status_layout.addWidget(status_icon)
        status_layout.addWidget(self.lbl_status)
        status_layout.addStretch()
        
        ml.addWidget(status_bar)
        
        self.setCentralWidget(main)

    def abrir_pdf_filler(self):
        dlg = PDFFillerWindow(self)  # Nova versão sem precisar de resultados
        dlg.exec()

    def open_selected_dialog(self):
        if not self.pdf_paths:
            QMessageBox.warning(self, "Erro", "Nenhum PDF selecionado.")
            return
        dlg = SelectedPDFsDialog(self.pdf_paths, parent=self)
        dlg.exec()

    def animate_startup(self):
        # Animate the info cards with a fade-in effect
        cards = [self.card_pdfs, self.card_quest, self.card_status]
        for i, c in enumerate(cards):
            eff = QGraphicsOpacityEffect(c)
            c.setGraphicsEffect(eff)
            eff.setOpacity(0)
            anim = QPropertyAnimation(eff, b"opacity", self)
            anim.setDuration(600 + i * 100)
            anim.setStartValue(0)
            anim.setEndValue(1)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.start()

    def aplicar_tema(self):
        # Apply a modern theme to the entire application
        QApplication.instance().setStyleSheet("""
            QMainWindow { 
                background-color: #f8fafc; 
            }
            QLabel { 
                font-size: 14px; 
                color: #334155; 
            }
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                margin-top: 20px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #1e293b;
            }
        """)

    def atualizar_status(self, txt):
        self.lbl_status.setText(f"Status: {txt}")
        self.statusbar.showMessage(txt)
        self.card_status.set_value(txt)

    def selecionar_pdfs(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Selecione PDFs", "", "PDF (*.pdf)")
        if not files:
            return
        self.pdf_paths = files
        self.card_pdfs.set_value(len(files))
        for i in reversed(range(self.thumb_layout.count())):
            w = self.thumb_layout.itemAt(i).widget()
            if w:
                w.deleteLater()
        self.threads_restantes = len(files)
        self.total_paginas = 0
        self.atualizar_status(f"Carregando {len(files)} PDF(s)...")
        row = col = 0
        for idx, path in enumerate(files):
            thumb = PDFThumbnail(path, idx)
            thumb.clicked.connect(lambda p=path: self.show_pdf_preview(p))
            self.thumb_layout.addWidget(thumb, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1
            loader = PDFLoaderWorker(path)
            loader.signals.finished.connect(self.on_loader_finished)
            loader.signals.error.connect(self.on_loader_error)
            self.threadpool.start(loader)
        self.thumb_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding), row + 1, 0, 1, 3)

    def show_pdf_preview(self, pdf_path):
        dlg = PDFPreviewDialog(pdf_path, parent=self)
        dlg.exec()

    def on_loader_finished(self, path, n):
        self.threads_restantes -= 1
        self.total_paginas += n
        if self.threads_restantes == 0:
            self.card_quest.set_value(self.total_paginas)
            self.atualizar_status("Todos os PDFs carregados.")

    def on_loader_error(self, msg):
        QMessageBox.warning(self, "Erro ao carregar PDF", msg)

    def processar_gabarito(self):
        if not self.pdf_paths:
            QMessageBox.warning(self, "Erro", "Nenhum PDF selecionado.")
            return
        self.atualizar_status("Processando gabaritos...")
        self.progress.setValue(5)
        self.config["threshold_fill"] = self.slider.value() / 100
        res_txt = self.res_combo.currentText()
        dpi = 300 if "300" in res_txt else 200 if "200" in res_txt else 150
        worker = ProcessWorker(
            pdf_paths=self.pdf_paths,
            config=self.config,
            n_alternativas=self.combo_alt.currentData(),
            dpi_escolhido=dpi
        )
        worker.signals.progress.connect(self.progress.setValue)
        worker.signals.message.connect(self.atualizar_status)
        worker.signals.error.connect(lambda e: QMessageBox.critical(self, "Erro", e))
        worker.signals.finished.connect(self.on_process_finished)
        self.threadpool.start(worker)

    def on_process_finished(self, all_pages):
        self.progress.setValue(90)
        if not all_pages:
            self.progress.setValue(100)
            self.atualizar_status("Processamento concluído (sem resultados).")
            return
        self.resultados = all_pages
        dlg = ResultadoDialog(all_pages, self)
        dlg.exec()
        reply = QMessageBox.question(self, "Exportar", "Deseja exportar os resultados para Excel?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            path, _ = QFileDialog.getSaveFileName(self, "Salvar Planilha", "", "XLSX (*.xlsx)")
            if path:
                importar_para_planilha(all_pages, path)
                QMessageBox.information(self, "Sucesso", f"Dados importados em:\n{path}")
        self.progress.setValue(100)
        self.atualizar_status("Processamento concluído com sucesso.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    import json
    cfg = json.load(open("config.json", encoding="utf-8"))
    window = GabaritoApp(cfg)
    window.show()
    sys.exit(app.exec())
