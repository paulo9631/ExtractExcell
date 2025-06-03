import sys
import os
import json
import logging

def resource_path(relative_path):
    """
    Retorna o caminho absoluto para recursos, considerando o bundle do PyInstaller.
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def carregar_configuracoes(path='config.json', config_padrao=None):
    if config_padrao is None:
        config_padrao = {
            "dpi_visualizacao": 150,
            "dpi_processamento": 300,
            "threshold_fill": 0.5,
            "caminho_saida": "resultados.xlsx"
        }
    real_path = resource_path(path)
    if os.path.exists(real_path):
        try:
            with open(real_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Erro ao carregar config: {e}")
    return config_padrao

def salvar_configuracoes(path, config):
    try:
        real_path = resource_path(path)
        with open(real_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        print(f"Configurações salvas em {real_path}")
    except Exception as e:
        print(f"Erro ao salvar config: {e}")

def exibir_mensagem_erro(msg):
    print(f"[ERRO] {msg}")

logger = logging.getLogger('GabaritoApp')
