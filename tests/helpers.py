"""Funções utilitárias para montar cenários de teste.

Não são fixtures: recebem `session`/`client` como argumento para que cada
teste monte só o que precisa (uma ONG, um voluntário, uma vaga...).
"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import Inscricao, Oportunidade, Usuario
from app.routers.auth import get_password_hash


def criar_organizacao(session: Session, email: str = "ong@example.com") -> Usuario:
    """Insere uma organização diretamente no banco (senha já com hash)."""
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


def criar_voluntario(
    session: Session, email: str = "voluntario@example.com"
) -> Usuario:
    """Insere um voluntário diretamente no banco (senha já com hash)."""
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


def fazer_login(client: TestClient, email: str, senha: str = "123456") -> str:
    """Retorna o access_token de um login via API."""
    response = client.post(
        "/auth/login",
        json={"email": email, "senha": senha},
    )
    return response.json()["access_token"]


def dados_oportunidade(**alteracoes) -> dict:
    """Payload válido para POST /oportunidades (aceita sobrescrever campos)."""
    dados = {
        "titulo": "Campanha de arrecadação",
        "descricao": "Ajudar na organização de doações para famílias carentes",
        "local": "Centro Comunitário, São Paulo",
        "data": datetime(2026, 10, 15, 9, 0, 0, tzinfo=timezone.utc).isoformat(),
        "vagas_disponiveis": 10,
    }
    dados.update(alteracoes)
    return dados


def criar_oportunidade(client: TestClient, token: str, **alteracoes) -> int:
    """Cria uma vaga pela API e devolve o id."""
    response = client.post(
        "/oportunidades/",
        json=dados_oportunidade(**alteracoes),
        headers={"Authorization": f"Bearer {token}"},
    )
    return response.json()["id"]


def inscrever(client: TestClient, token_vol: str, opp_id: int) -> dict:
    """Candidata o voluntário à vaga e devolve a inscrição criada."""
    response = client.post(
        f"/oportunidades/{opp_id}/inscricoes",
        headers={"Authorization": f"Bearer {token_vol}"},
    )
    return response.json()


def listar_oportunidades(session: Session) -> list[Oportunidade]:
    """Todas as vagas persistidas (para asserções diretas no banco)."""
    return session.exec(select(Oportunidade)).all()


def listar_inscricoes(session: Session) -> list[Inscricao]:
    """Todas as inscrições persistidas (para asserções diretas no banco)."""
    return session.exec(select(Inscricao)).all()
