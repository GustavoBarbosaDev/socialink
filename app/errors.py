"""Central de erros da API — mensagens, exceções de domínio e handlers.

Três coisas vivem aqui:

1. **Mensagens**: todo texto de `detail` nasce numa constante. Routers,
   dependencies e testes importam a mesma constante, então mudar um texto
   muda em um lugar só.
2. **Exceções de domínio**: cada uma amarra o status HTTP correto (400, 401,
   403, 404, 409), impedindo que um `raise` espalhado escolha o código errado.
3. **Handlers**: registrados em `app.main`, garantem o formato do corpo
   (`{"detail": ...}`) em qualquer caminho de erro — inclusive nos erros
   levantados pelo próprio framework (rota inexistente, corpo inválido,
   exceção não tratada).
"""

import logging

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.utils import is_body_allowed_for_status_code

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mensagens
# ---------------------------------------------------------------------------

EMAIL_JA_CADASTRADO = "Email já cadastrado"
EMAIL_OU_SENHA_INCORRETOS = "Email ou senha incorretos"
CREDENCIAIS_INVALIDAS = "Credenciais inválidas"

APENAS_ORGANIZACOES = "Apenas organizações podem executar esta ação"
APENAS_VOLUNTARIOS = "Apenas voluntários podem executar esta ação"

OPORTUNIDADE_NAO_ENCONTRADA = "Oportunidade não encontrada"
SEM_PERMISSAO_OPORTUNIDADE = "Sem permissão para alterar esta oportunidade"

INSCRICAO_NAO_ENCONTRADA = "Inscrição não encontrada"
INSCRICAO_DUPLICADA = "Voluntário já inscrito nesta oportunidade"
INSCRICAO_JA_DECIDIDA = "Inscrição já foi decidida"
SEM_PERMISSAO_INSCRICAO = "Sem permissão para decidir sobre esta inscrição"

ERRO_INTERNO = "Erro interno do servidor"


# ---------------------------------------------------------------------------
# Exceções de domínio
# ---------------------------------------------------------------------------


class ErroAPI(HTTPException):
    """HTTPException cujo status é definido pela subclasse.

    Assim nenhum `raise` do código de negócio precisa lembrar o número do
    erro: quem chama `raise NaoEncontrado(...)` já está dizendo 404.
    """

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, detail: str, headers: dict[str, str] | None = None):
        super().__init__(status_code=self.status_code, detail=detail, headers=headers)


class RequisicaoInvalida(ErroAPI):
    """400 — a requisição é sintaticamente válida, mas viola uma regra."""

    status_code = status.HTTP_400_BAD_REQUEST


class NaoAutenticado(ErroAPI):
    """401 — token ausente, inválido ou expirado (sempre com desafio Bearer)."""

    status_code = status.HTTP_401_UNAUTHORIZED

    def __init__(self, detail: str, headers: dict[str, str] | None = None):
        desafio = {"WWW-Authenticate": "Bearer"}
        desafio.update(headers or {})
        super().__init__(detail, headers=desafio)


class Proibido(ErroAPI):
    """403 — autenticado, mas sem papel ou sem dono do recurso."""

    status_code = status.HTTP_403_FORBIDDEN


class NaoEncontrado(ErroAPI):
    """404 — recurso inexistente ou rota desconhecida."""

    status_code = status.HTTP_404_NOT_FOUND


class Conflito(ErroAPI):
    """409 — a requisição conflita com o estado atual do recurso."""

    status_code = status.HTTP_409_CONFLICT


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


def tratar_http_exception(request: Request, exc: HTTPException) -> Response:
    """Padroniza todo erro HTTP da API em `{"detail": <texto>}`.

    Cobre tanto as exceções do projeto quanto as levantadas pelo Starlette
    (rota inexistente, método não permitido), que viriam em texto puro.
    """
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    headers = dict(exc.headers or {})

    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        headers.setdefault("WWW-Authenticate", "Bearer")

    if not is_body_allowed_for_status_code(exc.status_code):
        return Response(status_code=exc.status_code, headers=headers)

    return JSONResponse(
        {"detail": detail}, status_code=exc.status_code, headers=headers
    )


def tratar_erro_validacao(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Normaliza os erros do Pydantic (422) para `campo` + `mensagem`.

    Além de previsível, o corpo deixa de ecoar o valor enviado pelo cliente
    (o handler padrão do FastAPI devolve o campo `input` inteiro).
    """
    erros = [
        {
            "campo": ".".join(str(parte) for parte in erro.get("loc", ())),
            "mensagem": str(erro.get("msg", "")),
        }
        for erro in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": erros})


def tratar_erro_interno(request: Request, exc: Exception) -> JSONResponse:
    """500 — devolve mensagem genérica e registra o erro real no log."""
    logger.error(
        "Erro não tratado em %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=exc,
    )
    return JSONResponse({"detail": ERRO_INTERNO}, status_code=500)
