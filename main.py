import sys
import json
import os
import logging

# Configura os níveis de logging para bibliotecas externas
logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("pdf2image").setLevel(logging.WARNING)
logging.getLogger("pytesseract").setLevel(logging.WARNING)
logging.getLogger("fitz").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger().setLevel(logging.INFO)  # Nível geral do seu app

from PyQt6.QtWidgets import QApplication, QDialog
from modules.ui.login_window import LoginWindow
from modules.ui.gui import GabaritoApp

def carregar_configuracoes(path='config.json'):
    """Carrega as configurações do arquivo JSON."""
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Erro ao carregar config: {e}")
    return {
        "dpi_visualizacao": 150,
        "dpi_processamento": 300,
        "threshold_fill": 0.3,
        "caminho_saida": "resultados.xlsx"
    }

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    login_window = LoginWindow()
    if login_window.exec() == QDialog.DialogCode.Accepted:
        config = carregar_configuracoes()
        gui = GabaritoApp(config)
        gui.showFullScreen()  # Abre a tela principal em tela cheia
        sys.exit(app.exec())
    else:
        sys.exit(0)
