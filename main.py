import sys
import json
import os
from PyQt6.QtWidgets import QApplication, QDialog

from modules.ui.gui import GabaritoApp
from modules.ui.login_window import LoginWindow
from modules.utils import carregar_configuracoes

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
    resultado = login_window.exec()

    if resultado == QDialog.DialogCode.Accepted:
        config = carregar_configuracoes()
        gui = GabaritoApp(config)
        gui.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)
