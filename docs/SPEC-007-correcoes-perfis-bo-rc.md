# SPEC-007 — Correções de Perfis BO e RC: Backfill, Fontes, Limites e Preview

**Data:** 25/03/2026
**Baseado em:** PRD-007
**Status:** CONCLUÍDO

---

## Contexto

Correções identificadas no PRD-007 e confirmadas em sessão de diagnóstico. Nenhuma alteração foi feita antes deste SPEC. As correções são independentes entre si e podem ser executadas em qualquer ordem, com exceção de P1 (deve ser a primeira — protege todas as outras de serem apagadas no próximo deploy).

**P5 (expor overlay_interval_secs na UI) foi descartado:** campo já existe na UI admin em `app-portal/app/(app)/admin/marcas/[id]/page.tsx` linha 590–596. Não é necessário implementar.

---

## Ordem de execução recomendada

1. P1 — Corrigir backfill incondicional do BO *(pré-requisito das demais)*
2. P2 — Definir overlay_interval_secs = 10 para BO
3. P6 — Aumentar fontsize lyrics/tradução 32 → 40px no BO
4. P3 — Corrigir overlay_max_chars do RC
5. P4 — Corrigir fallback inconsistente no overlay_prompt.py + UI
6. P7 — Corrigir ESTILOS_PADRAO no admin_perfil.py
7. P8 — Esconder tracks lyrics/tradução no preview do RC

---

## P1 — Corrigir backfill incondicional do BO

**Arquivo:** `app-editor/backend/app/main.py`
**Linhas:** 227–240

### Problema
O UPDATE executa a cada restart/deploy sem condição de guarda. Sobrescreve `font_name`, `overlay_style`, `lyrics_style`, `traducao_style` do BO incondicionalmente. Qualquer ajuste feito na UI admin é apagado no próximo deploy.

### Correção
Adicionar condição de guarda: só executar se o BO ainda não estiver com a fonte correta.

```python
# ANTES (linha 228):
WHERE sigla = 'BO'

# DEPOIS:
WHERE sigla = 'BO' AND (font_name IS NULL OR font_name != 'TeX Gyre Schola')
```

### Critério de "feito"
- UPDATE tem cláusula WHERE com guarda de font_name
- Em banco já migrado (font_name = 'TeX Gyre Schola'), o UPDATE não executa
- Em banco antigo (font_name = NULL ou diferente), o UPDATE executa uma vez

---

## P2 — Definir overlay_interval_secs = 10 para BO

**Arquivo:** `app-editor/backend/app/main.py`

### Problema
O seed do BO (INSERT) não inclui `overlay_interval_secs`. O campo herda o default do modelo = 6. O correto para o BO, conforme brand doc, é 10s.

### Correção — parte 1: INSERT seed (para novos deploys)

Localizar o INSERT do BO (linhas 148–188) e adicionar `overlay_interval_secs` na lista de colunas e valores:

```python
# Na lista de colunas do INSERT, adicionar:
overlay_interval_secs,

# No SELECT, adicionar (após os outros valores numéricos):
10,
```

### Correção — parte 2: backfill para banco existente

Adicionar após o bloco do INSERT do BO (antes do seed RC):

```python
conn.execute(text("""
    UPDATE editor_perfis SET
        overlay_interval_secs = 10
    WHERE sigla = 'BO' AND overlay_interval_secs != 10
"""))
logger.info("Migration: backfill overlay_interval_secs BO = 10 OK")
```

### Critério de "feito"
- Perfil BO no banco tem `overlay_interval_secs = 10`
- Novo deploy não reseta o valor se já estiver em 10

---

## P3 — Corrigir overlay_max_chars do RC

**Arquivo:** `app-editor/backend/app/main.py`
**Linhas:** ~297

### Problema
O seed do RC usa `overlay_max_chars = 70` e `overlay_max_chars_linha = 35`. O Content Bible v3.4 define **66 chars** máx total e **33 por linha**.

### Correção — parte 1: INSERT seed (para novos deploys)

```python
# ANTES (linha 297):
70, 35, 43, 100, 1080, 1920,

# DEPOIS:
66, 33, 43, 100, 1080, 1920,
```

### Correção — parte 2: backfill para banco existente

Adicionar após o INSERT do RC:

```python
conn.execute(text("""
    UPDATE editor_perfis SET
        overlay_max_chars = 66,
        overlay_max_chars_linha = 33
    WHERE sigla = 'RC' AND overlay_max_chars = 70
"""))
logger.info("Migration: backfill overlay_max_chars RC = 66/33 OK")
```

### Critério de "feito"
- Perfil RC no banco tem `overlay_max_chars = 66`, `overlay_max_chars_linha = 33`

---

## P4 — Corrigir fallback inconsistente de overlay_interval_secs

Dois arquivos com fallbacks diferentes para quando `brand_config` não tem o campo.

### P4a — overlay_prompt.py

**Arquivo:** `app-redator/backend/prompts/overlay_prompt.py`
**Linha:** 48

```python
# ANTES:
interval_secs = (brand_config or {}).get("overlay_interval_secs", 15)

# DEPOIS:
interval_secs = (brand_config or {}).get("overlay_interval_secs", 6)
```

### P4b — UI admin (page.tsx)

**Arquivo:** `app-portal/app/(app)/admin/marcas/[id]/page.tsx`
**Linha:** 592

```tsx
// ANTES:
value={formData.overlay_interval_secs || 15}

// DEPOIS:
value={formData.overlay_interval_secs ?? 6}
```

Nota: usar `??` (nullish coalescing) em vez de `||` para não substituir o valor `6` (que é falsy-equivalente em JS — na verdade 6 é truthy, mas o `??` é mais correto semanticamente pois só substitui null/undefined, não 0).

### Critério de "feito"
- Ambos os fallbacks usam 6 como default
- UI admin exibe o valor correto do banco sem substituir por 15

---

## P6 — Aumentar fontsize lyrics e tradução de 32 → 40px no BO

**Arquivo:** `app-editor/backend/app/main.py`
**Linhas:** 105–128 (definição de `lyrics_style` e `traducao_style`)

### Problema
Lyrics (amarelo) e tradução (branco) estão em 32px, visualmente pequenos em dispositivos móveis. Confirmado com print de vídeo real.

### Correção — parte 1: variáveis do seed

```python
# lyrics_style (linha ~107):
# ANTES:
"fontsize": 32,
# DEPOIS:
"fontsize": 40,

# traducao_style (linha ~119):
# ANTES:
"fontsize": 32,
# DEPOIS:
"fontsize": 40,
```

### Correção — parte 2: backfill protegido pelo P1

Com P1 corrigido, o UPDATE incondicional deixa de existir. O novo UPDATE (com guarda `font_name != 'TeX Gyre Schola'`) não vai rodar para bancos já migrados.

Portanto, é necessário um backfill específico para atualizar o fontsize no banco existente:

```python
conn.execute(text("""
    UPDATE editor_perfis SET
        lyrics_style = jsonb_set(lyrics_style, '{fontsize}', '40'),
        traducao_style = jsonb_set(traducao_style, '{fontsize}', '40')
    WHERE sigla = 'BO'
      AND (lyrics_style->>'fontsize')::int < 40
"""))
logger.info("Migration: backfill lyrics/traducao fontsize BO = 40px OK")
```

### Critério de "feito"
- `lyrics_style.fontsize = 40` e `traducao_style.fontsize = 40` no banco para o BO
- Vídeos futuros renderizam lyrics/tradução em 40px

---

## P7 — Corrigir ESTILOS_PADRAO no admin_perfil.py

**Arquivo:** `app-editor/backend/app/routes/admin_perfil.py`
**Linhas:** 34–53

### Problema
`ESTILOS_PADRAO` usa "Playfair Display" com tamanhos que não correspondem a nenhum perfil real (overlay 63px, lyrics 45px, tradução 43px). Usado apenas ao criar novos perfis sem estilo definido.

### Correção

```python
ESTILOS_PADRAO = {
    "overlay": {
        "fontname": "TeX Gyre Schola", "fontsize": 44,
        "primarycolor": "#FFFFFF", "outlinecolor": "#000000",
        "outline": 0, "shadow": 0, "alignment": 2, "marginv": 1296,
        "bold": True, "italic": True,
    },
    "lyrics": {
        "fontname": "TeX Gyre Schola", "fontsize": 40,
        "primarycolor": "#E4F042", "outlinecolor": "#000000",
        "outline": 0, "shadow": 0, "alignment": 2, "marginv": 573,
        "bold": True, "italic": True,
    },
    "traducao": {
        "fontname": "TeX Gyre Schola", "fontsize": 40,
        "primarycolor": "#FFFFFF", "outlinecolor": "#000000",
        "outline": 0, "shadow": 0, "alignment": 8, "marginv": 1353,
        "bold": True, "italic": True,
    },
}
```

### Critério de "feito"
- `ESTILOS_PADRAO` reflete valores realistas baseados no BO atual
- Novos perfis criados pela UI admin começam com valores razoáveis

---

## P8 — Esconder tracks lyrics/tradução no preview do RC

**Arquivo:** `app-portal/components/admin/brand-preview.tsx`
**Linhas:** 115–127

### Problema
O preview exibe as tracks de lyrics e tradução com texto placeholder para todos os perfis, incluindo o RC. O RC é canal instrumental — 1 track apenas (overlay).

### Correção

O componente `BrandPreview` recebe `perfil` como prop. Adicionar verificação de `sigla`:

```tsx
{/* Lyrics Track — ocultar para perfis sem lyrics (RC) */}
{perfil.lyrics_style && perfil.sigla !== 'RC' && (
    <div style={getStyle(perfil.lyrics_style as StyleConfig)}>
        {(perfil.lyrics_style as any).text || "Lírica Principal (Lyrics)"}
    </div>
)}

{/* Tradução Track — ocultar para perfis sem lyrics (RC) */}
{perfil.traducao_style && perfil.sigla !== 'RC' && (
    <div style={getStyle(perfil.traducao_style as StyleConfig)}>
        {(perfil.traducao_style as any).text || "Tradução Acompanhamento"}
    </div>
)}
```

### Critério de "feito"
- Preview do RC mostra apenas a track de overlay
- Preview do BO continua mostrando as 3 tracks normalmente

---

## Arquivos alterados (resumo)

| Arquivo | Correções |
|---|---|
| `app-editor/backend/app/main.py` | P1, P2, P3, P6 |
| `app-redator/backend/prompts/overlay_prompt.py` | P4a |
| `app-portal/app/(app)/admin/marcas/[id]/page.tsx` | P4b |
| `app-editor/backend/app/routes/admin_perfil.py` | P7 |
| `app-portal/components/admin/brand-preview.tsx` | P8 |

---

## O que NÃO entra neste SPEC

- P5 (overlay_interval_secs na UI): **já implementado** — campo existe em `page.tsx` linha 590
- Workflow RC dentro da plataforma: documentado em PRD-008, escopo separado
- Aumentar fontsize do overlay (44/46px): tamanho validado como correto no print de produção
