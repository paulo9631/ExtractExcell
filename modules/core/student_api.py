import requests
import logging
import time
import json
import os
import jwt
from cryptography.fernet import Fernet

BASE_URL = "https://new-api.ideedutec.com"
TOKEN_FILE = "tokens.enc"
KEY_FILE = os.path.expanduser("~/.ideedutec_key.key")

logger = logging.getLogger(__name__)


def login_api(login: str, password: str):
    url = f"{BASE_URL}/auth/login"
    payload = {"login": login, "password": password}
    try:
        logger.info(f"[LOGIN_API] POST {url}")
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["accessToken"], data.get("refreshToken", None)
    except requests.HTTPError as http_err:
        logger.error(f"[LOGIN_API] HTTPError: {http_err}")
        raise Exception(f"Falha na autenticação: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"[LOGIN_API] Erro geral: {e}")
        raise Exception(f"Erro na requisição de login: {e}")


def gerar_chave_fernet():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
    with open(KEY_FILE, "rb") as f:
        return Fernet(f.read())


class StudentAPIClient:
    def __init__(self):
        self.token = None
        self.refresh_token = None
        self.fernet = gerar_chave_fernet()
        self.load_tokens()

    def login(self, email, senha):
        self.token, self.refresh_token = login_api(email, senha)
        self.save_tokens()

    def _headers(self):
        if not self.token:
            logger.warning("[AUTH] Usando modo não autenticado.")
            return {}  # Sem token, sem header
        if self.token_expirado():
            logger.info("[AUTH] Token expirado, tentando renovar...")
            if not self.refresh_token or not self.refresh_token_valido():
                logger.warning("[AUTH] Sessão expirada, seguindo sem autenticação.")
                return {}  # Fallback: header vazio
            self.renovar_token()
        return {"Authorization": f"Bearer {self.token}"}


    def renovar_token(self):
        url = f"{BASE_URL}/auth/refresh"
        payload = {"refreshToken": self.refresh_token}
        try:
            res = requests.post(url, json=payload)
            res.raise_for_status()
            data = res.json()
            self.token = data["accessToken"]
            self.save_tokens()
            logger.info("[AUTH] Token renovado com sucesso.")
        except Exception as e:
            logger.error(f"[AUTH] Falha ao renovar token: {e}")
            raise Exception("Não foi possível renovar o token.")

    def token_expirado(self):
        try:
            payload = jwt.decode(self.token, options={"verify_signature": False})
            return payload["exp"] < int(time.time()) + 30
        except Exception:
            return True

    def refresh_token_valido(self):
        try:
            payload = jwt.decode(self.refresh_token, options={"verify_signature": False})
            return payload["exp"] > int(time.time())
        except Exception:
            return False

    def save_tokens(self):
        try:
            data = {
                "accessToken": self.token,
                "refreshToken": self.refresh_token
            }
            json_bytes = json.dumps(data).encode("utf-8")
            encrypted = self.fernet.encrypt(json_bytes)
            with open(TOKEN_FILE, "wb") as f:
                f.write(encrypted)
            logger.info("[AUTH] Tokens criptografados e salvos.")
        except Exception as e:
            logger.warning(f"[AUTH] Falha ao salvar tokens: {e}")

    def load_tokens(self):
        if not os.path.exists(TOKEN_FILE):
            return
        try:
            with open(TOKEN_FILE, "rb") as f:
                encrypted = f.read()
                decrypted = self.fernet.decrypt(encrypted)
                data = json.loads(decrypted.decode("utf-8"))
                self.token = data.get("accessToken")
                self.refresh_token = data.get("refreshToken")
            logger.info("[AUTH] Tokens criptografados carregados.")
        except Exception as e:
            logger.warning(f"[AUTH] Falha ao carregar tokens: {e}")

    def logout(self):
        self.token = None
        self.refresh_token = None
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        logger.info("[AUTH] Sessão finalizada. Tokens apagados.")

    def buscar_por_matriculas(self, matriculas):
        url = f"{BASE_URL}/student/search"
        params = {"enrollments": ",".join(matriculas)}
        res = requests.get(url, headers=self._headers(), params=params)
        if res.status_code == 200:
            return res.json().get("data", [])
        elif res.status_code == 204:
            return []
        else:
            raise Exception(f"Erro API: {res.status_code} - {res.text}")

    def buscar_por_nomes(self, nomes):
        url = f"{BASE_URL}/student/search"
        params = {"names": ",".join(nomes)}
        res = requests.get(url, headers=self._headers(), params=params)
        if res.status_code == 200:
            return res.json().get("data", [])
        elif res.status_code == 204:
            return []
        else:
            raise Exception(f"Erro API: {res.status_code} - {res.text}")

    def buscar_por_inep(self, inep_codigo):
        """
        Busca estudantes pelo código INEP da escola.
        
        :param inep_codigo: Código INEP da escola
        :return: Lista de estudantes encontrados
        """
        logger.info(f"[BUSCAR_POR_INEP] Buscando estudantes para INEP: {inep_codigo}")
        url = f"{BASE_URL}/student/search"
        params = {"INEP": str(inep_codigo)}
        
        try:
            logger.debug(f"[BUSCAR_POR_INEP] GET {url} com params={params}")
            res = requests.get(url, headers=self._headers(), params=params)
            
            if res.status_code == 200:
                data = res.json().get("data", [])
                logger.info(f"[BUSCAR_POR_INEP] Encontrados {len(data)} estudantes")
                return data
            elif res.status_code == 204:
                logger.info("[BUSCAR_POR_INEP] Nenhum estudante encontrado")
                return []
            else:
                logger.error(f"[BUSCAR_POR_INEP] Erro na API: {res.status_code} - {res.text}")
                raise Exception(f"Erro API: {res.status_code} - {res.text}")
        except requests.RequestException as e:
            logger.error(f"[BUSCAR_POR_INEP] Erro na requisição: {e}")
            raise Exception(f"Erro na requisição: {e}")
        except Exception as e:
            logger.error(f"[BUSCAR_POR_INEP] Erro geral: {e}")
            raise Exception(f"Erro ao buscar estudantes: {e}")
