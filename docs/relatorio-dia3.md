# Relatório Técnico — Dia 3: Registro de usuário com hash de senha

**Data:** 21/09/2026 (relatório escrito em 28/09/2026 — Dia 12)
**Objetivo:** Implementar `POST /auth/registrar`
**Conceito principal:** Hash de senha, nunca salvar em texto puro

> **Nota de recuperação:** este era o único relatório faltando da série
> (pendência registrada no Dia 10). Foi reconstruído no Dia 12 a partir do
> commit `8a95f5a` ("feat: implementa registro de usuário com hash bcrypt"),
> do diff daquele dia e dos testes originais.

---

## 1. O que foi feito

### 1.1 Meta do dia cumprida

| Meta | Resultado |
|------|-----------|
| `POST /auth/registrar` | ✅ 201 com `UsuarioResponse` |
| Hash de senha com `passlib`/bcrypt | ✅ `get_password_hash()` |
| Schema de entrada/saída | ✅ `UsuarioCreate` e `UsuarioResponse` |
| Testes | ✅ **7 testes** (todos passaram) |

### 1.2 Endpoint implementado

| Endpoint | Método | Descrição | Status |
|----------|--------|-----------|--------|
| `/auth/registrar` | POST | Cria usuário (organização ou voluntário) | OK |

### 1.3 Schemas criados

| Schema | Uso |
|--------|-----|
| `UsuarioCreate` | Entrada — `nome`, `email` (`EmailStr`), `senha`, `papel` (padrão `voluntario`) |
| `UsuarioResponse` | Saída — `id`, `nome`, `email`, `papel` (**sem senha**) |

### 1.4 Arquivos modificados/criados

| Arquivo | Ação |
|---------|------|
| `app/routers/auth.py` | **Criado** — router `/auth` com `registrar` (52 linhas) |
| `app/schemas.py` | **Criado** — `UsuarioCreate` e `UsuarioResponse` (21 linhas) |
| `app/main.py` | Modificado — `app.include_router(auth.router)` |
| `requirements.txt` | Modificado — `+bcrypt==4.0.1` |
| `tests/test_auth.py` | **Criado** — 7 testes (161 linhas) |
| `.gitignore` | Modificado — `+docs/` (decisão revertida no Dia 5) |

---

## 2. Detalhes técnicos

### 2.1 Fluxo do registro

```
Cliente → POST /auth/registrar {nome, email, senha, papel}
    ↓
Pydantic valida (EmailStr, papel no enum) → 422 se inválido
    ↓
SELECT ... WHERE email = ? → se existe, 400 "Email já cadastrado"
    ↓
bcrypt.hash(senha) → senha_hash
    ↓
INSERT + commit + refresh
    ↓
201 {id, nome, email, papel}   ← a senha nunca aparece
```

### 2.2 O endpoint (como ficou no Dia 3)

```python
@router.post("/registrar", response_model=UsuarioResponse,
             status_code=status.HTTP_201_CREATED)
def registrar(usuario: UsuarioCreate, session: Session = Depends(get_session)):
    stmt = select(Usuario).where(Usuario.email == usuario.email)
    if session.exec(stmt).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado",
        )

    novo_usuario = Usuario(
        nome=usuario.nome,
        email=usuario.email,
        senha_hash=get_password_hash(usuario.senha),
        papel=usuario.papel,
    )
    session.add(novo_usuario)
    session.commit()
    session.refresh(novo_usuario)
    return novo_usuario
```

Três decisões que se mantiveram até hoje:

1. **`status_code=201`** explícito — recurso criado, não "200 que deu certo";
2. **`response_model=UsuarioResponse`** — o Pydantic filtra o corpo, então
   `senha_hash` não tem como vazar mesmo se o model inteiro for retornado;
3. **`Depends(get_session)`** — o endpoint não conhece engine nem sessão,
   só a injeção (revisada no Dia 5).

### 2.3 Hash de senha com bcrypt

```python
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

`CryptContext` é uma fachada: escolhe o algoritmo declarado, gera o salt a
cada hash e embute os parâmetros no próprio hash —

```
$2b$12$KIXx...  →  algoritmo $2b$, custo 12, salt de 16 bytes, hash
```

`verify()` lê tudo do hash salvo, então **não existe campo "salt" no
banco**: ele nasce, some e é refeito a cada chamada.

### 2.4 A senha nunca volta na resposta

`UsuarioResponse` declara quatro campos — `id`, `nome`, `email`, `papel` —
e não tem `senha` nem `senha_hash`. Mesmo que alguém acrescente o campo ao
model, o `response_model` derruba o payload antes de serializar.

---

## 3. Conceitos-chave aplicados

### 3.1 Hash ≠ criptografia

| | Criptografia | Hash |
|---|---|---|
| Reversível | sim, com a chave | **nunca** |
| Serve para | transportar dado | provar que o dado bate |
| Comparação | decifra e compara | `verify()` recalcula e compara |

Senha no banco é hash porque o servidor **não precisa saber a senha** —
precisa apenas conferir uma candidatura.

### 3.2 Salt automático

Mesma senha, dois usuários, dois hashes diferentes. Isso mata a tabela de
rainbow: quebrar um hash não revela nada sobre os outros.

### 3.3 Custo do bcrypt

O custo (12 aqui) faz o hash levar ~100ms de propósito. Ataque de força
bruta escala com o custo — o legítimo paga uma vez por login.

### 3.4 Validação de entrada no ponto de entrada

`EmailStr` (formato) e `papel: PapelUsuario` (enum) validam **antes** de o
código de negócio rodar — 422 vem do Pydantic, sem tocar no banco.

---

## 4. Problemas encontrados e soluções

### 4.1 `passlib` 1.7.4 quebra com `bcrypt` novo

A dependência `passlib[bcrypt]` não trava a versão do `bcrypt`, e um
`pip install` novo puxa a mais recente. Na época, o `bcrypt 4.1.0` quebrou
o `passlib` (tão quebrado que o PyPI **anulou** a versão: *"Incompatibility
with assumptions made by passlib"*). Solução no commit do Dia 3:

```
# Hash de senhas
passlib[bcrypt]>=1.7.4
bcrypt==4.0.1          # ← travado, não é capricho
```

**Verificado no Dia 12:** o pino continua sendo obrigatório. Sem ele, hoje
um `pip install` instalaria `bcrypt 5.0.0` e o `CryptContext().hash()`
explodiria com `ValueError: password cannot be longer than 72 bytes`. E a
`4.2.0` (que funciona) loga `error reading bcrypt version` porque o
`passlib` procura `bcrypt.__about__`, removido a partir da 4.1.

> Lição de entrega: **`requirements.txt` não é lista de desejos** — versão
> pinada de dependência transitiva pode ser o que mantém o projeto de pé.

### 4.2 E-mail duplicado: 422 ou 400?

O campo é válido (`EmailStr` ok), mas o **valor** viola uma regra de
negócio (já existe). 422 é para corpo malformado; 400 marcou a regra.

```
422 → "esse e-mail não é um e-mail"
400 → "esse e-mail já foi usado"      ← escolhido
```

No Dia 11 isso virou `raise RequisicaoInvalida(EMAIL_JA_CADASTRADO)`, com
a mensagem centralizada em `app/errors.py` — mas o status continuou 400.

### 4.3 `docs/` foi para o `.gitignore` (e voltou)

No Dia 3 os relatórios entraram no `.gitignore`. No Dia 5 (commit
`2c9aee0`) a linha saiu: relatório técnico é material do repositório, não
lixo local — e foi assim que a lacuna do Dia 3 virou pendência visível.

---

## 5. Como testar

```bash
# 1. Subir a API
uvicorn app.main:app --reload

# 2. Registrar um voluntário
curl -X POST http://localhost:8000/auth/registrar \
  -H "Content-Type: application/json" \
  -d '{"nome": "Ana", "email": "ana@example.com", "senha": "123456"}'

# 201 → {"id": 1, "nome": "Ana", "email": "ana@example.com", "papel": "voluntario"}

# 3. Mesmo e-mail de novo → 400
#    {"detail": "Email já cadastrado"}

# 4. E-mail malformado → 422 (Pydantic)

# 5. Conferir que a senha virou hash no banco
sqlite3 socialink.db "SELECT email, senha_hash FROM usuarios;"
```

---

## 6. Status dos testes

No Dia 3, os 7 testes (com fixtures `session`/`client` locais — o
`conftest.py` compartilhado só chegou no Dia 10):

| Teste | Cenário | Esperado |
|-------|---------|----------|
| `test_registrar_usuario_voluntario` | registro completo | 201 |
| `test_registrar_usuario_organizacao` | `papel: organizacao` | 201 |
| `test_registrar_email_duplicado` | mesmo e-mail duas vezes | 400 |
| `test_registrar_email_invalido` | `"email-invalido"` | 422 |
| `test_registrar_campos_obrigatorios` | sem `senha` | 422 |
| `test_registrar_papel_padrao` | sem `papel` | `voluntario` |
| `test_registrar_senha_hash` | consulta o banco direto | hash ≠ senha, `verify()` ok |

**Total no Dia 3: 7/7 passando.** Hoje `tests/test_auth.py` tem **15
testes** (registro + login + papel inválido + senha não exposta), e o
arquivo `test_registrar_senha_hash` continua fazendo o que fez pela
primeira vez: abrir a sessão e conferir que no banco não há senha pura.

---

## 7. Como o código evoluiu depois

| Momento | Mudança no `registrar` |
|---------|------------------------|
| Dia 3 | `HTTPException(400, "Email já cadastrado")` escrito na mão |
| Dia 11 | `raise RequisicaoInvalida(EMAIL_JA_CADASTRADO)` — constante de `app/errors.py` |
| Dia 10 | Fixtures locais de teste → `tests/conftest.py` + `tests/helpers.py` |

A regra (bloquear e-mail repetido com 400) nunca mudou; mudou onde o texto
mora e quem tem o direito de escolher o status.

---

## 8. Próximos passos (Dia 4)

- [ ] Implementar `POST /auth/login`
- [ ] Gerar token JWT com `python-jose`
- [ ] Comparar senha com `verify_password()`
- [ ] Testar login e o token retornado

---

**Status:** Dia 3 concluído (relatório recuperado no Dia 12)
**Próximo:** Dia 4 — Autenticação JWT com login
