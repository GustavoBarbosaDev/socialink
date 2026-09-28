# Relatório Técnico — Dia 12: Revisão de entrega (README, `.env` e dependências)

**Data:** 28/09/2026
**Objetivo:** Revisar o README e conferir o `.env`
**Conceito principal:** Boas práticas de entrega — configuração documentada, defaults seguros, dependências reproduzíveis

---

## 1. O que foi feito

### 1.1 Meta do dia cumprida

| Meta | Resultado |
|------|-----------|
| Revisar README | ✅ status do Dia 12, árvore corrigida, seção de variáveis, deploy nos próximos passos |
| Conferir `.env` / `.env.example` | ✅ `.env.example` com as **7** variáveis de `app/config.py`, `.env` local alinhado |
| Guard de `SECRET_KEY` (achado da auditoria) | ✅ placeholder/vazia derruba a subida com mensagem acionável |
| Relatório faltante do Dia 3 | ✅ reconstruído em `docs/relatorio-dia3.md` (276 linhas) |
| Higiene de dependências | ✅ `python-dotenv` removido (redundante); pino `bcrypt==4.0.1` **verificado como obrigatório** |
| Testes | 89 → **98 testes** (+9), **100%** de cobertura |

### 1.2 Arquivos modificados/criados

| Arquivo | Ação |
|---------|------|
| `docs/relatorio-dia3.md` | **Criado** — relatório que faltava da série (pendência do Dia 10) |
| `tests/test_config.py` | **Criado** — 9 testes: `DEBUG` default, espelho do `.env.example`, defaults, guard de `SECRET_KEY` (4 rejeições + exemplo + chave válida) |
| `.env.example` | Modificado — `+APP_NAME`, `+APP_VERSION`, `+DEBUG=true` |
| `.env` | Modificado (local, não versionado) — `+DEBUG=true` para manter o log de SQL no dev |
| `app/config.py` | Modificado — `DEBUG: bool = True` → `False`; `SECRET_KEY` sem default + validação |
| `requirements.txt` | Modificado — `-python-dotenv` |
| `README.md` | Modificado — status, variáveis de ambiente, árvore, próximos passos |
| `docs/relatorio-dia12.md` | **Criado** — este relatório |

---

## 2. Detalhes técnicos

### 2.1 O espelho `.env.example` × `config.py`, travado por um teste

`app/config.py` define sete campos; o `.env.example` trazia quatro. Quem
chegasse no projeto não teria como saber que `APP_NAME`, `APP_VERSION` e
`DEBUG` existiam. Depois de completar o exemplo, o que impede a nova
configuração de nascer documentada é um teste:

```python
def test_env_example_documenta_todos_os_campos():
    chaves = {
        linha.split("=", 1)[0].strip()
        for linha in ARQUIVO_ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
        if "=" in linha and not linha.lstrip().startswith("#")
    }
    assert chaves == set(Settings.model_fields)
```

`set(Settings.model_fields)` é a fonte da verdade (o código); as chaves do
arquivo são a documentação. A asserção é de **dois lados**: config nova sem
linha no exemplo quebra o teste, e linha morta no exemplo quebra também.

### 2.2 `DEBUG` nasce `false` — e o exemplo liga `true`

```python
# antes (app/config.py)
DEBUG: bool = True      # produção sem .env → log de cada SQL
# depois
DEBUG: bool = False     # default seguro; dev liga no .env
```

`DEBUG` controla o `echo` do engine (`app/database.py:16`): `true` imprime
cada `SELECT`/`INSERT` no console. Em produção isso é ruído — e vazamento
de dados de negócio nos logs do provedor. Verificado sem `.env` algum:

```
produção (sem .env): DEBUG = False | engine.echo = False
```

O `.env.example` mantém `DEBUG=true`, então quem segue o README (passo 3:
`cp .env.example .env`) continua com o log de SQL do Dia 2 — comportamento
de desenvolvimento **não** mudou, só o default.

### 2.3 `python-dotenv` saiu do `requirements.txt` (com prova)

O `grep` não acha `load_dotenv` em lugar nenhum do código: quem lê o
`.env` é o `pydantic-settings`, via `SettingsConfigDict(env_file=".env")`.
Antes de remover, duas provas de que nada quebra:

```
$ pip show python-dotenv | grep -i required-by
Required-by: pydantic-settings

$ requires('uvicorn')  →  "python-dotenv>=0.13; extra == 'standard'"
```

O pacote é dependência **direta** de quem usa (pydantic-settings) e do
extra `standard` do uvicorn — ou seja, ele continua sendo instalado em
qualquer `pip install -r requirements.txt`. A linha que saiu era uma
declaração duplicada, não uma remoção de pacote.

É a mesma lição do Dia 10 (`python-multipart` não podia sair): remove-se
só depois de provar que nada depende — só que, desta vez, a prova mostrou
**redundância** em vez de dependência.

### 2.4 A verificação de dependências encontrou um pino que salva o projeto

Como o Dia 12 é "conferir entrega", o `requirements.txt` foi auditado
versão a versão. O `bcrypt==4.0.1` (fixado no Dia 3) parece capricho —
não é. Testado num venv descartável:

| Versão do `bcrypt` | `passlib` 1.7.4 | Resultado |
|---|---|---|
| 4.0.1 (o pino) | funciona | ✅ hash + verify ok |
| 4.1.0 | **quebra** | ❌ `TypeError: argument 'salt': 'str' object cannot be converted to 'PyBytes'` — versão anulada no PyPI (*"Incompatibility with assumptions made by passlib"*) |
| 4.2.0 | funciona | ⚠️ loga `error reading bcrypt version` (passlib lê `bcrypt.__about__`, removido na 4.1) |
| 5.0.0 (hoje, a latest) | **quebra** | ❌ `ValueError: password cannot be longer than 72 bytes...` |

Ou seja: **sem o pino, um `pip install` limpo hoje instalaria o `bcrypt
5.0.0` e o registro de usuário explodiria**. O `passlib[bcrypt]` não
trava nada (`bcrypt>=0.7`). Quem clonar o projeto e rodar o passo 2 do
README depende dessa linha.

### 2.5 README: o que a revisão pegou

| Achado | Correção |
|---|---|
| Árvore listava só `docs/relatorio-dia11.md` (12 arquivos reais) | `relatorio-dia1.md … relatorio-dia12.md` + `tests/test_config.py` |
| Sem documentação das variáveis de ambiente | seção "Variáveis de ambiente" com as 7 + tabela |
| `SECRET_KEY` só dita "troque por algo aleatório" | comando `openssl rand -hex 32` no passo 3 |
| "Próximos passos" apontava só para o plan.md | Dia 13–14 (deploy) nomeado explicitamente |
| Status ainda descrevia o Dia 11 | status do Dia 12 + resumo do contrato de erro mantido |
| Tabela de rotas | conferida contra o `/openapi.json` real: **11 rotas** (10 da tabela + `/health`), batem |

### 2.6 O guard de `SECRET_KEY`: falhar na subida, não em produção

O achado da auditoria (seção 4.4) tinha uma consequência direta: enquanto o
`Settings` aceitasse o placeholder, um deploy esquecido **funcionava** —
e a "funcionando" era o pior cenário, porque ninguém percebe. O guard fecha
o buraco no único lugar que não depende do provedor, o próprio código:

```python
@model_validator(mode="after")
def secret_key_e_segura(self):
    if (
        not self.SECRET_KEY.strip()
        or self.SECRET_KEY in PLACEHOLDERS_DE_SECRET_KEY
    ):
        raise ValueError(MENSAGEM_SECRET_KEY)
    return self
```

Três decisões dentro do validador:

1. **`mode="after"`** — valida o valor já resolvido (variável de ambiente
   vencendo `.env`, que é a ordem do `pydantic-settings`), não o default do
   campo;
2. **`.strip()`** — `SECRET_KEY="   "` passaria em qualquer comparação
   ingênua e ainda assinaria tokens;
3. **conjunto de placeholders, não um** — cobre o valor do `.env.example`
   (`sua_chave_secreta_aqui`) e o default antigo que estava no código
   (`..._mude_em_producao`). Um teste amarra os dois lados: se o exemplo
   mudar o valor, o guard precisa mudar junto.

O `raise` vira `ValidationError` do Pydantic com a mensagem acionável —
copiar o exemplo sem gerar a chave produz:

```
ValueError: SECRET_KEY ausente ou ainda é um placeholder do .env.example.
Copie .env.example para .env e gere uma chave real: openssl rand -hex 32
```

A mensagem não é erro de framework: diz **o que fazer**, e o README passou
a repetir a ordem (copiar → gerar → colar) no passo 3. A suíte nunca vê
esse caminho por acidente — `tests/conftest.py` injeta uma chave de teste
**antes** de importar `app.*` (os módulos chamam `get_settings()` no import
e o `lru_cache` fixa o valor), então a suite roda em clone fresco, sem
`.env`, e sem usar o segredo real de quem desenvolve.

---

## 3. Conceitos-chave aplicados

### 3.1 Configuração é código — e documentação é teste

Padrão 12-factor: configuração vem do ambiente, o código traz o default.
Mas default sem documentação é segredo, e documentação sem teste é
promessa. O trio ficou:

```
app/config.py      → fonte da verdade (Settings)
.env.example       → contrato com quem vai implantar
tests/test_config.py → fiscal que os dois não divergem
```

### 3.2 Default seguro (secure by default)

Um default só é "neutro" para quem roda em desenvolvimento. Em produção,
`DEBUG=true` é o estado que ninguém escolheu. A regra adotada: **o default
é o estado seguro para quem não configurar nada**; quem quer o comportamento
de desenvolvimento acende a chave de propósito.

### 3.3 Dependência redundante ≠ dependência morta

| | Exemplo | O que fazer |
|---|---|---|
| Morta | nada importa o pacote | remover (com prova) |
| Redundante | outro pacote já a declara | remover a linha, manter o pacote |
| Oculta | importada num caminho indireto | **nunca** remover sem testar |

O dia 10 ensinou a categoria 3; o dia 12 aplicou a 2.

### 3.4 Pino de versão como parte da entrega

O `requirements.txt` é o que transforma "funciona na minha máquina" em
"funciona no clone do avaliador" e no deploy. Versionar dependência
transitiva crítica (aqui, `bcrypt`) é entrega, não burocracia.

---

## 4. Problemas encontrados e soluções

### 4.1 `relatorio-dia3.md` não existia (pendência desde o Dia 10)

A série tinha 12 dias e 11 relatórios. Sem o arquivo, não havia como
saber o que aconteceu no Dia 3 — os relatórios vizinhos citavam um
"próximo" que apontava para um arquivo que nunca existiu.

**Solução:** reconstruir a partir do commit `8a95f5a` (diff completo: 6
arquivos, +242 linhas) e dos 7 testes originais em
`git show 8a95f5a:tests/test_auth.py`. O relatório abre com a nota de
recuperação e a data original (21/09) ao lado da data da escrita (Dia 12),
para ninguém achar que foi escrito no dia.

### 4.2 O `.env.example` não dizia que `DEBUG` existia

Resultado prático: quem configura produção pela documentação nunca diga
`DEBUG=false` porque nunca soube que havia `DEBUG` — e, com o default
antigo (`True`), receberia log de SQL sem pedir. Resolvido nos dois lados
(exemplo documentado + default seguro).

### 4.3 `python-dotenv` parecia dependência órfã

Parecia o caso clássico de "código que não usa, remove". As duas provas da
seção 2.3 mostraram que a linha era só duplicata. Nenhum `import dotenv`
em `app/` — e o pacote segue instalado por quem depende dele.

### 4.4 Risco aberto: `SECRET_KEY` com fallback conhecido → resolvido no mesmo dia

Verificado na auditoria (antes da correção):

```
SECRET_KEY é placeholder? True     # quando não há .env nem variável de ambiente
```

Se o deploy subisse sem `SECRET_KEY`, a API subiria **funcionando** com a
chave `sua_chave_secreta_aqui_mude_em_producao` — ou seja, qualquer um que
lesse o repositório consegue assinar tokens válidos de organização. A
primeira redação deste relatório deixou a correção para o Dia 13, sob o
argumento de que "a solução certa depende de como o provedor injeta as
variáveis".

Esse raciocínio estava errado: o provedor só tem duas formas de entregar a
chave (variável de ambiente ou arquivo) — e **as duas já passam pelo
`Settings`**. Quem decide se placeholder é aceitável é o código, não o
Render. Por isso o guard da seção 2.6 entrou ainda no Dia 12, com os
testes do item 1.1 cobrindo os quatro casos (vazia, só espaços, placeholder
do exemplo, default antigo).

> Lição: quando o risco é "a aplicação aceita segredo fraco", a correção não
> depende da infra — depende de onde o valor é lido. Aqui é uma linha só.

---

## 5. Como testar

```bash
# Suíte inteira (com cobertura)
pytest

# Só a configuração de entrega (9 testes)
pytest tests/test_config.py -q

# O guard de SECRET_KEY, isolado
pytest tests/test_config.py -k secret_key -q      # 5 passam (4 rejeições + válida)

# Provar que o espelho quebra: comente uma linha no .env.example
pytest tests/test_config.py -q          # → falha em test_env_example_documenta_todos_os_campos

# Porta de entrada de quem clona o projeto (do zero)
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt          # bcrypt 4.0.1 garantido pelo pino
cp .env.example .env
uvicorn app.main:app --reload            # → ValidationError: SECRET_KEY ausente...
                                         #   (é o guard funcionando: falta gerar a chave)
openssl rand -hex 32                     # cole no SECRET_KEY do .env e suba de novo

# Estado do repositório
git status                               # .env e *.db fora do stage
```

---

## 6. Status

```
Name                           Stmts   Miss  Cover
------------------------------------------------------------
app/... (13 arquivos)             377      0   100%
------------------------------------------------------------
TOTAL                            377      0   100%

98 passed, 3 warnings in ~33s
```

| Teste novo (9) | O que trava |
|---|---|
| `test_debug_nasce_false_sem_env` | default de `DEBUG` é `False` sem `.env` |
| `test_env_example_documenta_todos_os_campos` | `.env.example` == campos de `Settings` |
| `test_defaults_de_entrega` | defaults batem com o que o exemplo promete |
| `test_secret_key_invalida_impede_subir[4 ids]` | vazia, só espaços, placeholder do exemplo e default antigo → `ValidationError` |
| `test_placeholder_do_env_example_e_rejeitado` | o valor do `.env.example` está no conjunto de placeholders |
| `test_secret_key_real_e_aceita` | chave aleatória passa; `DEBUG` continua `False` |

Os 3 warnings continuam sendo de terceiros (`starlette.testclient`,
`anyio`, `passlib`).

---

## 7. Arquivos modificados/criados

| Arquivo | Ação | Linhas |
|---------|------|--------|
| `docs/relatorio-dia3.md` | Criado | 276 |
| `tests/test_config.py` | Criado | 106 |
| `.env.example` | Modificado | 24 |
| `.env` | Modificado (local) | 14 |
| `app/config.py` | Modificado | 52 |
| `requirements.txt` | Modificado | 24 |
| `README.md` | Modificado | 166 |
| `docs/relatorio-dia12.md` | Criado | — |

---

## 8. Próximos passos (Dia 13–14)

- [x] Guard de `SECRET_KEY` (seção 2.6) — feito no Dia 12
- [ ] Deploy gratuito (Render ou Railway) com variáveis de ambiente do provedor
- [ ] Trocar `DATABASE_URL` para PostgreSQL e testar o caminho de produção
- [ ] Smoke test na URL pública: `/health`, registro e login de ponta a ponta
- [ ] Conferir se o provedor sobe sem `.env` (o guard deve derrubar o build com a mensagem certa)

---

**Status:** Dia 12 concluído
**Próximo:** Dia 13 — Deploy gratuito (Render ou Railway)
