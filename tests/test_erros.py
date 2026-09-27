"""Testes do contrato de erro padronizado (Dia 11).

Cada exception handler de `app.errors` é exercitado pelo caminho real da
aplicação: rota inexistente, método errado, corpo inválido, falha interna.
"""

from contextlib import contextmanager

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.errors import (
    ERRO_INTERNO,
    Conflito,
    NaoAutenticado,
    NaoEncontrado,
    Proibido,
    RequisicaoInvalida,
)
from app.main import app


@contextmanager
def rota_temporaria(caminho: str, funcao):
    """Publica uma rota só durante o teste e a remove depois.

    É o jeito de fazer a aplicação real falhar de propósito (500, 400 com
    detalhe inválido) sem deixar código de teste no projeto.
    """
    app.add_api_route(caminho, funcao, methods=["GET"])
    rota_publicada = app.routes[-1]
    app.openapi_schema = None
    try:
        yield
    finally:
        app.routes.remove(rota_publicada)
        app.openapi_schema = None


@pytest.mark.parametrize(
    "excecao,status_esperado",
    [
        (RequisicaoInvalida, 400),
        (NaoAutenticado, 401),
        (Proibido, 403),
        (NaoEncontrado, 404),
        (Conflito, 409),
    ],
)
def test_excecoes_de_dominio_amarram_o_status(excecao, status_esperado):
    """Nenhum `raise` espalhado escolhe o código: a subclasse já carrega ele."""
    assert excecao("mensagem").status_code == status_esperado


def test_nao_autenticado_sempre_envia_desafio_bearer():
    """O 401 sai com `WWW-Authenticate: Bearer`, mesmo sem header explícito."""
    erro = NaoAutenticado("Credenciais inválidas")
    assert erro.headers == {"WWW-Authenticate": "Bearer"}


def test_rota_inexistente_retorna_json_404(client: TestClient):
    """Erro levantado pelo Starlette (não pelo projeto) também vira JSON."""
    response = client.get("/rota-que-nao-existe")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert isinstance(response.json()["detail"], str)


def test_metodo_nao_permitido_retorna_json_405(client: TestClient):
    """405 é outro erro do framework e segue o mesmo formato da API."""
    response = client.delete("/")

    assert response.status_code == 405
    assert response.headers["content-type"].startswith("application/json")
    assert isinstance(response.json()["detail"], str)


def test_401_sem_token_envia_www_authenticate(client: TestClient):
    """OAuth2PasswordBearer responde 401 com o desafio Bearer."""
    response = client.get("/voluntario/me/inscricoes")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_401_com_token_invalido_envia_www_authenticate(client: TestClient):
    """401 do domínio (credentials_exception) também desafia com Bearer."""
    response = client.get(
        "/voluntario/me/inscricoes",
        headers={"Authorization": "Bearer token_invalido"},
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_422_lista_campo_e_mensagem(client: TestClient):
    """Os erros do Pydantic saem como `campo` + `mensagem`, sem resto."""
    response = client.post("/auth/login", json={"email": "nao-e-email"})

    assert response.status_code == 422
    detalhes = response.json()["detail"]
    assert isinstance(detalhes, list)
    assert all(set(erro) == {"campo", "mensagem"} for erro in detalhes)


def test_422_nao_ecoa_o_valor_enviado(client: TestClient):
    """O corpo do 422 não devolve o input do cliente (senha não vaza)."""
    response = client.post(
        "/auth/registrar",
        json={
            "nome": "Teste",
            "email": "teste@example.com",
            "senha": 123456,
            "papel": "voluntario",
        },
    )

    assert response.status_code == 422
    assert "123456" not in response.text


def test_detail_de_http_exception_e_sempre_string(client: TestClient):
    """Detail que não é texto chega stringified (contrato `{"detail": str}`)."""
    def quebrar():
        raise HTTPException(status_code=400, detail=[{"campo": "nome"}])

    with rota_temporaria("/erro-com-detalhe-lista", quebrar):
        response = client.get("/erro-com-detalhe-lista")

    assert response.status_code == 400
    assert isinstance(response.json()["detail"], str)


def test_erro_interno_retorna_500_sem_vazar_stack():
    """Exceção não tratada vira mensagem genérica — o detalhe fica no log."""
    def explodir():
        raise ValueError("segredo interno do banco")

    cliente = TestClient(app, raise_server_exceptions=False)
    with rota_temporaria("/erro-interno", explodir):
        response = cliente.get("/erro-interno")

    assert response.status_code == 500
    assert response.json() == {"detail": ERRO_INTERNO}
    assert "segredo" not in response.text


def test_erro_sem_corpo_nao_envia_body():
    """Status que não admite corpo (204/304) sai sem JSON pendurado."""
    def sem_corpo():
        raise HTTPException(status_code=204)

    cliente = TestClient(app, raise_server_exceptions=False)
    with rota_temporaria("/erro-204", sem_corpo):
        response = cliente.get("/erro-204")

    assert response.status_code == 204
    assert response.content == b""
