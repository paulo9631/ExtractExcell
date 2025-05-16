import requests
import logging
import time
import json
import os
import jwt

BASE_URL = "https://new-api.ideedutec.com"
TOKENS_FILE = "tokens.json"

logger = logging.getLogger(__name__)


def login_api(login: str, password: str):
    """
    Faz login no sistema IDEEDUTEC usando o endpoint /auth.
    Retorna accessToken e refreshToken.
    """
    url = f"{BASE_URL}/auth"
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


class StudentAPIClient:
    def __init__(self):
        self.token = None
        self.refresh_token = None
        self.load_tokens()

    def login(self, email, senha):
        self.token, self.refresh_token = login_api(email, senha)
        self.save_tokens()

    def _headers(self):
        if not self.token:
            raise Exception("Cliente não autenticado.")

        if self.token_expirado():
            logger.info("[AUTH] Token expirado, tentando renovar...")
            if not self.refresh_token or not self.refresh_token_valido():
                raise Exception("Sessão expirada. Faça login novamente.")
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
            return payload["exp"] < int(time.time()) + 30  # margem de 30s
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
            with open(TOKENS_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "accessToken": self.token,
                    "refreshToken": self.refresh_token
                }, f, indent=2)
            logger.info("[AUTH] Tokens salvos localmente.")
        except Exception as e:
            logger.warning(f"[AUTH] Falha ao salvar tokens: {e}")

    def load_tokens(self):
        if not os.path.exists(TOKENS_FILE):
            return
        try:
            with open(TOKENS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.token = data.get("accessToken")
                self.refresh_token = data.get("refreshToken")
            logger.info("[AUTH] Tokens carregados do disco.")
        except Exception as e:
            logger.warning(f"[AUTH] Falha ao carregar tokens: {e}")

    def logout(self):
        self.token = None
        self.refresh_token = None
        if os.path.exists(TOKENS_FILE):
            os.remove(TOKENS_FILE)
        logger.info("[AUTH] Tokens limpos.")

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
        url = f"{BASE_URL}/student/search"
        params = {"INEP": str(inep_codigo)}
        res = requests.get(url, headers=self._headers(), params=params)
        if res.status_code == 200:
            return res.json().get("data", [])
        elif res.status_code == 204:
            return []
        else:
            raise Exception(f"Erro API: {res.status_code} - {res.text}")
