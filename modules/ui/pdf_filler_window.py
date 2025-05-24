import os
import pandas as pd
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QWidget, QApplication,
    QProgressBar, QComboBox, QStackedWidget, QFormLayout, QToolButton, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor
from modules.core.pdf_filler import preencher_pdf_com_info
from PyPDF2 import PdfMerger
import tempfile

class PDFFillerWindow(QDialog):
    def __init__(self, client=None):
        super().__init__()
        from modules.core.student_api import StudentAPIClient
        if client is not None and not isinstance(client, StudentAPIClient):
            print(f"AVISO: O cliente não é uma instância de StudentAPIClient, é {type(client)}")
            self.client = StudentAPIClient()
        else:
            self.client = client
        
        self.setWindowTitle("Gerador de Gabaritos")
        self.setMinimumWidth(1200)
        self.setMinimumHeight(800)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #f8fafc;
            }
            QLabel {
                color: #334155;
            }
            QFrame {
                border-radius: 8px;
            }
        """)

        self.lista_alunos_inep = []
        self.turmas_disponiveis = []
        self.turma_selecionada = None

        self.modelo_path = "modelo_gabarito_base.pdf"
        if not os.path.exists(self.modelo_path):
            QMessageBox.critical(self, "Erro", f"Modelo PDF não encontrado em: {self.modelo_path}")
            self.close()
            return

        self.initUI()

    def initUI(self):
        # Definir estilos comuns
        self.btn_primary_style = """
            background-color: #10b981;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 10px 16px;
            font-weight: bold;
            font-size: 14px;
        """
        self.btn_primary_hover = """
            background-color: #059669;
        """
        self.btn_primary_pressed = """
            background-color: #047857;
        """
        
        self.btn_secondary_style = """
            background-color: #f1f5f9;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 14px;
            color: #334155;
        """
        self.btn_secondary_hover = """
            background-color: #e2e8f0;
        """
        
        self.frame_style = """
            background-color: white;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
        """
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # Header with original green color
        header_frame = self.create_frame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #10b981;
                border-radius: 8px;
            }
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(24, 16, 24, 16)
        
        header_title = QLabel("Gerador de Gabaritos PDF")
        header_title.setStyleSheet("""
            font-size: 20px; 
            font-weight: bold; 
            color: white;
        """)
        
        header_layout.addWidget(header_title)
        header_layout.addStretch()
        
        # Add document icon to header
        doc_icon = QLabel("📄")
        doc_icon.setStyleSheet("font-size: 20px; color: white;")
        header_layout.addWidget(doc_icon)
        
        main_layout.addWidget(header_frame)

        # Stacked Widget para diferentes telas
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # Página 1: Entrada do INEP - Simplified design
        inep_page = QWidget()
        inep_layout = QVBoxLayout(inep_page)
        inep_layout.setContentsMargins(0, 0, 0, 0)
        inep_layout.setSpacing(16)

        # INEP Input - Cleaner design
        inep_frame = self.create_frame()
        inep_frame_layout = QVBoxLayout(inep_frame)
        inep_frame_layout.setContentsMargins(24, 24, 24, 24)
        inep_frame_layout.setSpacing(16)

        inep_title = QLabel("Buscar Alunos por INEP")
        inep_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e293b;")
        inep_frame_layout.addWidget(inep_title)

        inep_description = QLabel("Digite o código INEP da escola para buscar os alunos cadastrados.")
        inep_description.setStyleSheet("color: #64748b; font-size: 14px;")
        inep_frame_layout.addWidget(inep_description)

        inep_input_layout = QHBoxLayout()
        inep_input_layout.setSpacing(12)
        
        self.inep_input = QLineEdit()
        self.inep_input.setPlaceholderText("Digite o código INEP e pressione Enter")
        self.inep_input.returnPressed.connect(self.buscar_por_inep)
        self.inep_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 10px 12px;
                background-color: #f8fafc;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #10b981;
                background-color: white;
            }
        """)
        
        inep_search_btn = self.create_button("Buscar", self.btn_primary_style, self.btn_primary_hover, self.btn_primary_pressed)
        inep_search_btn.clicked.connect(self.buscar_por_inep)
        
        inep_input_layout.addWidget(self.inep_input)
        inep_input_layout.addWidget(inep_search_btn)
        inep_frame_layout.addLayout(inep_input_layout)

        # Status message with icon - Cleaner design
        status_layout = QHBoxLayout()
        self.status_icon = QLabel("")
        self.status_icon.setFixedSize(16, 16)
        self.inep_status = QLabel("")
        self.inep_status.setStyleSheet("color: #64748b; font-style: italic; font-size: 14px;")
        status_layout.addWidget(self.status_icon)
        status_layout.addWidget(self.inep_status)
        status_layout.addStretch()
        inep_frame_layout.addLayout(status_layout)

        inep_layout.addWidget(inep_frame)
        
        # Excel import option - Simplified design with green accent
        excel_frame = self.create_frame()
        excel_layout = QVBoxLayout(excel_frame)
        excel_layout.setContentsMargins(24, 24, 24, 24)
        excel_layout.setSpacing(16)
        
        excel_title = QLabel("Gerar através do Excel")
        excel_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e293b;")
        excel_layout.addWidget(excel_title)
        
        excel_description = QLabel("Importe uma planilha Excel com os dados dos alunos para gerar os gabaritos em lote.")
        excel_description.setStyleSheet("color: #64748b; font-size: 14px;")
        excel_layout.addWidget(excel_description)
        
        excel_btn = self.create_button("Importar Planilha Excel", self.btn_primary_style, self.btn_primary_hover, self.btn_primary_pressed)
        excel_btn.clicked.connect(self.gerar_atraves_excel)
        excel_layout.addWidget(excel_btn)
        
        inep_layout.addWidget(excel_frame)
        inep_layout.addStretch()

        # Página 2: Seleção de Turma - Ajustada para garantir layout e tabela visíveis
        turma_page = QWidget()
        turma_layout = QVBoxLayout(turma_page)
        turma_layout.setContentsMargins(0, 0, 0, 0)
        turma_layout.setSpacing(12)

        # Cabeçalho da página
        turma_header = self.create_frame()
        turma_header_layout = QHBoxLayout(turma_header)
        turma_header_layout.setContentsMargins(20, 16, 20, 16)

        back_btn = self.create_button("← Voltar", self.btn_secondary_style, self.btn_secondary_hover)
        back_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))

        turma_title = QLabel("Selecione uma Turma")
        turma_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e293b;")

        self.escola_info = QLabel("")
        self.escola_info.setStyleSheet("color: #64748b; font-size: 14px;")

        turma_title_layout = QVBoxLayout()
        turma_title_layout.addWidget(turma_title)
        turma_title_layout.addWidget(self.escola_info)

        turma_header_layout.addWidget(back_btn)
        turma_header_layout.addSpacing(16)
        turma_header_layout.addLayout(turma_title_layout)
        turma_header_layout.addStretch()

        turma_layout.addWidget(turma_header)

        # Lista de turmas
        turma_list_frame = self.create_frame()
        turma_list_layout = QVBoxLayout(turma_list_frame)
        turma_list_layout.setContentsMargins(20, 20, 20, 20)
        turma_list_layout.setSpacing(12)

        turma_list_label = QLabel("Turmas Disponíveis")
        turma_list_label.setStyleSheet("font-weight: bold; color: #1e293b; font-size: 16px;")
        turma_list_layout.addWidget(turma_list_label)

        self.turma_combo = QComboBox()
        self.turma_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.turma_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 10px 12px;
                background-color: #f8fafc;
                font-size: 14px;
            }
            QComboBox:focus {
                border-color: #10b981;
                background-color: white;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 1px;
                border-left-color: #e2e8f0;
                border-left-style: solid;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }
        """)
        self.turma_combo.currentIndexChanged.connect(self.on_turma_selected)
        turma_list_layout.addWidget(self.turma_combo)

        turma_layout.addWidget(turma_list_frame)

        # Frame que contém a lista e busca de alunos
        alunos_frame = self.create_frame()
        alunos_layout = QVBoxLayout(alunos_frame)
        alunos_layout.setContentsMargins(20, 20, 20, 20)
        alunos_layout.setSpacing(16)

        # Cabeçalho com título e contador
        alunos_header = QHBoxLayout()
        alunos_header.setSpacing(8)

        alunos_title_container = QVBoxLayout()
        alunos_title_container.setSpacing(2)

        alunos_label = QLabel("Alunos na Turma")
        alunos_label.setStyleSheet("font-weight: bold; color: #1e293b; font-size: 16px;")

        self.alunos_count = QLabel("")
        self.alunos_count.setStyleSheet("color: #64748b; font-size: 14px;")

        alunos_title_container.addWidget(alunos_label)
        alunos_title_container.addWidget(self.alunos_count)

        alunos_header.addLayout(alunos_title_container)
        alunos_header.addStretch()

        alunos_layout.addLayout(alunos_header)

        # Campo de busca dos alunos
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar aluno por nome ou matrícula...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 8px 12px;
                background-color: white;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #10b981;
            }
        """)
        self.search_input.textChanged.connect(self.filtrar_alunos)
        alunos_layout.addWidget(self.search_input)

        # Indicador de filtro ativo (label que fica escondido inicialmente)
        self.filtro_info = QLabel("")
        self.filtro_info.setStyleSheet("""
            QLabel {
                color: #10b981;
                font-style: italic;
                font-size: 13px;
                margin-top: -8px;
                padding-left: 4px;
            }
        """)
        self.filtro_info.setVisible(False)
        alunos_layout.addWidget(self.filtro_info)  

        # Container para a tabela com tamanho expandido
        table_container = QFrame()
        table_container.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 6px;
                border: 1px solid #e2e8f0;
            }
        """)
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(4, 4, 4, 4)
        table_layout.addWidget(self.alunos_count)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setWidget(table_container)
        alunos_layout.addWidget(scroll_area)

        self.alunos_table = QTableWidget()
        self.alunos_table.setColumnCount(5)
        self.alunos_table.setHorizontalHeaderLabels(["Matrícula", "Nome", "Escola", "Turma", "Turno"])
        self.alunos_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)  # todas colunas se esticam
        self.alunos_table.setAlternatingRowColors(True)
        self.alunos_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.alunos_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.alunos_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.alunos_table.verticalHeader().setVisible(False)
        self.alunos_table.setShowGrid(True)
        self.alunos_table.setMinimumHeight(400)
        self.alunos_table.setMaximumHeight(600)
        self.alunos_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.alunos_table.itemSelectionChanged.connect(self.on_aluno_selected)

        table_layout.addWidget(self.alunos_table)
        alunos_layout.addWidget(table_container)

        # Depois adiciona alunos_frame ao layout da turma
        turma_layout.addWidget(alunos_frame)

        # Botões para gerar PDF etc.
        action_frame = self.create_frame()
        action_layout = QHBoxLayout(action_frame)
        action_layout.setContentsMargins(20, 16, 20, 16)
        action_layout.addStretch()

        self.gerar_pdf_btn = self.create_button(
            "Gerar PDF para Turma",
            """
            background-color: #16a34a;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 14px 28px;
            font-weight: bold;
            font-size: 16px;
            """,
            """
            background-color: #15803d;
            """,
            """
            background-color: #166534;
            """
        )

        self.gerar_pdf_btn.setEnabled(False)
        self.gerar_pdf_btn.clicked.connect(self.gerar_pdf_turma)

        action_layout.addWidget(self.gerar_pdf_btn)
        turma_layout.addWidget(action_frame)

        # Adiciona as páginas ao stacked widget
        self.stacked_widget.addWidget(inep_page)
        self.stacked_widget.addWidget(turma_page)

        # Footer - Minimalist design
        footer_frame = self.create_frame()
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(20, 14, 20, 14)
        
        info_layout = QHBoxLayout()
        model_label = QLabel("📄 Modelo:")
        model_label.setStyleSheet("color: #64748b; font-size: 13px;")
        model_name = QLabel(os.path.basename(self.modelo_path))
        model_name.setStyleSheet("color: #334155; font-weight: bold; font-size: 13px;")
        info_layout.addWidget(model_label)
        info_layout.addWidget(model_name)
        info_layout.addStretch()
        
        btn_cancelar = self.create_button("Fechar", self.btn_secondary_style, self.btn_secondary_hover)
        btn_cancelar.clicked.connect(self.reject)
        
        footer_layout.addLayout(info_layout)
        footer_layout.addStretch()
        footer_layout.addWidget(btn_cancelar)
        
        main_layout.addWidget(footer_frame)

    # Método para mostrar ajuda sobre a tabela
    def mostrar_ajuda_tabela(self):
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("Ajuda - Tabela de Alunos")
        help_dialog.setFixedSize(450, 300)
        help_dialog.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: #334155;
                font-size: 14px;
            }
            QLabel[heading="true"] {
                font-size: 18px;
                font-weight: bold;
                color: #1e293b;
                margin-bottom: 10px;
            }
        """)
        
        layout = QVBoxLayout(help_dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Título
        title = QLabel("Como usar a tabela de alunos")
        title.setProperty("heading", "true")
        layout.addWidget(title)
        
        # Conteúdo da ajuda
        help_frame = QFrame()
        help_frame.setStyleSheet("""
            QFrame {
                background-color: #f8fafc;
                border-radius: 6px;
                border: 1px solid #e2e8f0;
            }
        """)
        help_layout = QVBoxLayout(help_frame)
        help_layout.setContentsMargins(16, 16, 16, 16)
        help_layout.setSpacing(12)
        
        tips = [
            "<b>Buscar alunos:</b> Use a barra de pesquisa para filtrar por nome ou matrícula.",
            "<b>Ordenar:</b> Clique nos cabeçalhos das colunas para ordenar os dados.",
            "<b>Selecionar:</b> Clique em uma linha para selecionar um aluno.",
            "<b>Ações:</b> Use os botões na coluna 'Ações' para visualizar detalhes ou gerar PDF individual."
        ]
        
        for tip in tips:
            tip_label = QLabel(tip)
            tip_label.setWordWrap(True)
            help_layout.addWidget(tip_label)
        
        layout.addWidget(help_frame)
        
        # Botão de fechar
        close_btn = self.create_button("Fechar", self.btn_secondary_style, self.btn_secondary_hover)
        close_btn.clicked.connect(help_dialog.accept)
        
        layout.addStretch()
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        help_dialog.exec()

    # Método para exportar dados da tabela para Excel
    def exportar_para_excel(self):
        if self.alunos_table.rowCount() == 0:
            QMessageBox.warning(self, "Aviso", "Não há dados para exportar.")
            return
        
        # Perguntar onde salvar o arquivo
        arquivo_saida, _ = QFileDialog.getSaveFileName(
            self, "Salvar como Excel", "", "Arquivos Excel (*.xlsx);;Todos os arquivos (*)"
        )
        
        if not arquivo_saida:
            return
        
        try:
            # Coletar dados da tabela
            dados = []
            headers = []
            
            # Obter cabeçalhos
            for col in range(self.alunos_table.columnCount()):
                headers.append(self.alunos_table.horizontalHeaderItem(col).text())
            
            # Obter dados
            for row in range(self.alunos_table.rowCount()):
                row_data = {}
                for col in range(self.alunos_table.columnCount()):
                    item = self.alunos_table.item(row, col)
                    header = headers[col]
                    row_data[header] = item.text() if item else ""
                
                dados.append(row_data)
            
            # Criar DataFrame e salvar como Excel
            df = pd.DataFrame(dados)
            df.to_excel(arquivo_saida, index=False)
            
            QMessageBox.information(
                self,
                "Sucesso",
                f"Dados exportados com sucesso para:\n{arquivo_saida}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao exportar dados:\n{e}")

    # Adicionar um método para destacar alunos selecionados
    def on_aluno_selected(self):
        selected_rows = self.alunos_table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            # Destacar visualmente o aluno selecionado
            for col in range(self.alunos_table.columnCount()):
                item = self.alunos_table.item(row, col)
                if item:
                    item.setBackground(QColor("#d1fae5"))

    # Adicionar botões de ação para cada aluno na tabela
    def adicionar_acoes_aluno(self):
        # Adicionar uma coluna extra para ações se ainda não existir
        if self.alunos_table.columnCount() == 5:
            self.alunos_table.setColumnCount(6)
            self.alunos_table.setHorizontalHeaderLabels(["Matrícula", "Nome", "Escola", "Turma", "Turno", "Ações"])
        
        # Para cada linha na tabela
        for row in range(self.alunos_table.rowCount()):
            # Criar widget para os botões
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(4, 2, 4, 2)
            layout.setSpacing(8)
            
            # Botão de visualização
            view_btn = self.create_button("👁️", self.btn_primary_style, self.btn_primary_hover, tooltip="Visualizar detalhes do aluno")
            view_btn.setStyleSheet("""
                QPushButton {
                    background-color: #10b981;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px;
                    font-size: 12px;
                    min-width: 28px;
                    min-height: 28px;
                }
                QPushButton:hover {
                    background-color: #059669;
                }
            """)
            view_btn.clicked.connect(lambda _, r=row: self.visualizar_aluno(r))
            
            # Botão de PDF individual
            pdf_btn = self.create_button("📄", self.btn_primary_style, self.btn_primary_hover, tooltip="Gerar PDF individual")
            pdf_btn.setStyleSheet("""
                QPushButton {
                    background-color: #10b981;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px;
                    font-size: 12px;
                    min-width: 28px;
                    min-height: 28px;
                }
                QPushButton:hover {
                    background-color: #059669;
                }
            """)
            pdf_btn.clicked.connect(lambda _, r=row: self.gerar_pdf_individual(r))
            
            layout.addWidget(view_btn)
            layout.addWidget(pdf_btn)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Adicionar widget à tabela
            self.alunos_table.setCellWidget(row, 5, widget)
        
        # Ajustar largura da coluna de ações
        self.alunos_table.setColumnWidth(5, 80)

    # Método para visualizar detalhes do aluno
    def visualizar_aluno(self, row):
        if row < 0 or row >= self.alunos_table.rowCount():
            return
            
        matricula = self.alunos_table.item(row, 0).text()
        nome = self.alunos_table.item(row, 1).text()
        escola = self.alunos_table.item(row, 
2).text()
        turma = self.alunos_table.item(row, 3).text()
        turno = self.alunos_table.item(row, 4).text()
        
        # Encontrar o aluno completo para obter dados adicionais
        aluno_completo = None
        for aluno in self.lista_alunos_inep:
            if aluno["matricula"] == matricula and aluno["nome"] == nome:
                aluno_completo = aluno
                break
        
        # Criar diálogo de detalhes
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Detalhes do Aluno")
        dialog.setFixedSize(500, 350)
        dialog.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                font-size: 14px;
            }
            QLabel[title="true"] {
                font-size: 20px;
                font-weight: bold;
                color: #1e293b;
            }
            QLabel[subtitle="true"] {
                font-size: 14px;
                color: #64748b;
                margin-top: -8px;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Cabeçalho
        header_layout = QVBoxLayout()
        
        title = QLabel(nome)
        title.setProperty("title", "true")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitle = QLabel(f"Matrícula: {matricula}")
        subtitle.setProperty("subtitle", "true")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        
        layout.addLayout(header_layout)
        
        # Informações principais
        info_frame = self.create_frame()
        info_layout = QFormLayout(info_frame)
        info_layout.setContentsMargins(20, 20, 20, 20)
        info_layout.setSpacing(16)
        info_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Estilo para labels e valores
        label_style = """
            QLabel {
                font-weight: bold;
                color: #334155;
                font-size: 14px;
            }
        """
        
        value_style = """
            QLabel {
                color: #1e293b;
                font-size: 14px;
            }
        """
        
        # Escola
        escola_label = QLabel("Escola:")
        escola_label.setStyleSheet(label_style)
        escola_value = QLabel(escola)
        escola_value.setStyleSheet(value_style)
        info_layout.addRow(escola_label, escola_value)
        
        # Turma
        turma_label = QLabel("Turma:")
        turma_label.setStyleSheet(label_style)
        turma_value = QLabel(turma)
        turma_value.setStyleSheet(value_style)
        info_layout.addRow(turma_label, turma_value)
        
        # Turno
        turno_label = QLabel("Turno:")
        turno_label.setStyleSheet(label_style)
        turno_value = QLabel(turno)
        turno_value.setStyleSheet(value_style)
        info_layout.addRow(turno_label, turno_value)
        
        # Data de nascimento (se disponível)
        if aluno_completo and aluno_completo.get("data_nascimento"):
            data_nasc_label = QLabel("Data de Nascimento:")
            data_nasc_label.setStyleSheet(label_style)
            data_nasc_value = QLabel(aluno_completo["data_nascimento"])
            data_nasc_value.setStyleSheet(value_style)
            info_layout.addRow(data_nasc_label, data_nasc_value)
        
        layout.addWidget(info_frame)
        
        # Botões de ação
        actions_layout = QHBoxLayout()
        
        # Botão de PDF
        pdf_btn = self.create_button("Gerar PDF Individual", self.btn_primary_style, self.btn_primary_hover)
        pdf_btn.clicked.connect(lambda: self.gerar_pdf_individual(row))
        
        # Botão de fechar
        close_btn = self.create_button("Fechar", self.btn_secondary_style, self.btn_secondary_hover)
        close_btn.clicked.connect(dialog.accept)
        
        actions_layout.addWidget(pdf_btn)
        actions_layout.addStretch()
        actions_layout.addWidget(close_btn)
        
        layout.addStretch()
        layout.addLayout(actions_layout)
        
        dialog.exec()

    # Método para gerar PDF individual
    def gerar_pdf_individual(self, row):
        if row < 0 or row >= self.alunos_table.rowCount():
            return
            
        matricula = self.alunos_table.item(row, 0).text()
        nome = self.alunos_table.item(row, 1).text()
        
        # Encontrar o aluno completo na lista
        aluno = None
        for a in self.lista_alunos_inep:
            if a["matricula"] == matricula and a["nome"] == nome:
                aluno = a
                break
        
        if not aluno:
            QMessageBox.warning(self, "Erro", "Não foi possível encontrar os dados completos do aluno.")
            return
        
        # Perguntar onde salvar o PDF
        pasta_saida = QFileDialog.getExistingDirectory(self, "Selecione a pasta para salvar o PDF")
        if not pasta_saida:
            return
        
        try:
            # Criar nome de arquivo
            nome_arquivo = f"{aluno['matricula']}_{aluno['nome'].replace(' ', '_')}.pdf"
            caminho_saida = os.path.join(pasta_saida, nome_arquivo)
            
            # Gerar PDF
            preencher_pdf_com_info(self.modelo_path, [aluno], caminho_saida)
            
            QMessageBox.information(
                self,
                "Sucesso",
                f"PDF individual gerado com sucesso para {aluno['nome']}.\n\nSalvo em: {caminho_saida}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao gerar PDF individual:\n{e}")

    def buscar_por_inep(self):
        if not self.client:
            QMessageBox.warning(self, "Erro", "API não conectada.")
            return

        inep = self.inep_input.text().strip()
        if not inep:
            QMessageBox.warning(self, "Erro", "Digite o código INEP.")
            return

        self.inep_status.setText("Buscando alunos... Por favor, aguarde.")
        self.inep_status.setStyleSheet("color: #10b981; font-style: italic; font-size: 14px;")
        self.status_icon.setStyleSheet("background-color: #10b981; border-radius: 8px;")
        QApplication.processEvents()  # Atualiza a UI

        try:
            # Check if client has the method
            if not self.client:
                raise AttributeError("Cliente API não inicializado")
            
            if not hasattr(self.client, 'buscar_por_inep'):
                # Tenta importar e criar um novo cliente como fallback
                from modules.core.student_api import StudentAPIClient
                self.client = StudentAPIClient()
                if not hasattr(self.client, 'buscar_por_inep'):
                    raise AttributeError("O cliente API não possui o método 'buscar_por_inep'")

            dados = self.client.buscar_por_inep(inep)
            if not dados:
                self.inep_status.setText("Nenhum estudante foi localizado com esse INEP.")
                self.inep_status.setStyleSheet("color: #ef4444; font-style: italic; font-size: 14px;")
                self.status_icon.setStyleSheet("background-color: #ef4444; border-radius: 8px;")
                return

            # Verificar e corrigir os dados retornados
            print(f"Dados brutos da API: {dados[0] if dados else 'Nenhum dado'}")
            
            # Verificar quais campos estão disponíveis nos dados
            campos_disponiveis = set()
            for aluno in dados:
                campos_disponiveis.update(aluno.keys())
            print(f"Campos disponíveis nos dados: {campos_disponiveis}")
            
            # Mapear os campos corretamente
            campo_turma = None
            if "className" in campos_disponiveis:
                campo_turma = "className"
            elif "class" in campos_disponiveis:
                campo_turma = "class"
            elif "turma" in campos_disponiveis:
                campo_turma = "turma"
            
            campo_escola = None
            if "schoolName" in campos_disponiveis:
                campo_escola = "schoolName"
            elif "school" in campos_disponiveis:
                campo_escola = "school"
            elif "escola" in campos_disponiveis:
                campo_escola = "escola"
            
            campo_turno = None
            if "turn" in campos_disponiveis:
                campo_turno = "turn"
            elif "turno" in campos_disponiveis:
                campo_turno = "turno"
            
            print(f"Campos identificados - Turma: {campo_turma}, Escola: {campo_escola}, Turno: {campo_turno}")

            self.lista_alunos_inep = [{
                "nome": aluno.get("name", ""),
                "matricula": aluno.get("enrollment", ""),
                "escola": aluno.get(campo_escola, "") if campo_escola else "",
                "turma": aluno.get(campo_turma, "") if campo_turma else "",
                "turno": aluno.get(campo_turno, "") if campo_turno else "",
                "data_nascimento": aluno.get("birthDate", "")[:10] if aluno.get("birthDate") else "",
            } for aluno in dados]

            print(f"Alunos processados: {len(self.lista_alunos_inep)}")
            if self.lista_alunos_inep:
                print(f"Exemplo de aluno processado: {self.lista_alunos_inep[0]}")

            # Extrair turmas únicas e filtrar turmas vazias
            turmas_com_valor = [aluno["turma"] for aluno in self.lista_alunos_inep if aluno["turma"] and aluno["turma"].strip()]
            print(f"Turmas com valor: {turmas_com_valor}")
            self.turmas_disponiveis = sorted(list(set(turmas_com_valor)))
            print(f"Turmas disponíveis: {self.turmas_disponiveis}")
            
            if not self.turmas_disponiveis:
                print("Nenhuma turma disponível após processamento")
                # Verificar se há alunos com turma vazia
                alunos_sem_turma = [aluno for aluno in self.lista_alunos_inep if not aluno["turma"] or not aluno["turma"].strip()]
                print(f"Alunos sem turma: {len(alunos_sem_turma)}")
            
                # Se não houver turmas, mas houver alunos, criar uma turma padrão
                if self.lista_alunos_inep:
                    turma_padrao = "Turma Padrão"
                    print(f"Criando turma padrão: {turma_padrao}")
                    for aluno in self.lista_alunos_inep:
                        aluno["turma"] = turma_padrao
                    self.turmas_disponiveis = [turma_padrao]
                else:
                    self.inep_status.setText(f"Nenhuma turma encontrada para este INEP. {len(self.lista_alunos_inep)} alunos encontrados, mas sem turma definida.")
                    self.inep_status.setStyleSheet("color: #ef4444; font-style: italic; font-size: 14px;")
                    self.status_icon.setStyleSheet("background-color: #ef4444; border-radius: 8px;")
                    return

            # Preencher o combo de turmas
            self.turma_combo.clear()
            self.turma_combo.addItem("Selecione uma turma...")
            for turma in self.turmas_disponiveis:
                self.turma_combo.addItem(turma)
            
            # Atualizar informações da escola
            if self.lista_alunos_inep and self.lista_alunos_inep[0]["escola"]:
                self.escola_info.setText(f"Escola: {self.lista_alunos_inep[0]['escola']}")
            
            # Ir para a página de seleção de turma
            self.stacked_widget.setCurrentIndex(1)
            
            # Atualizar status
            self.inep_status.setText(f"Encontrados {len(self.lista_alunos_inep)} alunos em {len(self.turmas_disponiveis)} turmas.")
            self.inep_status.setStyleSheet("color: #10b981; font-style: italic; font-size: 14px;")
            self.status_icon.setStyleSheet("background-color: #10b981; border-radius: 8px;")
            
        except AttributeError as e:
            self.inep_status.setText(f"Erro: {str(e)}")
            self.inep_status.setStyleSheet("color: #ef4444; font-style: italic; font-size: 14px;")
            self.status_icon.setStyleSheet("background-color: #ef4444; border-radius: 8px;")
            QMessageBox.critical(self, "Erro de API", f"O cliente API não está configurado corretamente: {e}")
        except Exception as e:
            self.inep_status.setText(f"Falha na consulta: {e}")
            self.inep_status.setStyleSheet("color: #ef4444; font-style: italic; font-size: 14px;")
            self.status_icon.setStyleSheet("background-color: #ef4444; border-radius: 8px;")
            QMessageBox.critical(self, "Erro", f"Falha na consulta:\n{e}")

    def on_turma_selected(self, index):
        if index <= 0:
            self.alunos_table.clearContents()
            self.alunos_table.setRowCount(0)
            self.turma_selecionada = None
            self.alunos_count.setText("")
            self.gerar_pdf_btn.setEnabled(False)
            self.filtro_info.setVisible(False)
            return

        self.turma_selecionada = self.turma_combo.currentText()
        alunos_na_turma = [aluno for aluno in self.lista_alunos_inep if aluno["turma"] == self.turma_selecionada]

        self.alunos_table.setColumnCount(6)
        self.alunos_table.setHorizontalHeaderLabels(["Matrícula", "Nome", "Escola", "Turma", "Turno", "Data de Nascimento"])
        self.alunos_table.setRowCount(len(alunos_na_turma))
        self.alunos_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.alunos_table.horizontalHeader().setStretchLastSection(True)

        for row, aluno in enumerate(alunos_na_turma):
            self.alunos_table.setItem(row, 0, QTableWidgetItem(aluno.get("matricula", "")))
            self.alunos_table.setItem(row, 1, QTableWidgetItem(aluno.get("nome", "")))
            self.alunos_table.setItem(row, 2, QTableWidgetItem(aluno.get("escola", "")))
            self.alunos_table.setItem(row, 3, QTableWidgetItem(aluno.get("turma", "")))
            self.alunos_table.setItem(row, 4, QTableWidgetItem(aluno.get("turno", "")))
            self.alunos_table.setItem(row, 5, QTableWidgetItem(aluno.get("data_nascimento", "")))


        self.alunos_table.resizeColumnsToContents()
        self.alunos_table.update()

        self.alunos_count.setText(f"({len(alunos_na_turma)} alunos)")
        self.filtro_info.setVisible(False)
        self.alunos_count.setText(f"Mostrando {len(alunos_na_turma)} alunos na turma {self.turma_selecionada}")
        self.gerar_pdf_btn.setEnabled(len(alunos_na_turma) > 0)

    def filtrar_alunos(self):
        if not self.turma_selecionada:
            return
        
        texto_busca = self.search_input.text().lower().strip()
        
        # Filtra alunos da turma que contem texto na matrícula ou nome
        alunos_turma = [aluno for aluno in self.lista_alunos_inep if aluno["turma"] == self.turma_selecionada]
        if not texto_busca:
            # Se campo vazio, mostra todos
            self.on_turma_selected(self.turma_combo.currentIndex())
            self.filtro_info.setVisible(False)
            return

        alunos_filtrados = [
            aluno for aluno in alunos_turma
            if texto_busca in aluno["nome"].lower() or texto_busca in aluno["matricula"].lower()
        ]

        self.alunos_table.clearContents()
        self.alunos_table.setRowCount(len(alunos_filtrados))
        self.alunos_table.setColumnCount(6)
        self.alunos_table.setHorizontalHeaderLabels(["Matrícula", "Nome", "Escola", "Turma", "Turno", "Data de Nascimento"])
        self.alunos_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        for row, aluno in enumerate(alunos_filtrados):
            itens = [
                QTableWidgetItem(aluno.get("matricula", "")),
                QTableWidgetItem(aluno.get("nome", "")),
                QTableWidgetItem(aluno.get("escola", "")),
                QTableWidgetItem(aluno.get("turma", "")),
                QTableWidgetItem(aluno.get("turno", "")),
                QTableWidgetItem(aluno.get("data_nascimento", ""))
            ]

            # Destaca o texto buscado em matrícula e nome
            for i, campo in [(0, "matricula"), (1, "nome")]:
                if texto_busca in aluno[campo].lower():
                    itens[i].setBackground(QColor("#d1fae5"))
                    itens[i].setForeground(QColor("#047857"))
                itens[i].setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            # Colunas extras alinhamento padrão
            for item in itens[2:]:
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            for col, item in enumerate(itens):
                self.alunos_table.setItem(row, col, item)

        self.alunos_count.setText(f"({len(alunos_filtrados)} de {len(alunos_turma)})")
        self.filtro_info.setText(f"Filtro ativo: '{texto_busca}'")
        self.filtro_info.setVisible(True)

        if len(alunos_filtrados) > 0:
            self.table_status.setText(f"Mostrando {len(alunos_filtrados)} de {len(alunos_turma)} alunos")
        else:
            self.table_status.setText(f"Nenhum aluno encontrado para '{texto_busca}'")
            # Mostrar mensagem na tabela
            self.alunos_table.setRowCount(1)
            msg_item = QTableWidgetItem(f"Nenhum aluno encontrado para '{texto_busca}'")
            msg_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.alunos_table.setSpan(0, 0, 1, 5)
            self.alunos_table.setItem(0, 0, msg_item)

        self.gerar_pdf_btn.setEnabled(len(alunos_filtrados) > 0)


    def gerar_pdf_turma(self):
        if not self.turma_selecionada:
            return
            
        pasta_saida = QFileDialog.getExistingDirectory(self, "Selecione a pasta de saída")
        if not pasta_saida:
            return
            
        # Filtrar alunos da turma selecionada
        alunos_turma = [aluno for aluno in self.lista_alunos_inep if aluno["turma"] == self.turma_selecionada]
        
        if not alunos_turma:
            QMessageBox.warning(self, "Aviso", "Nenhum aluno encontrado na turma selecionada.")
            return
            
        try:
            # Criar diálogo de progresso
            progress_dialog = QDialog(self)
            progress_dialog.setWindowTitle("Gerando PDFs")
            progress_dialog.setFixedSize(400, 150)
            progress_dialog.setStyleSheet("""
                QDialog {
                    background-color: white;
                }
            """)
            
            progress_layout = QVBoxLayout(progress_dialog)
            progress_layout.setContentsMargins(20, 20, 20, 20)
            
            progress_label = QLabel("Gerando PDFs para os alunos...")
            progress_label.setStyleSheet("font-size: 14px; color: #334155;")
            progress_layout.addWidget(progress_label)
            
            progress_bar = QProgressBar()
            progress_bar.setRange(0, len(alunos_turma))
            progress_bar.setValue(0)
            progress_bar.setTextVisible(True)
            progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    background-color: #f8fafc;
                    text-align: center;
                    height: 24px;
                    margin-top: 10px;
                }
                QProgressBar::chunk {
                    background-color: #10b981;
                    border-radius: 7px;
                }
            """)
            progress_layout.addWidget(progress_bar)
            
            progress_detail = QLabel("Preparando...")
            progress_detail.setStyleSheet("font-size: 12px; color: #64748b; margin-top: 5px;")
            progress_layout.addWidget(progress_detail)
            
            progress_dialog.show()
            QApplication.processEvents()
            
            # Gerar PDF unificado
            merger = PdfMerger()
            arquivos_temp = []
            erros = 0
            
            for i, aluno in enumerate(alunos_turma):
                try:
                    progress_detail.setText(f"Processando: {aluno.get('nome', 'Aluno')}")
                    progress_bar.setValue(i)
                    QApplication.processEvents()
                    
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                    temp_file.close()
                    preencher_pdf_com_info(self.modelo_path, [aluno], temp_file.name)
                    merger.append(temp_file.name)
                    arquivos_temp.append(temp_file.name)
                except Exception as e:
                    erros += 1
                    print(f"Erro com {aluno.get('nome', 'Aluno')} -> {e}")
            
            progress_detail.setText("Finalizando PDF...")
            QApplication.processEvents()
            
            if arquivos_temp:
                escola = alunos_turma[0].get("escola", "Escola").replace(" ", "_")
                turma = self.turma_selecionada.replace(" ", "_")
                nome_arquivo = f"{escola}_{turma}_gabaritos.pdf"
                caminho_saida = os.path.join(pasta_saida, nome_arquivo)
                merger.write(caminho_saida)
                merger.close()
                
                for arq in arquivos_temp:
                    try:
                        os.remove(arq)
                    except Exception as e:
                        print(f"Erro ao remover {arq}: {e}")
                
                progress_dialog.close()
                
                QMessageBox.information(
                    self,
                    "Sucesso",
                    f"PDF unificado salvo em:\n{caminho_saida}\n\nAlunos processados: {len(alunos_turma)}\nFalhas: {erros}"
                )
                self.accept()
            else:
                progress_dialog.close()
                QMessageBox.warning(self, "Erro", "Não foi possível gerar nenhum PDF.")
                
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao gerar PDF:\n{e}")

    def gerar_atraves_excel(self):
        planilha_path, _ = QFileDialog.getOpenFileName(self, "Selecione a planilha de alunos", "", "Planilhas (*.xlsx *.csv)")
        if not planilha_path:
            return

        alunos = self.carregar_alunos_de_planilha(planilha_path)
        if not alunos:
            return

        pasta_saida = QFileDialog.getExistingDirectory(self, "Selecione a pasta de saída")
        if not pasta_saida:
            return

        # Criar diálogo de progresso
        progress_dialog = QDialog(self)
        progress_dialog.setWindowTitle("Gerando PDFs")
        progress_dialog.setFixedSize(400, 150)
        progress_dialog.setStyleSheet("""
            QDialog {
                background-color: white;
            }
        """)
        
        progress_layout = QVBoxLayout(progress_dialog)
        progress_layout.setContentsMargins(20, 20, 20, 20)
        
        progress_label = QLabel("Gerando PDFs a partir do Excel...")
        progress_label.setStyleSheet("font-size: 14px; color: #334155;")
        progress_layout.addWidget(progress_label)
        
        progress_bar = QProgressBar()
        progress_bar.setRange(0, len(alunos))
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                background-color: #f8fafc;
                text-align: center;
                height: 24px;
                margin-top: 10px;
            }
            QProgressBar::chunk {
                background-color: #10b981;
                border-radius: 7px;
            }
        """)
        progress_layout.addWidget(progress_bar)
        
        progress_detail = QLabel("Preparando...")
        progress_detail.setStyleSheet("font-size: 12px; color: #64748b; margin-top: 5px;")
        progress_layout.addWidget(progress_detail)
        
        progress_dialog.show()
        QApplication.processEvents()

        merger = PdfMerger()
        arquivos_temp = []
        erros = 0

        for i, aluno in enumerate(alunos):
            try:
                progress_detail.setText(f"Processando: {aluno.get('nome', 'Aluno')}")
                progress_bar.setValue(i)
                QApplication.processEvents()
                
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                temp_file.close()
                preencher_pdf_com_info(self.modelo_path, [aluno], temp_file.name)
                merger.append(temp_file.name)
                arquivos_temp.append(temp_file.name)
            except Exception as e:
                erros += 1
                print(f"Erro com {aluno.get('nome', 'Aluno')} -> {e}")

        progress_detail.setText("Finalizando PDF...")
        QApplication.processEvents()

        if arquivos_temp:
            escola = alunos[0].get("escola", "Escola").replace(" ", "_")
            turma = alunos[0].get("turma", "Turma").replace(" ", "_")
            nome_arquivo = f"{escola}_{turma}_gabaritos.pdf"
            caminho_saida = os.path.join(pasta_saida, nome_arquivo)
            merger.write(caminho_saida)
            merger.close()

            for arq in arquivos_temp:
                try:
                    os.remove(arq)
                except Exception as e:
                    print(f"Erro ao remover {arq}: {e}")

            progress_dialog.close()
            
            QMessageBox.information(
                self,
                "Sucesso",
                f"PDF unificado salvo em:\n{caminho_saida}\n\nAlunos processados: {len(alunos) - erros}\nFalhas: {erros}"
            )
            self.accept()
        else:
            progress_dialog.close()
            QMessageBox.warning(self, "Erro", "Não foi possível gerar nenhum PDF.")

    def carregar_alunos_de_planilha(self, caminho_arquivo):
        try:
            df = pd.read_excel(caminho_arquivo) if caminho_arquivo.endswith(".xlsx") else pd.read_csv(caminho_arquivo)
            df = df.fillna("")
            df = df.astype(str)
            return df.to_dict(orient="records")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao ler a planilha:\n{e}")
            return []

    def create_button(self, text, style, hover_style="", pressed_style="", tooltip="", icon=""):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        full_style = style
        if hover_style:
            full_style += f"QPushButton:hover {{ {hover_style} }}"
        if pressed_style:
            full_style += f"QPushButton:pressed {{ {pressed_style} }}"
           
        btn.setStyleSheet(full_style)
       
        if tooltip:
            btn.setToolTip(tooltip)
       
        return btn

    def create_frame(self, style=None):
        frame = QFrame()
        frame.setStyleSheet(style or self.frame_style)
        return frame
