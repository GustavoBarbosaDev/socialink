import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from app.main import app
from app.database import get_session
from app.models import Usuario


@pytest.fixture(name="session")
def session_fixture():
    """Cria uma sessão de teste isolada para cada teste."""
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
    """Cria um cliente de teste com sessão de banco isolada."""
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_registrar_usuario_voluntario(client: TestClient):
    """Testa registro de usuário voluntário com sucesso."""
    response = client.post(
        "/auth/registrar",
        json={
            "nome": "João Silva",
            "email": "joao@example.com",
            "senha": "123456",
            "papel": "voluntario"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["nome"] == "João Silva"
    assert data["email"] == "joao@example.com"
    assert data["papel"] == "voluntario"
    assert "id" in data
    assert "senha" not in data
    assert "senha_hash" not in data


def test_registrar_usuario_organizacao(client: TestClient):
    """Testa registro de usuário organização com sucesso."""
    response = client.post(
        "/auth/registrar",
        json={
            "nome": "ONG Ajuda",
            "email": "ong@example.com",
            "senha": "789012",
            "papel": "organizacao"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["papel"] == "organizacao"


def test_registrar_email_duplicado(client: TestClient):
    """Testa que email duplicado retorna erro 400."""
    # Primeiro registro
    client.post(
        "/auth/registrar",
        json={
            "nome": "João Silva",
            "email": "joao@example.com",
            "senha": "123456",
            "papel": "voluntario"
        }
    )

    # Segundo registro com mesmo email
    response = client.post(
        "/auth/registrar",
        json={
            "nome": "Outro João",
            "email": "joao@example.com",
            "senha": "789012",
            "papel": "voluntario"
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email já cadastrado"


def test_registrar_email_invalido(client: TestClient):
    """Testa que email inválido retorna erro de validação."""
    response = client.post(
        "/auth/registrar",
        json={
            "nome": "João Silva",
            "email": "email-invalido",
            "senha": "123456",
            "papel": "voluntario"
        }
    )
    assert response.status_code == 422


def test_registrar_campos_obrigatorios(client: TestClient):
    """Testa que campos obrigatórios são validados."""
    response = client.post(
        "/auth/registrar",
        json={
            "nome": "João Silva"
            # Faltando email e senha
        }
    )
    assert response.status_code == 422


def test_registrar_papel_padrao(client: TestClient):
    """Testa que o papel padrão é voluntário."""
    response = client.post(
        "/auth/registrar",
        json={
            "nome": "Maria Santos",
            "email": "maria@example.com",
            "senha": "123456"
            # Papel não informado, deve ser voluntário
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["papel"] == "voluntario"


def test_registrar_senha_hash(client: TestClient, session: Session):
    """Testa que a senha é armazenada como hash."""
    client.post(
        "/auth/registrar",
        json={
            "nome": "João Silva",
            "email": "joao@example.com",
            "senha": "123456",
            "papel": "voluntario"
        }
    )

    # Verificar no banco
    usuario = session.exec(
        select(Usuario).where(Usuario.email == "joao@example.com")
    ).first()

    assert usuario is not None
    assert usuario.senha_hash != "123456"
    assert usuario.senha_hash.startswith("$2b$")


# ============================================================
# Testes de Login
# ============================================================

def test_login_sucesso(client: TestClient):
    """Testa login com sucesso retorna token JWT."""
    # Registrar usuário primeiro
    client.post(
        "/auth/registrar",
        json={
            "nome": "João Silva",
            "email": "joao@example.com",
            "senha": "123456",
            "papel": "voluntario"
        }
    )

    # Fazer login
    response = client.post(
        "/auth/login",
        json={
            "email": "joao@example.com",
            "senha": "123456"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_email_inexistente(client: TestClient):
    """Testa login com email inexistente retorna erro 401."""
    response = client.post(
        "/auth/login",
        json={
            "email": "naoexiste@example.com",
            "senha": "123456"
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Email ou senha incorretos"


def test_login_senha_incorreta(client: TestClient):
    """Testa login com senha incorreta retorna erro 401."""
    # Registrar usuário primeiro
    client.post(
        "/auth/registrar",
        json={
            "nome": "João Silva",
            "email": "joao@example.com",
            "senha": "123456",
            "papel": "voluntario"
        }
    )

    # Tentar login com senha errada
    response = client.post(
        "/auth/login",
        json={
            "email": "joao@example.com",
            "senha": "senhaerrada"
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Email ou senha incorretos"


def test_login_token_valido(client: TestClient):
    """Testa que o token retornado é um JWT válido."""
    from jose import jwt
    from app.config import get_settings

    settings = get_settings()

    # Registrar usuário primeiro
    client.post(
        "/auth/registrar",
        json={
            "nome": "João Silva",
            "email": "joao@example.com",
            "senha": "123456",
            "papel": "voluntario"
        }
    )

    # Fazer login
    response = client.post(
        "/auth/login",
        json={
            "email": "joao@example.com",
            "senha": "123456"
        }
    )
    token = response.json()["access_token"]

    # Decodificar e verificar payload
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert payload["sub"] == "joao@example.com"
    assert payload["papel"] == "voluntario"
    assert "exp" in payload
