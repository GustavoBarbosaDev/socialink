"""Fixtures compartilhadas por toda a suíte de testes.

Cada teste recebe um banco SQLite em memória próprio (engine `sqlite://`)
e a aplicação real com a dependência `get_session` substituída por essa
sessão — assim nenhum teste enxerga dados de outro.
"""

import os

# Precisa rodar antes de importar app.*: Settings valida SECRET_KEY na criação
# e os módulos de app chamam get_settings() no import (cachê lru_cache).
# Assim a suíte é hermética — roda em clone fresco, sem .env, e nunca
# depende da chave secreta real de quem está desenvolvendo.
os.environ.setdefault("SECRET_KEY", "chave_de_teste_so_para_suíte_nao_usar_em_producao")

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import app


@pytest.fixture(name="session")
def session_fixture():
    """Cria uma sessão de teste isolada para cada teste."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Cliente de teste apontando para a aplicação real (app.main:app)."""
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
