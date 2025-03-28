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
    QToolButton, QGraphicsOpacityEffect, QSpacerItem, QSizePolicy
)

from modules.core.converter import converter_pdf_em_imagens
from modules.core.workers import ProcessWorker
from modules.core.dialogs import ResultadoDialog
from modules.ui.pdf_thumbnail import PDFThumbnail
from modules.core.exporter import importar_para_planilha
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

        font = QFont("Segoe UI", 10)
        QApplication.instance().setFont(font)

        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Pronto")

        toolbar = QToolBar("Barra de Ferramentas")
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar {
                background-color: #10b981;
                spacing: 10px;
                padding: 5px 10px;
            }
            QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 8px;
            }
            QToolButton:hover {
                background-color: rgba(255,255,255,0.2);
            }
            QToolButton:pressed {
                background-color: rgba(255,255,255,0.3);
            }
        """)
        self.addToolBar(toolbar)

        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        logo_label = QLabel()
        logo_pixmap = QPixmap("assets/ideedutec_icon.png")
        logo_label.setPixmap(
            logo_pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        )
        header_layout.addWidget(logo_label)

        title_label = QLabel("Sistema de Correção para Avaliações Diagnósticas")
        title_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        toolbar.addWidget(header_widget)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        self.card_pdfs = InfoCard("PDFs Selecionados", "0", "pdf", "#3b82f6")
        self.card_questoes = InfoCard("Total de Páginas", "0", "question", "#10b981")
        self.card_status = InfoCard("Status", "Aguardando", "status", "#f59e0b")

        info_cards_layout = QHBoxLayout()
        info_cards_layout.addWidget(self.card_pdfs)
        info_cards_layout.addWidget(self.card_questoes)
        info_cards_layout.addWidget(self.card_status)
        main_layout.addLayout(info_cards_layout)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        grp_pdfs = QGroupBox("Documentos Selecionados")
        grp_pdfs_layout = QVBoxLayout(grp_pdfs)
        grp_pdfs_layout.setContentsMargins(15, 25, 15, 15)
        grp_pdfs_layout.setSpacing(15)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.thumb_container = QWidget()
        self.thumb_layout = QGridLayout(self.thumb_container)
        self.thumb_layout.setContentsMargins(10, 10, 10, 10)
        self.thumb_layout.setSpacing(20)
        self.scroll_area.setWidget(self.thumb_container)
        grp_pdfs_layout.addWidget(self.scroll_area)

        self.btn_selecionar = ModernButton("Selecionar PDFs", primary=True)
        self.btn_selecionar.clicked.connect(self.selecionar_pdfs)
        grp_pdfs_layout.addWidget(self.btn_selecionar, alignment=Qt.AlignmentFlag.AlignCenter)

        left_layout.addWidget(grp_pdfs)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        grp_config = QGroupBox("Configurações de Processamento")
        grp_config_layout = QVBoxLayout(grp_config)
        grp_config_layout.setContentsMargins(20, 30, 20, 20)
        grp_config_layout.setSpacing(20)

        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(20)
        self.combo_alternativas = QComboBox()
        self.combo_alternativas.addItem("4 alternativas (A–D)", 4)
        self.combo_alternativas.addItem("5 alternativas (A–E)", 5)
        form_layout.addRow(QLabel("Número de alternativas:"), self.combo_alternativas)

        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["Alta (300 DPI)", "Média (200 DPI)", "Baixa (150 DPI)"])
        form_layout.addRow(QLabel("Resolução de processamento:"), self.resolution_combo)

        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setMinimum(10)
        self.threshold_slider.setMaximum(70)
        val_slider = int(self.config.get("threshold_fill", 0.3)*100)
        self.threshold_slider.setValue(val_slider)
        thr_layout = QHBoxLayout()
        thr_layout.addWidget(self.threshold_slider)
        self.threshold_label = QLabel(f"{val_slider/100:.2f}")
        thr_layout.addWidget(self.threshold_label)
        self.threshold_slider.valueChanged.connect(
            lambda v: self.threshold_label.setText(f"{v/100:.2f}")
        )
        form_layout.addRow(QLabel("Limiar de preenchimento:"), thr_layout)

        grp_config_layout.addLayout(form_layout)

        progress_layout = QVBoxLayout()
        progress_layout.addWidget(QLabel("Progresso:"))
        self.progress_bar = ModernProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        grp_config_layout.addLayout(progress_layout)

        self.btn_processar = ModernButton("Iniciar Processamento", primary=True)
        self.btn_processar.clicked.connect(self.processar_gabarito)
        grp_config_layout.addWidget(self.btn_processar, alignment=Qt.AlignmentFlag.AlignCenter)

        right_layout.addWidget(grp_config)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 700])
        main_layout.addWidget(splitter)

        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_icon = QLabel()
        status_icon.setPixmap(IconProvider.get_icon("info", "#64748b").pixmap(16,16))
        status_layout.addWidget(status_icon)
        self.status_label = QLabel("Status: Aguardando seleção de PDFs")
        status_layout.addWidget(self.status_label)
        status_layout.addItem(QSpacerItem(0,0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        main_layout.addWidget(status_container)

    def animate_startup(self):
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        cards = [self.card_pdfs, self.card_questoes, self.card_status]
        for i, card in enumerate(cards):
            effect = QGraphicsOpacityEffect(card)
            card.setGraphicsEffect(effect)
            effect.setOpacity(0.0)
            anim = QPropertyAnimation(effect, b"opacity", self)
            anim.setDuration(600 + i*100)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.start()

    def aplicar_tema(self):
        style = """
            QMainWindow { background-color: #f8fafc; }
            QLabel { font-size: 14px; color: #0f172a; }
        """
        app = QApplication.instance()
        app.setStyleSheet(style)

    def atualizar_status(self, texto):
        self.status_label.setText(f"Status: {texto}")
        self.statusbar.showMessage(texto)
        self.card_status.set_value(texto)

    def selecionar_pdfs(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Selecione um ou mais PDFs",
            "",
            "Arquivos PDF (*.pdf);;Todos os Arquivos (*)"
        )
        if not files:
            return

        self.pdf_paths = files
        self.card_pdfs.set_value(len(files))

        # Limpa os thubnails
        for i in reversed(range(self.thumb_layout.count())):
            item = self.thumb_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        self.threads_restantes = len(files)
        self.total_paginas = 0
        self.atualizar_status(f"Carregando {len(files)} PDF(s) em segundo plano...")

        row, col = 0, 0
        max_cols = 3
        for idx, pdf_path in enumerate(files):
            thumb = PDFThumbnail(pdf_path, idx)
            self.thumb_layout.addWidget(thumb, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

            loader_worker = PDFLoaderWorker(pdf_path)
            loader_worker.signals.finished.connect(self.on_loader_finished)
            loader_worker.signals.error.connect(self.on_loader_error)
            self.threadpool.start(loader_worker)

        self.thumb_layout.addItem(
            QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding),
            row+1, 0, 1, max_cols
        )

    def on_loader_finished(self, pdf_path, num_paginas):
        self.threads_restantes -= 1
        self.total_paginas += num_paginas
        if self.threads_restantes <= 0:
            self.card_questoes.set_value(self.total_paginas)
            self.atualizar_status("Todos os PDFs carregados (miniaturas e páginas).")

    def on_loader_error(self, msg):
        self.threads_restantes -= 1
        QMessageBox.warning(self, "Erro ao carregar PDF", msg)

    def processar_gabarito(self):
        if not self.pdf_paths:
            QMessageBox.warning(self, "Erro", "Nenhum PDF selecionado.")
            return

        self.atualizar_status("Processando gabaritos...")
        self.btn_processar.setEnabled(False)
        self.progress_bar.setValue(5)
        self.config["threshold_fill"] = self.threshold_slider.value() / 100

        resolucao_texto = self.resolution_combo.currentText()
        if "300" in resolucao_texto:
            dpi_escolhido = 300
        elif "200" in resolucao_texto:
            dpi_escolhido = 200
        else:
            dpi_escolhido = 150

        worker = ProcessWorker(
            pdf_paths=self.pdf_paths,
            config=self.config,
            n_alternativas=self.combo_alternativas.currentData(),
            dpi_escolhido=dpi_escolhido
        )
        worker.signals.progress.connect(self.on_worker_progress)
        worker.signals.message.connect(self.on_worker_message)
        worker.signals.error.connect(self.on_worker_error)
        worker.signals.finished.connect(self.on_worker_finished)
        self.threadpool.start(worker)

    def on_worker_progress(self, val):
        self.progress_bar.setValue(val)

    def on_worker_message(self, msg):
        self.atualizar_status(msg)

    def on_worker_error(self, e):
        QMessageBox.critical(self, "Erro", e)
        self.progress_bar.setValue(0)
        self.btn_processar.setEnabled(True)
        self.atualizar_status("Erro no processamento.")

    def on_worker_finished(self, all_pages):
        self.progress_bar.setValue(90)
        if not all_pages:
            self.progress_bar.setValue(100)
            self.btn_processar.setEnabled(True)
            self.atualizar_status("Processamento concluído (com erros ou sem resultados).")
            return

        dlg = ResultadoDialog(all_pages, self)
        dlg.exec()

        export_box = QMessageBox(self)
        export_box.setWindowTitle("Exportar para Excel")
        export_box.setText("Deseja exportar os resultados para uma planilha?")
        export_box.setIcon(QMessageBox.Icon.Question)
        export_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        resp = export_box.exec()
        if resp == QMessageBox.StandardButton.Yes:
            caminho_planilha, _ = QFileDialog.getOpenFileName(
                self,
                "Selecione a Planilha de Destino",
                "",
                "Excel Files (*.xlsx);;Todos os Arquivos (*)"
            )
            if caminho_planilha:
                importar_para_planilha(all_pages, caminho_planilha)
                QMessageBox.information(self, "Sucesso", f"Dados importados em:\n{caminho_planilha}")

        self.progress_bar.setValue(100)
        self.btn_processar.setEnabled(True)
        self.atualizar_status("Processamento concluído com sucesso.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    config = {
        "threshold_fill": 0.3,
        "grid_rois": [
            [{"x": 100, "y": 100, "width": 200, "height": 50}],
            [{"x": 100, "y": 160, "width": 200, "height": 50}]
        ]
    }
    window = GabaritoApp(config)
    window.setWindowState(Qt.WindowState.WindowFullScreen)
    window.show()
    sys.exit(app.exec())
    
