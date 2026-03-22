# SPEC-005b — Corrigir uso incorreto de prompts Best of Opera no Reels Classics

**Status:** CONCLUÍDO
**PRD de origem:** `docs/PRD-005-diagnostico-erros-plataforma.md` (problema #5)
**Data:** 22/03/2026

---

## Contexto

Projetos do Reels Classics estão sendo gerados com prompts, identidade e hashtags do Best of Opera. Causa: múltiplos fallbacks hardcoded `or "best-of-opera"` em toda a cadeia — endpoints de geração, schema, config e frontend. A correção é cirúrgica em 4 arquivos.

**BLOCKER obrigatório antes de executar:**
Rodar no banco do app-redator:
```sql
SELECT brand_slug, COUNT(*) FROM projects GROUP BY brand_slug;
```
Se existirem projetos com `brand_slug = NULL` ou `brand_slug = ''` — documentar count antes de prosseguir. Não tornar o campo NOT NULL sem migração.

---

## Tarefa 1 — `generation.py`: remover fallback silencioso nos 4 endpoints

**Arquivo:** `app-redator/backend/routers/generation.py`

**Linhas a modificar:** 62, 93, 112, 131 (mesmo padrão nas 4 funções)

**Antes (repetido 4×):**
```python
brand_slug = getattr(project, 'brand_slug', None) or "best-of-opera"
brand_config = load_brand_config(brand_slug)
```

**Depois (repetido 4×):**
```python
brand_slug = getattr(project, 'brand_slug', None)
if not brand_slug:
    raise HTTPException(400, "Projeto sem brand_slug definido. Recrie o projeto selecionando uma marca.")
brand_config = load_brand_config(brand_slug)
```

**Critério de feito:** nenhuma das 4 funções (`generate_all`, `regenerate_overlay`, `regenerate_post`, `regenerate_youtube`) contém `or "best-of-opera"`.

---

## Tarefa 2 — `config.py`: remover retorno de config do Best of Opera quando editor offline

**Arquivo:** `app-redator/backend/config.py`

**Linhas a modificar:** 48–68

**Problema:** quando `urllib.request.urlopen` falha (editor offline), retorna config hardcoded com `"brand_name": "Best of Opera"` e `"hashtags_fixas": ["#BestOfOpera", ...]`. Qualquer slug solicitado (incluindo `"reels-classics"`) recebe config do Best of Opera.

**Antes:**
```python
    except Exception as exc:
        print(f"⚠️ load_brand_config: editor offline ({exc}), usando defaults")

    data = {
        "brand_name": "Best of Opera",
        "brand_slug": "best-of-opera",
        ...
        "hashtags_fixas": ["#BestOfOpera", "#Opera", "#ClassicalMusic"],
        ...
    }
    _brand_config_cache[target_slug] = {"data": data, "ts": now}
    return data
```

**Depois:**
```python
    except Exception as exc:
        print(f"⚠️ load_brand_config: editor offline para slug='{target_slug}' ({exc})")
        raise HTTPException(
            503,
            f"Não foi possível carregar configuração da marca '{target_slug}'. "
            "Editor indisponível. Tente novamente em instantes."
        )
```

**Critério de feito:** `load_brand_config("reels-classics")` com editor offline levanta HTTPException 503, não retorna dados do Best of Opera. O bloco de dados hardcoded (`data = { "brand_name": "Best of Opera", ... }`) não existe mais no arquivo.

---

## Tarefa 3 — `schemas.py`: remover default silencioso no ProjectCreate

**Arquivo:** `app-redator/backend/schemas.py`

**Linha a modificar:** 40

**Antes:**
```python
brand_slug: str = "best-of-opera"
```

**Depois:**
```python
brand_slug: str
```

> ⚠️ **Atenção:** isso torna o campo obrigatório no schema Pydantic. Qualquer chamada a `POST /api/projects` sem `brand_slug` passará a retornar erro de validação 422. Verificar se há outros callers além de `new-project.tsx` antes de aplicar (grep por `createProject` e `POST.*projects` no codebase).

**Critério de feito:** `ProjectCreate` não tem default para `brand_slug`. Tentativa de criar projeto sem o campo retorna 422.

---

## Tarefa 4 — `new-project.tsx`: bloquear submit sem marca selecionada

**Arquivo:** `app-portal/components/redator/new-project.tsx`

### 4a. Adicionar `selectedBrand` na condição `canSubmit` (linha 200)

**Antes:**
```typescript
const canSubmit = stepAComplete && detected && !!interpreters[0]?.artist && !!shared.work && !!shared.composer
```

**Depois:**
```typescript
const canSubmit = stepAComplete && detected && !!interpreters[0]?.artist && !!shared.work && !!shared.composer && !!selectedBrand
```

### 4b. Adicionar validação explícita no `handleSubmit` (linha 202)

**Antes:**
```typescript
const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    setError("")
    setLoading(true)
```

**Depois:**
```typescript
const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    if (!selectedBrand) {
      setError("Selecione uma marca antes de criar o projeto.")
      return
    }
    setError("")
    setLoading(true)
```

**Critério de feito:** botão de submit fica desabilitado se `selectedBrand` for null. Mesmo que o botão seja ativado por outro caminho, o `handleSubmit` bloqueia com mensagem de erro clara.

---

## Ordem de execução

1. **Tarefa 1** — `generation.py` (sem dependências, impacto imediato, mais crítico)
2. **Tarefa 2** — `config.py` (sem dependências, protege a geração quando editor cair)
3. **Tarefa 4** — `new-project.tsx` (frontend, sem dependências de backend)
4. **Tarefa 3** — `schemas.py` (por último — verificar callers antes)

---

## Verificação pós-execução

- [ ] Criar projeto Reels Classics no redator → verificar que `brand_slug = "reels-classics"` no banco
- [ ] Gerar overlay de projeto Reels Classics → verificar que prompt não contém referências ao Best of Opera
- [ ] Tentar criar projeto sem selecionar marca → botão deve estar desabilitado
- [ ] Com editor offline (ou URL incorreta), tentar gerar overlay → deve retornar erro 503, não gerar com dados do Best of Opera
- [ ] Conferir no banco: `SELECT brand_slug, COUNT(*) FROM projects GROUP BY brand_slug` — comparar com snapshot tirado no BLOCKER inicial
