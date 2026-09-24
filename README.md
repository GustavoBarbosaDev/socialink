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

**Dia 8 concluído** — inscrição do voluntário implementada, com a regra
"não duplicar" (409) e listagem das próprias inscrições. Antes disso já
estavam prontos CRUD de oportunidades, autorização por dono do recurso e
autenticação JWT. A implementação segue o
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

A suite de testes cobre autenticação (registro e login), CRUD de
oportunidades, autorização por dono e inscrição de voluntários — incluindo
validações de entrada, regra "não duplicar" e os caminhos de erro (401/403/404/409).

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
│       ├── auth.py         # endpoints de autenticação (registrar, login)
│       ├── oportunidades.py# CRUD de oportunidades (só dono edita/remove)
│       └── inscricoes.py   # inscrição do voluntário + listagem própria
├── tests/
│   ├── test_auth.py        # testes de autenticação
│   ├── test_dependencies.py# testes de get_current_user
│   ├── test_oportunidades.py # testes do CRUD e autorização
│   └── test_inscricoes.py  # testes de inscrição e regra "não duplicar"
└── docs/
    └── relatorio-dia8.md   # relatório técnico do Dia 8
```

## Principais endpoints

| Método | Rota | Descrição | Status |
|---|---|---|---|
| POST | `/auth/registrar` | Cria um usuário (organização ou voluntário) | Implementado |
| POST | `/auth/login` | Retorna um token JWT | Implementado |
| GET | `/oportunidades` | Lista oportunidades | Implementado |
| POST | `/oportunidades` | Cria oportunidade (só organização) | Implementado |
| PATCH | `/oportunidades/{id}` | Atualiza oportunidade (só o dono) | Implementado |
| DELETE | `/oportunidades/{id}` | Remove oportunidade (só o dono) | Implementado |
| POST | `/oportunidades/{id}/inscricoes` | Voluntário se candidata a uma vaga | Implementado |
| GET | `/voluntario/me/inscricoes` | Lista as inscrições do voluntário | Implementado |
| PATCH | `/inscricoes/{id}` | Organização aprova ou recusa uma inscrição | Planejado |

Lista completa em [plan.md](./plan.md#5-endpoints-da-api).

## Próximos passos

Acompanhe o progresso e as ideias de evolução no [plan.md](./plan.md#10-ideias-de-evolução-depois-do-mvp).

## Licença

Uso livre para fins de estudo e portfólio.