# Relatório Técnico — Dia 7: Autorização por Dono do Recurso

**Data:** 23/09/2026  
**Objetivo:** Restringir edição/remoção só para o dono  
**Conceito principal:** Autorização por dono do recurso

---

## 1. O que foi feito

### 1.1 Arquivos modificados/criados

| Arquivo | Ação |
|---------|------|
| `app/dependencies.py` | Modificado — novas dependências de autorização |
| `app/routers/oportunidades.py` | Modificado — router usa as dependências |
| `tests/test_oportunidades.py` | Modificado — 5 novos testes (15 → 20) |

### 1.2 Dependências criadas

| Dependência | Função |
|-------------|--------|
| `get_current_organizacao` | Exige papel `organizacao` (403 para voluntários) |
| `get_oportunidade_dono` | Carrega a oportunidade e exige que o usuário seja o dono |

### 1.3 Matriz de autorização revisada

| Método | Rota | Autenticação | Papel | Dono |
|--------|------|--------------|-------|------|
| POST | `/oportunidades/` | Obrigatória | `organizacao` | — |
| GET | `/oportunidades/` | Não | — | — |
| GET | `/oportunidades/{id}` | Não | — | — |
| PATCH | `/oportunidades/{id}` | Obrigatória | — | Sim |
| DELETE | `/oportunidades/{id}` | Obrigatória | — | Sim |

### 1.4 Testes adicionados

| Teste | Cenário | Esperado |
|-------|---------|----------|
| `test_criar_oportunidade_voluntario_proibido` | Voluntário tenta criar oportunidade | 403 |
| `test_atualizar_oportunidade_sem_token` | PATCH sem header Authorization | 401 |
| `test_atualizar_oportunidade_voluntario_nao_dono` | Voluntário tenta editar oportunidade de ONG | 403 |
| `test_remover_oportunidade_sem_token` | DELETE sem header Authorization | 401 |
| `test_remover_oportunidade_voluntario_nao_dono` | Voluntário tenta remover oportunidade de ONG | 403 (recurso persiste) |

---

## 2. Detalhes técnicos

### 2.1 Dependência `get_current_organizacao`

```python
def get_current_organizacao(
    usuario: Usuario = Depends(get_current_user),
) -> Usuario:
    """Garante que o usuário autenticado tenha papel 'organizacao'."""
    if usuario.papel != PapelUsuario.ORGANIZACAO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas organizações podem executar esta ação",
        )
    return usuario
```

**Encadeamento de dependências:**

```
criar_oportunidade
    └── get_current_organizacao
            └── get_current_user
                    └── oauth2_scheme (extrai token)
                    └── get_session (sessão do banco)
```

O FastAPI resolve a cadeia inteira antes de chamar o endpoint. Se qualquer
nível falhar, os níveis seguintes nem executam.

### 2.2 Dependência `get_oportunidade_dono`

```python
def get_oportunidade_dono(
    oportunidade_id: int,
    usuario: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Oportunidade:
    oportunidade = session.get(Oportunidade, oportunidade_id)
    if not oportunidade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oportunidade não encontrada",
        )

    if oportunidade.organizacao_id != usuario.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para alterar esta oportunidade",
        )

    return oportunidade
```

**Pontos-chave:**

- Recebe `oportunidade_id` **direto do path** — o FastAPI injeta o path param
  na dependência automaticamente;
- Retorna o objeto `Oportunidade` pronto: o endpoint não precisa buscar nem
  validar nada;
- Ordem das verificações: **404 → 403** (401 é anterior, no `get_current_user`).

### 2.3 Router refatorado

**Antes (Dia 6):** cada endpoint repetia busca + 404 + 403 inline.

**Agora (Dia 7):** a autorização vive na dependência; o endpoint só faz
regra de negócio.

```python
@router.patch("/{oportunidade_id}", response_model=OportunidadeResponse)
def atualizar_oportunidade(
    dados: OportunidadeUpdate,
    oportunidade: Oportunidade = Depends(get_oportunidade_dono),
    session: Session = Depends(get_session),
):
    """Atualiza parcialmente uma oportunidade (apenas o dono)."""
    dados_dict = dados.model_dump(exclude_unset=True)
    for campo, valor in dados_dict.items():
        setattr(oportunidade, campo, valor)

    session.add(oportunidade)
    session.commit()
    session.refresh(oportunidade)
    return oportunidade


@router.delete("/{oportunidade_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_oportunidade(
    oportunidade: Oportunidade = Depends(get_oportunidade_dono),
    session: Session = Depends(get_session),
):
    """Remove uma oportunidade (apenas o dono)."""
    session.delete(oportunidade)
    session.commit()
```

**Ganho:** PATCH e DELETE compartilham a mesma regra de autorização sem
duplicação — alterou a regra em um lugar só, mudou para os dois.

### 2.4 Fluxo completo de uma requisição PATCH

```
PATCH /oportunidades/5  (Bearer token)
    ↓
oauth2_scheme extrai o token                → 401 se ausente
    ↓
get_current_user decodifica e busca usuário  → 401 se inválido
    ↓
get_oportunidade_dono busca a oportunidade   → 404 se não existe
    ↓
compara organizacao_id com usuario.id        → 403 se não é dono
    ↓
Pydantic valida o corpo (OportunidadeUpdate) → 422 se inválido
    ↓
endpoint aplica os campos enviados e persiste → 200
```

---

## 3. Conceitos-chave aplicados

### 3.1 Autenticação vs Autorização

| | Autenticação (Dia 4–5) | Autorização (Dia 7) |
|---|---|---|
| Pergunta | **Quem** é você? | **O que** você pode fazer? |
| Falha | 401 Unauthorized | 403 Forbidden |
| Implementação | `get_current_user` | `get_current_organizacao`, `get_oportunidade_dono` |

### 3.2 Autorização por dono do recurso (ownership)

Regra: **só quem criou o recurso pode alterá-lo ou removê-lo.**

```python
if oportunidade.organizacao_id != usuario.id:
    raise HTTPException(status_code=403, ...)
```

Comparação por **id** (`organizacao_id == usuario.id`), nunca por e-mail ou
nome — ids são estáveis e únicos.

### 3.3 Autorização por papel (role-based)

```python
if usuario.papel != PapelUsuario.ORGANIZACAO:
    raise HTTPException(status_code=403, ...)
```

Complementa o ownership: nem todo usuário autenticado pode **criar**
oportunidades — apenas organizações. Quem não é dono nunca chega na regra de
dono porque a criação já está bloqueada na fronteira.

### 3.4 Dependências compostas (encadeadas)

`get_current_organizacao` **não reimplementa** a extração de token — ela
depende de `get_current_user`:

```python
def get_current_organizacao(
    usuario: Usuario = Depends(get_current_user),  # ← reutiliza
) -> Usuario:
```

Padrão: dependências pequenas, compostas, cada uma com uma responsabilidade.
O mesmo princípio do Dia 5, agora aplicado a **autorização**.

---

## 4. Problemas encontrados e soluções

### 4.1 Código de permissão duplicado em PATCH e DELETE

No Dia 6, o bloco `if oportunidade.organizacao_id != usuario.id` estava
copiado nos dois endpoints — risco de um ser atualizado e o outro esquecido.

**Solução:** extrair para `get_oportunidade_dono` e injetar nos dois.

### 4.2 Voluntário conseguia criar oportunidades

A criação exigia apenas autenticação (`get_current_user`), qualquer papel
passava — mas o domínio diz que oportunidades são criadas por **organizações**.

**Solução:** dependência `get_current_organizacao` que valida o papel.

### 4.3 Ordem 404 vs 403

Se a oportunidade não existe, responder 403 vazaria que ela "existe em algum
lugar" para quem não é dono — e confundiria quem errou o id.

**Ordem adotada:**
1. 401 — token (antes de tudo, no `get_current_user`);
2. 404 — recurso não existe;
3. 403 — existe, mas não é seu.

---

## 5. Como testar

```bash
# 1. Registrar organização e voluntário
curl -X POST http://localhost:8000/auth/registrar \
  -H "Content-Type: application/json" \
  -d '{"nome": "ONG Ajuda", "email": "ong@example.com", "senha": "123456", "papel": "organizacao"}'

curl -X POST http://localhost:8000/auth/registrar \
  -H "Content-Type: application/json" \
  -d '{"nome": "Ana", "email": "ana@example.com", "senha": "123456", "papel": "voluntario"}'

# 2. Login da ONG → criar oportunidade
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "ong@example.com", "senha": "123456"}'
# copiar access_token → TOKEN_ONG

curl -X POST http://localhost:8000/oportunidades/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN_ONG" \
  -d '{
    "titulo": "Campanha de arrecadação",
    "descricao": "Ajudar na organização de doações",
    "local": "Centro Comunitário",
    "data": "2026-10-15T09:00:00",
    "vagas_disponiveis": 10
  }'

# 3. Login do voluntário → tentar criar (espera 403)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "ana@example.com", "senha": "123456"}'
# copiar access_token → TOKEN_VOL

curl -X POST http://localhost:8000/oportunidades/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN_VOL" \
  -d '{"titulo": "X", "descricao": "Y", "local": "Z", "data": "2026-10-15T09:00:00", "vagas_disponiveis": 1}'
# → 403 "Apenas organizações podem executar esta ação"

# 4. Voluntário tentar editar/remover a oportunidade da ONG (espera 403)
curl -X PATCH http://localhost:8000/oportunidades/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN_VOL" \
  -d '{"titulo": "Hackeado"}'
# → 403

curl -X DELETE http://localhost:8000/oportunidades/1 \
  -H "Authorization: Bearer TOKEN_VOL"
# → 403

# 5. Sem token (espera 401)
curl -X PATCH http://localhost:8000/oportunidades/1 \
  -H "Content-Type: application/json" -d '{"titulo": "X"}'
# → 401

# 6. Dono edita com sucesso (espera 200)
curl -X PATCH http://localhost:8000/oportunidades/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN_ONG" \
  -d '{"titulo": "Título Atualizado"}'
# → 200
```

---

## 6. Status dos testes

```
tests/test_auth.py           - 11 testes
tests/test_dependencies.py   -  5 testes
tests/test_oportunidades.py  - 20 testes  (15 + 5 novos)

Total: 36/36 testes passando
```

Novos cenários cobertos:
- voluntário não cria oportunidade (403);
- voluntário não edita/remove oportunidade de outrem (403);
- PATCH/DELETE sem token (401);
- recurso permanece intacto após tentativa de remoção indevida.

---

## 7. Arquivos modificados/criados

| Arquivo | Ação |
|---------|------|
| `app/dependencies.py` | Modificado — +`get_current_organizacao`, +`get_oportunidade_dono` |
| `app/routers/oportunidades.py` | Modificado — usa as novas dependências (menos código inline) |
| `tests/test_oportunidades.py` | Modificado — +5 testes, helper `_criar_voluntario` |

---

## 8. Próximos passos (Dia 8)

- [ ] Implementar inscrição do voluntário (`POST /oportunidades/{id}/inscricoes`)
- [ ] Regra "não duplicar": um voluntário só pode se inscrever uma vez na mesma oportunidade
- [ ] Listar inscrições do voluntário (`GET /voluntario/me/inscricoes`)
- [ ] Garantir que só `voluntario` se inscreva (autorização por papel, reutilizando o padrão do Dia 7)

---

**Status:** Dia 7 concluído  
**Próximo:** Dia 8 — Inscrição do voluntário + regra "não duplicar"
