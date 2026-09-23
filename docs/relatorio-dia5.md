# Relatório Técnico — Dia 5: Dependency Injection com get_current_user

**Data:** 22/09/2026  
**Objetivo:** Implementar `get_current_user` em `dependencies.py`  
**Conceito principal:** Dependency injection do FastAPI

---

## 1. O que foi feito

### 1.1 Arquivo criado

| Arquivo | Descrição |
|---------|-----------|
| `app/dependencies.py` | Dependências compartilhadas para autenticação |

### 1.2 Função implementada

| Função | Descrição |
|--------|-----------|
| `get_current_user` | Decodifica token JWT e retorna usuário autenticado |

### 1.3 Testes criados

| Arquivo | Quantidade |
|---------|------------|
| `tests/test_dependencies.py` | 5 novos testes |

### 1.4 Status dos testes

| Teste | Resultado |
|-------|-----------|
| `test_get_current_user_sucesso` | Passou |
| `test_get_current_user_token_ausente` | Passou |
| `test_get_current_user_token_invalido` | Passou |
| `test_get_current_user_email_nao_encontrado` | Passou |
| `test_get_current_user_token_expirado` | Passou |

---

## 2. Detalhes técnicos

### 2.1 Estrutura do `dependencies.py`

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session, select

from app.config import get_settings
from app.database import get_session
from app.models import Usuario

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> Usuario:
    """Decodifica o token JWT e retorna o usuário autenticado."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    stmt = select(Usuario).where(Usuario.email == email)
    usuario = session.exec(stmt).first()

    if usuario is None:
        raise credentials_exception

    return usuario
```

### 2.2 Fluxo de execução

```
Requisição com header Authorization: Bearer <token>
    ↓
OAuth2PasswordBearer extrai o token
    ↓
jwt.decode() decodifica o payload
    ↓
Extrai email do campo "sub"
    ↓
Busca usuário no banco pelo email
    ↓
Retorna objeto Usuario (ou 401 se falhar)
```

### 2.3 Como usar em endpoints

```python
from fastapi import Depends
from app.dependencies import get_current_user
from app.models import Usuario

@router.get("/me")
def read_me(usuario: Usuario = Depends(get_current_user)):
    return {"email": usuario.email, "papel": usuario.papel}
```

### 2.4 Testes implementados

#### Teste de sucesso
```python
def test_get_current_user_sucesso(client, session):
    usuario = _criar_usuario(session)
    token = _criar_token(usuario.email)

    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == usuario.email
```

#### Teste de token ausente
```python
def test_get_current_user_token_ausente(client):
    response = client.get("/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"
```

#### Teste de token inválido
```python
def test_get_current_user_token_invalido(client):
    response = client.get("/me", headers={"Authorization": "Bearer token_invalido"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciais inválidas"
```

#### Teste de email não encontrado
```python
def test_get_current_user_email_nao_encontrado(client, session):
    token = _criar_token("naoexiste@example.com")
    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
```

#### Teste de token expirado
```python
def test_get_current_user_token_expirado(client, session):
    usuario = _criar_usuario(session)
    payload = {"sub": usuario.email, "papel": "voluntario", "exp": 0}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
```

---

## 3. Conceitos-chave aplicados

### 3.1 Dependency Injection

**O que é:** Padrão de design onde dependências são fornecidas externamente.

**No FastAPI:**
```python
def get_current_user(
    token: str = Depends(oauth2_scheme),  # ← Injetado automaticamente
    session: Session = Depends(get_session),  # ← Injetado automaticamente
) -> Usuario:
```

**Vantagens:**
- Código mais testável (fácil de fazer mock)
- Separação de responsabilidades
- Reutilização entre endpoints

### 3.2 OAuth2PasswordBearer

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
```

| Parâmetro | Função |
|-----------|--------|
| `tokenUrl` | URL documentada no Swagger para obter o token |

**Comportamento:**
- Extrai token do header `Authorization: Bearer <token>`
- Se ausente, retorna 401 automaticamente
- Integrado com Swagger UI (botão "Authorize")

### 3.3 Camadas de validação

```
1. OAuth2PasswordBearer → Token existe?
2. jwt.decode() → Token é válido?
3. payload.get("sub") → Email existe no payload?
4. session.exec() → Usuário existe no banco?
```

Cada camada retorna 401 se falhar.

---

## 4. Problemas encontrados e soluções

### 4.1 Token ausente

Requisição sem header Authorization. O `OAuth2PasswordBearer` retorna automaticamente:

```json
{"detail": "Not authenticated"}
```

### 4.2 JWT malformado

Token com assinatura inválida. Captura `JWTError` e retorna credenciais inválidas:

```python
except JWTError:
    raise credentials_exception
```

### 4.3 Usuário deletado após login

Token válido mas usuário não existe mais. Verificação no banco após decodificar:

```python
usuario = session.exec(stmt).first()
if usuario is None:
    raise credentials_exception
```

---

## 5. Como testar

```bash
# 1. Registrar e fazer login
curl -X POST http://localhost:8000/auth/registrar \
  -H "Content-Type: application/json" \
  -d '{"nome": "João", "email": "joao@example.com", "senha": "123456"}'

curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "joao@example.com", "senha": "123456"}'

# 2. Copiar o access_token da resposta

# 3. Usar em endpoint protegido
curl http://localhost:8000/me \
  -H "Authorization: Bearer <seu_token>"

# Resposta: {"email": "joao@example.com", "papel": "voluntario"}
```

---

## 6. Status dos testes

```
tests/test_auth.py - 11 testes
tests/test_dependencies.py - 5 testes

Total: 16/16 testes passando
```

---

## 7. Arquivos modificados/criados

| Arquivo | Ação |
|---------|------|
| `app/dependencies.py` | Criado |
| `tests/test_dependencies.py` | Criado |

---

## 8. Próximos passos (Dia 6)

- [ ] Implementar CRUD de oportunidades (criar, listar, detalhar)
- [ ] Criar schemas para Oportunidade
- [ ] Criar router `app/routers/oportunidades.py`
- [ ] Usar `get_current_user` para autenticar criação de oportunidades

---

**Status:** Dia 5 concluído  
**Próximo:** Dia 6 — Implementar CRUD de oportunidades
