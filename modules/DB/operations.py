from typing import Optional
from sqlmodel import SQLModel, Session, create_engine, select
from modules.DB.models import Aluno

engine = create_engine("sqlite:///alunos.db")

def criar_tabelas_excel():
    SQLModel.metadata.create_all(engine)

def salvar_aluno_excel(aluno: Aluno):
    with Session(engine) as session:
        session.add(aluno)
        session.commit()

def salvar_alunos_em_lote_excel(lista_de_dicts: list[dict]):
    with Session(engine) as session:
        for dados in lista_de_dicts:
            aluno = Aluno(**dados)
            session.add(aluno)
        session.commit()

def buscar_por_matricula_excel(matricula: str):
    with Session(engine) as session:
        result = session.exec(select(Aluno).where(Aluno.matricula == matricula)).first()
        return result

def buscar_por_turma_excel(turma: str):
    with Session(engine) as session:
        result = session.exec(select(Aluno).where(Aluno.turma == turma)).all()
        return result

def buscar_por_matricula(matricula: str) -> Optional[Aluno]:
    with Session(engine) as session:
        return session.exec(select(Aluno).where(Aluno.matricula == matricula)).first()
