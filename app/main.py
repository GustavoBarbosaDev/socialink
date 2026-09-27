from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.database import criar_tabelas
from app.errors import (
    tratar_erro_interno,
    tratar_erro_validacao,
    tratar_http_exception,
)
from app.routers import auth, inscricoes, oportunidades


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Código executado na inicialização
    print(f"Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    criar_tabelas()
    print("Tabelas criadas com sucesso!")
    yield
    # Código executado no encerramento
    print("Encerrando aplicação...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API para gerenciamento de voluntariado em ONGs",
    lifespan=lifespan
)

# Incluir routers
app.include_router(auth.router)
app.include_router(oportunidades.router)
app.include_router(inscricoes.router)

# Exception handlers padronizados (substituem os defaults do FastAPI)
app.add_exception_handler(StarletteHTTPException, tratar_http_exception)
app.add_exception_handler(RequestValidationError, tratar_erro_validacao)
app.add_exception_handler(Exception, tratar_erro_interno)


@app.get("/")
def read_root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}
