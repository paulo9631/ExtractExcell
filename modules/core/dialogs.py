from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QLabel,
    QFormLayout, QHBoxLayout, QPushButton, QGroupBox,
    QScrollArea, QGraphicsDropShadowEffect, QGridLayout
)
from PyQt6.QtGui import QPixmap, QColor, QFont
from PIL.ImageQt import ImageQt

from modules.ui.icon_provider import IconProvider
from modules.ui.modern_widgets import ModernButton

class ResultadoDialog(QDialog):
    """Mostra as abas: Resumo e Detalhes (pré-visualização removida)."""
    def __init__(self, resultados, parent=None):
        super().__init__(parent)
        self.resultados = resultados
        self.setWindowTitle("Resultados do Processamento")
        self.setMinimumSize(900, 600)
        self.initUI()

        self.setWindowOpacity(0)
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.start()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(IconProvider.get_icon("chart", "#4a90e2", 32).pixmap(32, 32))
        header_layout.addWidget(icon_label)
        title_label = QLabel("Resultados do Processamento")
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #4a90e2;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._inicializar_tab_resumo()
        self._inicializar_tab_detalhes()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_fechar = ModernButton("Fechar", "close", False)
        btn_fechar.clicked.connect(self.accept)
        btn_layout.addWidget(btn_fechar)
        layout.addLayout(btn_layout)

    def _inicializar_tab_resumo(self):
        tab_resumo = QWidget()
        resumo_layout = QVBoxLayout(tab_resumo)
        resumo_layout.setContentsMargins(20, 20, 20, 20)
        resumo_layout.setSpacing(20)
        
        header_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(IconProvider.get_icon("chart", "#4a90e2", 24).pixmap(24, 24))
        header_layout.addWidget(icon_label)
        lbl_title = QLabel("Resumo do Processamento")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        resumo_layout.addLayout(header_layout)

        group_stats = QGroupBox("Estatísticas")
        stats_layout = QGridLayout(group_stats)
        stats_layout.setVerticalSpacing(15)
        stats_layout.setHorizontalSpacing(20)

        stats_layout.addWidget(QLabel("Total de páginas processadas:"), 0, 0)
        total_label = QLabel(f"{len(self.resultados)}")
        total_label.setStyleSheet("font-weight: bold; color: #4a90e2; font-size: 16px;")
        stats_layout.addWidget(total_label, 0, 1)

        contagem = {'A':0,'B':0,'C':0,'D':0,'E':0,'Não marcado':0,'Anulada':0}
        for pagina in self.resultados:
            for resp in pagina['Respostas'].values():
                if resp in contagem:
                    contagem[resp]+=1
                elif "Não marcado" in resp:
                    contagem["Não marcado"]+=1
                elif "anulada" in resp.lower():
                    contagem["Anulada"]+=1

        row = 1
        for k,v in contagem.items():
            if v>0:
                stats_layout.addWidget(QLabel(f"Respostas {k}:"), row, 0)
                value_label = QLabel(str(v))
                value_label.setStyleSheet("font-weight: bold; color: #4a90e2; font-size: 16px;")
                stats_layout.addWidget(value_label, row, 1)
                row += 1

        resumo_layout.addWidget(group_stats)
        resumo_layout.addStretch()

        self.tabs.addTab(tab_resumo, "Resumo")

    def _inicializar_tab_detalhes(self):
        tab_detalhes = QWidget()
        detalhes_layout = QVBoxLayout(tab_detalhes)
        detalhes_layout.setContentsMargins(20, 20, 20, 20)
        detalhes_layout.setSpacing(20)
        
        header_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(IconProvider.get_icon("file", "#4a90e2", 24).pixmap(24, 24))
        header_layout.addWidget(icon_label)
        lbl_title = QLabel("Detalhes das Respostas")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        detalhes_layout.addLayout(header_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        sc_layout = QVBoxLayout(scroll_content)
        sc_layout.setContentsMargins(10, 10, 10, 10)
        sc_layout.setSpacing(20)

        for idx, pagina in enumerate(self.resultados):
            grp = QGroupBox(f"{pagina['Página']} - {pagina.get('Arquivo','')}")
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(10)
            shadow.setColor(QColor(0, 0, 0, 20))
            shadow.setOffset(0, 2)
            grp.setGraphicsEffect(shadow)
            
            grp_lay = QVBoxLayout(grp)
            grp_lay.setContentsMargins(15, 20, 15, 15)
            grp_lay.setSpacing(15)

            if pagina.get("OCR"):
                ocr_info = pagina["OCR"]
                ocr_layout = QFormLayout()
                ocr_layout.setVerticalSpacing(10)
                ocr_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
                
                if ocr_info.get("nome_aluno"):
                    nome_label = QLabel(ocr_info['nome_aluno'])
                    nome_label.setStyleSheet("font-weight: bold; color: #333;")
                    ocr_layout.addRow("Nome:", nome_label)
                    
                if ocr_info.get("escola"):
                    escola_label = QLabel(ocr_info['escola'])
                    escola_label.setStyleSheet("font-weight: bold; color: #333;")
                    ocr_layout.addRow("Escola:", escola_label)
                    
                if ocr_info.get("turma"):
                    turma_label = QLabel(ocr_info['turma'])
                    turma_label.setStyleSheet("font-weight: bold; color: #333;")
                    ocr_layout.addRow("Turma:", turma_label)
                
                if ocr_layout.rowCount() > 0:
                    ocr_group = QGroupBox("Informações do Aluno")
                    ocr_group.setLayout(ocr_layout)
                    grp_lay.addWidget(ocr_group)

            respostas_group = QGroupBox("Respostas")
            respostas_layout = QGridLayout(respostas_group)
            respostas_layout.setVerticalSpacing(10)
            respostas_layout.setHorizontalSpacing(20)
            
            header_questao = QLabel("Questão")
            header_questao.setStyleSheet("font-weight: bold; color: #666;")
            respostas_layout.addWidget(header_questao, 0, 0)
            
            header_resposta = QLabel("Resposta")
            header_resposta.setStyleSheet("font-weight: bold; color: #666;")
            respostas_layout.addWidget(header_resposta, 0, 1)
            
            row = 1
            respostas_dict = pagina["Respostas"]
            respostas_ordenadas = sorted(respostas_dict.items(), key=lambda x: int(x[0].split()[1]))
            for questao, resp in respostas_ordenadas:
                q_label = QLabel(questao)
                q_label.setStyleSheet("color: #333;")
                respostas_layout.addWidget(q_label, row, 0)
                r_label = QLabel(resp)
                if resp in ['A', 'B', 'C', 'D', 'E']:
                    r_label.setStyleSheet("font-weight: bold; color: #4a90e2;")
                elif "Não marcado" in resp:
                    r_label.setStyleSheet("font-weight: bold; color: #f5a623;")
                elif "anulada" in resp.lower():
                    r_label.setStyleSheet("font-weight: bold; color: #d0021b;")
                else:
                    r_label.setStyleSheet("font-weight: bold; color: #333;")
                respostas_layout.addWidget(r_label, row, 1)
                row += 1
                
            grp_lay.addWidget(respostas_group)
            sc_layout.addWidget(grp)

        scroll.setWidget(scroll_content)
        detalhes_layout.addWidget(scroll)
        self.tabs.addTab(tab_detalhes, "Detalhes")
