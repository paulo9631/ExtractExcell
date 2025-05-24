# Em um script separado ou no console Python
from modules.core.student_api import StudentAPIClient

client = StudentAPIClient()
client.login("professortest1@prof.educa.milha.ce.gov.br", "clvdev")

# Testar o método
try:
    resultado = client.buscar_por_inep("563214")
    print("Método funcionou:", resultado)
except Exception as e:
    print("Erro:", e)