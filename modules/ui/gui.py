# modules/ui/gui.py

import sys
import os
from PyQt6.QtCore import (
    Qt, QSize, QPropertyAnimation, QEasingCurve,
    QThreadPool, QRunnable, pyqtSignal, QObject
)
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QStatusBar, QFileDialog,
    QWidget, QVBoxLayout, QLabel, QScrollArea, QGroupBox, QGridLayout,
    QSplitter, QFormLayout, QComboBox, QSlider, QHBoxLayout, QMessageBox,
    QToolButton, QGraphicsOpacityEffect, QSpacerItem, QSizePolicy,
    QDialog, QPushButton
)

from modules.core.converter import converter_pdf_em_imagens
from modules.core.workers import ProcessWorker
from modules.core.dialogs import ResultadoDialog
from modules.core.exporter import importar_para_planilha
from modules.ui.pdf_thumbnail import PDFThumbnail
from modules.ui.pdf_preview import PDFPreviewDialog
from modules.ui.modern_widgets import ModernButton, ModernProgressBar, InfoCard
from modules.ui.icon_provider import IconProvider


class PDFLoaderSignals(QObject):
    """Sinais para indicar quando terminou de carregar ou ocorreu erro."""
    finished = pyqtSignal(str, int)
    error = pyqtSignal(str)


class PDFLoaderWorker(QRunnable):
    """Worker para carregar/contar páginas de um PDF em segundo plano."""
    def __init__(self, pdf_path):
        super().__init__()
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
    """
    Diálogo para exibir todos os PDFs selecionados como miniaturas clicáveis.
    """
    def __init__(self, pdf_paths, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PDFs Selecionados")
        self.resize(800, 600)
        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(10)

        for idx, path in enumerate(pdf_paths):
            thumb = PDFThumbnail(path, idx, parent=self)
            thumb.clicked.connect(lambda p=path: self.open_preview(p))
            row, col = divmod(idx, 4)  # 4 colunas
            grid.addWidget(thumb, row, col)

        scroll.setWidget(container)
        layout.addWidget(scroll)

        btn_close = QPushButton("Fechar")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignCenter)

    def open_preview(self, pdf_path):
        dlg = PDFPreviewDialog(
            pdf_path,
            parent=self
        )
        dlg.exec()


class GabaritoApp(QMainWindow):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.pdf_paths = []
        self.threadpool = QThreadPool()
        self.threads_restantes = 0
        self.total_paginas = 0

        self.initUI()
        self.aplicar_tema()
        self.animate_startup()

    def initUI(self):
        self.setWindowTitle("Leitor de Gabaritos IDEEDUTEC")
        self.setMinimumSize(1200, 800)
        QApplication.instance().setFont(QFont("Segoe UI", 10))

        # Status bar
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Pronto")

        # Toolbar
        toolbar = QToolBar("Barra de Ferramentas")
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar { background-color: #10b981; spacing: 10px; padding: 5px 10px; }
            QToolButton { background-color: transparent; border: none; border-radius: 6px; padding: 8px; }
            QToolButton:hover { background-color: rgba(255,255,255,0.2); }
            QToolButton:pressed { background-color: rgba(255,255,255,0.3); }
        """)
        self.addToolBar(toolbar)

        # Header
        header = QWidget()
        hl = QHBoxLayout(header)
        hl.setContentsMargins(0,0,0,0)
        pix = QPixmap("assets/ideedutec_icon.png").scaled(64,64,Qt.AspectRatioMode.KeepAspectRatio)
        lbl_logo = QLabel(); lbl_logo.setPixmap(pix)
        hl.addWidget(lbl_logo)
        lbl_title = QLabel("Sistema de Correção para Avaliações Diagnósticas")
        lbl_title.setStyleSheet("color:white; font-size:18px; font-weight:bold;")
        hl.addWidget(lbl_title)
        hl.addStretch()
        toolbar.addWidget(header)

        # Info cards
        self.card_pdfs   = InfoCard("PDFs Selecionados", "0",   "pdf",     "#3b82f6")
        self.card_quest  = InfoCard("Total de Páginas",   "0",   "question","#10b981")
        self.card_status = InfoCard("Status",              "Aguardando","status","#f59e0b")
        info_layout = QHBoxLayout()
        info_layout.addWidget(self.card_pdfs)
        info_layout.addWidget(self.card_quest)
        info_layout.addWidget(self.card_status)

        # Splitter left/right
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)

        # Left panel: thumbnails
        left = QWidget()
        ll = QVBoxLayout(left); ll.setContentsMargins(0,0,0,0)
        grp = QGroupBox("Documentos Selecionados")
        gl = QVBoxLayout(grp); gl.setContentsMargins(15,25,15,15)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        cont = QWidget()
        self.thumb_layout = QGridLayout(cont)
        self.thumb_layout.setContentsMargins(10,10,10,10)
        self.thumb_layout.setSpacing(20)
        self.scroll_area.setWidget(cont)
        btn_sel = ModernButton("Selecionar PDFs", primary=True)
        btn_sel.clicked.connect(self.selecionar_pdfs)
        btn_vis = ModernButton("Visualizar Selecionados", primary=False)
        btn_vis.clicked.connect(self.open_selected_dialog)
        gl.addWidget(self.scroll_area)
        gl.addWidget(btn_sel, alignment=Qt.AlignmentFlag.AlignCenter)
        gl.addWidget(btn_vis, alignment=Qt.AlignmentFlag.AlignCenter)
        ll.addWidget(grp)

        # Right panel: config & process
        right = QWidget()
        rl = QVBoxLayout(right); rl.setContentsMargins(0,0,0,0)
        grp2 = QGroupBox("Configurações de Processamento")
        gl2 = QVBoxLayout(grp2); gl2.setContentsMargins(20,30,20,20)
        form = QFormLayout(); form.setVerticalSpacing(20)
        self.combo_alt = QComboBox()
        self.combo_alt.addItem("4 alternativas (A–D)", 4)
        self.combo_alt.addItem("5 alternativas (A–E)", 5)
        form.addRow(QLabel("Número de alternativas:"), self.combo_alt)
        self.res_combo = QComboBox()
        self.res_combo.addItems(["Alta (300 DPI)","Média (200 DPI)","Baixa (150 DPI)"])
        form.addRow(QLabel("Resolução de processamento:"), self.res_combo)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(10,70)
        v = int(self.config.get("threshold_fill",0.3)*100)
        self.slider.setValue(v)
        self.lbl_thr = QLabel(f"{v/100:.2f}")
        self.slider.valueChanged.connect(lambda x: self.lbl_thr.setText(f"{x/100:.2f}"))
        hl_thr = QHBoxLayout(); hl_thr.addWidget(self.slider); hl_thr.addWidget(self.lbl_thr)
        form.addRow(QLabel("Limiar de preenchimento:"), hl_thr)
        gl2.addLayout(form)

        prog_layout = QVBoxLayout()
        prog_layout.addWidget(QLabel("Progresso:"))
        self.progress = ModernProgressBar()
        self.progress.setValue(0)
        prog_layout.addWidget(self.progress)
        gl2.addLayout(prog_layout)

        btn_proc = ModernButton("Iniciar Processamento", primary=True)
        btn_proc.clicked.connect(self.processar_gabarito)
        gl2.addWidget(btn_proc, alignment=Qt.AlignmentFlag.AlignCenter)
        rl.addWidget(grp2)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([400,700])

        # Main layout
        main = QWidget()
        ml = QVBoxLayout(main)
        ml.setContentsMargins(20,20,20,20)
        ml.setSpacing(20)
        ml.addLayout(info_layout)
        ml.addWidget(splitter)

        # Bottom status
        st = QWidget()
        stl = QHBoxLayout(st)
        icon = QLabel()
        icon.setPixmap(IconProvider.get_icon("info","#64748b",16).pixmap(16,16))
        stl.addWidget(icon)
        self.lbl_status = QLabel("Status: Aguardando seleção de PDFs")
        stl.addWidget(self.lbl_status)
        stl.addItem(QSpacerItem(0,0,QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Minimum))
        ml.addWidget(st)

        self.setCentralWidget(main)

    def open_selected_dialog(self):
        if not self.pdf_paths:
            QMessageBox.warning(self, "Erro", "Nenhum PDF selecionado.")
            return
        dlg = SelectedPDFsDialog(self.pdf_paths, parent=self)
        dlg.exec()

    def animate_startup(self):
        cards = [self.card_pdfs, self.card_quest, self.card_status]
        for i, c in enumerate(cards):
            eff = QGraphicsOpacityEffect(c)
            c.setGraphicsEffect(eff)
            eff.setOpacity(0)
            anim = QPropertyAnimation(eff, b"opacity", self)
            anim.setDuration(600 + i*100)
            anim.setStartValue(0)
            anim.setEndValue(1)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.start()

    def aplicar_tema(self):
        QApplication.instance().setStyleSheet("""
            QMainWindow { background-color: #f8fafc; }
            QLabel { font-size: 14px; color: #0f172a; }
        """)

    def atualizar_status(self, txt):
        self.lbl_status.setText(f"Status: {txt}")
        self.statusbar.showMessage(txt)
        self.card_status.set_value(txt)

    def selecionar_pdfs(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Selecione PDFs", "", "PDF (*.pdf)"
        )
        if not files:
            return

        # Atualiza lista e miniaturas
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

        # Espaçador para scroll
        self.thumb_layout.addItem(
            QSpacerItem(20,20,QSizePolicy.Policy.Minimum,QSizePolicy.Policy.Expanding),
            row+1,0,1,3
        )

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

        dlg = ResultadoDialog(all_pages, self)
        dlg.exec()

        reply = QMessageBox.question(
            self, "Exportar", "Deseja exportar os resultados para Excel?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            path, _ = QFileDialog.getOpenFileName(self, "Selecione a Planilha", "", "XLSX (*.xlsx)")
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
    window.showFullScreen()
    sys.exit(app.exec())
