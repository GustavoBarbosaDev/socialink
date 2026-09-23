# Relatório Técnico — Dia 6: CRUD de Oportunidades

**Data:** 23/09/2026  
**Objetivo:** Implementar CRUD de oportunidades (criar, listar, detalhar)  
**Conceito principal:** Validação com Pydantic

---

## 1. O que foi feito

### 1.1 Arquivos modificados/criados

| Arquivo | Ação |
|---------|------|
| `app/schemas.py` | Modificado — schemas de Oportunidade |
| `app/routers/oportunidades.py` | Criado — router CRUD |
| `app/main.py` | Modificado — router registrado |
| `tests/test_oportunidades.py` | Criado — 15 testes |

### 1.2 Schemas criados

| Schema | Uso |
|--------|-----|
| `OportunidadeCreate` | Entrada de dados na criação |
| `OportunidadeResponse` | Saída de dados (sem dados internos) |
| `OportunidadeUpdate` | Atualização parcial (campos opcionais) |

### 1.3 Endpoints implementados

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| POST | `/oportunidades/` | Obrigatória | Cria oportunidade |
| GET | `/oportunidades/` | Não | Lista todas |
| GET | `/oportunidades/{id}` | Não | Detalha uma |
| PATCH | `/oportunidades/{id}` | Obrigatória | Atualiza (só dono) |
| DELETE | `/oportunidades/{id}` | Obrigatória | Remove (só dono) |

---

## 2. Detalhes técnicos

### 2.1 Schemas Pydantic

```python
class OportunidadeCreate(BaseModel):
    titulo: str
    descricao: str
    local: str
    data: datetime
    vagas_disponiveis: int = Field(ge=1)


class OportunidadeUpdate(BaseModel):
    titulo: str | None = None
    descricao: str | None = None
    local: str | None = None
    data: datetime | None = None
    vagas_disponiveis: int | None = Field(default=None, ge=1)
```

**Pontos-chave:**
- `Field(ge=1)` valida que vagas >= 1 já na entrada
- `OportunidadeUpdate` usa `| None = None` para atualização parcial
- `exclude_unset=True` no `model_dump()` ignora campos não enviados

### 2.2 Fluxo de criação

```
POST /oportunidades/ (com Bearer token)
    ↓
get_current_user extrai usuário do token
    ↓
Validação Pydantic do corpo (OportunidadeCreate)
    ↓
Cria Oportunidade com organizacao_id = usuario.id
    ↓
Retorna 201 com dados criados
```

### 2.3 Autorização por dono

PATCH e DELETE verificam se `oportunidade.organizacao_id == usuario.id`:

```python
if oportunidade.organizacao_id != usuario.id:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Sem permissão para editar esta oportunidade",
    )
```

---

## 3. Conceitos-chave aplicados

### 3.1 Validação com Pydantic

O FastAPI valida automaticamente usando os schemas:
- Campos obrigatórios ausentes → 422
- Tipo errado → 422
- `vagas_disponiveis < 1` → 422

### 3.2 Atualização parcial (PATCH)

```python
dados_dict = dados.model_dump(exclude_unset=True)
for campo, valor in dados_dict.items():
    setattr(oportunidade, campo, valor)
```

Só os campos enviados são atualizados — os demais mantêm o valor original.

### 3.3 Dependency Injection reutilizada

`get_current_user` (do Dia 5) foi injetado direto nos endpoints que precisam de autenticação.

---

## 4. Problemas encontrados e soluções

### 4.1 Validação de vagas não funcionava

O schema original não tinha `ge=1` — só o model SQLModel validava, mas a validação Pydantic acontece antes de chegar no banco.

**Solução:** Adicionar `Field(ge=1)` no schema:
```python
vagas_disponiveis: int = Field(ge=1)
```

---

## 5. Como testar

```bash
# 1. Registrar organização
curl -X POST http://localhost:8000/auth/registrar \
  -H "Content-Type: application/json" \
  -d '{"nome": "ONG Ajuda", "email": "ong@example.com", "senha": "123456", "papel": "organizacao"}'

# 2. Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "ong@example.com", "senha": "123456"}'

# 3. Criar oportunidade
curl -X POST http://localhost:8000/oportunidades/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <seu_token>" \
  -d '{
    "titulo": "Campanha de arrecadação",
    "descricao": "Ajudar na organização de doações",
    "local": "Centro Comunitário",
    "data": "2026-10-15T09:00:00",
    "vagas_disponiveis": 10
  }'

# 4. Listar
curl http://localhost:8000/oportunidades/

# 5. Detalhar
curl http://localhost:8000/oportunidades/1
```

---

## 6. Status dos testes

```
tests/test_auth.py - 11 testes
tests/test_dependencies.py - 5 testes
tests/test_oportunidades.py - 15 testes

Total: 31/31 testes passando
```

---

## 7. Próximos passos (Dia 7)

- [ ] Restringir edição/remoção só para o dono (já implementado parcialmente)
- [ ] Revisar regras de autorização
- [ ] Garantir que só organizações criem oportunidades (opcional)

---

**Status:** Dia 6 concluído  
**Próximo:** Dia 7 — Restringir edição/remoção só para o dono
