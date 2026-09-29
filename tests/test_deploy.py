"""Testes da configuração de deploy (Dia 13): Vercel + PostgreSQL.

Assim como tests/test_config.py fiscaliza o espelho `.env.example` ×
`config.py`, este arquivo fiscaliza o contrato entre o código e o
provedor de deploy: driver do banco no requirements, entrypoint que o
Vercel vai procurar e versão de Python pinada.
"""

import ast
import json
import sys
from pathlib import Path

import pytest

from app.database import DATABASE_URL, normalizar_url

RAIZ = Path(__file__).resolve().parent.parent


def test_requirements_traz_driver_do_postgres():
    """O requirements instala o driver do PostgreSQL, com versão pina.

    Sem a linha, o build de produção falha no primeiro create_engine com
    "No module named psycopg2". Sem o pino, um pip install limpo pode
    trazer uma versão que quebre no build (a lição do bcrypt==4.0.1).
    """
    linhas = [
        linha.strip()
        for linha in (RAIZ / "requirements.txt").read_text(encoding="utf-8").splitlines()
    ]
    driver = [linha for linha in linhas if linha.startswith("psycopg2-binary")]

    assert driver, "requirements.txt sem driver do PostgreSQL"
    assert "==" in driver[0], "driver do PostgreSQL precisa de versão pinada"


def test_vercel_json_e_valido():
    """vercel.json é JSON válido e aponta para o schema oficial."""
    configuracao = json.loads((RAIZ / "vercel.json").read_text(encoding="utf-8"))

    assert configuracao["$schema"] == "https://openapi.vercel.sh/vercel.json"


def test_vercel_json_aponta_para_o_entrypoint():
    """O functions key usa exatamente o arquivo que exporta a instância app.

    O Vercel localiza o FastAPI pelo caminho do arquivo (app/main.py) e
    pela variável de topo `app`. Se o arquivo mudar de lugar ou a
    instância for renomeada, o deploy para de detectar a app — e esse
    teste é quem avisa antes do push.
    """
    configuracao = json.loads((RAIZ / "vercel.json").read_text(encoding="utf-8"))

    assert "app/main.py" in configuracao["functions"]


def test_entrypoint_exporta_app_do_fastapi():
    """app/main.py define `app = FastAPI(...)` no topo do módulo.

    É a condição do Vercel para carregar o arquivo como função Python:
    uma variável de topo chamada `app` (ou `application`).
    """
    arvore = ast.parse((RAIZ / "app" / "main.py").read_text(encoding="utf-8"))

    atribuicoes_app = [
        no
        for no in arvore.body
        if isinstance(no, ast.Assign)
        and any(alvo.id == "app" for alvo in no.targets if isinstance(alvo, ast.Name))
    ]

    assert atribuicoes_app, "app/main.py não define a variável de topo `app`"
    assert any(
        isinstance(no.value, ast.Call)
        and isinstance(no.value.func, ast.Name)
        and no.value.func.id == "FastAPI"
        for no in atribuicoes_app
    ), "a variável `app` não é uma instância de FastAPI"


def test_vercel_json_exclui_arquivos_de_desenvolvimento():
    """Tests, docs e ambientes virtuais ficam fora do bundle da função.

    Python não tem tree-shaking no Vercel: tudo que é alcançável vai no
    pacote (limite de 500MB). Excluir o que é só de dev mantém o bundle
    enxuto — e evita instalar código que nunca roda em produção.
    """
    configuracao = json.loads((RAIZ / "vercel.json").read_text(encoding="utf-8"))
    padrao = configuracao["functions"]["app/main.py"]["excludeFiles"]

    assert "tests/**" in padrao
    assert "docs/**" in padrao
    assert "venv/**" in padrao


def test_python_version_igual_a_de_desenvolvimento():
    """.python-version acompanha a versão usada para desenvolver.

    O Vercel usa 3.12 por padrão; pinar evita que o build de produção
    suba numa versão diferente da que a suíte roda.
    """
    versao = (RAIZ / ".python-version").read_text(encoding="utf-8").strip()

    assert versao == f"{sys.version_info.major}.{sys.version_info.minor}"


@pytest.mark.parametrize(
    "url_entrada, esperado",
    [
        (
            "postgres://user:senha@host:5432/banco?sslmode=require",
            "postgresql://user:senha@host:5432/banco?sslmode=require",
        ),
        (
            "postgresql://user:senha@host:5432/banco",
            "postgresql://user:senha@host:5432/banco",
        ),
        ("sqlite:///./socialink.db", "sqlite:///./socialink.db"),
    ],
    ids=["alias_antigo_do_neon", "ja_correto", "sqlite_de_dev"],
)
def test_normalizar_url(url_entrada, esperado):
    """O alias `postgres://` (emitido por Neon/Vercel) vira `postgresql://`.

    O SQLAlchemy 2.0 rejeita o prefixo antigo; sem a normalização, o
    boot em produção falharia com a URL que o provedor entrega.
    """
    assert normalizar_url(url_entrada) == esperado


def test_database_url_do_engine_e_a_versao_normalizada():
    """O engine usa a URL já normalizada, não a crua das variáveis."""
    from app.config import get_settings

    assert DATABASE_URL == normalizar_url(get_settings().DATABASE_URL)
