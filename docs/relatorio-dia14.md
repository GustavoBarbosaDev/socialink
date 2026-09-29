# Relatório Técnico — Dia 14: Primeiro deploy e smoke test na URL pública

**Data:** 28/09/2026
**Objetivo:** Deploy gratuito + smoke test de ponta a ponta (fim do roadmap)
**Conceito principal:** Deploy de uma API real — variáveis de ambiente
por ambiente, validação do guard em produção, persistência entre deploys

---

## 1. O que foi feito

### 1.1 Meta do dia cumprida

| Meta | Resultado |
|------|-----------|
| Primeiro deploy na URL pública | ✅ https://socialink-gilt.vercel.app |
| Banco PostgreSQL em produção | ✅ Neon criado via CLI, `DATABASE_URL` nos 3 ambientes |
| Variáveis de ambiente do provedor | ✅ `SECRET_KEY` (Production + Preview) e `DATABASE_URL` (Production, Preview, Development) |
| Smoke test: `/health`, registro, login | ✅ `200` / `201` / `200` com JWT assinado |
| Persistência entre deploys | ✅ usuário registrado sobreviveu a um deploy novo |
| Guard de `SECRET_KEY` validado ao vivo | ✅ log real capturado, mensagem exata do `app/config.py` |
| Testes | 108 → **110 testes** (+2), **100%** de cobertura |

### 1.2 Arquivos modificados/criados

| Arquivo | Ação |
|---------|------|
| `requirements.txt` | Modificado — `+email-validator>=2.0.0` (Dia 14) |
| `tests/test_deploy.py` | Modificado — +2 testes: `email-validator` declarado e `.vercelignore` bloqueando segredos |
| `.vercelignore` | **Criado** — `.env*`, venvs e `*.db` fora do upload da CLI |
| `.gitignore` | Modificado — `.vercel`, `.env*` e a exceção `!.env.example` |
| `README.md` | Modificado — status do Dia 14, URL pública, Neon via CLI, testes |
| `docs/relatorio-dia14.md` | **Criado** — este relatório |

Fora do commit (instalados pela integração Neon, não são do projeto):
`.agents/`, `.claude/`, `skills-lock.json`.

---

## 2. Detalhes técnicos

### 2.1 A cronologia: 5 deploys de produção e 2 previews

| # | Deploy | Tipo | Resultado | Causa |
|---|--------|------|-----------|-------|
| 1 | import do repo (Dia 12) | produção | ❌ 500 | guard: nenhuma env var existia |
| 2 | `c524bd8` (Dia 13) | produção | ❌ 500 | mesmo guard — env vars continuavam ausentes |
| 3 | `7302bd7` (fix do `email-validator`) | produção | ❌ 500 | guard ainda falhava **antes** de chegar no schemas |
| 4 | redeploy com env vars + Neon | produção | ✅ 200 | tudo configurado |
| 5 | redeploy (teste de persistência) | produção | ✅ 200 | dados sobreviveram |
| 6 | preview sem `SECRET_KEY` (sem `.vercelignore`) | preview | ⚠️ 200 | **achado**: o `.env` local subiu no bundle |
| 7 | preview sem `SECRET_KEY` (com `.vercelignore`) | preview | ❌ 500 + log | guard disparando como projetado |

### 2.2 Bloqueador 1: o guard ao vivo (log real)

Os deploys 1–3 morriam com `FUNCTION_INVOCATION_FAILED` — um 500 genérico
que esconde o motivo. A prova veio do deploy 7 (preview sem
`SECRET_KEY`), cujo log a CLI (`vercel logs`) capturou:

```
File "/var/task/app/database.py", line 4, in <module>
    settings = get_settings()
File "/var/task/app/config.py", line 52, in get_settings
    return Settings()
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
  Value error, SECRET_KEY ausente ou ainda é um placeholder do .env.example.
  Copie .env.example para .env e gere uma chave real: openssl rand -hex 32
Python process exited with exit status: 1
```

A trilha confirma o desenho do Dia 12: `app/main.py:7` importa
`app.database`, que chama `get_settings()` **no import** (linha 4) — ou
seja, a app nem chega a montar rotas sem uma chave válida. O campo
`input_value` do erro mostra `DATABASE_URL` já presente (Neon), só a
`SECRET_KEY` faltando: a hipótese foi confirmada linha a linha.

> Lição: o guard transformou um "deploy esquecido que funciona com
> segredo público" em "deploy que falha com instrução de correção". O
> log mostra que a mensagem acionável chegou exatamente ao operador.

### 2.3 Bloqueador 2: o `email-validator` era o próximo da fila

Os deploys 1–3 nunca chegaram a executar `app/schemas.py`: o guard morre
antes (a ordem dos imports em `main.py` garante isso). Ou seja, o bug do
`email-validator` estava **empilhado** atrás do primeiro — quem olha só
o 500 vê um problema, mas havia dois.

A prova do segundo veio por simulação local (bloquear o import de
`email_validator` com um finder em `sys.meta_path`, exatamente como o
build limpo do Vercel o teria):

```
FALHA: ImportError: email-validator is not installed, run `pip install 'pydantic[email]'`
```

A auditoria que encontrou o caso varreu os imports de `app/**/*.py` e
comparou com o `requirements.txt` — e **não achou nada faltando**, porque
o código nunca escreve `import email_validator`: quem importa é o
pydantic, dentro do `EmailStr` (`app/schemas.py:7`). É uma dependência
**implícita** (extra `email` do pydantic). O fiscal criado
(`test_email_str_tem_dependencia_declarada`) acopla as duas pontas:
se `EmailStr` existir no schemas, a linha precisa existir no requirements.

### 2.4 Achado do dia: o deploy da CLI subia o `.env`

O deploy 6 foi a surpresa do dia: um preview **sem** `SECRET_KEY` no
ambiente respondeu `200 {"status":"ok"}` — o guard deveria ter derrubado.
Investigação:

| Superfície de deploy | O que sobe | `.env` local |
|---|---|---|
| Git (push para a `main`) | só o commit | ❌ nunca |
| CLI (`npx vercel deploy`) | arquivos do diretório | ⚠️ **subia** |

O pydantic-settings lê `env_file=".env"` (`app/config.py:35`), e a CLI
não tem `.vercelignore` para consultar — sem instruções, mandava tudo.
A chave de dev local entrava no bundle e o guard passava com um segredo
que não era o de produção.

A correção é o `.vercelignore` (o análogo do `.gitignore` para uploads):

```
.env
.env.*
.venv
venv
*.db
...
```

Com ele no lugar, o deploy 7 falhou com o log da seção 2.2 — a prova de
que o arquivo era o culpado. O teste
`test_vercelignore_bloqueia_segredos_no_upload_da_cli` impede que alguém
apague as linhas sem quebrar a suíte. O `.gitignore` ganhou a mesma
proteção (`.env*`) **com a exceção `!.env.example`** — o exemplo é
documentação e precisa continuar versionável.

### 2.5 Neon pela CLI: `vercel integration add neon`

Em vez de clicar no painel, o banco foi provisionado pela própria CLI:

```bash
npx vercel integration add neon --name socialink-db
```

A integração criou o banco **e injetou as variáveis** (produzindo o que
a seção do README prometia):

```
+ DATABASE_URL          Production, Preview, Development
+ DATABASE_URL_UNPOOLED  ...
+ POSTGRES_URL, PGHOST, PGUSER, PGPASSWORD, ...   (18 variáveis)
```

O nome injetado por padrão é exatamente `DATABASE_URL` — o que
`app/config.py` lê. O `--prefix` existe só para quem quer outro nome
(`NEON2_DATABASE_URL`), e nós não queremos: o código não deve saber de
qual provedor veio a URL.

O `SECRET_KEY` foi criado pela CLI com valor vindo de
`/dev/urandom` direto para o Vercel, **sem passar pelo histórico do
shell nem pelo transcript** (`vercel env add ... < arquivo`, depois
`rm` do arquivo). Guardas de cada ambiente são independentes — produção
e preview assinam JWTs com chaves diferentes.

### 2.6 O smoke test e a prova de persistência

```bash
GET  /health          → 200 {"status":"ok"}
GET  /                → 200 {"app":"Socialink","version":"0.1.0","docs":"/docs"}
POST /auth/registrar  → 201 {"id":1,"nome":"Smoke Dia 14",...}
POST /auth/login      → 200 {"access_token":"eyJhbGciOiJIUzI1NiIs...","token_type":"bearer"}
```

O token veio assinado (HS256) com a `SECRET_KEY` do Vercel — prova de
que a env var chega ao runtime. Mas o critério que separa "banco
externo" de "disco efêmero" é outro: **persistência entre deploys**.

```
1. registrar usuário           → 201 (grava no Neon)
2. vercel redeploy             → novo deploy, novo cold start
3. login com o mesmo usuário   → 200 (o registro sobreviveu)
```

Se os dados estivessem no filesystem da função, o passo 3 retornaria
401. Voltou 200 — o PostgreSQL está de fato no caminho dos dados.

E nos logs do deploy, o lifespan contra o banco externo:

```
λ POST /auth/login
Iniciando Socialink v0.1.0
Tabelas criadas com sucesso!
```

`criar_tabelas()` (o `create_all` do Dia 2) rodou no Neon em cada cold
start — idempotente, como sempre foi desenhado.

### 2.7 A CLI como painel de operação

A sequência operacional do dia (tudo sem sair do terminal):

```bash
npx vercel login                          # autorização por device code no navegador
npx vercel link --yes --project socialink # vincula o diretório ao projeto
npx vercel integration add neon           # banco + variáveis
npx vercel env add SECRET_KEY ...         # segredo por ambiente
npx vercel redeploy <url>                 # novo build com as variáveis
npx vercel logs <url>                     # logs de runtime (onde o guard apareceu)
```

Duas armadilhas reais: `env add` para preview trava num prompt de "Git
branch" em terminal não-interativo (resolvido com `--value` + `--yes`),
e `env add` **não altera deploys já existentes** — variável nova exige
redeploy, senão o build antigo continua sem ela.

---

## 3. Conceitos-chave aplicados

### 3.1 Fail fast validado onde importa

O guard do Dia 12 foi escrito com testes unitários — mas só no Dia 14
ele **falhou em produção**, com a mensagem andando do código até o log
do provedor. Teste prova o código; o deploy prova o caminho inteiro.

### 3.2 Dois bloqueadores empilhados

```
request → import app.main → config/database → [1] guard de SECRET_KEY
                                               ↓ (se passar)
                                          [2] schemas → EmailStr → email-validator
```

Um 500 só revela o primeiro da fila. A lição: quando o erro de produção
é genérico, destrinchar a **ordem de import** diz onde olhar — e a
simulação local (bloquear módulo por módulo) reproduz o ambiente limpo
sem precisar de uma esteira de CI.

### 3.3 Segredo é questão de superfície

| Superfície | Mecanismo | Risco se esquecer |
|---|---|---|
| Git | `.gitignore` | commitar `.env` (histórico eterno) |
| CLI | `.vercelignore` | subir `.env` no bundle (aconteceu) |
| Painel/CLI de env vars | guard no `Settings` | deploy sem chave (aconteceu, e era o esperado) |

Três camadas, três arquivos de defesa — e um teste para cada.

### 3.4 Persistência como critério de aceite

`200 OK` no `/health` prova que a função sobe. Só o **ciclo
registro → deploy → login** prova que o banco é externo. Smoke tests de
API precisam de um critério que o disco efêmero não consegue fingir.

---

## 4. Problemas encontrados e soluções

| # | Problema | Solução |
|---|----------|---------|
| 1 | 500 em todas as rotas (`FUNCTION_INVOCATION_FAILED`) | env vars ausentes → guard do Dia 12; criadas via CLI e confirmadas por log |
| 2 | `email-validator` ausente do `requirements.txt` | linha declarada + teste acoplado ao `EmailStr` (nunca alcançado em produção porque o guard falhava antes — achado por auditoria + simulação) |
| 3 | Preview sem `SECRET_KEY` respondeu 200 | o `.env` local subia no upload da CLI → `.vercelignore` + teste |
| 4 | Disco em **100%** (`ENOSPC`, CLI não baixava) | limpeza de caches descartáveis (`~/.npm`, `uv`, `pypoetry`, `pip`) — 0 → 2,1G livres, sem tocar em dados |
| 5 | `env add` travado no prompt de Git branch em non-interactive | `--value "$(cat arquivo)"` + `--yes` |
| 6 | Logs "No logs found" em deploys antigos | logs de runtime têm retenção curta; capturar a prova logo após o evento |

---

## 5. Como testar

```bash
# Suíte completa
pytest                                    # 110 passed, 100%

# Contrato de deploy (12 testes)
pytest tests/test_deploy.py -q

# Smoke test da URL pública
curl https://socialink-gilt.vercel.app/health
curl -X POST https://socialink-gilt.vercel.app/auth/registrar \
  -H "Content-Type: application/json" \
  -d '{"nome":"Teste","email":"teste@exemplo.com","senha":"senha123"}'
curl -X POST https://socialink-gilt.vercel.app/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"teste@exemplo.com","senha":"senha123"}'

# Prova de persistência
npx vercel redeploy <deployment-url>       # novo deploy
curl -X POST .../auth/login -d '{...}'     # mesmo usuário → 200

# Onde o guard aparece se faltar SECRET_KEY
npx vercel logs <url>
```

---

## 6. Status

```
Name                           Stmts   Miss  Cover
------------------------------------------------------------
app/... (12 arquivos)             382      0   100%
------------------------------------------------------------
TOTAL                            382      0   100%

110 passed, 3 warnings in ~33s
```

| Teste novo (Dia 14, 2) | O que trava |
|---|---|
| `test_email_str_tem_dependencia_declarada` | `EmailStr` ⇒ `email-validator` no requirements |
| `test_vercelignore_bloqueia_segredos_no_upload_da_cli` | `.env*` e venvs fora do upload da CLI |

---

## 7. Ambiente em produção

| Item | Valor |
|---|---|
| URL | https://socialink-gilt.vercel.app |
| Banco | Neon (marketplace do Vercel), PostgreSQL com `sslmode=require` |
| `SECRET_KEY` | Secret por ambiente (Production e Preview independentes) |
| Deploys | push na `main` → deploy automático de produção |
| Logs | `npx vercel logs <url>` (ret curto — capturar em seguida) |

---

## 8. Próximos passos (pós-roadmap)

O `plan.md` (Dia 1 a 14) está concluído. Evoluções em
[plan.md §9](../plan.md#9-ideias-de-evolução-depois-do-mvp):
paginação e busca, e-mail de confirmação, Docker, rate limiting e
migrações versionadas com Alembic.

Operação: monitorar os logs após deploys, rotacionar a `SECRET_KEY` se
o repositório algum dia for público, e revisar o free tier do Neon
(quando o projeto crescer, migrar o plano).

---

**Status:** Dia 14 concluído — **roadmap completo**
**Próximo:** evoluções pós-MVP (plan.md §9)
