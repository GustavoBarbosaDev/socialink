"""Testes dos endpoints básicos da aplicação (raiz, health e lifespan)."""

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_raiz_retorna_info_da_api(client: TestClient):
    """GET / devolve nome, versão e o caminho da documentação."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["app"] == get_settings().APP_NAME
    assert data["docs"] == "/docs"


def test_health(client: TestClient):
    """GET /health responde 200 com status ok (usado por load balancer)."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_lifespan_executa_startup_e_shutdown(capsys):
    """O lifespan cria as tabelas na subida e encerra a aplicação limpo."""
    with TestClient(app) as cliente:
        assert cliente.get("/health").status_code == 200

    saida = capsys.readouterr().out
    assert "Tabelas criadas com sucesso!" in saida
    assert "Encerrando aplicação..." in saida
