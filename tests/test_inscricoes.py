from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import Inscricao
from tests.helpers import (
    criar_organizacao,
    criar_oportunidade,
    criar_voluntario,
    fazer_login,
    inscrever,
)


# ============================================================
# Testes de Inscrição (POST /oportunidades/{id}/inscricoes)
# ============================================================

def test_inscrever_voluntario_sucesso(client: TestClient, session: Session):
    org = criar_organizacao(session)
    vol = criar_voluntario(session)
    token_org = fazer_login(client, org.email)
    token_vol = fazer_login(client, vol.email)
    opp_id = criar_oportunidade(client, token_org)

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
    org = criar_organizacao(session)
    vol = criar_voluntario(session)
    token_org = fazer_login(client, org.email)
    token_vol = fazer_login(client, vol.email)
    opp_id = criar_oportunidade(client, token_org)

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
    org = criar_organizacao(session)
    token_org = fazer_login(client, org.email)
    opp_id = criar_oportunidade(client, token_org)

    response = client.post(f"/oportunidades/{opp_id}/inscricoes")
    assert response.status_code == 401


def test_inscrever_token_invalido(client: TestClient, session: Session):
    org = criar_organizacao(session)
    token_org = fazer_login(client, org.email)
    opp_id = criar_oportunidade(client, token_org)

    response = client.post(
        f"/oportunidades/{opp_id}/inscricoes",
        headers={"Authorization": "Bearer token_invalido"},
    )
    assert response.status_code == 401


def test_inscrever_organizacao_proibido(client: TestClient, session: Session):
    org = criar_organizacao(session)
    token_org = fazer_login(client, org.email)
    opp_id = criar_oportunidade(client, token_org)

    response = client.post(
        f"/oportunidades/{opp_id}/inscricoes",
        headers={"Authorization": f"Bearer {token_org}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Apenas voluntários podem executar esta ação"


def test_inscrever_oportunidade_inexistente(client: TestClient, session: Session):
    vol = criar_voluntario(session)
    token_vol = fazer_login(client, vol.email)

    response = client.post(
        "/oportunidades/999/inscricoes",
        headers={"Authorization": f"Bearer {token_vol}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Oportunidade não encontrada"


def test_inscrever_outro_voluntario_mesma_oportunidade(
    client: TestClient, session: Session
):
    org = criar_organizacao(session)
    vol1 = criar_voluntario(session, email="vol1@example.com")
    vol2 = criar_voluntario(session, email="vol2@example.com")
    token_org = fazer_login(client, org.email)
    token_vol1 = fazer_login(client, vol1.email)
    token_vol2 = fazer_login(client, vol2.email)
    opp_id = criar_oportunidade(client, token_org)

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
    vol = criar_voluntario(session)
    token = fazer_login(client, vol.email)

    response = client.get(
        "/voluntario/me/inscricoes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_listar_minhas_inscricoes_com_dados(client: TestClient, session: Session):
    org = criar_organizacao(session)
    vol = criar_voluntario(session)
    token_org = fazer_login(client, org.email)
    token_vol = fazer_login(client, vol.email)
    opp_id = criar_oportunidade(client, token_org)

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
    org = criar_organizacao(session)
    vol1 = criar_voluntario(session, email="vol1@example.com")
    vol2 = criar_voluntario(session, email="vol2@example.com")
    token_org = fazer_login(client, org.email)
    token_vol1 = fazer_login(client, vol1.email)
    token_vol2 = fazer_login(client, vol2.email)
    opp_id = criar_oportunidade(client, token_org)

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
    org = criar_organizacao(session)
    token = fazer_login(client, org.email)

    response = client.get(
        "/voluntario/me/inscricoes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Apenas voluntários podem executar esta ação"


# ============================================================
# Testes de Listagem da Oportunidade (GET /oportunidades/{id}/inscricoes)
# ============================================================

def test_listar_inscricoes_da_oportunidade_dono(
    client: TestClient, session: Session
):
    org = criar_organizacao(session)
    vol = criar_voluntario(session)
    token_org = fazer_login(client, org.email)
    token_vol = fazer_login(client, vol.email)
    opp_id = criar_oportunidade(client, token_org)
    inscrever(client, token_vol, opp_id)

    response = client.get(
        f"/oportunidades/{opp_id}/inscricoes",
        headers={"Authorization": f"Bearer {token_org}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "pendente"
    assert data[0]["voluntario_id"] == vol.id


def test_listar_inscricoes_da_oportunidade_vazia(
    client: TestClient, session: Session
):
    org = criar_organizacao(session)
    token_org = fazer_login(client, org.email)
    opp_id = criar_oportunidade(client, token_org)

    response = client.get(
        f"/oportunidades/{opp_id}/inscricoes",
        headers={"Authorization": f"Bearer {token_org}"},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_listar_inscricoes_da_oportunidade_nao_dono(
    client: TestClient, session: Session
):
    org1 = criar_organizacao(session, email="ong1@example.com")
    org2 = criar_organizacao(session, email="ong2@example.com")
    token_org1 = fazer_login(client, org1.email)
    token_org2 = fazer_login(client, org2.email)
    opp_id = criar_oportunidade(client, token_org1)

    response = client.get(
        f"/oportunidades/{opp_id}/inscricoes",
        headers={"Authorization": f"Bearer {token_org2}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Sem permissão para alterar esta oportunidade"
    )


def test_listar_inscricoes_da_oportunidade_voluntario_proibido(
    client: TestClient, session: Session
):
    org = criar_organizacao(session)
    vol = criar_voluntario(session)
    token_org = fazer_login(client, org.email)
    token_vol = fazer_login(client, vol.email)
    opp_id = criar_oportunidade(client, token_org)

    response = client.get(
        f"/oportunidades/{opp_id}/inscricoes",
        headers={"Authorization": f"Bearer {token_vol}"},
    )
    assert response.status_code == 403


def test_listar_inscricoes_oportunidade_inexistente(
    client: TestClient, session: Session
):
    org = criar_organizacao(session)
    token_org = fazer_login(client, org.email)

    response = client.get(
        "/oportunidades/999/inscricoes",
        headers={"Authorization": f"Bearer {token_org}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Oportunidade não encontrada"


def test_listar_inscricoes_sem_token(client: TestClient):
    response = client.get("/oportunidades/1/inscricoes")
    assert response.status_code == 401


# ============================================================
# Testes de Decisão (PATCH /inscricoes/{id}) — máquina de estados
# ============================================================

def _criar_inscricao(client: TestClient, session: Session) -> dict:
    """Monta o cenário completo: ONG + voluntário + oportunidade + inscrição."""
    org = criar_organizacao(session)
    vol = criar_voluntario(session)
    token_org = fazer_login(client, org.email)
    token_vol = fazer_login(client, vol.email)
    opp_id = criar_oportunidade(client, token_org)
    inscricao = inscrever(client, token_vol, opp_id)
    return {
        "org": org,
        "vol": vol,
        "token_org": token_org,
        "token_vol": token_vol,
        "opp_id": opp_id,
        "inscricao_id": inscricao["id"],
    }


def _decidir(client: TestClient, inscricao_id: int, token: str, novo_status: str):
    return client.patch(
        f"/inscricoes/{inscricao_id}",
        json={"status": novo_status},
        headers={"Authorization": f"Bearer {token}"},
    )


def test_aprovar_inscricao_sucesso(client: TestClient, session: Session):
    cenario = _criar_inscricao(client, session)

    response = _decidir(
        client, cenario["inscricao_id"], cenario["token_org"], "aprovado"
    )
    assert response.status_code == 200
    assert response.json()["status"] == "aprovado"

    # O voluntário enxerga a decisão na listagem própria
    minhas = client.get(
        "/voluntario/me/inscricoes",
        headers={"Authorization": f"Bearer {cenario['token_vol']}"},
    )
    assert minhas.json()[0]["status"] == "aprovado"


def test_recusar_inscricao_sucesso(client: TestClient, session: Session):
    cenario = _criar_inscricao(client, session)

    response = _decidir(
        client, cenario["inscricao_id"], cenario["token_org"], "recusado"
    )
    assert response.status_code == 200
    assert response.json()["status"] == "recusado"


def test_decidir_sem_token(client: TestClient, session: Session):
    cenario = _criar_inscricao(client, session)

    response = client.patch(
        f"/inscricoes/{cenario['inscricao_id']}",
        json={"status": "aprovado"},
    )
    assert response.status_code == 401


def test_decidir_token_invalido(client: TestClient, session: Session):
    cenario = _criar_inscricao(client, session)

    response = client.patch(
        f"/inscricoes/{cenario['inscricao_id']}",
        json={"status": "aprovado"},
        headers={"Authorization": "Bearer token_invalido"},
    )
    assert response.status_code == 401


def test_decidir_voluntario_proibido(client: TestClient, session: Session):
    cenario = _criar_inscricao(client, session)

    response = _decidir(
        client, cenario["inscricao_id"], cenario["token_vol"], "aprovado"
    )
    assert response.status_code == 403


def test_decidir_inscricao_inexistente(client: TestClient, session: Session):
    cenario = _criar_inscricao(client, session)

    response = _decidir(client, 999, cenario["token_org"], "aprovado")
    assert response.status_code == 404
    assert response.json()["detail"] == "Inscrição não encontrada"


def test_decidir_inscricao_de_outra_organizacao(
    client: TestClient, session: Session
):
    cenario = _criar_inscricao(client, session)
    outra_org = criar_organizacao(session, email="outra@example.com")
    token_outra = fazer_login(client, outra_org.email)

    response = _decidir(
        client, cenario["inscricao_id"], token_outra, "aprovado"
    )
    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Sem permissão para decidir sobre esta inscrição"
    )

    # A inscrição continua intacta no banco
    inscricao = session.get(Inscricao, cenario["inscricao_id"])
    assert inscricao.status.value == "pendente"


def test_decidir_inscricao_ja_decidida(client: TestClient, session: Session):
    cenario = _criar_inscricao(client, session)
    _decidir(client, cenario["inscricao_id"], cenario["token_org"], "aprovado")

    # Aprovar de novo: sem transição de volta nem repetição
    repetir = _decidir(
        client, cenario["inscricao_id"], cenario["token_org"], "aprovado"
    )
    assert repetir.status_code == 409
    assert repetir.json()["detail"] == "Inscrição já foi decidida"

    # Trocar para recusado também é bloqueado (sem voltar atrás)
    trocar = _decidir(
        client, cenario["inscricao_id"], cenario["token_org"], "recusado"
    )
    assert trocar.status_code == 409

    inscricao = session.get(Inscricao, cenario["inscricao_id"])
    assert inscricao.status.value == "aprovado"


def test_decidir_status_pendente_proibido(client: TestClient, session: Session):
    cenario = _criar_inscricao(client, session)

    response = _decidir(
        client, cenario["inscricao_id"], cenario["token_org"], "pendente"
    )
    assert response.status_code == 422

    inscricao = session.get(Inscricao, cenario["inscricao_id"])
    assert inscricao.status.value == "pendente"


def test_decidir_status_invalido(client: TestClient, session: Session):
    cenario = _criar_inscricao(client, session)

    response = _decidir(
        client, cenario["inscricao_id"], cenario["token_org"], "qualquer"
    )
    assert response.status_code == 422
