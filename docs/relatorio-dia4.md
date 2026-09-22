# Relatório Técnico — Dia 4: Autenticação JWT com Login

**Data:** 22/09/2026  
**Objetivo:** Implementar `POST /auth/login`  
**Conceito principal:** JWT, autenticação stateless

---

## 1. O que foi feito

### 1.1 Endpoint implementado

| Endpoint | Método | Descrição | Status |
|----------|--------|-----------|--------|
| `/auth/login` | POST | Autenticação e retorno de token JWT | ✅ |

### 1.2 Schema criado

| Schema | Uso |
|--------|-----|
| `LoginRequest` | Entrada de dados (email + senha) |
| `TokenResponse` | Saída com `access_token` e `token_type` |

### 1.3 Testes executados

| Teste | Resultado |
|-------|-----------|
| `test_login_sucesso` | ✅ Passou |
| `test_login_email_inexistente` | ✅ Passou |
| `test_login_senha_incorreta` | ✅ Passou |
| `test_login_token_valido` | ✅ Passou |

---

## 2. Detalhes técnicos

### 2.1 Fluxo de autenticação

```
Cliente → POST /auth/login {email, senha}
    ↓
Buscar usuário pelo email no banco
    ↓
Verificar senha com bcrypt.verify()
    ↓
Gerar token JWT com email + papel
    ↓
Retornar {access_token, token_type: "bearer"}
```

### 2.2 Implementação do endpoint

```python
@router.post("/login", response_model=TokenResponse)
def login(dados: LoginRequest, session: Session = Depends(get_session)):
    # Buscar usuário pelo email
    stmt = select(Usuario).where(Usuario.email == dados.email)
    usuario = session.exec(stmt).first()

    # Verificar credenciais
    if not usuario or not verify_password(dados.senha, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
        )

    # Criar token JWT
    access_token = create_access_token(
        data={"sub": usuario.email, "papel": usuario.papel}
    )
    return TokenResponse(access_token=access_token)
```

### 2.3 Geração do token JWT

```python
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt
```

**Payload do token:**
```json
{
  "sub": "usuario@email.com",
  "papel": "voluntario",
  "exp": 1727052000
}
```

### 2.4 Validação de senha com bcrypt

```python
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

**Resultado:** Senhas são comparadas de forma segura, sem expor o hash.

---

## 3. Conceitos-chave aplicados

### 3.1 JWT (JSON Web Token)

| Componente | Função |
|------------|--------|
| `sub` | Subject — identificador do usuário (email) |
| `papel` | Role — tipo de usuário (organizacao/voluntario) |
| `exp` | Expiration — timestamp de expiração |

**Vantagens do JWT:**
- Stateless: servidor não precisa armazenar sessão
- Escalável: qualquer instância pode validar o token
- Padrão de mercado para APIs REST

### 3.2 Autenticação stateless

```
Servidor A (login) → Gera token → Cliente armazena
Servidor B (requisição) → Valida token → Acessa recurso
```

**Não precisa de:**
- Sessões no banco de dados
- Cache de tokens
- Store centralizada

### 3.3 Bcrypt para senhas

| Característica | Benefício |
|----------------|-----------|
| Salt automático | Mesmas senhas geram hashes diferentes |
| Fator de custo | Iterações lentas contra brute force |
| Padrão da indústria | Amplamente testado e auditado |

---

## 4. Problemas encontrados e soluções

### 4.1 Token sem data de expiração

**Problema:** Token permanecia válido indefinidamente.

**Solução:** Adicionar `exp` ao payload:
```python
expire = datetime.now(timezone.utc) + timedelta(minutes=30)
to_encode.update({"exp": expire})
```

### 4.2 Resposta genérica de erro

**Problema:** Mensagem de erro vazia ou inexistente.

**Solução:** Detalhe descritivo no HTTPException:
```python
raise HTTPException(
    status_code=401,
    detail="Email ou senha incorretos",
    headers={"WWW-Authenticate": "Bearer"},
)
```

---

## 5. Como testar

```bash
# 1. Registrar um usuário
curl -X POST http://localhost:8000/auth/registrar \
  -H "Content-Type: application/json" \
  -d '{"nome": "João", "email": "joao@example.com", "senha": "123456"}'

# 2. Fazer login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "joao@example.com", "senha": "123456"}'

# Resposta: {"access_token": "eyJ...", "token_type": "bearer"}

# 3. Usar o token em requisições protegidas
curl http://localhost:8000/me \
  -H "Authorization: Bearer eyJ..."
```

---

## 6. Status dos testes

```
tests/test_auth.py - 11 testes
├── test_registrar_usuario_voluntario ✅
├── test_registrar_usuario_organizacao ✅
├── test_registrar_email_duplicado ✅
├── test_registrar_email_invalido ✅
├── test_registrar_campos_obrigatorios ✅
├── test_registrar_papel_padrao ✅
├── test_registrar_senha_hash ✅
├── test_login_sucesso ✅
├── test_login_email_inexistente ✅
├── test_login_senha_incorreta ✅
└── test_login_token_valido ✅
```

**Total: 11/11 testes passando** ✅

---

## 7. Próximos passos (Dia 5)

- [ ] Criar `app/dependencies.py` com `get_current_user`
- [ ] Implementar decodificação do token JWT
- [ ] Buscar usuário pelo email no payload
- [ ] Criar testes para a dependência

---

**Status:** ✅ Dia 4 concluído  
**Próximo:** Dia 5 — Implementar `get_current_user` em `dependencies.py`
