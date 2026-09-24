from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.config import get_settings
from app.database import criar_tabelas
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
