from sqlmodel import SQLModel, Session, create_engine
from app.config import get_settings

settings = get_settings()


def normalizar_url(url: str) -> str:
    """Converte o alias antigo ``postgres://`` em ``postgresql://``.

    Provedores como Neon e Vercel ainda emitem ``postgres://`` na string de
    conexão, prefixo que o SQLAlchemy 2.0 não aceita mais — o engine falharia
    no boot com um erro de URL malformada. SQLite passa intacto.
    """
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


# Configuração do engine do banco de dados
# Para SQLite, precisamos do check_same_thread=False para permitir
# múltiplas threads (necessário para o FastAPI)
DATABASE_URL = normalizar_url(settings.DATABASE_URL)

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG,  # Log de queries SQL em modo debug
    # Serverless (Vercel): descarta do pool conexões que o banco já derrubou
    # de vez, evitando erro de "server closed the connection" em cold start
    pool_pre_ping=True,
)


def criar_tabelas():
    """Cria todas as tabelas no banco de dados."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependency injection para obter uma sessão do banco de dados."""
    with Session(engine) as session:
        yield session
