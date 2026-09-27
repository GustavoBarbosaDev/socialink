# Relatório Técnico — Dia 11: Tratamento de erros padronizado

**Data:** 27/09/2026  
**Objetivo:** Um único formato de erro para toda a API, com mensagens centralizadas  
**Conceito principal:** Exception handlers — exceções de domínio, handlers globais e contrato de erro

---

## 1. O que foi feito

### 1.1 Meta do dia cumprida

| Meta | Resultado |
|------|-----------|
| Exception handlers (400/401/403/404/409/422/500) | ✅ 3 handlers globais em `app/main.py` |
| Centralizar as mensagens de `detail` | ✅ 12 constantes em `app/errors.py`, importadas pelos testes |
| Manter 100% de cobertura | ✅ **100%** das 369 linhas de `app/` |
| Testes novos | 74 → **89 testes** (+15) |

### 1.2 Arquivos modificados/criados

| Arquivo | Ação |
|---------|------|
| `app/errors.py` | **Criado** — mensagens, exceções de domínio e handlers (152 linhas) |
| `app/main.py` | Modificado — registro dos 3 handlers |
| `app/dependencies.py` | Modificado — 8 `raise HTTPException` → exceções de domínio |
| `app/routers/auth.py` | Modificado — 400/401 com exceções de domínio |
| `app/routers/oportunidades.py` | Modificado — 404 com exceção de domínio |
| `app/routers/inscricoes.py` | Modificado — 2×409 com exceção de domínio |
| `tests/test_erros.py` | **Criado** — 15 testes do contrato de erro |
| `tests/test_auth.py` | Modificado — literais → constantes |
| `tests/test_dependencies.py` | Modificado — literais → constantes |
| `tests/test_oportunidades.py` | Modificado — literais → constantes |
| `tests/test_inscricoes.py` | Modificado — literais → constantes |
| `docs/relatorio-dia11.md` | **Criado** — este relatório |
| `README.md` | Modificado — status do Dia 11 |

### 1.3 O contrato de erro

Todo erro da API, **inclusive os levantados pelo próprio framework**, responde:

```json
{ "detail": "<texto>" }          // 400, 401, 403, 404, 405, 409, 500
{ "detail": [ {"campo", "mensagem"} ] }   // 422 (lista de erros de validação)
```

| Código | Onde nasce | Exceção / handler |
|--------|-----------|-------------------|
| 400 | e-mail duplicado, detail não-texto | `RequisicaoInvalida` |
| 401 | token ausente/inválido/expirado, login errado | `NaoAutenticado` (+ `WWW-Authenticate: Bearer`) |
| 403 | papel errado, não-dono | `Proibido` |
| 404 | recurso inexistente, rota/método desconhecido | `NaoEncontrado` + handler |
| 409 | inscrição duplicada ou já decidida | `Conflito` |
| 422 | Pydantic (corpo inválido) | `tratar_erro_validacao` |
| 500 | exceção não tratada | `tratar_erro_interno` (mensagem genérica) |

---

## 2. Detalhes técnicos

### 2.1 `app/errors.py`: três coisas num lugar só

```python
class Proibido(ErroAPI):
    """403 — autenticado, mas sem papel ou sem dono do recurso."""

    status_code = status.HTTP_403_FORBIDDEN
```

A subclasse carrega o código, então nenhum `raise` do negócio escolhe o
número errado — `raise Proibido(...)` **é** um 403. As mensagens vivem como
constantes no topo do módulo:

```python
OPORTUNIDADE_NAO_ENCONTRADA = "Oportunidade não encontrada"
# routers e dependencies
raise NaoEncontrado(OPORTUNIDADE_NAO_ENCONTRADA)
# testes
assert response.json()["detail"] == OPORTUNIDADE_NAO_ENCONTRADA
```

Antes, os 12 pontos que criavam `HTTPException` escreviam a string na mão e
**19 asserções** nos testes repetiam o mesmo texto — mudar uma frase exigia achar todas as ocorrências.
Agora é uma edição em `app/errors.py`.

### 2.2 Registrando no `starlette.exceptions.HTTPException`

```python
# app/main.py
app.add_exception_handler(StarletteHTTPException, tratar_http_exception)
app.add_exception_handler(RequestValidationError, tratar_erro_validacao)
app.add_exception_handler(Exception, tratar_erro_interno)
```

A chave importa: o FastAPI já usa **`starlette.exceptions.HTTPException`**
como handler padrão (`fastapi.applications.FastAPI.__init__` faz
`setdefault`), e o `fastapi.exceptions.HTTPException` é subclasse dela — o
Starlette procura o handler percorrendo o MRO da exceção, então um registro
na classe pai atende os dois.

Efeito colateral (desejado): erros que o próprio framework levanta — rota
inexistente (404) e método não permitido (405) — vinham em **texto puro**
(`PlainTextResponse` do Starlette) e agora saem no mesmo JSON da API.

### 2.3 `Exception` handler e o teste do 500

O `ServerErrorMiddleware` (a camada mais externa do Starlette) usa o handler
registrado sob a chave `Exception` — mas **re-lança a exceção depois de
enviar a resposta**, para o servidor de produção registrar o erro. O
`TestClient` segue a mesma lógica: com `raise_server_exceptions=True`
(padrão) ele devolve a exceção ao teste em vez da resposta.

Por isso o teste do 500 precisa dos dois ajustes:

```python
cliente = TestClient(app, raise_server_exceptions=False)
with rota_temporaria("/erro-interno", explodir):
    response = cliente.get("/erro-interno")
```

A rota temporária (context manager no próprio `tests/test_erros.py`)
publica um endpoint que falha de propósito e o remove depois — sem deixar
código de teste no projeto. O handler ainda registra o erro real via
`logger.error(..., exc_info=exc)`: o cliente vê a mensagem genérica, o log
leva o stack.

### 2.4 422: previsível e sem ecoar o input

O handler padrão do FastAPI devolve `loc`, `msg`, `type`, `input`, `ctx` e
`url` — inclusive o **valor enviado pelo cliente**. O handler novo reduz a:

```json
{"detail": [{"campo": "body.senha", "mensagem": "Input should be a valid string"}]}
```

O teste `test_422_nao_ecoa_o_valor_enviado` envia `senha` com tipo errado e
confirma que o valor não aparece em lugar nenhum do corpo.

### 2.5 Corpo em status que não admite corpo

`is_body_allowed_for_status_code` garante que um erro 204/304 saia **sem
JSON pendurado** (status que não pode ter corpo). É código defensivo —
nenhuma rota atual levanta 204 como erro — e, pela lição do Dia 10 ("código
defensivo sem teste" virou dívida), ele ganhou um teste próprio:
`test_erro_sem_corpo_nao_envia_body`.

---

## 3. Conceitos-chave aplicados

### 3.1 Handler ≠ middleware

O middleware roda **antes e depois** de cada rota; o handler roda **só
quando uma exceção sobe**. Isso mantém o caminho de sucesso limpo: nada de
`try/except` repetido em 13 endpoints — o erro é levantado uma vez no lugar
certo e formatado uma vez no centro.

### 3.2 Herança para fixar contrato

`ErroAPI` fixa `status_code` na subclasse. O custo de um erro de digitação
(`status_code=403` onde deveria ser 404) cai para zero porque quem escreve
`raise NaoEncontrado(...)` não tem como errar o número.

### 3.3 Mensagem é código

Texto de erro virou identificador de módulo. O benefício não é estético:
uma asserção que compara com string literal passa a quebrar **no lugar
certo** quando o texto muda, e a busca passa a ser `grep OPORTUNIDADE_NAO_ENCONTRADA`
em vez de caçar variações de acentuação e plural.

---

## 4. Problemas encontrados e soluções

### 4.1 `app.routes` tem `_IncludedRouter`, que não tem `.path`

A primeira versão do cleanup da rota temporária filtrava por
`rota.path != caminho` e quebrou:

```
AttributeError: '_IncludedRouter' object has no attribute 'path'
```

O `app.routes` do FastAPI 0.141 intercala `APIRoute` (rotas próprias) com
`_IncludedRouter` (o que cada `include_router` adiciona). A solução foi
guardar a referência do objeto criado e removê-lo por identidade:

```python
app.add_api_route(caminho, funcao, methods=["GET"])
rota_publicada = app.routes[-1]
...
app.routes.remove(rota_publicada)
```

O schema cacheado (`app.openapi_schema`) também é zerado antes e depois,
para um `/openapi.json` gerado durante o teste não engolir a rota
temporária.

### 4.2 O import ficou fora de ordem

A primeira inserção mecânica do bloco `from app.errors import (...)`
colocou-o depois de `from app.models import ...` e com parênteses para um
nome só. Corrigido para ordem alfabética de imports e import de uma linha
quando há uma constante só.

---

## 5. Como testar

```bash
# Suíte inteira (com cobertura)
pytest

# Só o contrato de erro
pytest tests/test_erros.py -q

# Garantir o piso de cobertura
pytest --cov-fail-under=95

# Conferir uma mensagem específica
pytest -k nao_encontrada -q
```

---

## 6. Status

```
Name                           Stmts   Miss  Cover
------------------------------------------------------------
app/... (12 arquivos)             369      0   100%
------------------------------------------------------------
TOTAL                            369      0   100%

89 passed, 3 warnings in ~31s
```

### Matriz dos caminhos de erro (asserções `status_code == N`)

| Código | Asserts | O que cobre |
|--------|---------|-------------|
| 400 | 2 | e-mail duplicado, `detail` não-texto normalizado |
| 401 | 20 | token ausente/inválido/expirado/sem `sub`, login errado, `WWW-Authenticate` |
| 403 | 11 | papel errado, não-dono, dono de recurso relacionado |
| 404 | 8 | recurso inexistente + **rota inexistente** |
| 405 | 1 | método não permitido (erro do framework em JSON) |
| 409 | 3 | inscrição duplicada e já decidida |
| 422 | 11 | Pydantic (`campo`/`mensagem`, sem ecoar input) |
| 500 | 1 | exceção não tratada → mensagem genérica |
| 204 | 2 | remoção sem corpo e erro 204 sem corpo |
| 200/201 | 26 | caminhos de sucesso |

---

## 7. Arquivos modificados/criados

| Arquivo | Ação | Linhas |
|---------|------|--------|
| `app/errors.py` | Criado | 152 |
| `tests/test_erros.py` | Criado | 161 |
| `app/main.py` | Modificado | 59 |
| `app/dependencies.py` | Modificado | 126 |
| `app/routers/auth.py` | Modificado | 86 |
| `app/routers/oportunidades.py` | Modificado | 86 |
| `app/routers/inscricoes.py` | Modificado | 98 |
| `tests/test_auth.py` | Modificado | 317 |
| `tests/test_dependencies.py` | Modificado | 119 |
| `tests/test_oportunidades.py` | Modificado | 339 |
| `tests/test_inscricoes.py` | Modificado | 470 |
| `README.md` | Modificado | — |

---

## 8. Próximos passos (Dia 12)

- [ ] Revisar README e conferir `.env` / `.env.example` (boas práticas de entrega)
- [ ] Revisar `docs/relatorio-dia3.md` (relatório faltando da série — pendência do Dia 10)
- [ ] Preparar o deploy (Dia 13–14: Render ou Railway)

---

**Status:** Dia 11 concluído  
**Próximo:** Dia 12 — Revisar README, conferir `.env`
