import requests

BASE_URL = "https://new-api.ideedutec.com"

import requests
import logging

BASE_URL = "https://new-api.ideedutec.com"

logger = logging.getLogger(__name__)

def login_api(email, senha, base_url=BASE_URL):
    """
    Faz a requisição POST para /auth/login e retorna accessToken e refreshToken.
    """
    url = f"{base_url}/auth/login"
    payload = {
        "login": email,
        "password": senha
    }
    try:
        logger.info(f"[LOGIN_API] Enviando POST para {url} com payload={payload}")
        
        response = requests.post(url, json=payload)
        
        logger.info(f"[LOGIN_API] Resposta HTTP {response.status_code} - {response.text}")
        
        response.raise_for_status()
        
        data = response.json()
        access_token = data.get("accessToken")
        refresh_token = data.get("refreshToken")
        
        logger.info(f"[LOGIN_API] accessToken={access_token}, refreshToken={refresh_token}")
        
        return access_token, refresh_token
    except requests.HTTPError as http_err:
        logger.error(f"[LOGIN_API] HTTPError: {http_err}")
        msg = f"Falha na autenticação (HTTP {response.status_code}): {response.text}"
        raise Exception(msg) from http_err
    except Exception as e:
        logger.error(f"[LOGIN_API] Erro geral: {e}")
        raise Exception(f"Erro na requisição de login: {e}")


def listar_escolas():
    """
    Chama GET /school para obter a lista de escolas.
    """
    url = f"{BASE_URL}/school"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Erro ao listar escolas: {e}")
        return []

def buscar_estudante(enrollment, base_url=BASE_URL):
    """
    Busca um estudante específico via matrícula.
    O endpoint retorna um objeto com a chave 'data' contendo uma lista.
    """
    url = f"{base_url}/student/search"
    params = {"enrollments": enrollment}
    print(f"[DEBUG] Requisição: {url} com parâmetros: {params}")
    try:
        response = requests.get(url, params=params)
        print(f"[DEBUG] Status Code: {response.status_code}")
        if response.status_code == 200:
            json_data = response.json()
            if "data" in json_data and isinstance(json_data["data"], list) and json_data["data"]:
                return json_data["data"][0]
            return {}
        elif response.status_code == 204:
            return {}
        else:
            print(f"API retornou status_code {response.status_code} - conteúdo: {response.text}")
            return {}
    except Exception as e:
        print(f"Erro ao buscar estudante: {e}")
        return {}

def buscar_estudantes_via_names(names):
    """
    Busca estudantes pelo nome.
    """
    url = f"{BASE_URL}/student/search"
    params = {"names": names}
    try:
        resp = requests.get(url, params=params)
        if resp.status_code == 200:
            json_data = resp.json()
            if "data" in json_data and isinstance(json_data["data"], list):
                return json_data["data"]
            return []
        elif resp.status_code == 204:
            return []
        else:
            raise Exception(f"Erro API: status={resp.status_code}")
    except Exception as e:
        raise Exception(f"Falha ao consultar API: {e}")
