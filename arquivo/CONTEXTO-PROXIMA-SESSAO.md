# Contexto — Próxima Sessão BLAST v4

**Data:** 2026-03-10
**Sessão anterior:** Prompts 2.5-B, 2.5-C, 2.5-D (concluídos via Agent Teams)

---

## Estado atual do BLAST v4

| Prompt | Status | O que foi feito |
|--------|--------|-----------------|
| Prompt 0 | ✅ | Definições Reels Classics preenchidas |
| Prompt 1 | ✅ | Multi-brand backend + re-render/re-tradução + testes |
| Prompt 2 | ✅ | Auth backend + Admin CRUD (Agent Teams) |
| Prompt 2.5-A | ✅ | Perfil: 5 campos novos + endpoint /redator-config + R2 prefix no pipeline |
| Prompt 2.5-B | ✅ | Redator multi-brand: load_brand_config + prompts + pipeline de geração |
| Prompt 2.5-C | ✅ | Dashboard + Reports: filtro por perfil_id em todos os endpoints |
| Prompt 2.5-D | ✅ | Curadoria R2 prefix + script de migração scripts/migrate_r2_to_brand_prefix.py |
| Prompt 1.5 | ✅ | Unificar Perfil: campos de curadoria + endpoint /curadoria-config + curadoria lê do editor |
| **Prompt 3** | ⬅️ **PRÓXIMO** | Frontend Admin + Stepper + Auth UI + Re-render (Antigravity) |
| Prompt 4 | ⏳ | Visual + Testes E2E (Antigravity) |
| Prompt 5 | ⏳ | Deploy + Seed (Claude Code) |

---

## Próximo passo: Prompt 3

O Prompt 1.5 foi concluído anteriormente. Todos os pré-requisitos do Prompt 3 estão prontos:
- Modelo Perfil unificado (editor + curadoria) ✅
- Endpoint `/api/internal/perfil/{slug}/curadoria-config` ✅
- Auth backend (JWT + roles) ✅
- Admin CRUD de perfis ✅
- Re-render/re-tradução individual ✅

**Executor:** Antigravity (Manager View — 2 agentes paralelos)
**Prompt já escrito em:** `/Users/administrator/BLAST-FASE2-MULTI-BRAND-v2.md` → seção "PROMPT 3"

---

## Revisões necessárias no Prompt 3 (antes de executar)

O Prompt 3 foi escrito ANTES dos prompts 2.5-x. Precisa ser atualizado com:

### 1. Campos novos do Perfil (adicionados no 2.5-A)
O modelo Perfil agora tem 5 campos extras que o Admin UI precisa mostrar:
- `identity_prompt_redator` (textarea) — versão do redator (distinta do identity_prompt do editor)
- `tom_de_voz_redator` (textarea) — versão do redator
- `hook_categories_redator` (JSON) — categorias de hook personalizadas por marca
- `logo_url` (input de URL) — logo da marca
- `font_name` (dropdown) — fonte padrão da marca

Esses campos devem aparecer na **Secao 1 — Identidade** do formulário de edição.

### 2. Campos de curadoria (serão adicionados pelo Prompt 1.5)
Após o 1.5, o Perfil terá: curadoria_categories, elite_hits, power_names,
scoring_weights, anti_spam_terms, playlist_id, etc.

O Prompt 3 precisa de uma **Secao 7 — Curadoria** no formulário de edição com:
- Tags/categorias de curadoria (editor JSON simplificado ou apenas readonly com link)
- elite_hits, power_names (textarea com lista, 1 por linha)
- scoring_weights (sliders numéricos ou JSON editor)
- anti_spam_terms (input texto)
- playlist_id (input texto)

**Recomendação:** Adicionar nota ao Agente 1 do Prompt 3:
> "O modelo Perfil tem campos de curadoria (curadoria_categories, elite_hits, etc.)
> adicionados pelo Prompt 1.5. Incluir Seção 7 — Curadoria no formulário. Para
> curadoria_categories, usar JSON textarea editável. Para listas simples (elite_hits,
> power_names), usar textarea 1 item por linha."

### 3. Seletor de marca na importação (Agente 2)
O Prompt 3 já menciona passar `?perfil_id=X` na importação.
O Redator (2.5-B) usa `brand_slug`, não `perfil_id`. Verificar qual o endpoint
de importação espera — provavelmente `perfil_id` do editor, não `brand_slug` do redator.

---

## Arquivos-chave para consulta

```
/Users/administrator/best-of-opera-app2/
├── app-editor/backend/app/
│   ├── models/perfil.py          — modelo Perfil com todos os campos
│   ├── models/usuario.py         — modelo Usuario (auth)
│   ├── routes/admin_perfil.py    — CRUD de perfis (inclui /redator-config e /curadoria-config após 1.5)
│   ├── routes/auth.py            — auth JWT
│   └── routes/pipeline.py        — pipeline multi-brand
├── app-redator/backend/
│   ├── config.py                 — load_brand_config() com cache 5min
│   └── routers/generation.py     — carrega brand_config e propaga
├── app-curadoria/backend/
│   ├── config.py                 — load_brand_config() (após 1.5: lê do editor)
│   └── routes/curadoria.py       — r2_prefix aplicado em todos os call sites
├── scripts/
│   └── migrate_r2_to_brand_prefix.py — script R2 (dry-run/execute/verify)
├── MEMORIA-VIVA.md               — histórico completo de decisões
└── BLAST-FASE2-MULTI-BRAND-v2.md — plano completo com todos os prompts
```

---

## Como iniciar a sessão

1. Cole o Prompt 1.5 do arquivo `BLAST-FASE2-MULTI-BRAND-v2.md` (seção "PROMPT 1.5")
2. Executor: Claude Code, sessão única
3. Pré-requisito confirmado: Prompts 1 e 2 estão concluídos
4. Após 1.5 concluído: revisar Prompt 3 com as atualizações listadas acima, depois colar no Antigravity

---

## Campos do Perfil (estado atual completo)

```python
# Identidade
identity_prompt, tom_de_voz, editorial_lang, hashtags_fixas, categorias_hook, escopo_conteudo
# Campos adicionados no 2.5-A:
identity_prompt_redator, tom_de_voz_redator, hook_categories_redator, logo_url, font_name

# Idiomas
idiomas_alvo, idioma_preview

# Estilos de legenda (JSON)
overlay_style, lyrics_style, traducao_style

# Limites
overlay_max_chars, overlay_max_chars_linha, lyrics_max_chars, traducao_max_chars

# Vídeo
video_width, video_height

# Curadoria (campos básicos já existem, campos completos virão no Prompt 1.5)
duracao_corte_min, duracao_corte_max

# Visual
cor_primaria, cor_secundaria

# Storage
r2_prefix, slug, sigla
```
