# Relatório Técnico — Dia 13: Deploy no Vercel

**Data:** 28/09/2026
**Objetivo:** Deploy gratuito de uma API real (o roadmap sugere Render ou
Railway; a escolha foi o **Vercel**)
**Conceito principal:** Deploy de uma API real — entrypoint detection,
função serverless, banco externo e variáveis de ambiente do provedor

---

## 1. O que foi feito

### 1.1 Meta do dia cumprida

| Meta | Resultado |
|------|-----------|
| Escolher e preparar o provedor | ✅ Vercel (zero-config para FastAPI, Hobby gratuito) |
| Entrance/entrypoint da função | ✅ `vercel.json` aponta `app/main.py` — o arquivo que o Vercel procura |
| Driver do PostgreSQL | ✅ `psycopg2-binary==2.9.13` **pino**, com wheel `cp312`/`cp313` manylinux verificado |
| URL do banco em produção | ✅ `normalizar_url()` converte o alias antigo `postgres://` que o Neon/Vercel emitem |
| Conexões em serverless | ✅ `pool_pre_ping=True` descarta conexões stales do pool |
| Versão de Python do build | ✅ `.python-version` = `3.12`, paridade com o dev |
| Bundle da função enxuto | ✅ `excludeFiles` no `vercel.json` tira tests, docs e venvs do pacote |
| Testes do contrato de deploy | ✅ `tests/test_deploy.py` — 10 testes no estilo do Dia 12 |
| Testes | 98 → **108 testes** (+10), **100%** de cobertura |

### 1.2 Arquivos modificados/criados

| Arquivo | Ação |
|---------|------|
| `requirements.txt` | Modificado — `+psycopg2-binary==2.9.13` |
| `app/database.py` | Modificado — `normalizar_url()`, `DATABASE_URL` normalizada, `pool_pre_ping=True` |
| `vercel.json` | **Criado** — entrypoint, `maxDuration` e `excludeFiles` |
| `.python-version` | **Criado** — `3.12` |
| `tests/test_deploy.py` | **Criado** — 10 testes: driver, JSON, entrypoint, exclusões, versão, URL |
| `README.md` | Modificado — status do Dia 13, seção "Deploy no Vercel", árvore, próximos passos |
| `docs/relatorio-dia13.md` | **Criado** — este relatório |

---

## 2. Detalhes técnicos

### 2.1 Por que o Vercel (e como ele encontra a app)

O roadmap sugere Render ou Railway, mas os dois exigem um **start
command** (`uvicorn app.main:app --host 0.0.0.0 --port $PORT`). O Vercel
não: ele roda a app como **Vercel Function** e *detecta* o framework.

A regra da detecção (documentação oficial do runtime Python deles):

1. Acha dependência do FastAPI no `requirements.txt` → sabe que é FastAPI;
2. Procura um arquivo `app.py`, `index.py`, `main.py`, etc. — inclusive
   **dentro de `app/`** — que declare uma variável de topo `app`;
3. Serve **toda a app** como uma função só; o roteador do FastAPI
   resolve o caminho de cada request.

O projeto já nasceu no formato exato: `app/main.py:30` faz
`app = FastAPI(...)`. Nenhum arquivo de bootstrap foi necessário — só o
`vercel.json` registrando qual arquivo é o entrypoint (e quanto ele pode
durar). O `lifespan` com `criar_tabelas()` também é suportado: roda no
cold start da função.

> Diferença de mentalidade: no Render você gerencia um **processo longo**
> (porta, workers, restart). No Vercel você entrega um **handler** que a
> plataforma sobe, esfria e escale sozinha (Fluid compute).

### 2.2 O blocker real: SQLite não sobrevive a serverless

O Dia 12 deixou a porta aberta: *"trocar `DATABASE_URL` para PostgreSQL e
testar o caminho de produção"*. No Vercel isso não é opcional, por dois
motivos:

| Problema | Consequência com `sqlite:///./socialink.db` |
|---|---|
| Filesystem da função é somente leitura na raiz | o `create_all()` do lifespan falharia ao tentar criar o arquivo |
| mesmo que gravasse, o disco é efêmero | dados sumiriam no próximo deploy/cold start |

Ou seja: subir com o default atual produziria uma API que **aparenta
funcionar** (o `/health` responde) mas não persiste nada — exatamente o
cenário que o guard de `SECRET_KEY` do Dia 12 evitou, só que do lado do
banco. A solução é um PostgreSQL externo (recomendado: **Neon** pelo
Marketplace do Vercel, free tier) e `DATABASE_URL` nas variáveis de
ambiente do projeto.

### 2.3 `psycopg2-binary` pino — a mesma lição do `bcrypt`

O `requirements.txt` não tinha nenhum driver de PostgreSQL: um build de
produção quebraria com `ModuleNotFoundError: No module named 'psycopg2'`
no primeiro `create_engine`. A linha adicionada:

```txt
psycopg2-binary==2.9.13
```

O pino repete a aula do Dia 12 (seção 2.4 do relatório de ontem): sem
`==`, um `pip install` limpo instala a *última* versão — que pode trazer
breaking changes amanhã e quebrar o build de quem clona hoje. Antes de
fixar, a versão 2.9.13 foi verificada no PyPI: tem wheel **pré-compilado**
para `cp312` e `cp313` em `manylinux2014_x86_64` — que é exatamente o
ambiente de build do Vercel (Linux, Python 3.12 pinado no
`.python-version`). Sem wheel, o build precisaria compilar C na nuvem e
falharia sem as headers de desenvolvimento.

Por que `psycopg2` e não `psycopg` (v3)? Por zero-config: com o
`psycopg2`, o diafragma padrão do SQLAlchemy para `postgresql://` já é o
driver certo — nenhuma mudança de URL, nenhuma configuração extra.

### 2.4 `postgres://` → `postgresql://`: a URL que o provedor entrega

Este foi o problema mais sutil — e que só apareceria **em produção**, com
a string real do banco:

```
# Neon/Vercel emitem (formato legado do Heroku):
DATABASE_URL=postgres://user:senha@ep-xxx.aws.neon.tech/neondb?sslmode=require

# O que o SQLAlchemy 2.0 aceita:
postgresql://user:senha@ep-xxx.aws.neon.tech/neondb?sslmode=require
```

O prefixo `postgres://` era um alias aceito até o SQLAlchemy 1.4 e
**removido no 2.0** — o erro (`Could not parse SQLAlchemy URL`) só
acontece no boot, com a URL do provedor, ou seja, no primeiro request da
produção. A defesa ficou em `app/database.py`:

```python
def normalizar_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url

DATABASE_URL = normalizar_url(settings.DATABASE_URL)
```

Três decisões:

1. **Normalizar no código, não na documentação** — pedir para o usuário
   editar a string que o provedor copiou é pedir para alguém errar;
   `startswith` cobre só o prefixo, preservando host, senha e query
   (`?sslmode=require` chega intacto ao psycopg2);
2. **SQLite passa intacto** — o dev local não muda nada;
3. **`DATABASE_URL` como módulo-level** — o engine (e os testes) leem a
   versão normalizada, não a crua, impossibilitando esquecer a chamada.

### 2.5 `pool_pre_ping=True`: conexões que o banco derrubou

Em serverless, a função dorme entre requests (e o Neon também pode derrubar
conexões ociosas). Sem o pre-ping, o primeiro request depois do sono pega
uma conexão morta do pool e falha com `server closed the connection
unexpectedly` — um 500 intermitente e aleatório, o pior tipo de bug. Com
`pool_pre_ping=True`, o SQLAlchemy emite um `SELECT 1` antes de usar a
conexão; se estiver morta, descarta e abre outra. Custa um round-trip
mínimo e elimina uma classe inteira de erro intermitente.

### 2.6 `vercel.json`: entrypoint, duração e tamanho do bundle

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "functions": {
    "app/main.py": {
      "maxDuration": 60,
      "excludeFiles": "{tests/**,docs/**,venv/**,.venv/**,.pytest_cache/**,**/__pycache__/**,**/*.pyc,**/*.db}"
    }
  }
}

| Propriedade | Por quê |
|---|---|
| chave `app/main.py` | é o arquivo que exporta `app` — se mudar de lugar, a detecção falha |
| `maxDuration: 60` | teto de 60s por request; nossos endpoints respondem em ms, mas o valor documenta o contrato |
| `excludeFiles` | Python no Vercel **não tem tree-shaking**: tudo que é alcançável vai no bundle (limite de 500MB). Tests, docs, venvs e os `.db` locais ficam de fora |

O `$schema` dá autocomplete/validação no editor — mesmo papel do
`.env.example`, mas para JSON de configuração.

### 2.7 `.python-version`: o build roda a mesma versão do dev

```text
3.12
```

O Vercel aceita 3.12, 3.13 e 3.14 (default 3.12). O `.python-version`
torna explícito o que já era default — e um teste falha se a versão de
desenvolvimento mudar sem o arquivo acompanhar. É o espelho `.env.example`
× `config.py` do Dia 12 aplicado à versão de interpretador.

### 2.8 `tests/test_deploy.py`: o fiscal do contrato com o provedor

Nenhum teste local executa um deploy de verdade — então os testes
fiscalizam **o contrato** que torna o deploy possível:

| Teste | O que trava |
|---|---|
| `test_requirements_traz_driver_do_postgres` | linha `psycopg2-binary` presente **e** pinada com `==` |
| `test_vercel_json_e_valido` | JSON parseável + schema oficial |
| `test_vercel_json_aponta_para_o_entrypoint` | `functions` contém `app/main.py` |
| `test_entrypoint_exporta_app_do_fastapi` | AST: `app/main.py` tem `app = FastAPI(...)` no topo |
| `test_vercel_json_exclui_arquivos_de_desenvolvimento` | padrão exclui `tests/**`, `docs/**`, `venv/**` |
| `test_python_version_igual_a_de_desenvolvimento` | `.python-version` == versão do interpretador que roda a suíte |
| `test_normalizar_url[3 ids]` | alias antigo convertido; `postgresql://` e SQLite intactos |
| `test_database_url_do_engine_e_a_versao_normalizada` | o engine usa a URL já normalizada |

O teste de AST merece nota: em vez de só checar que o arquivo existe, ele
**parseia o Python** e confirma que a variável `app` é uma chamada a
`FastAPI`. Renomear a instância para `aplicacao` quebra o teste no local —
antes de um push que derrubaria o deploy silenciosamente.

---

## 3. Conceitos-chave aplicados

### 3.1 Serverless: entregar um handler, não um processo

| | Render/Railway (processo) | Vercel (função) |
|---|---|---|
| Start command | obrigatório (`uvicorn ... --port $PORT`) | não existe — detecção automática |
| Porta | você escolhe/expõe | irrelevante |
| Estado em disco | volume persistente (se configurado) | efêmero → **banco externo obrigatório** |
| Escala | você provisiona | plataforma (Fluid compute) |

A escolha do provedor redefine o que é "produção obrigatória": com
processo, o SQLite até funciona com volume; em função, ele não sobrevive.

### 3.2 Configuração é entregue por ambiente — de novo

O Dia 12 estabeleceu o trio `config.py` × `.env.example` × teste. O Dia 13
adiciona a quarta ponta: **o painel do provedor**. O código continua não
sabendo de onde veio o valor (`Settings` lê `.env` ou variável de
ambiente, tanto faz) — é isso que torna o mesmo binário válido para dev e
produção.

### 3.3 Defesa no código, não na boa memória de quem deploya

Duas armadilhas que **só aparecem em produção** foram neutralizadas no
código, não na documentação:

```
guard de SECRET_KEY (Dia 12)  → recusa segredo fraco   (falha alto)
normalizar_url (Dia 13)       → conserta URL do provedor (falha silenciosamente pior)
```

A segunda é mais perigosa que a primeira: um segredo fraco é um risco de
segurança visível; uma URL malformada é um deploy "ok" que explode no
primeiro request com um erro de framework. Nos dois casos, quem decide é o
código — o provedor só entrega o valor cru.

### 3.4 Pino de versão como parte da entrega (repetição deliberada)

O `bcrypt==4.0.1` do Dia 3 salvou o Dia 12; o `psycopg2-binary==2.9.13`
salva qualquer clone de hoje. A regra consolidada: **dependência crítica
de infraestrutura vai pinada**; o resto segue com `>=` para absorver correções.

---

## 4. Problemas encontrados e soluções

### 4.1 O `requirements.txt` não tinha driver de PostgreSQL

Detectado na análise de prontidão antes de começar. Sem a linha, o
primeiro `create_engine("postgresql://...")` falharia com
`ModuleNotFoundError` — no build, não no dev (o dev usa SQLite e nunca
repara). Solução: linha + teste (`test_requirements_traz_driver_do_postgres`).

### 4.2 O alias `postgres://` só quebraria em produção

Nenhum teste local pegaria: o `DATABASE_URL` de dev é SQLite. Foi
identificado na leitura da documentação do próprio provedor (a string do
Neon vem nesse formato). Solução: `normalizar_url()` + 3 testes
parametrizados — o caso do Neon virou fixture de teste.

### 4.3 SQLite como default parecia "inofensivo"

Para quem só lê o README, trocar de banco parece configuração de gosto.
A seção 2.2 mostra que no Vercel é a diferença entre "API que persiste"
e "API que apaga tudo a cada request" — e o pior é que **as duas parecem
funcionar** num smoke test ingênuo (o `200 OK` do `/health` vem igual).
Daí a regra do Dia 14: validar persistência **entre dois deploys**.

### 4.4 Suíte local não simula serverless (limitação assumida)

Os 108 testes rodam em SQLite em memória com `TestClient` — nenhum deles
abre uma conexão Postgres nem exercita cold start. Isso é aceitável porque
o que é testável localmente **está** testado (contrato do deploy), e o que
só existe em produção ganha checklist manual no Dia 14 (seção 5). Não
fingir que a suíte cobre o provedor é parte da entrega honesta.

---

## 5. Como testar

```bash
# Suíte inteira (com cobertura)
pytest

# Só o contrato de deploy (10 testes)
pytest tests/test_deploy.py -q

# Provar que o fiscal funciona: renomeie `app = FastAPI(...)` em app/main.py
# → test_entrypoint_exporta_app_do_fastapi falha

# ------------------------------------------------------------------
# Depois de publicar (passo a passo completo no README):
# ------------------------------------------------------------------
# 1. Neon pelo Marketplace do Vercel → copiar DATABASE_URL
# 2. Settings → Environment Variables: SECRET_KEY (openssl rand -hex 32) + DATABASE_URL
# 3. vercel.com/new → importar GustavoBarbosaDev/socialink → Deploy
# 4. Smoke test:
curl https://<projeto>.vercel.app/health
curl -X POST https://<projeto>.vercel.app/auth/registrar \
  -H "Content-Type: application/json" \
  -d '{"nome":"Smoke","email":"smoke@exemplo.com","senha":"senha123"}'
curl -X POST https://<projeto>.vercel.app/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"smoke@exemplo.com","senha":"senha123"}'
```

---

## 6. Status

```
Name                           Stmts   Miss  Cover
------------------------------------------------------------
app/... (12 arquivos)             382      0   100%
------------------------------------------------------------
TOTAL                            382      0   100%

108 passed, 3 warnings in ~33s
```

Os 3 warnings continuam sendo de terceiros (`starlette.testclient`,
`anyio`, `passlib`).

---

## 7. Arquivos modificados/criados

| Arquivo | Ação | Linhas |
|---------|------|--------|
| `requirements.txt` | Modificado | +4 |
| `app/database.py` | Modificado | 28 → 46 |
| `vercel.json` | Criado | 9 |
| `.python-version` | Criado | 1 |
| `tests/test_deploy.py` | Criado | 147 |
| `README.md` | Modificado | seção de deploy + status |
| `docs/relatorio-dia13.md` | Criado | — |

---

## 8. Próximos passos (Dia 14)

- [ ] Criar conta no Vercel + banco Neon (Marketplace)
- [ ] Definir `SECRET_KEY` e `DATABASE_URL` nas variáveis do projeto
- [ ] Importar o repo e subir — primeiro deploy
- [ ] Smoke test na URL pública: `/health`, registro e login de ponta a ponta
- [ ] **Persistência real:** verificar os dados criados antes de um novo deploy continuarem lá
- [ ] **Guard na prática:** tentar um deploy sem `SECRET_KEY` e confirmar que falha com a mensagem do guard
- [ ] Relatório do Dia 14 com a URL pública e os prints/logs do smoke test

---

**Status:** Dia 13 concluído (preparação do deploy)
**Próximo:** Dia 14 — primeiro deploy + smoke test na URL pública
