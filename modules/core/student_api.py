import requests

# Defina o BASE_URL com https:// e sem repetir “/student/search”
BASE_URL = "https://new-api.ideedutec.com"

def listar_escolas():
    """
    Exemplo de função que chama GET /school para obter a lista de escolas.
    Ajuste o endpoint e o formato do retorno conforme seu back-end.
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
    url = f"{base_url}/student/search"
    params = {"enrollments": enrollment}
    print(f"[DEBUG] Requisição: {url} com parâmetros: {params}")
    try:
        response = requests.get(url, params=params)
        print(f"[DEBUG] Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and data:
                return data[0]
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
    Chama GET /student/search?names={names}, retornando uma lista de alunos (ou lista vazia).
    """
    url = f"{BASE_URL}/student/search"
    params = {"names": names}
    try:
        resp = requests.get(url, params=params)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                return data
            return []
        elif resp.status_code == 204:
            return []
        else:
            raise Exception(f"Erro API: status={resp.status_code}")
    except Exception as e:
        raise Exception(f"Falha ao consultar API: {e}")