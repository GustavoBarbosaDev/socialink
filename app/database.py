from sqlmodel import SQLModel, Session, create_engine
from app.config import get_settings

settings = get_settings()

# Configuração do engine do banco de dados
# Para SQLite, precisamos do check_same_thread=False para permitir
# múltiplas threads (necessário para o FastAPI)
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG  # Log de queries SQL em modo debug
)


def criar_tabelas():
    """Cria todas as tabelas no banco de dados."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependency injection para obter uma sessão do banco de dados."""
    with Session(engine) as session:
        yield session
