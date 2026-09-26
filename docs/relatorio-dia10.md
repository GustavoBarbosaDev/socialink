# Relatório Técnico — Dia 10: Testes Automatizados

**Data:** 26/09/2026  
**Objetivo:** Consolidar a suíte de testes, eliminar duplicação e medir cobertura  
**Conceito principal:** Testes automatizados — fixtures compartilhadas, DRY e cobertura de código

---

## 1. O que foi feito

### 1.1 Meta do dia cumprida

O relatório do Dia 9 deixou três pendências: preencher os testes,
conferir os caminhos de erro e ter a suíte verde **sem tocar no código da
aplicação**.

| Meta | Resultado |
|------|-----------|
| Preencher/acrescentar testes | 64 → **74 testes** (+10) |
| Conferir 400/401/403/404/409/422 | Todos cobertos (matriz na seção 1.4) |
| Suíte verde sem tocar em `app/` | ✅ **zero** alteração em `app/` |
| Cobertura medida | **100%** das 309 linhas de `app/` |

### 1.2 Arquivos modificados/criados

| Arquivo | Ação |
|---------|------|
| `tests/conftest.py` | Criado — fixtures `session` e `client` compartilhadas |
| `tests/helpers.py` | Criado — builders de cenário (usuários, vagas, login) |
| `tests/test_app.py` | Criado — `/`, `/health` e ciclo do lifespan |
| `pytest.ini` | Criado — `testpaths`, `pythonpath` e cobertura automática |
| `tests/test_auth.py` | Modificado — fixtures removidas, **+4 testes** |
| `tests/test_dependencies.py` | Modificado — `session` removida, **+2 testes** |
| `tests/test_oportunidades.py` | Modificado — fixtures removidas, **+1 teste** |
| `tests/test_inscricoes.py` | Modificado — fixtures e helpers removidos |
| `requirements.txt` | Modificado — +`pytest-cov>=5.0.0` |
| `README.md` | Modificado — status do Dia 10, seção de testes e estrutura |
| `docs/relatorio-dia10.md` | Criado — este relatório |

### 1.3 Os 10 testes novos

| Teste | Cenário | Esperado |
|-------|---------|----------|
| `test_registrar_papel_invalido` | `papel` fora do enum (`superadmin`) | 422 |
| `test_login_campos_obrigatorios` | Login só com `email` (sem senha) | 422 |
| `test_login_nao_expoe_senha` | Senha em texto puro na resposta do login | ausente no corpo |
| `test_token_expirado_em_endpoint` | JWT assinado com `exp: 0` em rota real | 401 |
| `test_atualizar_oportunidade_vagas_invalida` | `PATCH` com `vagas_disponiveis: 0` | 422 e valor não muda |
| `test_raiz_retorna_info_da_api` | `GET /` | 200 + app/docs |
| `test_health` | `GET /health` | 200 `{"status":"ok"}` |
| `test_lifespan_executa_startup_e_shutdown` | App sobe e desce com `with TestClient` | tabelas criadas + shutdown |
| `test_get_current_user_token_sem_sub` | Token válido sem o claim `sub` | 401 |
| `test_get_session_devolve_sessao` | A dependência `get_session` entrega uma `Session` | sessão viva |

### 1.4 Matriz dos caminhos de erro

Contagem de `assert ... status_code == N` em toda a suite:

| Código | Asserts | Exemplos cobertos |
|--------|---------|-------------------|
| 400 | 1 | e-mail duplicado no registro |
| 401 | 18 | token ausente, inválido, **expirado**, sem `sub`, login errado |
| 403 | 11 | papel errado, não-dono, dono de recurso relacionado |
| 404 | 7 | oportunidade/inscrição inexistente |
| 409 | 3 | inscrição duplicada e já decidida (máquina de estados) |
| 422 | 9 | Pydantic, papel inválido, `vagas` ≤ 0, `status` pendente |
| 200/201/204 | 27 | caminhos de sucesso |

---

## 2. Detalhes técnicos

### 2.1 `conftest.py`: onde as fixtures vivem

Antes, **quatro arquivos repetiam** o mesmo par de fixtures:

```python
# estava copiado em test_auth, test_dependencies,
# test_oportunidades e test_inscricoes
@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite://", ...)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
```

O pytest carrega `tests/conftest.py` automaticamente para todo teste do
diretório — então o par `session` + `client` foi movido para lá **uma
única vez**:

```python
@pytest.fixture(name="session")
def session_fixture():
    """Cria uma sessão de teste isolada para cada teste."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Cliente de teste apontando para a aplicação real (app.main:app)."""
    def get_session_override():
        return session
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
```

Resultado: cada teste continua com um banco em memória próprio e a
aplicação real com `get_session` substituída, só que sem repetição.

### 2.2 `helpers.py`: builders, não fixtures

Os builders (`criar_organizacao`, `criar_voluntario`, `fazer_login`,
`dados_oportunidade`, `criar_oportunidade`, `inscrever`) **não** viraram
fixtures de fábrica — viraram funções importáveis:

```python
from tests.helpers import criar_organizacao, fazer_login, criar_oportunidade
```

Por quê? Uma fixture-fábrica obrigaria a assinar todo teste com
`criar_organizacao(...)` na lista de parâmetros (74 assinaturas para
mudar) e esconderia de onde o dado vem. A função explícita mantém o
teste legível e a mudança foi apenas mecânica (renomear `_criar_...` →
`criar_...`).

Bônus: `dados_oportunidade(**alteracoes)` agora aceita sobrescrever
campos, então um teste inválido monta o payload com uma linha:

```python
criar_oportunidade(client, token, vagas_disponiveis=0)  # 422
```

### 2.3 Sombreamento de fixture no `test_dependencies.py`

Este arquivo mantém a **própria** fixture `client` — e isso é
intencional:

```python
@pytest.fixture(name="client")
def client_fixture(session: Session):
    app = FastAPI()                      # app mínima, não a real

    @app.get("/me")
    def read_me(usuario: Usuario = Depends(get_current_user)):
        ...
```

Para testar `get_current_user` isoladamente, o teste sobe um FastAPI
com uma rota só. A fixture local **sombrea** a do `conftest.py` (regra do
pytest: fixture definida no módulo vence a herdada) e continua usando a
`session` do conftest — só a `session` duplicada foi apagada.

### 2.4 `pytest.ini`

```ini
[pytest]
testpaths = tests
pythonpath = .
addopts = --cov=app --cov-report=term-missing
```

- `testpaths` — `pytest` sem argumentos acha os testes sozinho;
- `pythonpath` — garante `import app` e `import tests.helpers` em
  qualquer diretório de onde o comando for chamado;
- `addopts` — todo `pytest` já imprime a cobertura de `app/` com as
  linhas que faltam.

### 2.5 Cobertura com `pytest-cov`

```
Name                           Stmts   Miss  Cover
------------------------------------------------------------
app/config.py                     14      0   100%
app/database.py                   12      0   100%
app/dependencies.py               50      0   100%
app/main.py                       23      0   100%
app/models.py                     40      0   100%
app/routers/auth.py               42      0   100%
app/routers/inscricoes.py         34      0   100%
app/routers/oportunidades.py      38      0   100%
app/schemas.py                    56      0   100%
------------------------------------------------------------
TOTAL                            309      0   100%
```

---

## 3. Conceitos-chave aplicados

### 3.1 DRY aplicado à própria suíte

DRY não vale só para o código de produção: código de teste duplicado é
pior, porque quando a regra muda você ajusta em um lugar e esquece os
outros três. Um bug real era possível: os quatro `client_fixture`
divergentes passariam a valer regras diferentes para a mesma aplicação.

### 3.2 `dependency_overrides` como fio de teste

O coração do `client` fixture é:

```python
app.dependency_overrides[get_session] = get_session_override
...
app.dependency_overrides.clear()   # sempre no teardown
```

É o mesmo princípio do Dia 5 (dependency injection), usado ao contrário:
em vez de injetar, **substituímos** a dependência para apontar o teste
para um banco efêmero. O `clear()` evita vazamento entre testes.

### 3.3 Cobertura: o que ela mede (e o que não mede)

100% de cobertura quer dizer **toda linha foi executada**, não que todo
comportamento está verificado. Por isso a matriz da seção 1.4 existe
separadamente: cobertura diz "passou por aqui", as asserções dizem "o
resultado esperado é esse". Teste sem asserção derruba cobertura e não
prova nada.

---

## 4. Problemas encontrados e soluções

### 4.1 `python-multipart` não podia sair do requirements

A anotação dizia "opcional, para referência" e o pacote não era usado em
nenhum `Form`/`File` do código — parecia dependência morta. Antes de
remover, testei bloqueando o import:

```python
class Blocker:
    def find_spec(self, name, path=None, target=None):
        if name.split('.')[0] == 'python_multipart':
            raise ImportError('BLOQUEADO')
```

Resultado: **`from app.main import app` quebra**. O caminho é
`fastapi → starlette.requests → starlette.formparsers → python_multipart`,
ou seja, é dependência dura no import. A solução foi manter o pacote e
corrigir a anotação:

```
# Multipart (exigido pelo Starlette/FastAPI no import)
python-multipart>=0.0.6
```

**Lição:** remova dependências só depois de provar que nada quebra.

### 4.2 `--cov-fail-under` quebrava execuções parciais

Com o piso de 95% no `addopts`, rodar `pytest tests/test_app.py` falhava
(cobertura daquele arquivo isolado era 67%) e até `pytest --collect-only`
dava erro. Como o fluxo normal de estudo é rodar um arquivo ou `-k`,
o piso saiu do `addopts`:

```bash
pytest --cov-fail-under=95   # só quando quiser travar o gate
```

### 4.3 O lifespan nunca tinha sido exercitado

`app/main.py:15-20` estava sem cobertura: o `TestClient` comum **não**
dispara o shutdown da aplicação, porque ele precisa ser usado como
context manager:

```python
with TestClient(app) as cliente:      # sobe e desce a aplicação
    assert cliente.get("/health").status_code == 200
```

O teste ainda valida a saída com `capsys` (`Tabelas criadas com sucesso!`
e `Encerrando aplicação...`), então o lifespan passou a ser coberto de
verdade — inclusive a chamada a `criar_tabelas()`.

### 4.4 Token assinado sem o claim `sub`

A linha `raise credentials_exception` dentro do `if email is None`
(`app/dependencies.py:32`) era código defensivo sem teste — um token
assinado com a chave certa mas sem o campo `sub` não podia ser simulado
por nenhum teste anterior. Novo teste: 401, sem vazar detalhe.

---

## 5. Como testar

```bash
# Suíte inteira (com relatório de cobertura)
pytest

# Um arquivo
pytest tests/test_auth.py -q

# Pelo nome do teste
pytest -k token_expirado -q

# Só as falhas, com detalhe
pytest -x -vv

# Exigir piso de cobertura (gate manual)
pytest --cov-fail-under=95
```

---

## 6. Status dos testes

```
Name                           Stmts   Miss  Cover
------------------------------------------------------------
app/... (10 arquivos)            309      0   100%
------------------------------------------------------------
TOTAL                            309      0   100%

74 passed, 3 warnings in ~31s
```

| Arquivo | Testes | Linhas |
|---------|--------|--------|
| `tests/test_app.py` | 3 | 34 |
| `tests/test_auth.py` | 15 | 312 |
| `tests/test_dependencies.py` | 7 | 118 |
| `tests/test_oportunidades.py` | 21 | 335 |
| `tests/test_inscricoes.py` | 28 | 465 |
| `tests/conftest.py` + `tests/helpers.py` | — | 133 |
| **Total** | **74** | **1.397** |

Os 3 warnings restantes vêm de bibliotecas de terceiros
(`starlette.testclient`, `anyio` e `passlib`) — nenhum do projeto.

---

## 7. Arquivos modificados/criados

| Arquivo | Ação | Linhas |
|---------|------|--------|
| `tests/conftest.py` | Criado | 39 |
| `tests/helpers.py` | Criado | 94 |
| `tests/test_app.py` | Criado | 34 |
| `pytest.ini` | Criado | 4 |
| `tests/test_auth.py` | Modificado | 312 |
| `tests/test_dependencies.py` | Modificado | 118 |
| `tests/test_oportunidades.py` | Modificado | 335 |
| `tests/test_inscricoes.py` | Modificado | 465 |
| `requirements.txt` | Modificado | 27 |
| `README.md` | Modificado | — |
| `docs/relatorio-dia10.md` | Criado | — |

---

## 8. Próximos passos (Dia 11)

- [ ] Tratamento de erros padronizado (404, 403, 400) com exception handlers
- [ ] Centralizar as mensagens de `detail` para os testes deixarem de
      repetir strings literais
- [ ] Manter 100% de cobertura em todo código novo
- [ ] Revisar `docs/relatorio-dia3.md` (relatório faltando da série)

---

**Status:** Dia 10 concluído  
**Próximo:** Dia 11 — Tratamento de erros padronizado
