# Relatório Técnico — Dia 9: Aprovação/Recusa de Inscrições

**Data:** 25/09/2026  
**Objetivo:** Permitir que a organização dona decida sobre as inscrições da própria vaga  
**Conceito principal:** Máquina de estados simples

---

## 1. O que foi feito

### 1.1 Arquivos modificados/criados

| Arquivo | Ação |
|---------|------|
| `app/dependencies.py` | Modificado — +`get_inscricao`, +`get_inscricao_dono` |
| `app/schemas.py` | Modificado — +`InscricaoUpdate` com validação de status alvo |
| `app/routers/inscricoes.py` | Modificado — +`PATCH /inscricoes/{id}`, +`GET /oportunidades/{id}/inscricoes` |
| `tests/test_inscricoes.py` | Modificado — +16 testes |
| `README.md` | Modificado — status do projeto, tabela de endpoints e estrutura |

### 1.2 Endpoints implementados

| Método | Rota | Autenticação | Regra |
|--------|------|--------------|-------|
| PATCH | `/inscricoes/{id}` | Obrigatória | Só a organização **dona da oportunidade** decide; transição `pendente → aprovado \| recusado` |
| GET | `/oportunidades/{id}/inscricoes` | Obrigatória | Só a organização **dona** lista as candidaturas da vaga |

### 1.3 Matriz de respostas do PATCH de decisão

| Código | Quando |
|--------|--------|
| 401 | Token ausente ou inválido |
| 403 | Inscrição existe, mas a oportunidade não pertence ao usuário |
| 404 | Inscrição não existe |
| 409 | Inscrição já foi decidida (não há transição de volta) |
| 422 | `status` alvo é `pendente` ou não é um valor válido |
| 200 | Status atualizado e persistido |

### 1.4 Testes adicionados (16)

| Teste | Cenário | Esperado |
|-------|---------|----------|
| `test_listar_inscricoes_da_oportunidade_dono` | ONG lista a própria vaga | 200 + 1 item `pendente` |
| `test_listar_inscricoes_da_oportunidade_vazia` | Vaga sem candidaturas | 200 + `[]` |
| `test_listar_inscricoes_da_oportunidade_nao_dono` | Outra ONG lista a vaga | 403 |
| `test_listar_inscricoes_da_oportunidade_voluntario_proibido` | Voluntário lista a vaga | 403 |
| `test_listar_inscricoes_oportunidade_inexistente` | GET em `/oportunidades/999/...` | 404 |
| `test_listar_inscricoes_sem_token` | GET sem header Authorization | 401 |
| `test_aprovar_inscricao_sucesso` | ONG aprova | 200 `aprovado` + voluntário vê na listagem |
| `test_recusar_inscricao_sucesso` | ONG recusa | 200 `recusado` |
| `test_decidir_sem_token` | PATCH sem header Authorization | 401 |
| `test_decidir_token_invalido` | PATCH com token forjado | 401 |
| `test_decidir_voluntario_proibido` | Voluntário tenta decidir | 403 |
| `test_decidir_inscricao_inexistente` | PATCH em `/inscricoes/999` | 404 |
| `test_decidir_inscricao_de_outra_organizacao` | ONG de fora decide | 403 + status no banco intacto |
| `test_decidir_inscricao_ja_decidida` | Repetir ou inverter decisão | 409 + banco preserva `aprovado` |
| `test_decidir_status_pendente_proibido` | Body `{"status": "pendente"}` | 422 |
| `test_decidir_status_invalido` | Body `{"status": "qualquer"}` | 422 |

---

## 2. Detalhes técnicos

### 2.1 Máquina de estados

```
            ┌──────────── aprovado   (estado final)
            │
pendente ───┤
            │
            └──────────── recusado   (estado final)
```

A máquina vive em **dois pontos**, um por tipo de falha:

**1. Estado alvo — validação de entrada (Pydantic, `schemas.py`):**

```python
@field_validator("status")
@classmethod
def status_deve_ser_final(cls, valor: StatusInscricao) -> StatusInscricao:
    if valor == StatusInscricao.PENDENTE:
        raise ValueError("Status alvo deve ser 'aprovado' ou 'recusado'")
    return valor
```

Rejeita a *intenção* de voltar para `pendente` → 422 (o corpo está malformado
do ponto de vista do contrato).

**2. Estado atual — regra de negócio (endpoint, `inscricoes.py`):**

```python
if inscricao.status != StatusInscricao.PENDENTE:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Inscrição já foi decidida",
    )
```

Rejeita a *transição* a partir de um estado final → 409 (o corpo é válido,
mas contradiz o estado atual do recurso).

| | Estado alvo (422) | Estado atual (409) |
|---|---|---|
| Onde vive | Schema | Corpo do endpoint |
| O que pergunta | "o pedido faz sentido?" | "a transição é permitida?" |
| Camada | Validação de entrada | Regra de negócio |

### 2.2 Dependência `get_inscricao` (espelho de `get_oportunidade`)

Mesma extração do Dia 8: carregamento + 404 virou dependência própria,
reaproveitada por quem precisa só do 404:

```python
def get_inscricao(
    inscricao_id: int,
    session: Session = Depends(get_session),
) -> Inscricao:
    inscricao = session.get(Inscricao, inscricao_id)
    if not inscricao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inscrição não encontrada",
        )
    return inscricao
```

### 2.3 Dependência `get_inscricao_dono` (autorização por dono, duas chaves)

O dono **não está na inscrição**, está na oportunidade *vinculada* a ela.
Por isso a verificação atravessa o relacionamento:

```python
def get_inscricao_dono(
    usuario: Usuario = Depends(get_current_user),
    inscricao: Inscricao = Depends(get_inscricao),
) -> Inscricao:
    oportunidade = inscricao.oportunidade
    if oportunidade.organizacao_id != usuario.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para decidir sobre esta inscrição",
        )
    return inscricao
```

Ordem das verificações (mesma lógica do `get_oportunidade_dono`, Dia 7):

1. **401** — token ausente/inválido (`get_current_user`);
2. **404** — inscrição não existe (`get_inscricao`);
3. **403** — inscrição existe, mas a oportunidade não pertence ao usuário.

Não é preciso checar papel separadamente: quem é dono de uma oportunidade
só pode ser `organizacao`, porque `POST /oportunidades` já exige esse papel
(Dia 6). A checagem de dono é estritamente mais forte.

Comparação com o Dia 8:

| | Dia 8 (POST de inscrição) | Dia 9 (PATCH de decisão) |
|---|---|---|
| Papel | Dependência explícita (`get_current_voluntario`) | Implícito no dono da oportunidade |
| Regra | Não duplicar (409) | Transição de estado (409) |
| Quem decide | O próprio usuário | O dono do recurso relacionado |

### 2.4 Fluxo completo de uma decisão

```
PATCH /inscricoes/7  {"status": "aprovado"}   (Bearer token)
    ↓
oauth2_scheme extrai o token                       → 401 se ausente
    ↓
get_current_user decodifica e busca usuário        → 401 se inválido
    ↓
get_inscricao carrega a inscrição do path          → 404 se não existe
    ↓
get_inscricao_dono compara o dono da oportunidade  → 403 se não é o dono
    ↓
InscricaoUpdate valida o status alvo               → 422 se for pendente/inválido
    ↓
checa inscricao.status == "pendente"               → 409 se já decidida
    ↓
grava o novo status e persiste                     → 200
```

### 2.5 Listagem da vaga (`GET /oportunidades/{id}/inscricoes`)

```python
def listar_inscricoes_da_oportunidade(
    oportunidade: Oportunidade = Depends(get_oportunidade_dono),
    session: Session = Depends(get_session),
):
    stmt = select(Inscricao).where(
        Inscricao.oportunidade_id == oportunidade.id
    )
    return session.exec(stmt).all()
```

Reaproveita `get_oportunidade_dono` do Dia 7 sem código novo: 401 → 404 →
403 já vêm resolvidos. Sem ela a organização teria de adivinhar o id da
inscrição para decidir — a listagem é o "quadro branco" do fluxo.

---

## 3. Conceitos-chave aplicados

### 3.1 Máquina de estados

Um recurso com status tem **transições permitidas**, não apenas valores
válidos. `pendente`, `aprovado` e `recusado` são todos valores válidos no
enum — mas `aprovado → recusado` não é uma *transição* válida. Guardar isso
no enum não basta; a regra mora onde a mudança acontece.

### 3.2 409 vs 422: mesma "coisa errada", camadas diferentes

- **422** — o corpo não satisfaz o contrato do schema (status alvo proibido);
- **409** — o corpo está ok, mas conflita com o estado atual do recurso.

Regra prática: se o erro já existia *antes* do servidor ler o banco, é
validação (422); se só aparece ao comparar com o banco, é conflito (409).

### 3.3 Autorização por dono de recurso relacionado

O Dia 7 autorizava pelo dono direto (`oportunidade.organizacao_id`). Aqui o
recurso protegido é a inscrição, cujo dono é indireto — a autorização
"atravessa" um relacionamento até chegar na oportunidade. Padrão comum em
APIs com fluxos de aprovação (reviews, pedidos, tickets).

---

## 4. Problemas encontrados e soluções

### 4.1 O status alvo inválido deve dar 422 ou 409?

Duas hands: 422 (Pydantic rejeita no schema) ou 409 (regra de máquina de
estados no endpoint). **Solução:** dividir — o schema barra `pendente`
como alvo (o contrato não aceita "voltar para o início"), e o endpoint
barra transição a partir de um estado final (conflito com o banco). Fica
cada regra na camada que tem a informação necessária para avaliá-la.

### 4.2 Dois endpoints em rotas com prefixos diferentes no mesmo router

`PATCH /inscricoes/{id}` e `GET /oportunidades/{id}/inscricoes` não
compartilham prefixo. **Solução:** manter o `inscricoes.py` sem `prefix`
(já era assim desde o Dia 8) e escrever o caminho completo em cada rota.
`GET /oportunidades/{id}/inscricoes` não colide com
`GET /oportunidades/{id}` do router de oportunidades porque a contagem de
segmentos é diferente (2 contra 1 após o prefixo).

### 4.3 Voluntário decidindo sobre a própria inscrição

`get_inscricao_dono` compara o dono da oportunidade com o usuário
autenticado — o voluntário inscrito falha nessa comparação e recebe 403.
Não é possível "auto-aprovar": o caminho até a transição passa
obrigatoriamente pela posse da vaga.

### 4.4 Mensagem do 403 ao listar a vaga

`get_oportunidade_dono` foi escrito no Dia 7 para mutações e diz
*"Sem permissão para alterar esta oportunidade"*. Reusado numa listagem,
a palavra "alterar" soa estranha. **Decisão:** manter a mensagem para não
quebrar o contrato já testado nos Dia 7/8 — o código de status (403) é o
que os clientes dependem. Se a API crescer, vale separar uma dependência
de leitura com mensagem própria.

---

## 5. Como testar

```bash
# 1. Registrar ONG e voluntário (como no Dia 8)
curl -X POST http://localhost:8000/auth/registrar \
  -H "Content-Type: application/json" \
  -d '{"nome": "ONG Ajuda", "email": "ong@example.com", "senha": "123456", "papel": "organizacao"}'

curl -X POST http://localhost:8000/auth/registrar \
  -H "Content-Type: application/json" \
  -d '{"nome": "Ana", "email": "ana@example.com", "senha": "123456", "papel": "voluntario"}'

# 2. ONG cria a oportunidade (TOKEN_ONG) → id 1
# 3. Login da Ana → TOKEN_VOL
# 4. Ana se inscreve (espera 201) → inscrição id 1, status pendente

# 5. ONG lista as candidaturas da vaga (espera 200)
curl http://localhost:8000/oportunidades/1/inscricoes \
  -H "Authorization: Bearer TOKEN_ONG"
# → 200  [ {"id":1,...,"status":"pendente"} ]

# 6. Aprovar (espera 200)
curl -X PATCH http://localhost:8000/inscricoes/1 \
  -H "Authorization: Bearer TOKEN_ONG" \
  -H "Content-Type: application/json" \
  -d '{"status": "aprovado"}'
# → 200  {"status":"aprovado"}

# 7. Tentar mudar de novo (espera 409 — sem voltar atrás)
curl -X PATCH http://localhost:8000/inscricoes/1 \
  -H "Authorization: Bearer TOKEN_ONG" \
  -H "Content-Type: application/json" \
  -d '{"status": "recusado"}'
# → 409 "Inscrição já foi decidida"

# 8. Tentar voltar para pendente (espera 422)
curl -X PATCH http://localhost:8000/inscricoes/1 \
  -H "Authorization: Bearer TOKEN_ONG" \
  -H "Content-Type: application/json" \
  -d '{"status": "pendente"}'
# → 422

# 9. Voluntário tenta decidir (espera 403)
curl -X PATCH http://localhost:8000/inscricoes/1 \
  -H "Authorization: Bearer TOKEN_VOL" \
  -H "Content-Type: application/json" \
  -d '{"status": "aprovado"}'
# → 403

# 10. Inscrição inexistente (espera 404)
curl -X PATCH http://localhost:8000/inscricoes/999 \
  -H "Authorization: Bearer TOKEN_ONG" \
  -H "Content-Type: application/json" \
  -d '{"status": "aprovado"}'
# → 404 "Inscrição não encontrada"

# 11. Voluntário vê a decisão (espera 200)
curl http://localhost:8000/voluntario/me/inscricoes \
  -H "Authorization: Bearer TOKEN_VOL"
# → 200  [ {...,"status":"aprovado"} ]
```

---

## 6. Status dos testes

```
tests/test_auth.py           - 11 testes
tests/test_dependencies.py   -  5 testes
tests/test_oportunidades.py  - 20 testes
tests/test_inscricoes.py     - 28 testes  (+16)

Total: 64/64 testes passando
```

Comando: `pytest`

---

## 7. Arquivos modificados/criados

| Arquivo | Ação |
|---------|------|
| `app/dependencies.py` | Modificado — +`get_inscricao`, +`get_inscricao_dono` |
| `app/schemas.py` | Modificado — +`InscricaoUpdate` |
| `app/routers/inscricoes.py` | Modificado — `PATCH /inscricoes/{id}` + `GET /oportunidades/{id}/inscricoes` |
| `tests/test_inscricoes.py` | Modificado — 16 novos testes |
| `README.md` | Modificado — status Dia 9, endpoints e estrutura |
| `docs/relatorio-dia9.md` | Criado — este relatório |

---

## 8. Próximos passos (Dia 10)

- [ ] Preencher/acrescentar testes em `tests/` (já com os nomes prontos)
- [ ] Conferir cobertura dos caminhos de erro (401/403/404/409/422)
- [ ] Meta: suíte verde sem tocar no código da aplicação

---

**Status:** Dia 9 concluído  
**Próximo:** Dia 10 — Testes automatizados
