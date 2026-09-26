from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import Usuario


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


# ============================================================
# Testes de validação de entrada e expiração de token
# ============================================================

def test_registrar_papel_invalido(client: TestClient):
    """Testa que papel fora do enum (organizacao|voluntario) retorna 422."""
    response = client.post(
        "/auth/registrar",
        json={
            "nome": "Administrador",
            "email": "admin@example.com",
            "senha": "123456",
            "papel": "superadmin"
        }
    )
    assert response.status_code == 422


def test_login_campos_obrigatorios(client: TestClient):
    """Testa que o login valida o corpo da requisição (422)."""
    response = client.post(
        "/auth/login",
        json={"email": "joao@example.com"}  # faltando a senha
    )
    assert response.status_code == 422


def test_login_nao_expoe_senha(client: TestClient):
    """Testa que a senha em texto puro nunca aparece numa resposta."""
    client.post(
        "/auth/registrar",
        json={
            "nome": "João Silva",
            "email": "joao@example.com",
            "senha": "123456",
            "papel": "voluntario"
        }
    )

    response = client.post(
        "/auth/login",
        json={"email": "joao@example.com", "senha": "123456"}
    )
    assert response.status_code == 200
    assert "123456" not in response.text


def test_token_expirado_em_endpoint(client: TestClient):
    """Testa que um endpoint protegido recusa token expirado (401)."""
    from jose import jwt
    from app.config import get_settings

    settings = get_settings()

    client.post(
        "/auth/registrar",
        json={
            "nome": "João Silva",
            "email": "joao@example.com",
            "senha": "123456",
            "papel": "voluntario"
        }
    )

    # Token assinado corretamente, mas com expiração em 1970
    payload = {"sub": "joao@example.com", "papel": "voluntario", "exp": 0}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    response = client.get(
        "/voluntario/me/inscricoes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciais inválidas"
