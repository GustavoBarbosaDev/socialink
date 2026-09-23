import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.main import app
from app.database import get_session
from app.models import Usuario, Oportunidade


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


# ============================================================
# Testes de Criação (POST /oportunidades)
# ============================================================

def test_criar_oportunidade_sucesso(client: TestClient, session: Session):
    org = _criar_organizacao(session)
    token = _fazer_login(client, org.email)

    response = client.post(
        "/oportunidades/",
        json=_dados_oportunidade(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["titulo"] == "Campanha de arrecadação"
    assert data["vagas_disponiveis"] == 10
    assert data["organizacao_id"] == org.id
    assert "id" in data


def test_criar_oportunidade_sem_token(client: TestClient):
    response = client.post("/oportunidades/", json=_dados_oportunidade())
    assert response.status_code == 401


def test_criar_oportunidade_token_invalido(client: TestClient):
    response = client.post(
        "/oportunidades/",
        json=_dados_oportunidade(),
        headers={"Authorization": "Bearer token_invalido"},
    )
    assert response.status_code == 401


def test_criar_oportunidade_vagas_invalida(client: TestClient, session: Session):
    org = _criar_organizacao(session)
    token = _fazer_login(client, org.email)

    dados = _dados_oportunidade()
    dados["vagas_disponiveis"] = 0  # mínimo é 1

    response = client.post(
        "/oportunidades/",
        json=dados,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_criar_oportunidade_campos_obrigatorios(client: TestClient, session: Session):
    org = _criar_organizacao(session)
    token = _fazer_login(client, org.email)

    response = client.post(
        "/oportunidades/",
        json={"titulo": "Sem os outros campos"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


# ============================================================
# Testes de Listagem (GET /oportunidades)
# ============================================================

def test_listar_oportunidades_vazia(client: TestClient):
    response = client.get("/oportunidades/")
    assert response.status_code == 200
    assert response.json() == []


def test_listar_oportunidades_com_dados(client: TestClient, session: Session):
    org = _criar_organizacao(session)
    token = _fazer_login(client, org.email)

    client.post(
        "/oportunidades/",
        json=_dados_oportunidade(),
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.get("/oportunidades/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["titulo"] == "Campanha de arrecadação"


# ============================================================
# Testes de Detalhe (GET /oportunidades/{id})
# ============================================================

def test_detalhar_oportunidade_existente(client: TestClient, session: Session):
    org = _criar_organizacao(session)
    token = _fazer_login(client, org.email)

    create_response = client.post(
        "/oportunidades/",
        json=_dados_oportunidade(),
        headers={"Authorization": f"Bearer {token}"},
    )
    opp_id = create_response.json()["id"]

    response = client.get(f"/oportunidades/{opp_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == opp_id
    assert data["titulo"] == "Campanha de arrecadação"


def test_detalhar_oportunidade_inexistente(client: TestClient):
    response = client.get("/oportunidades/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Oportunidade não encontrada"


# ============================================================
# Testes de Atualização (PATCH /oportunidades/{id})
# ============================================================

def test_atualizar_oportunidade_dono(client: TestClient, session: Session):
    org = _criar_organizacao(session)
    token = _fazer_login(client, org.email)

    create_response = client.post(
        "/oportunidades/",
        json=_dados_oportunidade(),
        headers={"Authorization": f"Bearer {token}"},
    )
    opp_id = create_response.json()["id"]

    response = client.patch(
        f"/oportunidades/{opp_id}",
        json={"titulo": "Título Atualizado"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["titulo"] == "Título Atualizado"
    assert data["descricao"] == "Ajudar na organização de doações para famílias carentes"


def test_atualizar_oportunidade_nao_dono(client: TestClient, session: Session):
    org1 = _criar_organizacao(session, email="ong1@example.com")
    org2 = _criar_organizacao(session, email="ong2@example.com")
    token1 = _fazer_login(client, org1.email)
    token2 = _fazer_login(client, org2.email)

    create_response = client.post(
        "/oportunidades/",
        json=_dados_oportunidade(),
        headers={"Authorization": f"Bearer {token1}"},
    )
    opp_id = create_response.json()["id"]

    response = client.patch(
        f"/oportunidades/{opp_id}",
        json={"titulo": "Tentativa de Hack"},
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert response.status_code == 403


def test_atualizar_oportunidade_inexistente(client: TestClient, session: Session):
    org = _criar_organizacao(session)
    token = _fazer_login(client, org.email)

    response = client.patch(
        "/oportunidades/999",
        json={"titulo": "Qualquer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# ============================================================
# Testes de Remoção (DELETE /oportunidades/{id})
# ============================================================

def test_remover_oportunidade_dono(client: TestClient, session: Session):
    org = _criar_organizacao(session)
    token = _fazer_login(client, org.email)

    create_response = client.post(
        "/oportunidades/",
        json=_dados_oportunidade(),
        headers={"Authorization": f"Bearer {token}"},
    )
    opp_id = create_response.json()["id"]

    response = client.delete(
        f"/oportunidades/{opp_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    # Verificar que não existe mais
    get_response = client.get(f"/oportunidades/{opp_id}")
    assert get_response.status_code == 404


def test_remover_oportunidade_nao_dono(client: TestClient, session: Session):
    org1 = _criar_organizacao(session, email="ong1@example.com")
    org2 = _criar_organizacao(session, email="ong2@example.com")
    token1 = _fazer_login(client, org1.email)
    token2 = _fazer_login(client, org2.email)

    create_response = client.post(
        "/oportunidades/",
        json=_dados_oportunidade(),
        headers={"Authorization": f"Bearer {token1}"},
    )
    opp_id = create_response.json()["id"]

    response = client.delete(
        f"/oportunidades/{opp_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert response.status_code == 403


def test_remover_oportunidade_inexistente(client: TestClient, session: Session):
    org = _criar_organizacao(session)
    token = _fazer_login(client, org.email)

    response = client.delete(
        "/oportunidades/999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
