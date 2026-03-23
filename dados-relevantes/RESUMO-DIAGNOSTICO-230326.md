# Resumo Diagnóstico — 23/03/2026

**Contexto:** Sessão de correção de bugs e diagnóstico de problemas da plataforma.
**PRD de referência:** `docs/PRD-005-diagnostico-erros-plataforma.md`

---

## 1. O que foi feito nesta sessão

### ✅ SPEC-005a — Guard de perfil + persistência (CONCLUÍDO, deploy feito)
- **Arquivo:** `app-portal/lib/brand-context.tsx`
  - Adicionado `useEffect` que lê `selectedBrandId` do `localStorage` na montagem
  - `setSelectedBrand` agora salva/remove do `localStorage` automaticamente
  - Expõe `savedBrandId` no contexto
- **Arquivo:** `app-portal/components/brand-selector.tsx`
  - Pré-seleciona perfil salvo ao carregar (em vez de sempre pegar o primeiro)
  - Adicionado `usePathname()` para detectar se está em página de edição
  - Dentro de `/editor/edicoes/[id]` → abre Dialog de confirmação antes de trocar
  - Fora de edição → troca imediata sem diálogo
- **Commit:** `55cf1f5` — deploy Railway concluído

### ✅ SPEC-005c — Modal de idioma automático no import (CONCLUÍDO, confirmado em produção)
- **Arquivo:** `app-portal/components/editor/editing-queue.tsx` (~linha 183)
- **Problema:** quando backend retorna HTTP 422 com `idioma_necessario: true`, o frontend só mostrava um toast que sumia. Modal de seleção nunca abria.
- **Fix:** no handler do erro 422, chamar `setModalIdioma({projectId, artist, work, category})` com dados do projeto encontrado em `projetosRedator`. Modal abre automaticamente.
- **Também:** renomeado `"Detectar automaticamente"` → `"Detectar automaticamente (se possível)"`
- **Commit:** `0993602` — deploy Railway concluído
- **✅ VERIFICADO:** fix confirmado funcionando — a mensagem "Idioma não detectado automaticamente. Selecione abaixo." + abertura automática do modal é o comportamento correto pós-fix.

### ✅ PRD-005 atualizado
- Problema #5 (prompts RC/BO) marcado como ✅ CORRIGIDO
- Problema #6 (guard de perfil) marcado como ✅ CORRIGIDO

---

## 2. Diagnóstico aprofundado realizado (sem implementação)

### Problema #1 — Detecção de idioma (causa raiz entendida, baixa prioridade)
- `_detect_music_lang()` em `app-editor/backend/app/routes/importar.py` linhas 27–54
- Tenta ler campos `language`, `music_language`, `original_language` do projeto Redator — **esses campos não existem no modelo `Project`** (`app-redator/backend/models.py`). O campo `language` existe apenas no modelo `Translation`.
- Fallback de inferência por exclusão só funciona quando projeto tem quase todas as traduções — falha em projetos novos
- Fix do frontend (SPEC-005c) mitiga o problema: modal abre automaticamente quando detecção falha
- **Risco de idioma errado:** cascata de problemas (letra errada, transcrição degradada, tradução invertida), mas a etapa "Validar Letra" é barreira de contenção — operador revisa antes de avançar. Erro é humano, não sistêmico.
- **Não há como corrigir `edicao.idioma` após o import** — única recuperação é "Limpar Edição" e reimportar.
- Correção estrutural pendente (escopo futuro, baixa prioridade): adicionar campo `music_language` ao modelo `Project` do Redator + campo no formulário de criação + `ALTER TABLE` manual no Railway. Editor não precisa de alteração (já lê `music_language` em `_detect_music_lang`).

### Problema #2 — Vídeo não encontrado no R2
- **Causa real:** não é divergência de key — é falha no download
- PASSO C reconstrói key localmente → se não achar no R2 → PASSO D chama curadoria
- PASSO D já funciona corretamente: curadoria retorna `r2_key` correto e editor salva no banco
- **Problema real:** PASSO D falha quando curadoria não consegue baixar o vídeo do YouTube
- Problemas #2 e #4 são **o mesmo problema**: falha no download

### Problema #3 — Timeout na transcrição ✅ RESOLVIDO (23/03/2026)
- Frontend tinha timeout fixo de 8 minutos; backend pode levar até ~60 minutos
- **Fix aplicado:**
  - `app-portal/components/editor/validate-alignment.tsx` linha 112: `8 * 60 * 1000` → `90 * 60 * 1000`
  - Adicionada exibição do passo atual na UI (upload_gemini, transcricao_cega, transcricao_guiada, completando)
- **Commit:** `93b1c1b` — deploy Railway concluído

### Problema #4 — Download falha na curadoria ✅ RESOLVIDO (23/03/2026)

**Causa raiz confirmada — duas camadas:**

**Camada 1 — yt-dlp:**
- YouTube exige **PO Token (Proof of Origin Token)** desde meados de 2024
- Sem ele, YouTube identifica como bot mesmo com cookies válidos
- Container já tinha Deno instalado para esse fim, mas o plugin nunca foi ativado
- **Fix aplicado (SPEC-005d):**
  - Substituído Deno por Node.js no Dockerfile (compatível com o plugin)
  - Adicionado `bgutil-ytdlp-pot-provider` ao `requirements.txt`
  - Adicionado `extractor_args: pot_from_server: bgutil` em `_get_ydl_opts()`
  - **Confirmado em produção:** primeiro vídeo baixou 51MB em ~7s e subiu para o R2 ✅

**Camada 2 — Cobalt (fallback):**
- API pública `api.cobalt.tools` exige autenticação — retorna `error.api.auth.jwt.missing`
- Cobalt self-hosted ainda pendente, mas agora é fallback opcional, não urgente
- Vídeos que falham no yt-dlp por motivos não relacionados a bot detection (copyright, indisponível, region lock) continuarão falhando — são casos isolados, não sistêmicos

---

## 3. Relatório enviado aos proprietários

Foi preparado e enviado via WhatsApp um relatório com:
- Problemas 1 e 2 (guard perfil + modal idioma): ✅ corrigidos sem custo
- Problema download (crítico, 46 vídeos/semana): solução Cobalt self-hosted ~$5-8/mês
- Problema timeout alinhamento: correção sem custo, ~3h trabalho
- Aguardando aprovação para implementar os dois pendentes

---

## 4. Estado dos SPECs do ciclo PRD-005

| SPEC | Problema | Status |
|---|---|---|
| SPEC-005a-guard-perfil.md | #6 guard de perfil | ✅ CONCLUÍDO |
| SPEC-005b-prompts-brand-slug.md | #5 prompts RC/BO | ✅ CONCLUÍDO (sessão anterior) |
| SPEC-005c-idioma-import.md | #1 modal idioma | ✅ CONCLUÍDO (confirmado em produção) |
| validate-alignment.tsx | #3 timeout alinhamento | ✅ CONCLUÍDO (23/03/2026) |
| SPEC-005d-po-token-ytdlp.md | #4 download / yt-dlp | ✅ CONCLUÍDO (confirmado em produção) |
| — | #2 vídeo R2 | ✅ Resolvido indiretamente pelo #4 |

---

## 5. Ciclo PRD-005 — CONCLUÍDO

Todos os 6 problemas do ciclo foram resolvidos em 22–23/03/2026.

**Única pendência de escopo futuro (baixa prioridade):**
- Detecção automática de idioma estrutural: adicionar campo `music_language` ao modelo `Project` do Redator + campo no formulário de criação + `ALTER TABLE` no Railway. Operação manual continua funcionando normalmente enquanto isso não for implementado.

---

## 6. Commits desta sessão

| Commit | O que fez |
|---|---|
| `55cf1f5` | Guard de perfil + localStorage (SPEC-005a) |
| `0993602` | Modal idioma automático (SPEC-005c) |
| `44a096b` | PO Token plugin + Node.js (SPEC-005d) |
| `379557d` | Dockerfile: Deno → Node.js |
| `284896a` | Log de falhas silenciosas do yt-dlp |
| `bb50ac9` | Limite de duração 15min → 30min |
| `93b1c1b` | Timeout transcrição 8min → 90min + passo atual na UI |
