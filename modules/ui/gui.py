import sys
import os
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QIcon, QPixmap
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

class GabaritoApp(QMainWindow):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.pdf_paths = []

        from PyQt6.QtCore import QThreadPool
        self.threadpool = QThreadPool()
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
        self.statusbar.setStyleSheet("""
            QStatusBar {
                background-color: #f8fafc;
                color: #64748b;
                border-top: 1px solid #e2e8f0;
                padding: 4px;
                font-size: 13px;
            }
        """)

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
            logo_pixmap.scaled(
                64, 64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        )
        header_layout.addWidget(logo_label)

        title_label = QLabel("Sistema de Correção para Avaliações Diagnósticas")
        title_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        historico_button = QToolButton()
        historico_button.setText("Histórico")
        historico_button.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        header_layout.addWidget(historico_button)

        profile_label = QLabel()
        profile_pixmap = QPixmap("assets/profile_icon.png")
        profile_label.setPixmap(
            profile_pixmap.scaled(
                32, 32,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        )
        header_layout.addWidget(profile_label)

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
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #e2e8f0;
                border-radius: 4px;
            }
            QSplitter::handle:hover {
                background-color: #cbd5e1;
            }
        """)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        grp_pdfs = QGroupBox("Documentos Selecionados")
        grp_pdfs.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #334155;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                margin-top: 15px;
                padding: 15px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
                background-color: #ffffff;
            }
        """)

        grp_pdfs_layout = QVBoxLayout(grp_pdfs)
        grp_pdfs_layout.setContentsMargins(15, 25, 15, 15)
        grp_pdfs_layout.setSpacing(15)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #f1f5f9;
                width: 10px;
                border-radius: 5px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #94a3b8;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #64748b;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.thumb_container = QWidget()
        self.thumb_layout = QGridLayout(self.thumb_container)
        self.thumb_layout.setContentsMargins(10, 10, 10, 10)
        self.thumb_layout.setSpacing(20)
        self.scroll_area.setWidget(self.thumb_container)
        grp_pdfs_layout.addWidget(self.scroll_area)

        self.btn_selecionar = ModernButton(
            "Selecionar PDFs",
            primary=True
        )
        self.btn_selecionar.clicked.connect(self.selecionar_pdfs)
        grp_pdfs_layout.addWidget(self.btn_selecionar, alignment=Qt.AlignmentFlag.AlignCenter)

        left_layout.addWidget(grp_pdfs)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        grp_config = QGroupBox("Configurações de Processamento")
        grp_config.setStyleSheet(grp_pdfs.styleSheet())
        grp_config_layout = QVBoxLayout(grp_config)
        grp_config_layout.setContentsMargins(20, 30, 20, 20)
        grp_config_layout.setSpacing(20)

        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(20)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)

        self.combo_alternativas = QComboBox()
        self.combo_alternativas.addItem("4 alternativas (A–D)", 4)
        self.combo_alternativas.addItem("5 alternativas (A–E)", 5)
        self.combo_alternativas.setStyleSheet("""
            QComboBox {
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 8px 15px;
                background-color: #f8fafc;
                color: #334155;
                min-height: 40px;
                font-size: 14px;
            }
            QComboBox:hover {
                border-color: #94a3b8;
            }
            QComboBox:focus {
                border-color: #3b82f6;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 20px;
                border: none;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                background-color: #ffffff;
                selection-background-color: #e2e8f0;
                selection-color: #334155;
            }
        """)
        alt_label = QLabel("Número de alternativas:")
        alt_label.setStyleSheet("font-size: 14px; color: #334155; font-weight: bold;")
        form_layout.addRow(alt_label, self.combo_alternativas)

        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["Alta (300 DPI)", "Média (200 DPI)", "Baixa (150 DPI)"])
        self.resolution_combo.setStyleSheet(self.combo_alternativas.styleSheet())
        res_label = QLabel("Resolução de processamento:")
        res_label.setStyleSheet("font-size: 14px; color: #334155; font-weight: bold;")
        form_layout.addRow(res_label, self.resolution_combo)

        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setMinimum(10)
        self.threshold_slider.setMaximum(70)
        val_slider = int(self.config.get("threshold_fill", 0.3) * 100)
        self.threshold_slider.setValue(val_slider)
        self.threshold_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.threshold_slider.setTickInterval(10)
        self.threshold_slider.setStyleSheet("""
            QSlider {
                height: 30px;
            }
            QSlider::groove:horizontal {
                height: 8px;
                background-color: #e2e8f0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background-color: #10b981;
                border: none;
                width: 18px;
                height: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background-color: #0ea172;
            }
            QSlider::sub-page:horizontal {
                background-color: #93c5fd;
                border-radius: 4px;
            }
        """)
        thr_layout = QHBoxLayout()
        thr_layout.addWidget(self.threshold_slider)
        self.threshold_label = QLabel(f"{val_slider/100:.2f}")
        self.threshold_label.setStyleSheet("font-size: 14px; color: #334155; font-weight: bold; min-width: 40px;")
        thr_layout.addWidget(self.threshold_label)
        self.threshold_slider.valueChanged.connect(
            lambda v: self.threshold_label.setText(f"{v/100:.2f}")
        )
        thr_title = QLabel("Limiar de preenchimento:")
        thr_title.setStyleSheet("font-size: 14px; color: #334155; font-weight: bold;")
        form_layout.addRow(thr_title, thr_layout)

        grp_config_layout.addLayout(form_layout)

        progress_layout = QVBoxLayout()
        progress_label = QLabel("Progresso:")
        progress_label.setStyleSheet("font-size: 14px; color: #334155; font-weight: bold;")
        progress_layout.addWidget(progress_label)
        self.progress_bar = ModernProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        grp_config_layout.addLayout(progress_layout)

        self.btn_processar = ModernButton(
            "Iniciar Processamento",
            primary=True
        )
        self.btn_processar.clicked.connect(self.processar_gabarito)
        grp_config_layout.addWidget(self.btn_processar, alignment=Qt.AlignmentFlag.AlignCenter)

        right_layout.addWidget(grp_config)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 700])
        main_layout.addWidget(splitter)

        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)

        status_icon = QLabel()
        status_icon.setPixmap(IconProvider.get_icon("info", "#64748b").pixmap(16, 16))
        status_layout.addWidget(status_icon)

        self.status_label = QLabel("Status: Aguardando seleção de PDFs")
        self.status_label.setStyleSheet("color: #64748b; font-size: 14px; padding: 5px;")
        status_layout.addWidget(self.status_label)

        status_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        main_layout.addWidget(status_container)

    def animate_startup(self):
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        cards = [self.card_pdfs, self.card_questoes, self.card_status]
        for i, card in enumerate(cards):
            effect = QGraphicsOpacityEffect(card)
            card.setGraphicsEffect(effect)
            effect.setOpacity(0.0)
            anim = QPropertyAnimation(effect, b"opacity", self)
            anim.setDuration(600 + i * 100)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.start()

    def aplicar_tema(self):
        from PyQt6.QtWidgets import QApplication
        style = self.get_light_style()
        app = QApplication.instance()
        app.setStyleSheet(style)

    def get_light_style(self):
        return """
            QMainWindow { background-color: #f8fafc; }
            QLabel { font-size: 14px; color: #0f172a; }
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #334155;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                margin-top: 15px;
                padding: 15px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
                background-color: #ffffff;
            }
            QComboBox {
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 8px 15px;
                background-color: #f8fafc;
                color: #334155;
                min-height: 40px;
                font-size: 14px;
            }
            QComboBox:hover { border-color: #94a3b8; }
            QComboBox:focus { border-color: #10b981; }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 20px;
                border: none;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                background-color: #ffffff;
                selection-background-color: #e2e8f0;
                selection-color: #334155;
            }
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #0ea172; }
            QPushButton:pressed { background-color: #0c8f68; }
            QPushButton:disabled {
                background-color: #94a3b8;
                color: #e2e8f0;
            }
            QProgressBar {
                border: none;
                border-radius: 6px;
                text-align: center;
                background-color: #e2e8f0;
                color: transparent;
                height: 12px;
            }
            QProgressBar::chunk {
                border-radius: 6px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #10b981, stop:1 #0ea172);
            }
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical {
                border: none;
                background-color: #f1f5f9;
                width: 10px;
                border-radius: 5px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #94a3b8;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover { background-color: #64748b; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QStatusBar {
                background-color: #f8fafc;
                color: #64748b;
                border-top: 1px solid #e2e8f0;
                padding: 4px;
                font-size: 13px;
            }
        """

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
        self.atualizar_status(f"{len(files)} arquivo(s) selecionado(s).")
        self.card_pdfs.set_value(len(files))

        total_paginas = 0
        for pdf in files:
            try:
                paginas = converter_pdf_em_imagens(pdf, dpi=50)
                total_paginas += len(paginas)
            except Exception as e:
                total_paginas += 0  

        self.card_questoes.set_value(total_paginas)

        # Limpa os thumbnails
        for i in reversed(range(self.thumb_layout.count())):
            item = self.thumb_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        # Exibe thumbnails/miniaturas dos PDFs(ainda em produção)
        row, col = 0, 0
        max_cols = 3
        for idx, p in enumerate(files):
            thumb = PDFThumbnail(p, idx)
            self.thumb_layout.addWidget(thumb, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        self.thumb_layout.addItem(
            QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding),
            row+1, 0, 1, max_cols
        )

    def processar_gabarito(self):
        if not self.pdf_paths:
            error_box = QMessageBox(self)
            error_box.setWindowTitle("Erro")
            error_box.setIcon(QMessageBox.Icon.Warning)
            error_box.setText("Nenhum PDF selecionado.")
            error_box.setStyleSheet("""
                QMessageBox { background-color: #ffffff; }
                QLabel { color: #334155; font-size: 14px; }
                QPushButton {
                    background-color: #2563eb;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 14px;
                }
                QPushButton:hover { background-color: #1d4ed8; }
            """)
            error_box.exec()
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
        error_box = QMessageBox(self)
        error_box.setWindowTitle("Erro")
        error_box.setIcon(QMessageBox.Icon.Critical)
        error_box.setText(e)
        error_box.setStyleSheet("""
            QMessageBox { background-color: #ffffff; }
            QLabel { color: #ef4444; font-size: 14px; }
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        error_box.exec()
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
        export_box.setStyleSheet("""
            QMessageBox { background-color: #ffffff; }
            QLabel { color: #334155; font-size: 14px; }
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
                min-width: 100px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
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
                success_box = QMessageBox(self)
                success_box.setWindowTitle("Sucesso")
                success_box.setIcon(QMessageBox.Icon.Information)
                success_box.setText(f"Dados importados em:\n{caminho_planilha}")
                success_box.setStyleSheet("""
                    QMessageBox { background-color: #ffffff; }
                    QLabel { color: #334155; font-size: 14px; }
                    QPushButton {
                        background-color: #2563eb;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        padding: 8px 16px;
                        font-size: 14px;
                    }
                    QPushButton:hover { background-color: #1d4ed8; }
                """)
                success_box.exec()

        self.progress_bar.setValue(100)
        self.atualizar_status("Processamento concluído com sucesso.")
        self.btn_processar.setEnabled(True)


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
    window.show()
    sys.exit(app.exec())