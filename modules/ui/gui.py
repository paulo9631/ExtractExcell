import sys
import os
from PyQt6.QtCore import (
    Qt, QSize, QPropertyAnimation, QEasingCurve,
    QThreadPool, QRunnable, pyqtSignal, QObject,
    QTimer
)
from PyQt6.QtGui import QFont, QPixmap, QColor, QPalette, QIcon, QFontDatabase
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QStatusBar, QFileDialog,
    QWidget, QVBoxLayout, QLabel, QScrollArea, QGroupBox, QGridLayout,
    QSplitter, QFormLayout, QComboBox, QSlider, QHBoxLayout, QMessageBox,
    QToolButton, QGraphicsOpacityEffect, QSpacerItem, QSizePolicy,
    QDialog, QPushButton, QFrame, QStackedWidget, QLineEdit
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
from modules.utils import resource_path



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

        btn_close = ModernButton("Fechar", "x-circle", False)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignCenter)

    def open_preview(self, pdf_path):
        dlg = PDFPreviewDialog(pdf_path, parent=self)
        dlg.exec()


class GabaritoApp(QMainWindow):
    def __init__(self, config, client=None):
        super().__init__()
        self.client = client
        self.config = config
        self.pdf_paths = []
        self.threadpool = QThreadPool()
        self.threads_restantes = 0
        self.total_paginas = 0
        self.resultados = None

        self.load_fonts()

        self.initUI()
        self.aplicar_tema()
        self.animate_startup()

    def load_fonts(self):
        pass

    def initUI(self):
        self.setWindowTitle(" ")
        self.setMinimumSize(1200, 800)  # Tamanho mínimo da janela
        QApplication.instance().setFont(QFont("Segoe UI", 10))

        # Barra de status
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

        # Barra de ferramentas
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

        # Cabeçalho com logo e título
        header = QWidget()
        hl = QHBoxLayout(header)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(15)

        # Logo à esquerda
        lbl_logo = QLabel()
        pix = QPixmap(resource_path("assets/ideedutec_icon.png")).scaled(45, 45, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        lbl_logo.setPixmap(pix)
        lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(lbl_logo)

        # Título à direita
        lbl_title = QLabel("Sistema de Avaliações Diagnósticas")
        lbl_title.setStyleSheet("color:white; font-size:20px; font-weight:bold;")
        hl.addWidget(lbl_title)

        # Ajusta o layout da toolbar para incluir o cabeçalho
        toolbar.addWidget(header)

        # Layout principal
        main = QWidget()
        main.setStyleSheet("""
            QWidget {
                background-color: #f8fafc;
            }
        """)
        ml = QVBoxLayout(main)
        ml.setContentsMargins(20, 20, 20, 20)
        ml.setSpacing(20)

        # Cards com informações
        self.card_pdfs = InfoCard("PDFs Selecionados", "0", "file-text", "#3b82f6")
        self.card_quest = InfoCard("Total de Páginas", "0", "layers", "#10b981")
        self.card_status = InfoCard("Status", "Aguardando", "activity", "#f59e0b")

        info_layout = QHBoxLayout()
        info_layout.setSpacing(15)
        info_layout.addWidget(self.card_pdfs)
        info_layout.addWidget(self.card_quest)
        info_layout.addWidget(self.card_status)
        ml.addLayout(info_layout)

        # Splitter para separar as áreas
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #e2e8f0;
            }
        """)

        # Configura a parte esquerda
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

        # Configura a parte direita
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
                padding: 6px 12px;
                font-size: 14px;
                min-height: 30px;
            }
            QSlider {
                min-height: 30px;
            }
        """)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(20, 20, 20, 20)

        grp_alt = QGroupBox("Número de alternativas")
        alt_layout = QVBoxLayout(grp_alt)
        self.combo_alt = QComboBox()
        self.combo_alt.addItem("5 alternativas", 5)
        self.combo_alt.addItem("4 alternativas", 4)
        self.combo_alt.setCurrentIndex(0)
        alt_layout.addWidget(self.combo_alt)
        rl.addWidget(grp_alt)

        grp_res = QGroupBox("Resolução de processamento (DPI)")
        res_layout = QVBoxLayout(grp_res)
        self.res_combo = QComboBox()
        self.res_combo.addItem("150 DPI", 150)
        self.res_combo.addItem("200 DPI", 200)
        self.res_combo.addItem("300 DPI", 300)
        self.res_combo.setCurrentIndex(1)
        res_layout.addWidget(self.res_combo)
        rl.addWidget(grp_res)

        grp_thresh = QGroupBox("Threshold de preenchimento (%)")
        thresh_layout = QVBoxLayout(grp_thresh)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(1)
        self.slider.setMaximum(100)
        self.slider.setValue(int(self.config.get("threshold_fill", 0.5)*100))
        self.lbl_thresh = QLabel(f"{self.slider.value()}%")
        self.slider.valueChanged.connect(lambda v: self.lbl_thresh.setText(f"{v}%"))
        thresh_layout.addWidget(self.slider)
        thresh_layout.addWidget(self.lbl_thresh, alignment=Qt.AlignmentFlag.AlignRight)
        rl.addWidget(grp_thresh)

        grp_quest = QGroupBox("Quantidade de Questões")
        quest_layout = QVBoxLayout(grp_quest)
        self.combo_quest = QComboBox()
        self.combo_quest.addItem("10 questões", 10)
        self.combo_quest.addItem("20 questões", 20)
        self.combo_quest.addItem("30 questões", 30)
        self.combo_quest.addItem("40 questões", 40)
        self.combo_quest.setCurrentIndex(1)  # Padrão: 20
        quest_layout.addWidget(self.combo_quest)
        rl.addWidget(grp_quest)
        
        grp_google = QGroupBox("Link do Google Sheets (obrigatório)")
        google_layout = QVBoxLayout(grp_google)
        self.google_sheet_input = QLineEdit()
        self.google_sheet_input.setPlaceholderText("Cole aqui o link do Google Sheets...")
        google_layout.addWidget(self.google_sheet_input)
        rl.addWidget(grp_google)


        self.progress = ModernProgressBar()
        rl.addWidget(self.progress)

        btn_proc = ModernButton("Iniciar Processamento", "play", True)
        btn_proc.clicked.connect(self.processar_gabarito)
        rl.addWidget(btn_proc)
        self.btn_processar = btn_proc

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        ml.addWidget(splitter)

        footer = QLabel("© 2025 IDEEDUTEC - Todos os direitos reservados")
        footer.setStyleSheet("color: #94a3b8; font-size: 12px;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ml.addWidget(footer)

        self.setCentralWidget(main)

        self.lbl_status = QLabel("Status: Aguardando")
        self.lbl_status.setStyleSheet("font-size: 14px; color: #64748b; font-weight: normal;")
        self.statusbar.addPermanentWidget(self.lbl_status)

        self.limpar_thumbnails()

        self.atualizar_status("Pronto", "info")

    def aplicar_tema(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#f8fafc"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#0f172a"))
        self.setPalette(palette)

    def animate_startup(self):
        for card in [self.card_pdfs, self.card_quest, self.card_status]:
            anim = QPropertyAnimation(card, b"windowOpacity")
            anim.setDuration(800)
            anim.setStartValue(0)
            anim.setEndValue(1)
            anim.setEasingCurve(QEasingCurve.Type.OutQuad)
            anim.start()
            setattr(self, f"_anim_{card.objectName()}", anim)

    def selecionar_pdfs(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Selecionar arquivos PDF", "", "PDF Files (*.pdf)"
        )
        if not files:
            return

        self.pdf_paths = files
        self.limpar_thumbnails()
        self.criar_thumbnails()

        self.card_pdfs.set_value(str(len(files)))
        self.card_quest.set_value("0")
        self.atualizar_status("PDFs selecionados.", "info")

    def limpar_thumbnails(self):
        while self.thumb_layout.count():
            item = self.thumb_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def criar_thumbnails(self):
        for idx, pdf_path in enumerate(self.pdf_paths):
            # Container para stack thumbnail + botão X
            container = QFrame()
            container.setStyleSheet("QFrame { border: none; }")
            container.setFixedSize(150, 200)  # Ajuste conforme seu PDFThumbnail

            # Usar layout de pilha para sobrepor o botão no thumbnail
            stack = QStackedWidget(container)

            thumb_widget = QWidget()
            vlayout = QVBoxLayout(thumb_widget)
            vlayout.setContentsMargins(0, 0, 0, 0)
            vlayout.setSpacing(0)

            thumb = PDFThumbnail(pdf_path, idx)
            thumb.clicked.connect(lambda p=pdf_path: self.abrir_preview(p))
            vlayout.addWidget(thumb)

            # Botão X no canto
            btn_x = QPushButton("✕", container)
            btn_x.setFixedSize(24, 24)
            btn_x.setStyleSheet("""
                QPushButton {
                    background-color: #ef4444;
                    color: white;
                    border: none;
                    border-radius: 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #dc2626;
                }
            """)
            btn_x.move(120, 10)  # Posição no canto superior direito (ajuste se precisar)
            btn_x.clicked.connect(lambda _, p=pdf_path: self.remover_pdf(p))

            stack.addWidget(thumb_widget)
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.addWidget(stack)

            self.thumb_layout.addWidget(container, idx // 4, idx % 4)

    def remover_pdf(self, pdf_path):
        if pdf_path in self.pdf_paths:
            self.pdf_paths.remove(pdf_path)
            self.limpar_thumbnails()
            self.criar_thumbnails()
            self.card_pdfs.set_value(str(len(self.pdf_paths)))

    def abrir_preview(self, pdf_path):
        dlg = PDFPreviewDialog(pdf_path, self)
        dlg.exec()

    def open_selected_dialog(self):
        if not self.pdf_paths:
            QMessageBox.warning(self, "Aviso", "Nenhum PDF selecionado.")
            return
        dlg = SelectedPDFsDialog(self.pdf_paths, self)
        dlg.exec()

    def atualizar_status(self, txt, status_tipo='info'):
        cores = {
            'info': ('#3b82f6', 'info'),
            'success': ('#10b981', 'check'),
            'warning': ('#f59e0b', 'alert'),
            'error': ('#ef4444', 'close'),
        }
        cor, icone_nome = cores.get(status_tipo, ('#64748b', 'info'))

        self.lbl_status.setText(f"Status: {txt}")
        self.lbl_status.setStyleSheet(f"color: {cor}; font-weight: bold;")
        self.statusbar.showMessage(txt)

        self.card_status.set_value(txt)
        self.card_status.title_label.setStyleSheet(f"color: {cor}; font-size: 14px; font-weight: bold;")

        if hasattr(self.card_status, 'icon_label'):
            icon = IconProvider.get_icon(icone_nome, cor, 24)
            self.card_status.icon_label.setPixmap(icon.pixmap(24, 24))

        anim = QPropertyAnimation(self.card_status, b"windowOpacity")
        anim.setDuration(400)
        anim.setStartValue(0.6)
        anim.setEndValue(1.0)
        anim.start()
        self._status_anim = anim

    def processar_gabarito(self):
        if not self.pdf_paths:
            QMessageBox.warning(self, "Erro", "Nenhum PDF selecionado.")
            return
        self.atualizar_status("Processando gabaritos...", "info")
        self.progress.setValue(5)
        self.config["threshold_fill"] = self.slider.value() / 100

        n_questoes = self.combo_quest.currentData()
        grid_rois = self.config["grid_rois"].get(str(n_questoes), [])

        # Escolhe o template certo:
        template_path = self.config["template_path"].get(str(n_questoes), None)

        # Atualiza o config para este processamento:
        self.config["template_path_atual"] = template_path
        
        res_txt = self.res_combo.currentText()
        dpi = 300 if "300" in res_txt else 200 if "200" in res_txt else 150

        link_google = self.google_sheet_input.text().strip()
        if not link_google:
            QMessageBox.warning(self, "Erro", "Você deve colar o link do Google Sheets antes de processar!")
            self.btn_processar.setEnabled(True)
            self.btn_processar.setText("Iniciar Processamento")
            return
        
        self.btn_processar.setEnabled(False)
        self.btn_processar.setText("Processando...")
        
    
        worker = ProcessWorker(
            pdf_paths=self.pdf_paths,
            config=self.config,
            n_alternativas=self.combo_alt.currentData(),
            dpi_escolhido=dpi,
            grid_rois=grid_rois,
            client=self.client
        )
        worker.google_sheet_id_dinamico = link_google  
        worker.signals.finished.connect(self.processamento_concluido)
        worker.signals.error.connect(self.mostrar_erro)
        worker.signals.progress.connect(self.progress.setValue)
        worker.signals.message.connect(self.atualizar_status)
        worker.signals.error.connect(lambda e: QMessageBox.critical(self, "Erro", e))
        worker.signals.finished.connect(self.on_process_finished)
        self.threadpool.start(worker)
    
    def processamento_concluido(self, resultado):
            self.btn_processar.setEnabled(True)
            self.btn_processar.setText("Iniciar Processamento")
            QMessageBox.information(self, "Concluído", "Processamento e exportação concluídos com sucesso! 🚀")

    def mostrar_erro(self, erro):
        self.btn_processar.setEnabled(True)
        self.btn_processar.setText("Iniciar Processamento")
        QMessageBox.critical(self, "Erro", f"Ocorreu um erro durante o processamento ou exportação:\n\n{erro}")


    def on_process_finished(self, all_pages):
        self.btn_processar.setEnabled(True)
        self.btn_processar.setText("Iniciar Processamento")
        self.progress.setValue(90)

        if not all_pages:
            self.progress.setValue(100)
            self.atualizar_status("Processamento concluído (sem resultados).", "warning")
            QMessageBox.warning(self, "Aviso", "Processamento concluído mas sem resultados.")
            return

        self.resultados = all_pages
        dlg = ResultadoDialog(all_pages, self)
        dlg.exec()

        self.progress.setValue(100)


    def abrir_pdf_filler(self):
        dlg = PDFFillerWindow(self.client)
        dlg.exec()

    def marcar_pdf_processado(self, pdf_path):
        for i in range(self.thumb_layout.count()):
            widget = self.thumb_layout.itemAt(i).widget()
            if hasattr(widget, '_pdf_path') and widget._pdf_path == pdf_path:
                if hasattr(widget, 'mark_processed'):
                    widget.mark_processed(True)
                break
            
    
    def closeEvent(self, event):
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    config = {"threshold_fill": 0.5}
    client = None
    window = GabaritoApp(config, client)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
