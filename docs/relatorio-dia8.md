# Relatório Técnico — Dia 8: Inscrição do Voluntário + Regra "não duplicar"

**Data:** 24/09/2026  
**Objetivo:** Permitir que o voluntário se inscreva em oportunidades, sem duplicidade  
**Conceito principal:** Regras de negócio

---

## 1. O que foi feito

### 1.1 Arquivos modificados/criados

| Arquivo | Ação |
|---------|------|
| `app/dependencies.py` | Modificado — +`get_current_voluntario`, +`get_oportunidade`; `get_oportunidade_dono` passou a reutilizar `get_oportunidade` |
| `app/schemas.py` | Modificado — +`InscricaoResponse` |
| `app/routers/inscricoes.py` | Criado — router de inscrições |
| `app/main.py` | Modificado — registra `inscricoes.router` |
| `tests/test_inscricoes.py` | Criado — 12 novos testes |
| `README.md` | Modificado — status do projeto, tabela de endpoints e estrutura |

### 1.2 Endpoints implementados

| Método | Rota | Autenticação | Papel | Regra |
|--------|------|--------------|-------|-------|
| POST | `/oportunidades/{id}/inscricoes` | Obrigatória | `voluntario` | Não duplicar (409) |
| GET | `/voluntario/me/inscricoes` | Obrigatória | `voluntario` | Só retorna as próprias |

### 1.3 Matriz de respostas do POST de inscrição

| Código | Quando |
|--------|--------|
| 401 | Token ausente ou inválido |
| 403 | Usuário autenticado não é `voluntario` |
| 404 | Oportunidade não existe |
| 409 | Voluntário já está inscrito naquela oportunidade |
| 201 | Inscrição criada com `status = "pendente"` |

### 1.4 Testes adicionados (12)

| Teste | Cenário | Esperado |
|-------|---------|----------|
| `test_inscrever_voluntario_sucesso` | Voluntário se inscreve | 201, `status = pendente` |
| `test_inscrever_duplicado_proibido` | Mesmo voluntário se inscreve de novo | 409 + apenas 1 registro no banco |
| `test_inscrever_sem_token` | POST sem header Authorization | 401 |
| `test_inscrever_token_invalido` | POST com token forjado | 401 |
| `test_inscrever_organizacao_proibido` | Organização tenta se inscrever | 403 |
| `test_inscrever_oportunidade_inexistente` | POST em `/oportunidades/999/...` | 404 |
| `test_inscrever_outro_voluntario_mesma_oportunidade` | Dois voluntários na mesma vaga | 201 + 2 registros |
| `test_listar_minhas_inscricoes_vazia` | Sem inscrições ainda | 200 + `[]` |
| `test_listar_minhas_inscricoes_com_dados` | Após se inscrever | 200 + 1 item |
| `test_listar_minhas_inscricoes_isoladas_por_usuario` | Dois voluntários inscritos | Cada um vê só a sua |
| `test_listar_minhas_inscricoes_sem_token` | GET sem header Authorization | 401 |
| `test_listar_minhas_inscricoes_organizacao_proibido` | Organização consulta "minhas inscrições" | 403 |

---

## 2. Detalhes técnicos

### 2.1 Dependência `get_current_voluntario`

Espelho simétrico de `get_current_organizacao` (Dia 7):

```python
def get_current_voluntario(
    usuario: Usuario = Depends(get_current_user),
) -> Usuario:
    """Garante que o usuário autenticado tenha papel 'voluntario'."""
    if usuario.papel != PapelUsuario.VOLUNTARIO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas voluntários podem executar esta ação",
        )
    return usuario
```

Mesma composição do Dia 5/7: **não reimplementa** a extração do token —
depende de `get_current_user` e só acrescenta a checagem de papel.

### 2.2 Dependência `get_oportunidade` (extração do Dia 7)

O carregamento + 404 saiu de dentro de `get_oportunidade_dono` e virou uma
dependência própria, agora reaproveitada pelos dois domínios:

```python
def get_oportunidade(
    oportunidade_id: int,
    session: Session = Depends(get_session),
) -> Oportunidade:
    oportunidade = session.get(Oportunidade, oportunidade_id)
    if not oportunidade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oportunidade não encontrada",
        )
    return oportunidade
```

`get_oportunidade_dono` ficou menor e com a mesma ordem de verificação
(401 → 404 → 403):

```python
def get_oportunidade_dono(
    usuario: Usuario = Depends(get_current_user),
    oportunidade: Oportunidade = Depends(get_oportunidade),
) -> Oportunidade:
    if oportunidade.organizacao_id != usuario.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para alterar esta oportunidade",
        )
    return oportunidade
```

### 2.3 Regra "não duplicar"

A regra vive **no endpoint**, não no banco — é regra de negócio, e o
Dia 8 é sobre isso:

```python
stmt = select(Inscricao).where(
    Inscricao.oportunidade_id == oportunidade_id,
    Inscricao.voluntario_id == usuario.id,
)
if session.exec(stmt).first():
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Voluntário já inscrito nesta oportunidade",
    )
```

A consulta compara **os dois ids** (oportunidade + voluntário): a mesma
pessoa pode se inscrever em quantas oportunidades quiser, e a mesma
oportunidade aceita quantos voluntários quiser — só o par é único.

Comparação com o padrão do Dia 7:

| | Dia 7 (autorização) | Dia 8 (regra de negócio) |
|---|---|---|
| Onde vive | Dependência | Corpo do endpoint |
| Por quê | Regra transversal, repetida em vários endpoints | Regra específica de um caso de uso |
| Falha | 403 | 409 |

### 2.4 Fluxo completo de uma inscrição

```
POST /oportunidades/5/inscricoes  (Bearer token)
    ↓
oauth2_scheme extrai o token                    → 401 se ausente
    ↓
get_current_user decodifica e busca usuário     → 401 se inválido
    ↓
get_current_voluntario confere o papel          → 403 se é organização
    ↓
get_oportunidade busca a oportunidade           → 404 se não existe
    ↓
SELECT em inscricoes (oportunidade + voluntário)→ 409 se já existe
    ↓
cria Inscricao(status="pendente") e persiste    → 201
```

### 2.5 Listagem própria (`GET /voluntario/me/inscricoes`)

```python
stmt = select(Inscricao).where(Inscricao.voluntario_id == usuario.id)
return session.exec(stmt).all()
```

O filtro sai do **usuário autenticado**, nunca de parâmetro enviado pelo
cliente — quem pede é quem recebe. Não há como "espiar" as inscrições de
outro voluntário mudando a URL.

---

## 3. Conceitos-chave aplicados

### 3.1 Regras de negócio vs autorização

- **Autorização** (Dia 7): quem pode chamar o endpoint → 401/403;
- **Regra de negócio** (Dia 8): o que é *válido* dentro do endpoint → 409.

São camadas diferentes: primeiro "você é quem diz ser?" e só depois
"sua ação faz sentido no domínio?".

### 3.2 HTTP 409 Conflict

409 = conflito com o estado atual do recurso. É o código certo quando o
pedido é válido em si (usuário autenticado, papel certo, recurso existe),
mas **contradiz algo que já está no banco** — aqui, uma inscrição existente.

### 3.3 Status da inscrição (máquina de estados, adiante)

A inscrição nasce `pendente`. A transição para `aprovado`/`recusado` é o
tema do **Dia 9** (aprovação pela organização) — hoje o estado inicial é
definido pelo default do model:

```python
status: StatusInscricao = Field(default=StatusInscricao.PENDENTE)
```

---

## 4. Problemas encontrados e soluções

### 4.1 Duas rotas com prefixes diferentes no mesmo domínio

`POST /oportunidades/{id}/inscricoes` e `GET /voluntario/me/inscricoes`
não compartilham prefixo. **Solução:** router sem `prefix` em
`inscricoes.py`, com o caminho completo em cada rota — e a rota de
inscrição não colide com `GET /oportunidades/{id}` porque a contagem de
segmentos é diferente.

### 4.2 Quem checa primeiro: papel ou recurso existente?

Ordem adotada no POST de inscrição:

1. **401** — token (`get_current_user`);
2. **403** — papel (`get_current_voluntario`);
3. **404** — oportunidade existe (`get_oportunidade`);
4. **409** — duplicidade (regra no endpoint).

A ordem das dependências no `Depends` da assinatura define a ordem de
resolução — `usuario` vem antes de `oportunidade` de propósito.

### 4.3 Filtrar "minhas inscrições" por parâmetro seria um buraco

A alternativa seria `GET /inscricoes?voluntario_id=123` — aí qualquer um
consultaria os dados de outro. **Solução:** rota `/voluntario/me/...` que
lê o id do token JWT.

---

## 5. Como testar

```bash
# 1. Registrar organização e voluntário (como no Dia 7)
curl -X POST http://localhost:8000/auth/registrar \
  -H "Content-Type: application/json" \
  -d '{"nome": "ONG Ajuda", "email": "ong@example.com", "senha": "123456", "papel": "organizacao"}'

curl -X POST http://localhost:8000/auth/registrar \
  -H "Content-Type: application/json" \
  -d '{"nome": "Ana", "email": "ana@example.com", "senha": "123456", "papel": "voluntario"}'

# 2. ONG cria a oportunidade (TOKEN_ONG) → id 1
# 3. Login da Ana → TOKEN_VOL

# 4. Inscrever (espera 201)
curl -X POST http://localhost:8000/oportunidades/1/inscricoes \
  -H "Authorization: Bearer TOKEN_VOL"
# → 201  {"id":1,"oportunidade_id":1,"voluntario_id":2,"status":"pendente",...}

# 5. Tentar de novo (espera 409 — regra "não duplicar")
curl -X POST http://localhost:8000/oportunidades/1/inscricoes \
  -H "Authorization: Bearer TOKEN_VOL"
# → 409 "Voluntário já inscrito nesta oportunidade"

# 6. Organização tenta se inscrever (espera 403)
curl -X POST http://localhost:8000/oportunidades/1/inscricoes \
  -H "Authorization: Bearer TOKEN_ONG"
# → 403 "Apenas voluntários podem executar esta ação"

# 7. Oportunidade inexistente (espera 404)
curl -X POST http://localhost:8000/oportunidades/999/inscricoes \
  -H "Authorization: Bearer TOKEN_VOL"
# → 404 "Oportunidade não encontrada"

# 8. Listar as minhas inscrições (espera 200)
curl http://localhost:8000/voluntario/me/inscricoes \
  -H "Authorization: Bearer TOKEN_VOL"
# → 200  [ {...} ]
```

---

## 6. Status dos testes

```
tests/test_auth.py           - 11 testes
tests/test_dependencies.py   -  5 testes
tests/test_oportunidades.py  - 20 testes
tests/test_inscricoes.py     - 12 testes  (novo)

Total: 48/48 testes passando
```

Comando: `pytest`

---

## 7. Arquivos modificados/criados

| Arquivo | Ação |
|---------|------|
| `app/dependencies.py` | Modificado — +`get_current_voluntario`, +`get_oportunidade`, `get_oportunidade_dono` reutiliza `get_oportunidade` |
| `app/schemas.py` | Modificado — +`InscricaoResponse` |
| `app/routers/inscricoes.py` | Criado — POST de inscrição + listagem própria |
| `app/main.py` | Modificado — `app.include_router(inscricoes.router)` |
| `tests/test_inscricoes.py` | Criado — 12 testes |
| `README.md` | Modificado — status Dia 8, endpoints e estrutura |

---

## 8. Próximos passos (Dia 9)

- [ ] Aprovação/recusa de inscrições pela organização (`PATCH /inscricoes/{id}`)
- [ ] Só a organização **dona da oportunidade** pode decidir (reaproveitar `get_oportunidade_dono`)
- [ ] Máquina de estados: `pendente → aprovado | recusado` (sem voltar atrás)
- [ ] Testes dos novos caminhos

---

**Status:** Dia 8 concluído  
**Próximo:** Dia 9 — Aprovação/recusa de inscrições
