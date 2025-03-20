import json
import os
import logging

def carregar_configuracoes(path='config.json', config_padrao=None):
    if config_padrao is None:
        config_padrao = {
            "dpi_visualizacao": 150,
            "dpi_processamento": 300,
            "threshold_fill": 0.5,
            "caminho_saida": "resultados.xlsx"
        }
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Erro ao carregar config: {e}")
    return config_padrao

def salvar_configuracoes(path, config):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        print(f"Configurações salvas em {path}")
    except Exception as e:
        print(f"Erro ao salvar config: {e}")

def exibir_mensagem_erro(msg):
    print(f"[ERRO] {msg}")

logger = logging.getLogger('GabaritoApp')
