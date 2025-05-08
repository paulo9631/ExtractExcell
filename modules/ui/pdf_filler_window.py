import os
import pandas as pd
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QFrame, QGridLayout,
    QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import Qt
from modules.core.pdf_filler import preencher_pdf_com_info
from PyPDF2 import PdfMerger
import tempfile
import os

class PDFFillerWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preencher Gabarito PDF")
        self.setMinimumWidth(500)
        self.setMinimumHeight(500)

        self.modelo_path = "modelo_gabarito_base.pdf"
        if not os.path.exists(self.modelo_path):
            QMessageBox.critical(self, "Erro", f"Modelo PDF não encontrado em: {self.modelo_path}")
            self.close()
            return

        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        section_title = QLabel("Informações do Aluno")
        section_title.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px;")
        main_layout.addWidget(section_title)

        form_frame = QFrame()
        form_frame.setStyleSheet("background-color: white; border-radius: 8px; border: 1px solid #e0e0e0;")
        form_layout = QGridLayout(form_frame)
        form_layout.setContentsMargins(15, 15, 15, 15)
        form_layout.setSpacing(10)

        self.campos = {}
        field_titles = {
            "nome": "Nome Completo",
            "matricula": "Matrícula",
            "escola": "Escola",
            "turma": "Turma",
            "turno": "Turno",
            "data_nascimento": "Data de Nascimento"
        }
        field_placeholders = {
            "nome": "Digite o nome completo do aluno",
            "matricula": "Digite a matrícula do aluno",
            "escola": "Digite o nome da escola",
            "turma": "Digite a turma (ex: 9º Ano A)",
            "turno": "Digite o turno (ex: Manhã, Tarde)",
            "data_nascimento": "Digite a data (ex: 01/01/2010)"
        }

        for row, campo in enumerate(field_titles):
            label = QLabel(field_titles[campo] + ":")
            label.setStyleSheet("font-weight: 500;")

            input_field = QLineEdit()
            input_field.setPlaceholderText(field_placeholders[campo])
            input_field.setStyleSheet("""
                QLineEdit {
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    padding: 8px;
                    background-color: #f9f9f9;
                }
                QLineEdit:focus {
                    border-color: #10b981;
                    background-color: white;
                }
            """)

            form_layout.addWidget(label, row, 0)
            form_layout.addWidget(input_field, row, 1)
            self.campos[campo] = input_field

        main_layout.addWidget(form_frame)

        info_layout = QHBoxLayout()
        model_label = QLabel("📄 Modelo:")
        model_label.setStyleSheet("color: #666;")
        model_name = QLabel(os.path.basename(self.modelo_path))
        model_name.setStyleSheet("color: #666;")
        info_layout.addWidget(model_label)
        info_layout.addWidget(model_name)
        info_layout.addStretch()
        main_layout.addLayout(info_layout)

        actions_layout = QHBoxLayout()
        btn_clear = QPushButton("Limpar Campos")
        btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
            }
        """)
        btn_clear.clicked.connect(self.clear_fields)

        btn_sample = QPushButton("Dados de Exemplo")
        btn_sample.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
            }
        """)
        btn_sample.clicked.connect(self.fill_sample_data)

        actions_layout.addWidget(btn_clear)
        actions_layout.addWidget(btn_sample)
        actions_layout.addStretch()
        main_layout.addLayout(actions_layout)

        main_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        footer_layout = QHBoxLayout()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
            }
        """)
        btn_cancelar.clicked.connect(self.reject)

        btn_lote = QPushButton("Gerar em Lote")
        btn_lote.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        btn_lote.clicked.connect(self.gerar_em_lote)

        self.btn_salvar = QPushButton("Gerar PDF")
        self.btn_salvar.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:disabled {
                background-color: #94a3b8;
            }
        """)
        self.btn_salvar.clicked.connect(self.gerar_pdf)

        footer_layout.addWidget(btn_cancelar)
        footer_layout.addWidget(btn_lote)
        footer_layout.addStretch()
        footer_layout.addWidget(self.btn_salvar)
        main_layout.addLayout(footer_layout)

    def clear_fields(self):
        for campo in self.campos.values():
            campo.clear()

    def fill_sample_data(self):
        exemplo = {
            'nome': 'João da Silva',
            'matricula': '12345678',
            'escola': 'Escola Municipal Exemplo',
            'turma': '9º Ano A',
            'turno': 'Manhã',
            'data_nascimento': '01/01/2010'
        }
        for k, v in exemplo.items():
            if k in self.campos:
                self.campos[k].setText(v)

    def carregar_alunos_de_planilha(self, caminho_arquivo):
        try:
            import pandas as pd
            df = pd.read_excel(caminho_arquivo) if caminho_arquivo.endswith(".xlsx") else pd.read_csv(caminho_arquivo)
            df = df.fillna("")  # substitui NaN por string vazia
            df = df.astype(str)  # converte tudo para string
            alunos = df.to_dict(orient="records")
            return alunos
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao ler a planilha:\n{e}")
            return []

    def gerar_em_lote(self):
        planilha_path, _ = QFileDialog.getOpenFileName(self, "Selecione a planilha de alunos", "", "Planilhas (*.xlsx *.csv)")
        if not planilha_path:
            return

        alunos = self.carregar_alunos_de_planilha(planilha_path)
        if not alunos:
            return

        pasta_saida = QFileDialog.getExistingDirectory(self, "Selecione a pasta de saída")
        if not pasta_saida:
            return

        merger = PdfMerger()
        arquivos_temp = []
        erros = 0

        for aluno in alunos:
            try:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                temp_file.close()
                preencher_pdf_com_info(self.modelo_path, [aluno], temp_file.name)
                merger.append(temp_file.name)
                arquivos_temp.append(temp_file.name)
            except Exception as e:
                erros += 1
                print(f"Erro com {aluno.get('nome', 'Aluno')} -> {e}")

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

            QMessageBox.information(
                self,
                "Sucesso",
                f"PDF unificado salvo em:\n{caminho_saida}\n\nFalhas: {erros}"
            )

    def gerar_pdf(self):
        pasta_saida = QFileDialog.getExistingDirectory(self, "Selecione a pasta para salvar o PDF")
        if not pasta_saida:
            return

        aluno = {k: campo.text().strip() for k, campo in self.campos.items()}
        if not aluno["nome"] or not aluno["matricula"]:
            QMessageBox.warning(self, "Campos Obrigatórios", "Preencha pelo menos nome e matrícula.")
            return

        nome_arquivo = f"{aluno['nome'].replace(' ', '_')}_gabarito.pdf"
        caminho_saida = os.path.join(pasta_saida, nome_arquivo)

        try:
            self.btn_salvar.setEnabled(False)
            self.btn_salvar.setText("Gerando PDF...")
            preencher_pdf_com_info(self.modelo_path, [aluno], caminho_saida)
            QMessageBox.information(self, "Sucesso", f"PDF salvo em:\n{caminho_saida}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao gerar PDF:\n{e}")
            self.btn_salvar.setEnabled(True)
            self.btn_salvar.setText("Gerar PDF")
