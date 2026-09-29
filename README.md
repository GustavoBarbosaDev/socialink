# Socialink

**API REST de voluntariado** — conecta voluntários a oportunidades de trabalho comunitário publicadas por ONGs e coletivos.

![Status](https://img.shields.io/badge/status-API%20online-brightgreen?style=flat-square)
[![CI](https://github.com/GustavoBarbosaDev/socialink/actions/workflows/ci.yml/badge.svg)](https://github.com/GustavoBarbosaDev/socialink/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-framework-009688?style=flat-square&logo=fastapi&logoColor=white)
![Testes](https://img.shields.io/badge/testes-113%20%C2%B7%20100%25%20cobertura-2ea44f?style=flat-square)

**Demo:** https://socialink-gilt.vercel.app &nbsp;|&nbsp; **Swagger:** [/docs](https://socialink-gilt.vercel.app/docs) &nbsp;|&nbsp; **Plano:** [plan.md](./plan.md)

---

## Sobre o projeto

Muitas ONGs pequenas ainda organizam vagas de voluntariado por planilha,
WhatsApp ou formulário — sem histórico de quem se candidatou, sem filtro e
sem controle de status. O Socialink resolve isso com uma API backend:

- **Organizações** publicam oportunidades e decidem sobre as candidaturas;
- **Voluntários** se inscrevem nas vagas e acompanham o andamento;
- **Autenticação JWT** e autorização por papel e por dono do recurso
  garantem que cada um aja apenas onde pode.

O roadmap completo (problema, modelagem de dados e evolução) está no
[plan.md](./plan.md).

## Recursos

- **Autenticação** — registro e login com JWT (`python-jose`) e senhas com bcrypt
- **Autorização em dois níveis** — papel (`organizacao` / `voluntario`) e dono do recurso
- **CRUD de oportunidades** — criação, listagem, edição e remoção restritas ao dono
- **Fluxo de inscrição** — candidatura única (409 em duplicidade) e decisão aprovar/recusar com máquina de estados
- **Contrato de erro padronizado** — `{"detail": ...}` em todos os caminhos, inclusive erros do próprio framework
- **Configuração validada no boot** — a aplicação recusa `SECRET_KEY` ausente ou placeholder
- **Deploy no Vercel** — PostgreSQL (Neon), `pool_pre_ping` para serverless e smoke test de ponta a ponta
- **113 testes com 100% de cobertura de linhas** em `app/`, suíte hermética (banco em memória por teste)
- **CI no GitHub Actions** — a suíte roda a cada push e a cada pull request

## Stack

| Camada | Escolha | Por quê |
|---|---|---|
| Framework web | **FastAPI** | Validação automática, injeção de dependência e Swagger gerado |
| ORM | **SQLModel** | Une Pydantic e SQLAlchemy, menos boilerplate |
| Banco | **SQLite** (dev) / **PostgreSQL** (produção) | Zero config local e persistência real no Vercel |
| Auth | **JWT** + **bcrypt** | Padrão de mercado para API stateless |
| Testes | **pytest** + `TestClient` | Teste de contrato na camada de rota |
| Deploy | **Vercel Functions** | Deploy contínuo a partir da `main` |

## Estrutura

```
socialink/
├── .github/workflows/ci.yml # CI: pytest a cada push/PR
├── LICENSE                  # MIT
├── app/
│   ├── config.py            # Settings validados (guard de SECRET_KEY)
│   ├── database.py          # Engine, sessão e normalização da URL Postgres
│   ├── dependencies.py      # get_current_user e autorização por papel/dono
│   ├── errors.py            # Mensagens, exceções de domínio e handlers
│   ├── main.py              # Ponto de entrada FastAPI (lifespan)
│   ├── models.py            # Models SQLModel (Usuario, Oportunidade, Inscricao)
│   ├── schemas.py           # Schemas Pydantic de request/response
│   └── routers/
│       ├── auth.py          # /auth/registrar, /auth/login
│       ├── oportunidades.py # CRUD de oportunidades
│       └── inscricoes.py    # Candidatura, listagem e decisão
├── tests/                   # 113 testes (suíte hermética)
├── docs/                    # Relatórios técnicos dia a dia
├── plan.md                  # Problema, modelagem e roadmap
├── pytest.ini               # testpaths + cobertura
├── requirements.txt         # Dependências
└── vercel.json              # Entrypoint e exclusões do bundle
```

## Início rápido

```bash
# 1. Clonar e entrar no projeto
git clone https://github.com/GustavoBarbosaDev/socialink.git
cd socialink

# 2. Ambiente virtual e dependências
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Variáveis de ambiente (obrigatório: sem chave real a API não sobe)
cp .env.example .env
openssl rand -hex 32            # cole o resultado no SECRET_KEY do .env

# 4. Subir o servidor
uvicorn app.main:app --reload
```

A API sobe em `http://127.0.0.1:8000` e a documentação interativa em
`http://127.0.0.1:8000/docs`.

> **Windows:** os comandos acima assumem bash; no PowerShell use
> `venv\Scripts\Activate.ps1`.

## Variáveis de ambiente

Todas são lidas do `.env` (em produção, das variáveis do provedor) e têm
valor padrão em [`app/config.py`](./app/config.py). O `.env.example` traz as
sete — `tests/test_config.py` falha se uma nova aparecer no código sem ser
documentada.

| Variável | Padrão | Descrição |
|---|---|---|
| `APP_NAME` | `Socialink` | Nome exibido no `/` e no Swagger |
| `APP_VERSION` | `0.1.0` | Versão exibida no `/` e no Swagger |
| `DEBUG` | `false` | `true` ativa o log de queries SQL (dev) |
| `DATABASE_URL` | `sqlite:///./socialink.db` | Banco de dados; PostgreSQL em produção |
| `SECRET_KEY` | *(obrigatória)* | Assinatura do JWT — gere com `openssl rand -hex 32` |
| `JWT_ALGORITHM` | `HS256` | Algoritmo de assinatura do token |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Validade do token |

> O `.env` está no `.gitignore` e nunca deve ser committado.

## API

### Endpoints

| Método | Rota | Descrição | Acesso |
|---|---|---|---|
| POST | `/auth/registrar` | Cria usuário (organização ou voluntário) | público |
| POST | `/auth/login` | Retorna um token JWT | público |
| GET | `/oportunidades/` | Lista oportunidades | público |
| POST | `/oportunidades/` | Cria oportunidade | organização |
| GET | `/oportunidades/{id}` | Detalha oportunidade | público |
| PATCH | `/oportunidades/{id}` | Atualiza oportunidade | dono |
| DELETE | `/oportunidades/{id}` | Remove oportunidade | dono |
| POST | `/oportunidades/{id}/inscricoes` | Voluntário se candidata | voluntário |
| GET | `/oportunidades/{id}/inscricoes` | Lista inscrições da vaga | dono |
| GET | `/voluntario/me/inscricoes` | Lista inscrições do voluntário | voluntário |
| PATCH | `/inscricoes/{id}` | Aprova ou recusa inscrição | dono |

### Contrato de erros

Toda resposta de erro segue `{"detail": ...}`:

```jsonc
// 401 — token ausente ou inválido
{"detail": "Credenciais inválidas"}

// 409 — regra de negócio violada
{"detail": "Voluntário já inscrito nesta oportunidade"}

// 422 — validação de entrada (lista campo + mensagem)
{"detail": [{"campo": "body.email", "mensagem": "value is not a valid email address..."}]}
```

Os handlers estão centralizados em [`app/errors.py`](./app/errors.py) e
cubrem também os erros levantados pelo próprio framework (rota inexistente,
método não permitido, exceção não tratada → mensagem genérica no cliente,
detalhe no log).

### Exemplos rápidos

```bash
BASE=https://socialink-gilt.vercel.app

# Saúde
curl -s $BASE/health
# {"status":"ok"}

# Registrar organização
curl -s -X POST $BASE/auth/registrar \
  -H "Content-Type: application/json" \
  -d '{"nome":"Coletivo Raiz","email":"contato@raiz.org","senha":"senha123","papel":"organizacao"}'
# 201 {"id":1,"nome":"Coletivo Raiz","email":"contato@raiz.org","papel":"organizacao"}

# Login
curl -s -X POST $BASE/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"contato@raiz.org","senha":"senha123"}'
# 200 {"access_token":"...","token_type":"bearer"}
```

Com o token em mãos, basta enviar `Authorization: Bearer <access_token>` nas
demais rotas — no Swagger ([/docs](https://socialink-gilt.vercel.app/docs))
isso é automático pelo botão **Authorize**.

## Testes

```bash
pytest                                # roda tudo + cobertura
pytest tests/test_auth.py -q          # um arquivo
pytest -k inscricao -q                # pelo nome
pytest --cov-fail-under=95            # trava piso de cobertura
```

O `pytest.ini` aponta para `tests/`, adiciona o projeto ao `pythonpath` e
habilita o `pytest-cov` — todo `pytest` imprime a cobertura de `app/` ao
final. A mesma suíte roda no GitHub Actions a cada push e a cada pull
request (badge no topo).

A suíte cobre autenticação, CRUD, autorização por dono, inscrição e decisão,
contrato de erro (400/401/403/404/405/409/422/500), configuração
(`.env.example` × `config.py`, defaults e guard de `SECRET_KEY`), contrato
de deploy (`vercel.json`, entrypoint, driver do PostgreSQL,
`email-validator`, `.vercelignore`) e o corpo dos erros em si.

> Os testes rodam em banco SQLite em memória, isolados por caso — não
> dependem do `.env` nem da sua chave secreta.

## Deploy

A API roda como Vercel Function com detecção automática: o Vercel procura a
instância `app` em `app/main.py` e instala tudo que está no
`requirements.txt`.

1. **Banco:** o filesystem da função é efêmero, então o SQLite não serve
   para produção. Crie um PostgreSQL gratuito direto do projeto:

   ```bash
   npx vercel integration add neon   # cria o banco e injeta DATABASE_URL
   ```

2. **Variáveis de ambiente** (*Settings → Environment Variables*), **antes**
   do primeiro deploy:

   | Variável | Valor |
   |---|---|
   | `SECRET_KEY` | gere com `openssl rand -hex 32` |
   | `DATABASE_URL` | string de conexão do Neon (`postgres://` funciona: o código normaliza) |

3. **Deploy:** importe o repositório em [vercel.com/new](https://vercel.com/new) —
   pushes na `main` disparam novos deploys.

4. **Smoke test:** rode os `curl` da seção [Exemplos rápidos](#exemplos-rápidos)
   contra a URL pública e confirme que dados persistem entre deploys.

> **Sem `SECRET_KEY` a função falha ao iniciar** com a mensagem do guard de
> `app/config.py` — comportamento intencional, validado em produção.

> **Deploys via CLI** (`npx vercel deploy`) enviam os arquivos da máquina,
> não o commit: por isso existe o `.vercelignore`, que bloqueia `.env*`,
> ambientes virtuais e `*.db` no upload.

## Próximos passos

O roadmap do [plan.md](./plan.md) está concluído (MVP completo). As evoluções
previstas para depois do MVP estão em
[plan.md §9](./plan.md#9-ideias-de-evolução-depois-do-mvp): paginação e
busca, e-mail de confirmação, Docker, rate limiting e migrações versionadas
com Alembic.

## Licença

Distribuído sob a licença [MIT](./LICENSE) — livre para uso, estudo e
modificação, inclusive em fins comerciais.
