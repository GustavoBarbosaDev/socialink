# Socialink

API backend que conecta **voluntários** a **oportunidades de voluntariado**
publicadas por ONGs e coletivos comunitários.

> 📄 Veja o [plan.md](./plan.md) para o problema que o projeto resolve, a
> modelagem de dados completa e o roadmap dia a dia.

## Stack

- [FastAPI](https://fastapi.tiangolo.com/) — framework web
- [SQLModel](https://sqlmodel.tiangolo.com/) — ORM (SQLAlchemy + Pydantic)
- SQLite (dev) / PostgreSQL (produção, opcional)
- JWT (`python-jose`) + `passlib` (hash de senha)
- `pytest` para testes

## Status do projeto

📋 **Estrutura do projeto** — pastas, documentação e configurações iniciais
prontos. A implementação do código segue o [roadmap](./plan.md#7-roadmap-dia-a-dia).

## Como rodar localmente

> ⚠️ As dependências ainda não foram adicionadas ao `requirements.txt`.
> Os comandos abaixo funcionarão após a implementação do código.

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

> ⚠️ Os testes ainda não foram implementados.

```bash
pytest
```

## Estrutura do projeto

```
socialink/
├── .gitignore
├── .env.example          # variáveis de ambiente (copie para .env)
├── README.md
├── plan.md               # problema, modelagem e roadmap completo
├── app/
│   └── routers/
├── tests/
```

## Principais endpoints

> ⚠️ Endpoints planejados — serão implementados conforme o roadmap.

| Método | Rota | Descrição |
|---|---|---|
| POST | `/auth/registrar` | Cria um usuário (organização ou voluntário) |
| POST | `/auth/login` | Retorna um token JWT |
| GET | `/oportunidades` | Lista oportunidades (filtro por local) |
| POST | `/oportunidades` | Cria oportunidade (só organização) |
| POST | `/oportunidades/{id}/inscricoes` | Voluntário se candidata a uma vaga |
| PATCH | `/inscricoes/{id}` | Organização aprova ou recusa uma inscrição |

Lista completa em [plan.md](./plan.md#5-endpoints-da-api).

## Próximos passos

Acompanhe o progresso e as ideias de evolução no [plan.md](./plan.md#10-ideias-de-evolução-depois-do-mvp).

## Licença

Uso livre para fins de estudo e portfólio.