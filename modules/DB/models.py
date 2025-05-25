from sqlmodel import SQLModel, Field

class Aluno(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nome: str
    matricula: str
    escola: str
    turma: str
    turno: str
    data_nascimento: str
    fonte: str
