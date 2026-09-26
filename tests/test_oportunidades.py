from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Oportunidade
from tests.helpers import (
    criar_organizacao,
    criar_oportunidade,
    criar_voluntario,
    dados_oportunidade,
    fazer_login,
)


# ============================================================
# Testes de Criação (POST /oportunidades)
# ============================================================

def test_criar_oportunidade_sucesso(client: TestClient, session: Session):
    org = criar_organizacao(session)
    token = fazer_login(client, org.email)

    response = client.post(
        "/oportunidades/",
        json=dados_oportunidade(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["titulo"] == "Campanha de arrecadação"
    assert data["vagas_disponiveis"] == 10
    assert data["organizacao_id"] == org.id
    assert "id" in data


def test_criar_oportunidade_sem_token(client: TestClient):
    response = client.post("/oportunidades/", json=dados_oportunidade())
    assert response.status_code == 401


def test_criar_oportunidade_token_invalido(client: TestClient):
    response = client.post(
        "/oportunidades/",
        json=dados_oportunidade(),
        headers={"Authorization": "Bearer token_invalido"},
    )
    assert response.status_code == 401


def test_criar_oportunidade_vagas_invalida(client: TestClient, session: Session):
    org = criar_organizacao(session)
    token = fazer_login(client, org.email)

    dados = dados_oportunidade()
    dados["vagas_disponiveis"] = 0  # mínimo é 1

    response = client.post(
        "/oportunidades/",
        json=dados,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_criar_oportunidade_campos_obrigatorios(client: TestClient, session: Session):
    org = criar_organizacao(session)
    token = fazer_login(client, org.email)

    response = client.post(
        "/oportunidades/",
        json={"titulo": "Sem os outros campos"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_criar_oportunidade_voluntario_proibido(client: TestClient, session: Session):
    vol = criar_voluntario(session)
    token = fazer_login(client, vol.email)

    response = client.post(
        "/oportunidades/",
        json=dados_oportunidade(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Apenas organizações podem executar esta ação"


# ============================================================
# Testes de Listagem (GET /oportunidades)
# ============================================================

def test_listar_oportunidades_vazia(client: TestClient):
    response = client.get("/oportunidades/")
    assert response.status_code == 200
    assert response.json() == []


def test_listar_oportunidades_com_dados(client: TestClient, session: Session):
    org = criar_organizacao(session)
    token = fazer_login(client, org.email)

    client.post(
        "/oportunidades/",
        json=dados_oportunidade(),
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
    org = criar_organizacao(session)
    token = fazer_login(client, org.email)

    create_response = client.post(
        "/oportunidades/",
        json=dados_oportunidade(),
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
    org = criar_organizacao(session)
    token = fazer_login(client, org.email)

    create_response = client.post(
        "/oportunidades/",
        json=dados_oportunidade(),
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
    org1 = criar_organizacao(session, email="ong1@example.com")
    org2 = criar_organizacao(session, email="ong2@example.com")
    token1 = fazer_login(client, org1.email)
    token2 = fazer_login(client, org2.email)

    create_response = client.post(
        "/oportunidades/",
        json=dados_oportunidade(),
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
    org = criar_organizacao(session)
    token = fazer_login(client, org.email)

    response = client.patch(
        "/oportunidades/999",
        json={"titulo": "Qualquer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_atualizar_oportunidade_sem_token(client: TestClient):
    response = client.patch("/oportunidades/1", json={"titulo": "Sem token"})
    assert response.status_code == 401


def test_atualizar_oportunidade_voluntario_nao_dono(
    client: TestClient, session: Session
):
    org = criar_organizacao(session)
    vol = criar_voluntario(session)
    token_org = fazer_login(client, org.email)
    token_vol = fazer_login(client, vol.email)

    create_response = client.post(
        "/oportunidades/",
        json=dados_oportunidade(),
        headers={"Authorization": f"Bearer {token_org}"},
    )
    opp_id = create_response.json()["id"]

    response = client.patch(
        f"/oportunidades/{opp_id}",
        json={"titulo": "Tentativa de Edição"},
        headers={"Authorization": f"Bearer {token_vol}"},
    )
    assert response.status_code == 403


def test_atualizar_oportunidade_vagas_invalida(
    client: TestClient, session: Session
):
    org = criar_organizacao(session)
    token = fazer_login(client, org.email)
    opp_id = criar_oportunidade(client, token)

    response = client.patch(
        f"/oportunidades/{opp_id}",
        json={"vagas_disponiveis": 0},  # mínimo é 1
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422

    # A vaga permanece com o valor original
    atual = session.get(Oportunidade, opp_id)
    assert atual.vagas_disponiveis == 10


# ============================================================
# Testes de Remoção (DELETE /oportunidades/{id})
# ============================================================

def test_remover_oportunidade_dono(client: TestClient, session: Session):
    org = criar_organizacao(session)
    token = fazer_login(client, org.email)

    create_response = client.post(
        "/oportunidades/",
        json=dados_oportunidade(),
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
    org1 = criar_organizacao(session, email="ong1@example.com")
    org2 = criar_organizacao(session, email="ong2@example.com")
    token1 = fazer_login(client, org1.email)
    token2 = fazer_login(client, org2.email)

    create_response = client.post(
        "/oportunidades/",
        json=dados_oportunidade(),
        headers={"Authorization": f"Bearer {token1}"},
    )
    opp_id = create_response.json()["id"]

    response = client.delete(
        f"/oportunidades/{opp_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert response.status_code == 403


def test_remover_oportunidade_inexistente(client: TestClient, session: Session):
    org = criar_organizacao(session)
    token = fazer_login(client, org.email)

    response = client.delete(
        "/oportunidades/999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_remover_oportunidade_sem_token(client: TestClient):
    response = client.delete("/oportunidades/1")
    assert response.status_code == 401


def test_remover_oportunidade_voluntario_nao_dono(
    client: TestClient, session: Session
):
    org = criar_organizacao(session)
    vol = criar_voluntario(session)
    token_org = fazer_login(client, org.email)
    token_vol = fazer_login(client, vol.email)

    create_response = client.post(
        "/oportunidades/",
        json=dados_oportunidade(),
        headers={"Authorization": f"Bearer {token_org}"},
    )
    opp_id = create_response.json()["id"]

    response = client.delete(
        f"/oportunidades/{opp_id}",
        headers={"Authorization": f"Bearer {token_vol}"},
    )
    assert response.status_code == 403

    # Recurso continua existindo
    get_response = client.get(f"/oportunidades/{opp_id}")
    assert get_response.status_code == 200
