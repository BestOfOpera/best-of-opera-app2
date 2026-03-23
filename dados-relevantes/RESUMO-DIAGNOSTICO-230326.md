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

### Problema #3 — Timeout na transcrição
- Frontend: timeout fixo de **8 minutos** (linha 112 de `validate-alignment.tsx`: `8 * 60 * 1000`)
- Backend: pode levar legitimamente **até ~51 minutos** (upload Gemini + mapeamento + guiada + completação)
- Campo `progresso_detalhe` já existe no banco, já é retornado pela API, atualizado em 8 pontos no backend — **frontend nunca lê nem exibe**
- **Fix:** aumentar timeout para `90 * 60 * 1000` + exibir `edicao.progresso_detalhe?.passo` na UI
- **Arquivo a modificar:** apenas `app-portal/components/editor/validate-alignment.tsx`
- **Sem custo de infraestrutura**
- **PENDENTE: aguardando aprovação dos proprietários**

### Problema #4 — Download falha na curadoria (CRÍTICO)
**Causa raiz confirmada — duas camadas:**

**Camada 1 — yt-dlp:**
- `YOUTUBE_COOKIES` está configurado corretamente no Railway (typo `YOU_TUBECOOKIES` foi corrigido em 13/03)
- Cookies têm validade futura (~2027) e formato correto
- **Porém:** desde meados de 2024 o YouTube exige **PO Token (Proof of Origin Token)** além dos cookies
- Sem o PO Token, YouTube identifica como bot e bloqueia mesmo com cookies válidos
- PO Token não é valor estático — expira e precisa ser renovado automaticamente via plugin (bgutil-ytdlp-pot-provider) que requer Node.js no container — complexidade alta

**Camada 2 — Cobalt (fallback):**
- `COBALT_API_URL` **NÃO existe** como variável no Railway no serviço `curadoria-backend`
- Porém: `config.py` linha 25 tem default: `COBALT_API_URL = os.getenv("COBALT_API_URL", "https://api.cobalt.tools")`
- Logo: cobalt público (`api.cobalt.tools`) está sendo tentado
- **Porém:** a API pública do cobalt agora exige autenticação (Cloudflare Turnstile/API key) — requisições sem auth são bloqueadas
- Resultado: yt-dlp falha → cobalt falha → operador faz upload manual

**Volume afetado:** 46 vídeos/semana entre BO e RC

**Solução recomendada:** Cobalt self-hosted no Railway
- Criar novo serviço Railway usando imagem Docker oficial do cobalt
- Adicionar `COBALT_API_URL` no `curadoria-backend` apontando para URL do novo serviço
- Nenhuma alteração de código necessária
- Custo estimado: ~$5-8/mês adicionais no Railway
- Tempo: ~4 horas de implementação
- **PENDENTE: aguardando aprovação dos proprietários**

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
| — | #3 timeout alinhamento | 🟡 PENDENTE APROVAÇÃO |
| — | #4 download / cobalt | 🔴 PENDENTE APROVAÇÃO |
| — | #2 vídeo R2 | ✅ Resolvido indiretamente pelo #4 |

---

## 5. Próximos passos (próxima sessão)

1. ✅ ~~Verificar se SPEC-005c (modal idioma) está funcionando em produção~~ — confirmado
2. **Prioridade atual:** implementar Cobalt self-hosted (problema #4 — aprovação recebida)
   - Cobalt self-hosted no Railway (problema #4)
   - Fix de timeout no alinhamento (problema #3)
3. **Após aprovação do Cobalt:**
   - Criar serviço Railway com imagem Docker do cobalt
   - Adicionar variável `COBALT_API_URL` no `curadoria-backend`
   - Testar com 2-3 vídeos reais
4. **Após aprovação do timeout:**
   - Editar `app-portal/components/editor/validate-alignment.tsx` linha 112: `8 * 60 * 1000` → `90 * 60 * 1000`
   - Adicionar exibição de `edicao.progresso_detalhe?.passo` na UI de loading
   - Deploy e verificar

---

## 6. Arquivos relevantes para próxima sessão

| Arquivo | Por quê |
|---|---|
| `app-portal/components/editor/validate-alignment.tsx` linha 112 | Timeout a corrigir |
| `app-curadoria/backend/services/download.py` | Download yt-dlp + cobalt |
| `app-curadoria/backend/config.py` linha 25 | COBALT_API_URL default |
| `app-editor/backend/app/routes/pipeline.py` linhas 324–397 | PASSOS C/D download |
| `dados-relevantes/sentry-access.md` | Token Sentry não estava em settings.json — verificar se foi configurado |
