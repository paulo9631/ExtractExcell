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
logging.getLogger().setLevel(logging.INFO)

from PyQt6.QtWidgets import QApplication, QDialog
from modules.ui.login_window import LoginWindow
from modules.ui.gui import GabaritoApp
from modules.core.student_api import StudentAPIClient


def resource_path(relative_path):
    """
    Retorna o caminho absoluto para recursos, dentro ou fora do bundle PyInstaller.
    """
    try:
        base_path = sys._MEIPASS  # PyInstaller cria essa variável em runtime
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def carregar_configuracoes(path='config.json'):
    real_path = resource_path(path)
    if os.path.exists(real_path):
        try:
            with open(real_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Erro ao carregar config: {e}")
    # Retorno padrão se falhar
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
        client = login_window.client  # Cliente autenticado com token
        gui = GabaritoApp(config, client=client)  # GUI recebe o client
        gui.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)
