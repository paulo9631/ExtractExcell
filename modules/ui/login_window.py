import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QWidget, QApplication, QFrame, QMessageBox
)
from PyQt6.QtGui import QFont, QPixmap, QIcon, QColor
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QGraphicsDropShadowEffect

from modules.core.student_api import StudentAPIClient

class LoginWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("iDEEDUTEC - Login")
        self.setFixedSize(1200, 800)
        self.setWindowIcon(QIcon("assets/ideedutec_icon.png"))
        self.client = StudentAPIClient()
        self.token = None

        self.showFullScreen()
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        card_widget = QFrame()
        card_widget.setObjectName("card")
        card_widget.setStyleSheet("""
            #card {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e0e0e0;
            }
        """)
        card_layout = QVBoxLayout(card_widget)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(25)

        card_widget.setFixedWidth(650)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 4)
        card_widget.setGraphicsEffect(shadow)

        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(5)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo_label = QLabel()
        logo_pixmap = QPixmap("assets/logo_horizontal.png")
        logo_pixmap = logo_pixmap.scaled(
            200, 100,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        logo_label.setPixmap(logo_pixmap)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(logo_label)

        card_layout.addWidget(header_widget)

        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(15)
        form_layout.setContentsMargins(0, 15, 0, 0)

        email_label = QLabel("E-mail")
        email_label.setStyleSheet("font-size: 16px; color: #333; font-weight: 500;")
        self.input_email = QLineEdit()
        self.input_email.setPlaceholderText("exemplo@ideedutec.com.br")
        self.input_email.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                background-color: #f8f9fa;
                font-size: 15px;
                color: #333;
            }
            QLineEdit:focus {
                border: 1px solid #2563eb;
                background-color: white;
            }
        """)
        self.input_email.setMinimumHeight(45)

        form_layout.addWidget(email_label)
        form_layout.addWidget(self.input_email)

        senha_label = QLabel("Senha")
        senha_label.setStyleSheet("font-size: 16px; color: #333; font-weight: 500;")
        self.input_senha = QLineEdit()
        self.input_senha.setPlaceholderText("Digite sua senha")
        self.input_senha.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_senha.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                background-color: #f8f9fa;
                font-size: 15px;
                color: #333;
            }
            QLineEdit:focus {
                border: 1px solid #2563eb;
                background-color: white;
            }
        """)
        self.input_senha.setMinimumHeight(45)

        form_layout.addWidget(senha_label)
        form_layout.addWidget(self.input_senha)

        card_layout.addWidget(form_widget)

        btn_entrar = QPushButton("ENTRAR")
        btn_entrar.setFixedHeight(50)
        btn_entrar.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:pressed {
                background-color: #047857;
            }
        """)
        btn_entrar.clicked.connect(self.fazer_login)
        card_layout.addWidget(btn_entrar)

        main_layout.addStretch(1)
        main_layout.addWidget(card_widget, 0, Qt.AlignmentFlag.AlignHCenter)
        main_layout.addStretch(1)

        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255,255,255,0.4), stop:1 rgba(255,255,255,0.4)
                ), 
                url("assets/background.jpg");
                background-repeat: no-repeat;
                background-position: center;
                background-size: cover;
            }
            QLabel {
                color: #333;
            }
        """)

    def create_shadow_effect(self):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 4)
        return shadow

    def fazer_login(self):
        email = self.input_email.text().strip()
        senha = self.input_senha.text().strip()

        if not email or not senha:
            QMessageBox.warning(self, "Erro", "Preencha o e-mail e a senha.")
            return

        try:
            self.client.login(email, senha)
            self.token = self.client.token
            QMessageBox.information(self, "Sucesso", "Login bem-sucedido!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao realizar login:\n{e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())
