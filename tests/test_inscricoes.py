import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.main import app
from app.database import get_session
from app.models import Inscricao, Usuario


@pytest.fixture(name="session")
def session_fixture():
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
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def _criar_organizacao(session: Session, email: str = "ong@example.com") -> Usuario:
    from app.routers.auth import get_password_hash

    usuario = Usuario(
        nome="ONG Teste",
        email=email,
        senha_hash=get_password_hash("123456"),
        papel="organizacao",
    )
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


def _criar_voluntario(session: Session, email: str = "voluntario@example.com") -> Usuario:
    from app.routers.auth import get_password_hash

    usuario = Usuario(
        nome="Voluntário Teste",
        email=email,
        senha_hash=get_password_hash("123456"),
        papel="voluntario",
    )
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


def _fazer_login(client: TestClient, email: str, senha: str = "123456") -> str:
    response = client.post(
        "/auth/login",
        json={"email": email, "senha": senha},
    )
    return response.json()["access_token"]


def _dados_oportunidade() -> dict:
    return {
        "titulo": "Campanha de arrecadação",
        "descricao": "Ajudar na organização de doações para famílias carentes",
        "local": "Centro Comunitário, São Paulo",
        "data": datetime(2026, 10, 15, 9, 0, 0, tzinfo=timezone.utc).isoformat(),
        "vagas_disponiveis": 10,
    }


def _criar_oportunidade(client: TestClient, token: str) -> int:
    response = client.post(
        "/oportunidades/",
        json=_dados_oportunidade(),
        headers={"Authorization": f"Bearer {token}"},
    )
    return response.json()["id"]


# ============================================================
# Testes de Inscrição (POST /oportunidades/{id}/inscricoes)
# ============================================================

def test_inscrever_voluntario_sucesso(client: TestClient, session: Session):
    org = _criar_organizacao(session)
    vol = _criar_voluntario(session)
    token_org = _fazer_login(client, org.email)
    token_vol = _fazer_login(client, vol.email)
    opp_id = _criar_oportunidade(client, token_org)

    response = client.post(
        f"/oportunidades/{opp_id}/inscricoes",
        headers={"Authorization": f"Bearer {token_vol}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["oportunidade_id"] == opp_id
    assert data["voluntario_id"] == vol.id
    assert data["status"] == "pendente"
    assert "id" in data


def test_inscrever_duplicado_proibido(client: TestClient, session: Session):
    org = _criar_organizacao(session)
    vol = _criar_voluntario(session)
    token_org = _fazer_login(client, org.email)
    token_vol = _fazer_login(client, vol.email)
    opp_id = _criar_oportunidade(client, token_org)

    headers = {"Authorization": f"Bearer {token_vol}"}
    primeira = client.post(f"/oportunidades/{opp_id}/inscricoes", headers=headers)
    assert primeira.status_code == 201

    segunda = client.post(f"/oportunidades/{opp_id}/inscricoes", headers=headers)
    assert segunda.status_code == 409
    assert segunda.json()["detail"] == "Voluntário já inscrito nesta oportunidade"

    # Apenas uma inscrição persistida
    inscricoes = session.exec(select(Inscricao)).all()
    assert len(inscricoes) == 1


def test_inscrever_sem_token(client: TestClient, session: Session):
    org = _criar_organizacao(session)
    token_org = _fazer_login(client, org.email)
    opp_id = _criar_oportunidade(client, token_org)

    response = client.post(f"/oportunidades/{opp_id}/inscricoes")
    assert response.status_code == 401


def test_inscrever_token_invalido(client: TestClient, session: Session):
    org = _criar_organizacao(session)
    token_org = _fazer_login(client, org.email)
    opp_id = _criar_oportunidade(client, token_org)

    response = client.post(
        f"/oportunidades/{opp_id}/inscricoes",
        headers={"Authorization": "Bearer token_invalido"},
    )
    assert response.status_code == 401


def test_inscrever_organizacao_proibido(client: TestClient, session: Session):
    org = _criar_organizacao(session)
    token_org = _fazer_login(client, org.email)
    opp_id = _criar_oportunidade(client, token_org)

    response = client.post(
        f"/oportunidades/{opp_id}/inscricoes",
        headers={"Authorization": f"Bearer {token_org}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Apenas voluntários podem executar esta ação"


def test_inscrever_oportunidade_inexistente(client: TestClient, session: Session):
    vol = _criar_voluntario(session)
    token_vol = _fazer_login(client, vol.email)

    response = client.post(
        "/oportunidades/999/inscricoes",
        headers={"Authorization": f"Bearer {token_vol}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Oportunidade não encontrada"


def test_inscrever_outro_voluntario_mesma_oportunidade(
    client: TestClient, session: Session
):
    org = _criar_organizacao(session)
    vol1 = _criar_voluntario(session, email="vol1@example.com")
    vol2 = _criar_voluntario(session, email="vol2@example.com")
    token_org = _fazer_login(client, org.email)
    token_vol1 = _fazer_login(client, vol1.email)
    token_vol2 = _fazer_login(client, vol2.email)
    opp_id = _criar_oportunidade(client, token_org)

    primeira = client.post(
        f"/oportunidades/{opp_id}/inscricoes",
        headers={"Authorization": f"Bearer {token_vol1}"},
    )
    segunda = client.post(
        f"/oportunidades/{opp_id}/inscricoes",
        headers={"Authorization": f"Bearer {token_vol2}"},
    )
    assert primeira.status_code == 201
    assert segunda.status_code == 201

    inscricoes = session.exec(select(Inscricao)).all()
    assert len(inscricoes) == 2


# ============================================================
# Testes de Listagem (GET /voluntario/me/inscricoes)
# ============================================================

def test_listar_minhas_inscricoes_vazia(client: TestClient, session: Session):
    vol = _criar_voluntario(session)
    token = _fazer_login(client, vol.email)

    response = client.get(
        "/voluntario/me/inscricoes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_listar_minhas_inscricoes_com_dados(client: TestClient, session: Session):
    org = _criar_organizacao(session)
    vol = _criar_voluntario(session)
    token_org = _fazer_login(client, org.email)
    token_vol = _fazer_login(client, vol.email)
    opp_id = _criar_oportunidade(client, token_org)

    client.post(
        f"/oportunidades/{opp_id}/inscricoes",
        headers={"Authorization": f"Bearer {token_vol}"},
    )

    response = client.get(
        "/voluntario/me/inscricoes",
        headers={"Authorization": f"Bearer {token_vol}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["oportunidade_id"] == opp_id
    assert data[0]["voluntario_id"] == vol.id


def test_listar_minhas_inscricoes_isoladas_por_usuario(
    client: TestClient, session: Session
):
    org = _criar_organizacao(session)
    vol1 = _criar_voluntario(session, email="vol1@example.com")
    vol2 = _criar_voluntario(session, email="vol2@example.com")
    token_org = _fazer_login(client, org.email)
    token_vol1 = _fazer_login(client, vol1.email)
    token_vol2 = _fazer_login(client, vol2.email)
    opp_id = _criar_oportunidade(client, token_org)

    client.post(
        f"/oportunidades/{opp_id}/inscricoes",
        headers={"Authorization": f"Bearer {token_vol1}"},
    )
    client.post(
        f"/oportunidades/{opp_id}/inscricoes",
        headers={"Authorization": f"Bearer {token_vol2}"},
    )

    response = client.get(
        "/voluntario/me/inscricoes",
        headers={"Authorization": f"Bearer {token_vol1}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["voluntario_id"] == vol1.id


def test_listar_minhas_inscricoes_sem_token(client: TestClient):
    response = client.get("/voluntario/me/inscricoes")
    assert response.status_code == 401


def test_listar_minhas_inscricoes_organizacao_proibido(
    client: TestClient, session: Session
):
    org = _criar_organizacao(session)
    token = _fazer_login(client, org.email)

    response = client.get(
        "/voluntario/me/inscricoes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Apenas voluntários podem executar esta ação"
