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

**Dia 12 concluído** — revisão de entrega. O `.env.example` agora espelha
todas as variáveis de `app/config.py` (e um teste trava esse espelho), o
`DEBUG` nasce `false` — seguro para produção, onde ninguém define essa
variável — enquanto o exemplo liga `true` para o desenvolvimento, e saiu
do `requirements.txt` o `python-dotenv`, que era redundante (quem lê o
`.env` é o `pydantic-settings`). O `SECRET_KEY` ganhou guard: valor vazio
ou placeholder **derruba a aplicação na subida** com a instrução de como
gerar a chave — um deploy esquecido não sobe mais assinando JWT com segredo
público. O relatório faltante da série foi recuperado em
[`docs/relatorio-dia3.md`](./docs/relatorio-dia3.md).
**98 testes cobrem 100% das linhas de `app/`.**

A API responde erros padronizados desde o Dia 11: `{"detail": ...}` (e
`{"detail": [{"campo", "mensagem"}]}` no 422), inclusive os levantados
pelo próprio framework, com as mensagens centralizadas em `app/errors.py`.
A implementação segue o [roadmap](./plan.md#7-roadmap-dia-a-dia).

## Como rodar localmente

```bash
# 1. Criar e ativar o ambiente virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Copiar as variáveis de ambiente e gerar a chave
#    (obrigatório: sem SECRET_KEY real a API não sobe)
cp .env.example .env
openssl rand -hex 32    # cole o resultado no SECRET_KEY do .env

# 4. Rodar o servidor
uvicorn app.main:app --reload
```

A API sobe em `http://127.0.0.1:8000`. A documentação interativa (Swagger)
fica em `http://127.0.0.1:8000/docs`.

## Variáveis de ambiente

Todas são lidas do `.env` (em produção, das variáveis do provedor) e têm
valor padrão em [`app/config.py`](./app/config.py). O `.env.example` traz
as sete — `tests/test_config.py` falha se uma nova aparecer no código sem
ser documentada.

| Variável | Padrão | O que faz |
|---|---|---|
| `APP_NAME` | `Socialink` | nome exibido no `/` e no Swagger |
| `APP_VERSION` | `0.1.0` | versão exibida no `/` e no Swagger |
| `DEBUG` | `false` | `true` liga o log de queries SQL do engine (dev) |
| `DATABASE_URL` | `sqlite:///./socialink.db` | banco de dados; PostgreSQL em produção |
| `SECRET_KEY` | *(obrigatória)* | assinatura do JWT — **gere com `openssl rand -hex 32`**; a app recusa placeholder |
| `JWT_ALGORITHM` | `HS256` | algoritmo de assinatura do token |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | validade do token |

> O `.env` está no `.gitignore` e nunca deve ser committado — o histórico
> do repositório é cheio o bastante para um segredo vazado.

## Rodando os testes

```bash
pytest
```

O `pytest.ini` na raiz já aponta para `tests/`, adiciona o projeto ao
`pythonpath` e habilita o `pytest-cov` — todo `pytest` imprime, ao final,
a cobertura de `app/`.

**98 testes, 100% de cobertura das linhas.** A suite cobre autenticação
(registro e login), CRUD de oportunidades, autorização por dono,
inscrição de voluntários, a decisão da organização, o contrato de erro
(400/401/403/404/405/409/422/500), a configuração de entrega
(`.env.example` × `app/config.py`, defaults seguros e o guard de
`SECRET_KEY`) — incluindo validações de entrada,
regra "não duplicar", máquina de estados de status, lifespan da
aplicação e o corpo dos erros em si.

```bash
pytest tests/test_auth.py -q      # roda um arquivo
pytest -k inscricao -q            # roda pelo nome do teste
pytest --cov-fail-under=95        # só se quiser travar o piso de cobertura
```

## Estrutura do projeto

```
socialink/
├── .gitignore
├── .env.example          # variáveis de ambiente (copie para .env)
├── README.md
├── plan.md               # problema, modelagem e roadmap completo
├── pytest.ini            # configuração do pytest (testpaths + cobertura)
├── requirements.txt      # dependências do projeto
├── app/
│   ├── __init__.py
│   ├── config.py         # configurações centralizadas
│   ├── database.py       # engine e sessão do banco
│   ├── dependencies.py   # get_current_user e autorização por papel/dono
│   ├── errors.py         # mensagens, exceções de domínio e exception handlers
│   ├── main.py           # ponto de entrada FastAPI (lifespan)
│   ├── models.py         # models SQLModel (Usuario, Oportunidade, Inscricao)
│   ├── schemas.py        # schemas Pydantic para request/response
│   └── routers/
│       ├── auth.py         # endpoints de autenticação (registrar, login)
│       ├── oportunidades.py# CRUD de oportunidades (só dono edita/remove)
│       └── inscricoes.py   # inscrição, listagem e decisão (aprovar/recusar)
├── tests/
│   ├── __init__.py
│   ├── conftest.py       # fixtures compartilhadas (session, client)
│   ├── helpers.py        # builders de cenário (usuários, vagas, login)
│   ├── test_app.py       # raiz, health e lifespan
│   ├── test_auth.py      # testes de autenticação
│   ├── test_config.py    # .env.example × config.py + guard de SECRET_KEY
│   ├── test_dependencies.py # testes de get_current_user e get_session
│   ├── test_erros.py     # contrato de erro (handlers, 422, 500)
│   ├── test_oportunidades.py # testes do CRUD e autorização
│   └── test_inscricoes.py  # testes de inscrição, listagem e decisão
└── docs/
    └── relatorio-dia1.md … relatorio-dia12.md  # 12 relatórios técnicos
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
| GET | `/oportunidades/{id}/inscricoes` | Lista as inscrições da vaga (só a dona) | Implementado |
| PATCH | `/inscricoes/{id}` | Organização aprova ou recusa uma inscrição | Implementado |

Lista completa em [plan.md](./plan.md#5-endpoints-da-api).

## Próximos passos

- **Dia 13–14 — deploy** (Render ou Railway): subir a API numa URL real,
  trocar o SQLite por PostgreSQL e configurar as variáveis de ambiente do
  provedor.
- Evoluções depois do MVP: [plan.md §9](./plan.md#9-ideias-de-evolução-depois-do-mvp).

## Licença

Uso livre para fins de estudo e portfólio.