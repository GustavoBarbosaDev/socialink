# Dia 14 — primeiro deploy e smoke test na URL pública

28/09/2026, fim do roadmap. Objetivo do dia: subir a API numa URL pública,
colocar o banco de produção no lugar e bater nos endpoints de ponta a
ponta. O que o dia ensinou de verdade foi sobre variável de ambiente por
ambiente, guard em produção e persistência entre deploys.

## Como ficou

A API está em <https://socialink-gilt.vercel.app>. Banco PostgreSQL no
Neon (marketplace do Vercel, `sslmode=require`), `DATABASE_URL` nos três
ambientes (Production, Preview, Development) e `SECRET_KEY` em Production
e Preview — chaves independentes, cada ambiente assina seu próprio JWT.
Smoke test no ar: `/health` 200, `/` 200, `POST /auth/registrar` 201,
`POST /auth/login` 200 com token HS256 assinado no Vercel. Suíte de 108
para 110 testes, 100% de cobertura.

A prova que interessa não é o 200 do `/health`, é a persistência:
registrei um usuário, mandei um redeploy, loguei com o mesmo usuário e
voltou 200. Se os dados estivessem no disco da função, o login depois do
deploy novo teria dado 401. Nos logs aparece o lifespan batendo no banco
externo a cada cold start:

```
λ POST /auth/login
Iniciando Socialink v0.1.0
Tabelas criadas com sucesso!
```

`criar_tabelas()` (o `create_all` do Dia 2) rodou no Neon, idempotente
como sempre foi desenhado.

Arquivos mexidos: `requirements.txt` ganhou `email-validator>=2.0.0`;
`tests/test_deploy.py` cresceu em 2 testes; `.vercelignore` foi criado;
`.gitignore` ganhou `.vercel`, `.env*` e a exceção `!.env.example`; README
e este relatório atualizados. O que a integração do Neon instalou
localmente (`.agents/`, `.claude/`, `skills-lock.json`) não é parte do
projeto — hoje está no `.gitignore`.

## Os 500 que não queriam ir embora

Foram 7 deploys: 3 de produção falhando, 2 passando, 2 de preview
servindo de laboratório. Os três primeiros morriam com
`FUNCTION_INVOCATION_FAILED`, um 500 genérico que esconde o motivo. A
prova do que acontecia veio no deploy de preview sem `SECRET_KEY`, cujo
log a CLI capturou:

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
`app.database`, que chama `get_settings()` **no import** (linha 4) — a
app nem chega a montar rotas sem uma chave válida. O `input_value` do
erro mostrava `DATABASE_URL` já presente (Neon), só a `SECRET_KEY`
faltando. O guard transformou um "deploy esquecido que funciona com
segredo público" em "deploy que falha com instrução de correção", e a
mensagem acionável chegou exatamente ao operador.

## O email-validator era o próximo da fila

Os primeiros deploys nunca executaram `app/schemas.py`: o guard morre
antes, porque a ordem dos imports em `main.py` garante isso. Ou seja, o
bug do `email-validator` estava empilhado atrás do primeiro — um 500 na
superfície, dois problemas embaixo. A prova do segundo veio por
simulação local, bloqueando o import com um finder em `sys.meta_path`,
exatamente como o build limpo do Vercel teria feito:

```
FALHA: ImportError: email-validator is not installed, run `pip install 'pydantic[email]'`
```

A auditoria que achou o caso varreu os imports de `app/**/*.py` contra o
`requirements.txt` e **não achou nada faltando**, porque o código nunca
escreve `import email_validator`: quem importa é o pydantic, dentro do
`EmailStr` (`app/schemas.py:7`). É dependência implícita (a extra
`email`). O teste `test_email_str_tem_dependencia_declarada` acopla as
duas pontas: se `EmailStr` existir no schemas, a linha precisa existir no
requirements.

## O achado do dia: o .env subia no bundle

Um preview **sem** `SECRET_KEY` respondeu `200 {"status":"ok"}` — o
guard deveria ter derrubado. Um push para a `main` nunca leva o `.env`,
porque o que sobe é o commit. A CLI (`npx vercel deploy`) manda os
arquivos do diretório, e não tem `.vercelignore` para consultar: sem
instruções, mandava tudo. O pydantic-settings lê `env_file=".env"`
(`app/config.py:35`), então a chave de dev local entrava no bundle e o
guard passava com um segredo que não era o de produção.

A correção é o `.vercelignore`, o análogo do `.gitignore` para uploads:

```
.env
.env.*
.venv
venv
*.db
```

Com ele no lugar, o deploy seguinte falhou com o log da seção anterior —
a prova de que o arquivo era o culpado. O teste
`test_vercelignore_bloqueia_segredos_no_upload_da_cli` impede que alguém
apague as linhas sem quebrar a suíte, e o `.gitignore` ganhou a mesma
proteção (`.env*`) **com a exceção `!.env.example`**, já que o exemplo é
documentação e precisa continuar versionável. Resumindo as superfícies:
git tem `.gitignore`, a CLI tem `.vercelignore`, o painel de env vars tem
o guard — três camadas, três defesas, um teste para cada.

## Neon pela CLI

Em vez de clicar no painel:

```bash
npx vercel integration add neon --name socialink-db
```

A integração criou o banco **e injetou as variáveis** — 18 no total,
incluindo `DATABASE_URL` em Production, Preview e Development, mais
`DATABASE_URL_UNPOOLED`, `POSTGRES_URL`, `PGHOST`, `PGUSER`, `PGPASSWORD`.
O nome injetado por padrão é exatamente `DATABASE_URL`, o que
`app/config.py` lê; o `--prefix` existe só para quem quer outro nome
(`NEON2_DATABASE_URL`), e nós não queremos: o código não deve saber de
qual provedor veio a URL.

A `SECRET_KEY` foi criada pela CLI com valor vindo de `/dev/urandom`
direto para o Vercel, **sem passar pelo histórico do shell nem pelo
transcript** (`vercel env add ... < arquivo`, depois `rm` do arquivo). As
guardas de cada ambiente são independentes — produção e preview assinam
JWTs com chaves diferentes.

## Operação pela CLI

Tudo feito sem sair do terminal: `npx vercel login` (device code no
navegador), `link --yes --project socialink`, `integration add neon`,
`env add SECRET_KEY ...`, `redeploy <url>` e `logs <url>` — foi nos logs
que o guard apareceu.

Duas armadilhas reais no caminho. O `env add` para preview trava num
prompt de "Git branch" em terminal não-interativo (resolvido com
`--value` + `--yes`), e `env add` **não altera deploys já existentes** —
variável nova exige redeploy, senão o build antigo continua sem ela. De
quebra, o disco da máquina chegou a 100% (`ENOSPC`, a CLI não baixava
mais): resolvi limpando caches descartáveis (`~/.npm`, `uv`, `pypoetry`,
`pip`), de 0 para 2,1G livres sem tocar em dados. E logs de deploys
antigos respondem "No logs found" — runtime logs têm retenção curta,
então a prova precisa ser capturada logo depois do evento.

## O que o dia ensinou

Fail fast só se prova quando falha em produção. O guard foi escrito com
testes unitários no Dia 12, mas só aqui a mensagem andou do código até o
log do provedor — teste prova o código, deploy prova o caminho inteiro.

Dois bloqueadores empilhados: `request → import app.main → config/database
→ [1] guard de SECRET_KEY → (se passar) [2] schemas → EmailStr →
email-validator`. Um 500 só revela o primeiro da fila; destrinchar a
ordem de import diz onde olhar, e a simulação local módulo a módulo
reproduz o ambiente limpo sem precisar de esteira de CI.

Segredo é questão de superfície, e as duas primeiras falharam aqui de
jeitos diferentes: commitar `.env` deixa rastro eterno no histórico,
subir no bundle da CLI faz o guard passar com a chave errada, faltar a
env var derruba o deploy (que era o esperado).

Persistência é critério de aceite. `200 OK` no `/health` prova que a
função sobe; só o ciclo registro → deploy → login prova que o banco é
externo. O disco efêmero não consegue fingir isso.

## Como testar

```bash
pytest                          # 110 passed, 100%
pytest tests/test_deploy.py -q  # contrato de deploy (12 testes)

curl https://socialink-gilt.vercel.app/health
curl -X POST .../auth/registrar -H "Content-Type: application/json" \
  -d '{"nome":"Teste","email":"teste@exemplo.com","senha":"senha123"}'
curl -X POST .../auth/login -H "Content-Type: application/json" \
  -d '{"email":"teste@exemplo.com","senha":"senha123"}'

# persistência: registrar, depois `npx vercel redeploy <url>`, e logar de
# novo com o mesmo usuário — tem que voltar 200
npx vercel logs <url>           # onde o guard aparece se faltar SECRET_KEY
```

Os 2 testes novos do dia: `test_email_str_tem_dependencia_declarada`
(`EmailStr` exige `email-validator` no requirements) e
`test_vercelignore_bloqueia_segredos_no_upload_da_cli` (`.env*` e venvs
fora do upload da CLI).

## Próximos passos

O `plan.md` (Dia 1 a 14) está concluído. As evoluções estão em
[plan.md §9](../plan.md#9-ideias-de-evolução-depois-do-mvp): paginação e
busca, e-mail de confirmação, Docker, rate limiting e migrações
versionadas com Alembic. Na operação: monitorar os logs após deploys,
rotacionar a `SECRET_KEY` se o repositório algum dia for público, e
revisar o free tier do Neon quando o projeto crescer.

Dia 14 concluído — roadmap completo. Próximo: evoluções pós-MVP.
