import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.config import get_settings
from app.database import get_session
from app.dependencies import get_current_user
from app.models import Usuario
from app.routers.auth import get_password_hash

settings = get_settings()


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    app = FastAPI()

    @app.get("/me")
    def read_me(usuario: Usuario = Depends(get_current_user)):
        return {"id": usuario.id, "email": usuario.email, "papel": usuario.papel}

    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def _criar_usuario(session: Session, email: str = "teste@example.com") -> Usuario:
    usuario = Usuario(
        nome="Teste",
        email=email,
        senha_hash=get_password_hash("123456"),
        papel="voluntario",
    )
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


def _criar_token(email: str) -> str:
    payload = {"sub": email, "papel": "voluntario"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def test_get_current_user_sucesso(client: TestClient, session: Session):
    usuario = _criar_usuario(session)
    token = _criar_token(usuario.email)

    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == usuario.email
    assert data["papel"] == "voluntario"


def test_get_current_user_token_ausente(client: TestClient):
    response = client.get("/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_get_current_user_token_invalido(client: TestClient):
    response = client.get("/me", headers={"Authorization": "Bearer token_invalido"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciais inválidas"


def test_get_current_user_email_nao_encontrado(client: TestClient, session: Session):
    token = _criar_token("naoexiste@example.com")

    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciais inválidas"


def test_get_current_user_token_expirado(client: TestClient, session: Session):
    usuario = _criar_usuario(session)
    payload = {"sub": usuario.email, "papel": "voluntario", "exp": 0}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciais inválidas"
