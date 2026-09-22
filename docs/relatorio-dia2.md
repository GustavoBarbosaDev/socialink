# Relatório Técnico — Dia 2: Execução e Teste da Aplicação

**Data:** 20/09/2026  
**Objetivo:** Rodar `criar_tabelas()`, testar no Swagger (`/docs`)  
**Conceito principal:** ORM, sessão de banco

---

## 1. O que foi feito

### 1.1 Verificação do ambiente

| Item | Status |
|------|--------|
| Virtual environment (`venv/`) | ✅ Configurado |
| Dependências instaladas | ✅ Todas presentes |
| Arquivo `.env` | ✅ Configurado com SECRET_KEY |
| Banco de dados `socialink.db` | ✅ Criado automaticamente |

### 1.2 Tabelas criadas no banco

| Tabela | Colunas |
|--------|---------|
| `usuarios` | id, nome, email, senha_hash, papel |
| `oportunidades` | id, titulo, descricao, local, data, vagas_disponiveis, organizacao_id |
| `inscricoes` | id, oportunidade_id, voluntario_id, status, criado_em |

### 1.3 Endpoints testados

| Endpoint | Método | Status | Resposta |
|----------|--------|--------|----------|
| `/` | GET | ✅ 200 | `{"app": "Socialink", "version": "0.1.0", "docs": "/docs"}` |
| `/health` | GET | ✅ 200 | `{"status": "ok"}` |
| `/docs` | GET | ✅ 200 | Swagger UI funcional |
| `/openapi.json` | GET | ✅ 200 | Schema OpenAPI gerado |

---

## 2. Detalhes técnicos

### 2.1 Execução do `criar_tabelas()`

A função `criar_tabelas()` foi chamada automaticamente na inicialização da aplicação via `lifespan`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    criar_tabelas()  # ← Cria tabelas na inicialização
    print("Tabelas criadas com sucesso!")
    yield
    print("Encerrando aplicação...")
```

**Resultado:** Todas as 3 tabelas foram criadas com sucesso no banco SQLite.

### 2.2 Sessão do banco de dados

A dependência `get_session()` foi testada e está funcionando corretamente:

```python
def get_session():
    """Dependency injection para obter uma sessão do banco de dados."""
    with Session(engine) as session:
        yield session
```

**Teste realizado:**
```python
with Session(engine) as session:
    result = session.exec(select(Usuario)).all()
    # Tabela usuarios: 0 registros (correto - banco vazio)
```

### 2.3 Swagger UI

O Swagger UI está acessível em `http://localhost:8000/docs` com:
- Título: "Socialink"
- Versão: "0.1.0"
- Descrição: "API para gerenciamento de voluntariado em ONGs"
- Endpoints documentados: `/` e `/health`

---

## 3. Conceitos-chave aplicados

### 3.1生命周期 (Lifespan)

O FastAPI moderno usa `lifespan` com `@asynccontextmanager` em vez do deprecated `@app.on_event`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code
    criar_tabelas()
    yield
    # Shutdown code
```

**Vantagens:**
- Código de inicialização e encerramento claro
- Melhor controle de recursos
- Padrão atual do FastAPI

### 3.2 Dependency Injection

O `get_session()` é um exemplo clássico de dependency injection:

```python
def get_session():
    with Session(engine) as session:
        yield session  # yield = dependency injection
```

**Como funciona:**
1. FastAPI detecta a função como dependência
2. Abre uma sessão antes de chamar o endpoint
3. Passa a sessão como parâmetro
4. Fecha a sessão após o endpoint retornar

### 3.3 SQLModel ORM

O SQLModel permite:
- Criar tabelas automaticamente a partir dos models
- Type hints completos para validação
- Integração nativa com FastAPI

---

## 4. Problemas encontrados e soluções

### 4.1 `check_same_thread=False`

**Problema:** SQLite por padrão não permite múltiplas threads.

**Solução:** Configuração no `database.py`:
```python
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
```

### 4.2 Logs de SQL

**Problema:** Queries SQL poluíam o console.

**Solução:** Configuração condicional via `DEBUG`:
```python
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG  # Log apenas em modo debug
)
```

---

## 5. Como testar

```bash
# 1. Ativar ambiente virtual
source venv/bin/activate

# 2. Rodar a aplicação
uvicorn app.main:app --reload

# 3. Acessar
# - API: http://localhost:8000
# - Docs: http://localhost:8000/docs
# - Health: http://localhost:8000/health

# 4. Testar endpoints
curl http://localhost:8000/
curl http://localhost:8000/health
```

---

## 6. Próximos passos (Dia 3)

- [ ] Implementar `POST /auth/registrar`
- [ ] Configurar hash de senhas com `passlib`
- [ ] Criar schema de entrada para registro
- [ ] Testar registro de usuário no Swagger

---

**Status:** ✅ Dia 2 concluído  
**Próximo:** Dia 3 — Implementar `POST /auth/registrar`
