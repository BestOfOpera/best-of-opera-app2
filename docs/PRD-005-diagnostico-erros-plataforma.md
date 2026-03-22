# PRD-005 — Diagnóstico de Erros da Plataforma

**Data:** 22/03/2026
**Baseado em:** diagnóstico via 6 agentes paralelos (sessão 22/03)
**SPECs derivados:**
- `docs/SPEC-005a-guard-perfil-deteccao-idioma.md` — problemas #6 e #1 *(a criar)*
- `docs/SPEC-005b-prompts-brand-slug.md` — problema #5 *(a criar)*
- `docs/SPEC-005c-pipeline-transcricao.md` — problemas #3 e #2 *(a criar)*
- `docs/SPEC-005d-download-infra.md` — problema #4 *(a criar)*

---

## 1. O que foi pesquisado

Análise completa do monorepo via 6 agentes simultâneos, cada um investigando um problema reportado pelo usuário na plataforma em produção. Foram inspecionados `app-portal/`, `app-editor/backend/`, `app-redator/backend/`, `app-curadoria/backend/` e `shared/`.

---

## 2. Problemas confirmados (escopo deste ciclo)

### #1 — Detecção automática de idioma falha no import

- **Arquivo confirmado:** `app-editor/backend/app/routes/importar.py` linhas 27–54
- **Função:** `_detect_music_lang(proj, idiomas_alvo)`
- **Problema:** Não usa biblioteca de NLP. Funciona por inferência de exclusão: analisa traduções existentes no projeto do Redator e infere o idioma original pelo que está faltando. Só funciona quando exatamente 1 idioma está ausente.
- **Falha em:** projetos novos (sem traduções), projetos completos (todos os idiomas presentes), projetos sem campos `language` / `music_language` / `original_language`
- **Resposta:** HTTP 422 com `idioma_necessario: true` → frontend exibe toast e mantém modal aberta
- **Frontend:** `app-portal/components/editor/editing-queue.tsx` linhas 173–205 (handleImportar) e 325–544 (modal)

---

### #2 — Vídeo não encontrado no R2 (página do projeto / Validar Letra)

- **Arquivo confirmado:** `app-editor/backend/app/routes/pipeline.py` linhas 248–472 (`_download_task`)
- **Problema:** O editor reconstrói a key R2 localmente no PASSO C (`f"{prefix}/{base}/video/original.mp4"`) e só então chama a curadoria (PASSO D). Se a curadoria já salvou o vídeo com uma key diferente (ex: conflito de nome resolvido com sufixo de `video_id`), o PASSO C não encontra e cai na cadeia completa (cobalt → yt-dlp → erro).
- **Cadeia de fallback:** PASSO C (R2 local) → D (curadoria) → E (cobalt.tools) → F (yt-dlp) → erro + upload manual
- **Key construída por:** `shared/storage_service.py` linhas 55–118 (`sanitize_name` → `project_base` → `check_conflict`)
- **Frontend:** erro exibido na seção "Validar Letra" com botão "Enviar vídeo manualmente"
- **Nota:** `CLAUDE.md` define "curadoria é autoridade de vídeo — editor não re-baixa", mas o código ainda re-baixa quando a key não bate

---

### #3 — Timeout na transcrição (Validar Alinhamento)

- **Arquivo confirmado:** `app-portal/components/editor/validate-alignment.tsx` linhas 101–120
- **Arquivo backend:** `app-editor/backend/app/services/gemini.py` e `app-editor/backend/app/routes/pipeline.py` linhas 654–1004
- **Problema:** Descompasso crítico de timeouts. Frontend faz polling com timeout fixo de **8 minutos**. Backend pode levar legitimamente **até 60 minutos** com retries:
  - Upload áudio ao Gemini: 120s × 3 tentativas ≈ 6 min
  - Mapeamento estrutural: 300s × 3 tentativas ≈ 15 min
  - Transcrição guiada: 300s × 3 tentativas ≈ 15 min
  - Completação: 300s × 3 tentativas ≈ 15 min
- **Resultado:** frontend declara timeout enquanto backend ainda processa legitimamente
- **Campo disponível mas não usado:** `progresso_detalhe` (JSON no banco) registra passo atual — frontend não lê para mostrar progresso real

---

### #4 — Download falha ao preparar vídeo (curadoria)

- **Arquivo confirmado:** `app-curadoria/backend/services/download.py` linhas 70–222
- **Três causas identificadas:**
  1. **yt-dlp sem cookies:** Se `YOUTUBE_COOKIES` não está configurado e `/app/cookies.txt` não existe, roda sem autenticação → bot detection frequente do YouTube
  2. **COBALT_API_URL vazio:** Se não configurado, `_download_via_cobalt()` retorna `False` imediatamente (linha 114–117) — fallback desativado silenciosamente
  3. **Timeout frontend menor que backend:** Frontend mostra upload manual após 180s; cobalt.tools pode levar até 300s — risco de conflito de versão se usuário faz upload manual enquanto backend ainda processa
- **Frontend:** `app-portal/components/curadoria/video-detail-modal.tsx` linhas 67–141 — usa `alert()` nativo (UX pobre)
- **Config:** `app-curadoria/backend/config.py` linha 25 (`COBALT_API_URL`)

---

### #5 — Reels Classics usando prompts do Best of Opera (Export / geração de legendas)

- **Confirmado:** sim, ocorre em produção
- **Causa raiz — múltiplos fallbacks hardcoded para `"best-of-opera"` em toda a cadeia:**

  1. **4 endpoints de geração** — `app-redator/backend/routers/generation.py` linhas 62, 93, 112, 131:
     ```python
     brand_slug = getattr(project, 'brand_slug', None) or "best-of-opera"
     ```

  2. **Schema e banco** — `app-redator/backend/schemas.py` linhas 40, 101 e `app-redator/backend/models.py` linha 44:
     `brand_slug` com default `"best-of-opera"` — projeto criado sem brand_slug explícito vira Best of Opera

  3. **Frontend pode enviar `undefined`** — `app-portal/components/redator/new-project.tsx` linhas 59, 218:
     `selectedBrand?.slug` retorna `undefined` se `selectedBrand` for null; campo não é incluído no body → backend usa default

  4. **`load_brand_config()` com fallback hardcoded** — `app-redator/backend/config.py` linhas 32–69:
     Se editor offline, retorna config hardcoded do Best of Opera para qualquer brand_slug solicitado

  5. **Defaults nos prompts** — `app-redator/backend/prompts/overlay_prompt.py` linhas 48–86:
     Strings identitárias do Best of Opera hardcoded como fallback quando `brand_config` está incompleto

---

### #6 — Troca de perfil sem critério durante edição ativa

- **Arquivo confirmado:** `app-portal/lib/brand-context.tsx` linhas 1–28 e `app-portal/components/brand-selector.tsx` linha 107
- **Problema:** Perfil armazenado apenas em `useState` (sem localStorage). Dropdown executa `setSelectedBrand()` imediatamente sem guard ou confirmação.
- **Consequência:** `editing-queue.tsx` linha 122 dispara `useEffect` ao detectar mudança de `selectedBrand.id`, resetando lista de edições. Edição continua aberta na URL mas interpretada no contexto do novo perfil.
- **Sem validação:** nenhum dos componentes de edição (`overview.tsx`, `validate-lyrics.tsx`, `validate-alignment.tsx`, `conclusion.tsx`) verifica se `edicao.perfil_id === selectedBrand?.id`
- **Vetor do problema #5:** troca de perfil durante geração é o caminho mais provável para Reels Classics receber prompts do Best of Opera em runtime

---

## 3. Dependências e riscos

| Risco | Mitigação |
|---|---|
| #5 e #6 são interdependentes | Corrigir #6 (guard) antes ou junto com #5 (fallbacks) |
| `brand_slug` NULL em projetos existentes no banco | SELECT antes de tornar campo NOT NULL — documentar como BLOCKER se NULL |
| Aumentar timeout do frontend (#3) pode mascarar travamentos reais | Combinar com exibição de `progresso_detalhe` para distinguir "processando" de "travado" |
| Remoção dos fallbacks `or "best-of-opera"` (#5) pode quebrar projetos antigos | Migração de dados ou valor sentinela explícito antes de remover defaults |
| COBALT_API_URL vazio em produção (#4) | Verificar variável no Railway antes de qualquer fix de código |

---

## 4. O que NÃO está no escopo deste ciclo

- Refactor completo da cadeia de download (apenas correções cirúrgicas nos pontos identificados)
- Implementação de NLP para detecção de idioma (#1) — solução mínima: melhorar lógica de inferência
- Redesign do sistema de brand_context (apenas guard e persistência simples)
- Alterações em infraestrutura Railway

---

## 5. Estado do sistema antes deste ciclo

- 4 serviços Railway ativos: `portal`, `editor-backend`, `curadoria-backend`, `redator-backend`
- Problemas #4 e #5 confirmados ativos em produção
- `YOUTUBE_COOKIES` e `COBALT_API_URL` com status desconhecido — verificar em `dados-relevantes/`
- Último PRD/SPEC ativo: `PRD-004-reels-classics-visual.md` / `SPEC-004-reels-classics-visual.md`

---

## 6. Arquivos a ler na sessão de SPEC

1. `app-redator/backend/routers/generation.py` — linhas 55–140 (4 endpoints com fallback)
2. `app-redator/backend/config.py` — linhas 32–69 (`load_brand_config` e fallback)
3. `app-redator/backend/models.py` e `schemas.py` — confirmar default de `brand_slug`
4. `app-portal/components/brand-selector.tsx` — componente completo para adicionar guard
5. `app-portal/lib/brand-context.tsx` — adicionar persistência localStorage
6. `app-portal/components/editor/validate-alignment.tsx` — linhas 101–120 (timeout polling)
7. `app-editor/backend/app/routes/pipeline.py` — linhas 248–400 (PASSO C e D do `_download_task`)
8. `dados-relevantes/` — verificar status de `YOUTUBE_COOKIES` e `COBALT_API_URL` em produção
