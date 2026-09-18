# Relatório Técnico — Dia 1: Estrutura do Projeto e Models

**Data:** 18/09/2026  
**Objetivo:** Estrutura do projeto configurada, models criados  
**Conceito principal:** Estrutura de projeto, SQLModel

---

## 1. O que foi feito

### 1.1 Arquivos criados

| Arquivo | Descrição |
|---------|-----------|
| `requirements.txt` | Lista de dependências do projeto |
| `app/config.py` | Configurações centralizadas using pydantic-settings |
| `app/database.py` | Configuração do engine SQLModel e sessão do banco |
| `app/models.py` | Models de domínio (Usuario, Oportunidade, Inscricao) |
| `app/main.py` | Ponto de entrada da aplicação FastAPI |

### 1.2 Estrutura final do projeto

```
socialink/
├── app/
│   ├── __init__.py
│   ├── config.py          ← Configurações centralizadas
│   ├── database.py        ← Engine e sessão do banco
│   ├── main.py            ← Ponto de entrada FastAPI
│   ├── models.py          ← Models SQLModel
│   └── routers/
│       └── __init__.py
├── tests/
│   └── __init__.py
├── .env.example
├── .gitignore
├── plan.md
├── README.md
└── requirements.txt       ← Dependências
```

---

## 2. Por que cada escolha foi feita

### 2.1 `requirements.txt`

**Por quê:**  
- Documenta todas as dependências necessárias para rodar o projeto
- Permite recriar o ambiente facilmente com `pip install -r requirements.txt`
- Essencial para colaboradores e para deploy em produção

**Dependências incluídas:**
- `fastapi` + `uvicorn`: Framework web e servidor ASGI
- `sqlmodel`: ORM que une Pydantic + SQLAlchemy
- `python-jose`: Para assinatura de tokens JWT
- `passlib`: Para hash de senhas (bcrypt)
- `python-dotenv`: Para carregar variáveis de ambiente do `.env`
- `pytest` + `httpx`: Para testes automatizados

---

### 2.2 `app/config.py`

**Por quê:**  
- Centraliza todas as configurações em um único lugar
- Usa `pydantic-settings` para:
  - Carregar automaticamente do arquivo `.env`
  - Fornecer tipagem forte
  - Validação automática
- `@lru_cache()` garante que as configurações sejam carregadas apenas uma vez (performance)

**Decisões técnicas:**
```python
class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./socialink.db"  # SQLite como padrão
    SECRET_KEY: str = "..."  # Chave para JWT
    JWT_ALGORITHM: str = "HS256"  # Algoritmo padrão
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # Expiração de 30 min
```

---

### 2.3 `app/database.py`

**Por quê:**  
- Separa a configuração do banco da lógica de negócio
- Fornece `criar_tabelas()` para criar as tabelas na inicialização
- Fornece `get_session()` como dependency injection (padrão FastAPI)

**Decisões técnicas:**
- `check_same_thread=False` para SQLite: necessário porque FastAPI usa múltiplas threads
- `echo=settings.DEBUG`: Log de queries SQL apenas em modo debug (útil para desenvolvimento)
- Usa context manager (`with Session(...)`) para garantir fechamento correto da sessão

---

### 2.4 `app/models.py`

**Por quê:**  
- SQLModel permite definir models que servem como:
  - Schema do banco de dados (SQLAlchemy)
  - Schema de validação de entrada/saída (Pydantic)
- Menos boilerplate: uma única classe para tudo
- Type hints completos para IDE e validação

**Models implementados:**

#### `Usuario`
```python
class Usuario(SQLModel, table=True):
    id: Optional[int]  # PK auto-increment
    nome: str          # Nome completo
    email: str         # Único + indexado para buscas rápidas
    senha_hash: str    # Nunca salvar senha em texto puro!
    papel: PapelUsuario  # "organizacao" ou "voluntario"
```

**Decisões:**
- `email` com `unique=True` e `index=True`: impede duplicatas e acelera buscas
- `senha_hash`: armazena apenas o hash, nunca a senha original
- `papel` como Enum: força que apenas valores válidos sejam aceitos

#### `Oportunidade`
```python
class Oportunidade(SQLModel, table=True):
    id: Optional[int]
    titulo: str
    descricao: str
    local: str
    data: datetime
    vagas_disponiveis: int  # ge=1 (mínimo 1 vaga)
    organizacao_id: int     # FK para Usuario
```

**Decisões:**
- `vagas_disponiveis: int = Field(ge=1)`: garante pelo menos 1 vaga
- `organizacao_id`: chave estrangeira para saber quem criou a oportunidade
- `data` como `datetime`: permite ordenação e filtros por data

#### `Inscricao`
```python
class Inscricao(SQLModel, table=True):
    id: Optional[int]
    oportunidade_id: int   # FK para Oportunidade
    voluntario_id: int     # FK para Usuario
    status: StatusInscricao  # "pendente", "aprovado", "recusado"
    criado_em: datetime    # Timestamp da candidatura
```

**Decisões:**
- `status` como Enum: máquina de estados simples (pendente → aprovado/recusado)
- `criado_em`: `default_factory=datetime.now` para timestamp automático
- Chaves estrangeiras para `oportunidade_id` e `voluntario_id`

---

### 2.5 `app/main.py`

**Por quê:**  
- Ponto de entrada único da aplicação
- Usa `lifespan` (moderno, substitui `@app.on_event`)
- Endpoints básicos de saúde e informações

**Decisões técnicas:**
- `@asynccontextmanager` + `lifespan`: padrão atual do FastAPI (substitui deprecated `on_event`)
- `criar_tabelas()` na inicialização: cria tabelas automaticamente ao iniciar
- Endpoints `/` e `/health`: úteis para verificar se a API está rodando

---

## 3. Conceitos-chave aplicados

### 3.1 SQLModel vs SQLAlchemy puro

| Aspecto | SQLAlchemy puro | SQLModel |
|---------|-----------------|----------|
| Validação | Precisa de Pydantic separado | Integrado |
| Boilerplate | Mais código | Menos código |
| Type hints | Opcional | Obrigatório |
| Documentação | Manual | Automática (Swagger) |

**Escolha:** SQLModel porque reduz complexidade para um projeto novo.

### 3.2 Dependency Injection

O FastAPI usa dependency injection para:
- Conectar ao banco de dados
- Validar tokens JWT
- Injetar configurações

Exemplo no `database.py`:
```python
def get_session():
    with Session(engine) as session:
        yield session  # yield = dependency injection
```

### 3.3 Enums para consistência

Usar Enums em vez de strings soltas:
- **Garante** que apenas valores válidos sejam aceitos
- **Documenta** as opções disponíveis
- **Previne** erros de digitação

---

## 4. Próximos passos (Dia 2)

- [ ] Rodar `criar_tabelas()` e verificar se as tabelas são criadas
- [ ] Testar no Swagger (`/docs`)
- [ ] Implementar `POST /auth/registrar` (Dia 3)

---

## 5. Como testar

```bash
# 1. Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Rodar a aplicação
uvicorn app.main:app --reload

# 4. Acessar
# - API: http://localhost:8000
# - Docs: http://localhost:8000/docs
# - Health: http://localhost:8000/health
```

---

## 6. Dúvidas e decisões pendentes

1. **Migrações:** Usar Alembic agora ou deixar para depois?
   - **Decisão:** Deixar para quando precisar alterar a estrutura do banco

2. **Upload de imagens:** Não está no escopo do MVP
   - Pode ser adicionado depois com `python-multipart`

3. **Testes:** Criar estrutura básica no Dia 10
   - Por enquanto, foco na implementação dos endpoints

---

**Status:** ✅ Dia 1 concluído  
**Próximo:** Dia 2 — Rodar tabelas e testar no Swagger
