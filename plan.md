# Socialink — plano do projeto

## 1. O problema real

Muitas ONGs pequenas e coletivos comunitários ainda organizam vagas de
voluntariado por planilha, WhatsApp ou formulário do Google. Isso gera:

- Falta de histórico de quem já se candidatou ou participou;
- Dificuldade de filtrar voluntários por vaga, local ou data;
- Nenhum controle de status (pendente, aprovado, recusado).

O **Socialink** resolve isso com uma API backend simples: ONGs publicam
oportunidades de voluntariado, voluntários se candidatam, e as ONGs
gerenciam essas candidaturas.

## 2. Escopo do MVP (enxuto, 1–2 semanas)

Duas entidades de usuário e duas entidades de domínio:

- **Usuário**: pode ser `organizacao` ou `voluntario` (mesmo modelo, com um campo de papel/role).
- **Oportunidade**: vaga de voluntariado criada por uma organização.
- **Inscrição**: candidatura de um voluntário a uma oportunidade.

Fora do escopo (deixar para "próximos passos"): upload de imagens,
notificações por e-mail, painel administrativo com frontend, geolocalização
real com mapas.

## 3. Stack tecnológica (e por que essa e não outra)

|       Camada       |                        Escolha                          |                                  Por quê                                   |
|--------------------|---------------------------------------------------------|----------------------------------------------------------------------------|
|   Framework web    |                      **FastAPI**                        | Sintaxe moderna, validação automática, gera documentação Swagger sozinho.  |
|   ORM / modelagem  |                      **SQLModel**                       | Une Pydantic + SQLAlchemy, menos boilerplate para quem está começando.     |
|   Banco de dados   | **SQLite** em dev (fácil trocar para PostgreSQL depois) | Zero configuração local, código já pronto para produção.                   |
|    Autenticação    |             **JWT** (`python-jose` + `passlib`)         | Autenticação stateless é o padrão de mercado em APIs REST.                 |
|       Testes       |            **pytest** + `TestClient` do FastAPI         | Testar endpoints é habilidade essencial de backend.                        |
|      Migrações     |           **Alembic** (opcional, evolução futura)       | Ensina a evoluir um banco em produção sem perder dados.                    |

## 4. Modelagem do banco de dados

```
Usuario
- id (PK)
- nome
- email (único)
- senha_hash
- papel (enum: "organizacao" | "voluntario")

Oportunidade
- id (PK)
- titulo
- descricao
- local
- data
- vagas_disponiveis
- organizacao_id (FK -> Usuario.id)

Inscricao
- id (PK)
- oportunidade_id (FK -> Oportunidade.id)
- voluntario_id (FK -> Usuario.id)
- status (enum: "pendente" | "aprovado" | "recusado")
- criado_em
```

Será implementado em `app/models.py`.

## 5. Endpoints da API

```
Autenticação
POST   /auth/registrar
POST   /auth/login

Oportunidades
GET    /oportunidades
POST   /oportunidades
GET    /oportunidades/{id}
PATCH  /oportunidades/{id}
DELETE /oportunidades/{id}

Inscrições
POST   /oportunidades/{id}/inscricoes
GET    /oportunidades/{id}/inscricoes
PATCH  /inscricoes/{id}
GET    /voluntario/me/inscricoes
```

Os arquivos dos routers serão criados em `app/routers/`.

## 6. Estrutura de pastas

```
socialink/
├── app/
│   ├── __init__.py
│   └── routers/
│       └── __init__.py
├── tests/
│   └── __init__.py
├── .env.example
├── .gitignore
├── plan.md
└── README.md
```

> Os módulos (`main.py`, `database.py`, `models.py`, etc.) serão criados
> conforme o roadmap.

## 7. Roadmap dia a dia

| Dia | Objetivo | Conceito principal |
|---|---|---|
| 1 | Estrutura do projeto configurada, models criados | Estrutura de projeto, SQLModel |
| 2 | Rodar `criar_tabelas()`, testar no Swagger (`/docs`) | ORM, sessão de banco |
| 3 | Implementar `POST /auth/registrar` | Hash de senha, nunca salvar em texto puro |
| 4 | Implementar `POST /auth/login` | JWT, autenticação stateless |
| 5 | Implementar `get_current_user` em `dependencies.py` | Dependency injection do FastAPI |
| 6 | Implementar CRUD de oportunidades (criar, listar, detalhar) | Validação com Pydantic |
| 7 | Restringir edição/remoção só para o dono | Autorização por dono do recurso |
| 8 | Implementar inscrição do voluntário + regra "não duplicar" | Regras de negócio |
| 9 | Implementar aprovação/recusa de inscrições pela organização | Máquina de estados simples |
| 10 | Preencher os testes em `tests/` (já com os nomes prontos) | Testes automatizados |
| 11 | Tratamento de erros padronizado (404, 403, 400) | Exception handlers |
| 12 | Revisar README, conferir `.env` | Boas práticas de entrega |
| 13–14 | Deploy gratuito (Render ou Railway) | Deploy de uma API real |

## 8. O que você vai aprender de verdade

- Modelar dados com relacionamentos (1-N) em um ORM;
- Autenticação JWT do zero, linha por linha;
- Autorização por papel e por dono do recurso;
- Validação de entrada e códigos HTTP corretos;
- Testes de API automatizados;
- Estruturar um projeto Python de forma legível para outro dev.

## 9. Ideias de evolução (depois do MVP)

- Paginação e busca por texto nas oportunidades;
- Envio de e-mail de confirmação;
- Métricas de horas voluntariadas por pessoa;
- Dockerizar a aplicação;
- Rate limiting nos endpoints públicos;
- Trocar SQLite por PostgreSQL com migrações via Alembic.