from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import (
    MENSAGEM_SECRET_KEY,
    PLACEHOLDERS_DE_SECRET_KEY,
    Settings,
)

ARQUIVO_ENV_EXAMPLE = Path(__file__).resolve().parent.parent / ".env.example"


def chaves_do_env_example():
    return {
        linha.split("=", 1)[0].strip(): linha.split("=", 1)[1].strip()
        for linha in ARQUIVO_ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
        if "=" in linha and not linha.lstrip().startswith("#")
    }


def test_debug_nasce_false_sem_env(monkeypatch):
    """Sem .env e sem variável de ambiente, DEBUG começa em False.

    Padrão seguro: produção (Render/Railway) não define DEBUG, então o
    engine não abre log de SQL por acidente. Quem quer echo liga DEBUG=true
    no .env — que é o que o .env.example faz.
    """
    monkeypatch.delenv("DEBUG", raising=False)
    assert Settings(_env_file=None).DEBUG is False


def test_env_example_documenta_todos_os_campos():
    """Toda variável de Settings aparece no .env.example (e só elas).

    Evita que uma configuração nova exista no código e ninguém saiba
    configurá-la em produção — ou que sobe uma chave morta no exemplo.
    """
    chaves = set(chaves_do_env_example())
    assert chaves == set(Settings.model_fields)


@pytest.mark.parametrize(
    "chave",
    [
        "",
        "   ",
        "sua_chave_secreta_aqui",
        "sua_chave_secreta_aqui_mude_em_producao",
    ],
    ids=["vazia", "so_espacos", "placeholder_do_exemplo", "default_antigo"],
)
def test_secret_key_invalida_impede_subir(chave, monkeypatch):
    """Chave vazia ou placeholder derruba a app na hora de criar Settings.

    Sem esse guard, um deploy sem SECRET_KEY sobe funcionando com uma chave
    conhecida por quem lê o repositório — e qualquer pessoa assina token
    válido de organização.
    """
    monkeypatch.setenv("SECRET_KEY", chave)

    with pytest.raises(ValidationError) as erro:
        Settings(_env_file=None)

    assert MENSAGEM_SECRET_KEY in str(erro.value)


def test_placeholder_do_env_example_e_rejeitado():
    """O SECRET_KEY do .env.example não pode ser uma chave utilizável.

    Quem copia o exemplo e esquece de gerar a chave recebe o erro do guard
    em vez de uma API rodando com segredo público. Se o valor do exemplo
    mudar, o conjunto de placeholders precisa mudar junto.
    """
    assert chaves_do_env_example()["SECRET_KEY"] in PLACEHOLDERS_DE_SECRET_KEY


def test_defaults_de_entrega(monkeypatch):
    """Os defaults batem com o que o .env.example promete ao deploy."""
    for campo in (
        "APP_NAME",
        "APP_VERSION",
        "DATABASE_URL",
        "JWT_ALGORITHM",
        "ACCESS_TOKEN_EXPIRE_MINUTES",
    ):
        monkeypatch.delenv(campo, raising=False)

    configuracao = Settings(_env_file=None)

    assert configuracao.APP_NAME == "Socialink"
    assert configuracao.APP_VERSION == "0.1.0"
    assert configuracao.DATABASE_URL == "sqlite:///./socialink.db"
    assert configuracao.JWT_ALGORITHM == "HS256"
    assert configuracao.ACCESS_TOKEN_EXPIRE_MINUTES == 30


def test_secret_key_real_e_aceita(monkeypatch):
    """Chave aleatória passa pelo validador e o resto continua com default."""
    monkeypatch.delenv("SECRET_KEY", raising=False)

    configuracao = Settings(_env_file=None, SECRET_KEY="a1b2" * 16)

    assert configuracao.SECRET_KEY == "a1b2" * 16
    assert configuracao.DEBUG is False
