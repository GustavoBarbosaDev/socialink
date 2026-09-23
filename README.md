# Socialink

API backend que conecta **voluntários** a **oportunidades de voluntariado**
publicadas por ONGs e coletivos comunitários.

> Veja o [plan.md](./plan.md) para o problema que o projeto resolve, a
> modelagem de dados completa e o roadmap dia a dia.

## Stack

- [FastAPI](https://fastapi.tiangolo.com/) — framework web
- [SQLModel](https://sqlmodel.tiangolo.com/) — ORM (SQLAlchemy + Pydantic)
- SQLite (dev) / PostgreSQL (produção, opcional)
- JWT (`python-jose`) + `passlib` (hash de senha)
- `pytest` para testes

## Status do projeto

**Dia 4 concluído** — autenticação JWT implementada. Os endpoints de
registro e login de usuários já funcionam, com senhas hasheadas por bcrypt
e tokens JWT para autenticação stateless. A implementação dos endpoints segue o
[roadmap](./plan.md#7-roadmap-dia-a-dia).

## Como rodar localmente

```bash
# 1. Criar e ativar o ambiente virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Copiar as variáveis de ambiente
cp .env.example .env
# edite o .env e troque o SECRET_KEY por algo aleatório

# 4. Rodar o servidor
uvicorn app.main:app --reload
```

A API sobe em `http://127.0.0.1:8000`. A documentação interativa (Swagger)
fica em `http://127.0.0.1:8000/docs`.

## Rodando os testes

```bash
pytest
```

A suite de testes cobre os endpoints de autenticação (registro e login),
incluindo validações de entrada, hash de senhas e geração de tokens JWT.

## Estrutura do projeto

```
socialink/
├── .gitignore
├── .env.example          # variáveis de ambiente (copie para .env)
├── README.md
├── plan.md               # problema, modelagem e roadmap completo
├── requirements.txt      # dependências do projeto
├── app/
│   ├── __init__.py
│   ├── config.py         # configurações centralizadas
│   ├── database.py       # engine e sessão do banco
│   ├── main.py           # ponto de entrada FastAPI
│   ├── models.py         # models SQLModel (Usuario, Oportunidade, Inscricao)
│   ├── schemas.py        # schemas Pydantic para request/response
│   └── routers/
│       └── auth.py       # endpoints de autenticação (registrar, login)
├── tests/
│   └── test_auth.py      # testes dos endpoints de autenticação
└── docs/
    └── relatorio-dia1.md # relatório técnico do Dia 1
```

## Principais endpoints

| Método | Rota | Descrição | Status |
|---|---|---|---|
| POST | `/auth/registrar` | Cria um usuário (organização ou voluntário) | Implementado |
| POST | `/auth/login` | Retorna um token JWT | Implementado |
| GET | `/oportunidades` | Lista oportunidades (filtro por local) | Planejado |
| POST | `/oportunidades` | Cria oportunidade (só organização) | Planejado |
| POST | `/oportunidades/{id}/inscricoes` | Voluntário se candidata a uma vaga | Planejado |
| PATCH | `/inscricoes/{id}` | Organização aprova ou recusa uma inscrição | Planejado |

Lista completa em [plan.md](./plan.md#5-endpoints-da-api).

## Próximos passos

Acompanhe o progresso e as ideias de evolução no [plan.md](./plan.md#10-ideias-de-evolução-depois-do-mvp).

## Licença

Uso livre para fins de estudo e portfólio.