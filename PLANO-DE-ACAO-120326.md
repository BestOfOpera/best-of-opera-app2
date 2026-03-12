# PLANO-DE-ACAO-120326
**Objetivo:** Melhorias no menu "Nova Marca" — backend + frontend

| # | Agente | Tarefa | Depende de | Status |
|---|--------|--------|------------|--------|
| 01 | CLAUDE CODE | Expor campos curadoria na API (PerfilDetalheOut) | — | [x] |
| 02 | CLAUDE CODE | Default idiomas_alvo = 7 idiomas para novas marcas | — | [x] |
| 03 | CLAUDE CODE | Endpoint GET /template-bo (valores BO como template) | — | [x] |
| 04 | CLAUDE CODE | Coluna font_file_r2_key + migration | — | [x] |
| 05 | CLAUDE CODE | Endpoint upload de fonte + font_service.py | 04 | [x] |
| 06 | CLAUDE CODE | Suporte a fonte customizada no render (FFmpeg fontsdir) | 05 | [x] |
| 07 | ANTIGRAVITY | Sincronizar interface TypeScript Perfil (corrigir 4+ nomes errados) | 01 | [x] |
| 08 | ANTIGRAVITY | Config Gerais — textos explicativos em todos os campos | 07 | [x] |
| 09 | ANTIGRAVITY | Nova seção "Motor da Marca (Curadoria)" com formulário visual | 07 | [x] |
| 10 | ANTIGRAVITY | Idiomas — default 7, chips visuais em vez de texto livre | 07 | [x] |
| 11 | ANTIGRAVITY | Prompts — renomear label, presets tom de voz, nota escopo | 07 | [x] |
| 12 | ANTIGRAVITY | Fonte da marca — UI de upload .ttf/.otf | 05, 07 | [x] |
| 13 | ANTIGRAVITY | Medidas gerais — campos de limites de caracteres | 07 | [x] |
| 14 | ANTIGRAVITY | Substituir JSONs por formulários visuais (3 tracks) | 07 | [x] |

---

## DETALHES

### 01 — CLAUDE CODE: Expor campos curadoria na API
**Contexto:** O backend tem todos os campos de curadoria no model Perfil, mas o schema `PerfilDetalheOut` não os declara. O Pydantic descarta silenciosamente os dados na resposta.
**Arquivos:** `app-editor/backend/app/routes/admin_perfil.py`
**Ação:** Adicionar ao `PerfilDetalheOut`: curadoria_categories, elite_hits, power_names, voice_keywords, institutional_channels, category_specialty, scoring_weights, curadoria_filters, anti_spam_terms, playlist_id
**Entrega:** `GET /api/v1/editor/admin/perfis/1` retorna todos os campos de curadoria no JSON

### 02 — CLAUDE CODE: Default idiomas_alvo = 7 idiomas
**Contexto:** Hoje o default é lista vazia. Deve ser os 7 idiomas do Redator: en, pt, es, de, fr, it, pl
**Arquivos:** `app-editor/backend/app/models/perfil.py`, `app-editor/backend/app/routes/admin_perfil.py`
**Ação:** Alterar default do column e aplicar default em `criar_perfil()` se não fornecido
**Entrega:** Criar perfil sem especificar idiomas → vem com os 7

### 03 — CLAUDE CODE: Endpoint GET /template-bo
**Contexto:** Frontend precisa dos valores do BO para pré-preencher formulário de nova marca (curadoria, prompts, estilos)
**Arquivos:** `app-editor/backend/app/routes/admin_perfil.py`
**Ação:** Novo endpoint `GET /admin/perfis/template-bo` que retorna todos os valores do perfil BO. Registrar ANTES das rotas `/{perfil_id}` para evitar conflito de path
**Entrega:** Endpoint acessível e retornando dados completos do BO

### 04 — CLAUDE CODE: Coluna font_file_r2_key + migration
**Contexto:** Para upload de fontes, precisamos saber onde o arquivo .ttf/.otf está no R2
**Arquivos:** `app-editor/backend/app/models/perfil.py`, `app-editor/backend/app/main.py`, `app-editor/backend/app/routes/admin_perfil.py`
**Ação:** Novo campo `font_file_r2_key = Column(String(200))` no model, ALTER TABLE migration, adicionar ao PerfilDetalheOut, resetar para None na duplicação
**Entrega:** Campo existe no banco e aparece na API

### 05 — CLAUDE CODE: Endpoint upload de fonte + font_service.py
**Contexto:** Usuário faz upload de .ttf/.otf, backend salva no R2 e extrai o nome da família da fonte
**Arquivos novos:** `app-editor/backend/app/services/font_service.py`
**Arquivos modificados:** `app-editor/backend/app/routes/admin_perfil.py`, `requirements.txt`
**Ação:**
- `font_service.py`: funções `extract_font_family(path)` (usa fonttools), `upload_font_to_r2(path, slug, filename)`, `ensure_font_local(r2_key)` (baixa do R2 para /tmp/custom-fonts/, copia para /usr/local/share/fonts/custom/, roda fc-cache)
- Endpoint `POST /{perfil_id}/upload-font`: aceita .ttf/.otf (max 10MB), extrai family name, faz upload pro R2, atualiza perfil.font_name e font_file_r2_key
- Adicionar `fonttools` ao requirements.txt
**Entrega:** Upload funciona, font_name é populado automaticamente, arquivo fica no R2

### 06 — CLAUDE CODE: Suporte a fonte customizada no render
**Contexto:** Ao renderizar vídeo de marca com fonte customizada, o FFmpeg precisa encontrar a fonte
**Arquivos:** `app-editor/backend/app/routes/pipeline.py`, `app-editor/backend/app/services/ffmpeg_service.py`
**Ação:**
- Em `_render_task`: se perfil tem font_file_r2_key, chamar `ensure_font_local()` antes do render
- Em `ffmpeg_service.py`: adicionar `fontsdir=/usr/local/share/fonts/custom` ao filtro ASS
**Entrega:** Vídeo renderizado com fonte customizada da marca

### 07-14 — ANTIGRAVITY (Frontend)
**Contexto completo:** Ver plano detalhado em `~/.claude/plans/idempotent-toasting-lovelace.md`
**Arquivos:** `app-portal/lib/api/editor.ts`, `app-portal/app/(app)/admin/marcas/nova/page.tsx`, `app-portal/app/(app)/admin/marcas/[id]/page.tsx`
**CRÍTICO (tarefa 07):** A interface TypeScript `Perfil` tem nomes errados vs backend: `tom_voz` → `tom_de_voz`, `duracao_min_sec` → `duracao_corte_min`, `hashtags` → `hashtags_fixas`, `idiomas_alvo` é string mas backend envia array. Isso causa perda silenciosa de dados ao salvar. DEVE ser corrigido PRIMEIRO.
