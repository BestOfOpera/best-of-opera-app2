# PRD-010 — CTA Fixo por Marca, Idiomas Dinâmicos e Hooks Configuráveis

**Data:** 30/03/2026
**Sessão:** Diagnóstico de CTA ausente no overlay + análise de gaps restantes na separação multi-brand
**Status:** EM EXECUÇÃO
**Continuação de:** PRD-009 (isolamento de marcas)

---

## 1. Contexto

O PRD-009 resolveu o isolamento estrutural das marcas (fallbacks, pipeline configurável, UI). Este PRD trata dos **gaps restantes na geração de conteúdo** que foram identificados durante investigação do CTA ausente na tela "Aprovar Overlay" do Best of Opera.

### Problema original reportado
Na tela "Aprovar Overlay" do BO, o CTA ("Follow for more Best of Opera! 🎶") não aparece. As 6 legendas geradas são todas narrativas — nenhuma é CTA.

### Causa raiz
O CTA não é um texto gerado pelo Claude — é um texto **fixo por marca e por idioma**, conforme definido nos Brand Definition docs e Content Bibles. O sistema atual depende do Claude gerar o CTA como parte das legendas, o que é inconsistente (às vezes gera, às vezes não).

**Referências dos CTAs definidos nos documentos:**
- **BO** (Brand Definition v1.0, §8c): "Follow for more Best of Opera! 🎶" (traduzido por idioma)
- **RC** (Content Bible v3.4, §5.2): "Siga, o melhor da música clássica, diariamente no seu feed. ❤️" (7 traduções manuais definidas)

### Outros gaps identificados na sessão
Durante a investigação, foram mapeados mais 3 problemas que o PRD-009 não cobriu:
1. Tradução ignora `idiomas_alvo` do Perfil (hardcoded 7 idiomas)
2. Detecção de idioma ignora `editorial_lang` do Perfil (assume português sempre)
3. Hook categories hardcoded no código (não editáveis pelo admin)

---

## 2. Decisões tomadas com o usuário

| Decisão | Justificativa |
|---|---|
| CTA é fixo por marca, não gerado pelo Claude | Brand Definition e Content Bible definem CTAs exatos — consistência > criatividade |
| Operador preenche CTA em PT-BR no admin | Operadores falam português |
| Backend traduz automaticamente via Google Translate | Mesmo serviço já usado no pipeline de tradução |
| Traduções editáveis manualmente por idioma | Tradução automática pode ficar inadequada (ex: francês) |
| Traduções manuais protegidas de re-tradução | Flag `manual: true` impede sobrescrita |
| Idiomas do CTA são dinâmicos (lidos de `idiomas_alvo`) | Se adicionar idioma novo, CTA aparece automaticamente |
| Tarefas executadas uma por vez | Projeto tem histórico de desalinhamento ao alterar múltiplas coisas simultaneamente |
| Hook categories iguais para todas as marcas | Confirmado pelo usuário — são genéricas o suficiente para qualquer marca de música |
| Validação backend de campos obrigatórios é baixa prioridade | Operadores não usam API diretamente — risco mínimo |

---

## 3. Blocos de implementação

### BLOCO 1 — CTA fixo por marca (PRIORIDADE MÁXIMA)

**Objetivo:** CTA definido no Perfil da marca, injetado automaticamente como última legenda do overlay — sem depender do Claude.

**Modelo de dados — novo campo no Perfil:**

```python
# app-editor/backend/app/models/perfil.py
overlay_cta = Column(JSON, default=dict)
# Estrutura:
# {
#   "pt": {"text": "Siga, o melhor da música clássica...", "manual": true},
#   "en": {"text": "Follow for the best of classical...", "manual": false},
#   ...
# }
```

**Fluxo completo:**

1. **Admin (Perfil):** Nova seção "CTA do Overlay"
   - Campo de texto para CTA em PT-BR
   - Botão "Traduzir automaticamente" → chama Google Translate para cada idioma em `idiomas_alvo`
   - Lista de idiomas com traduções preenchidas, cada uma editável
   - Traduções editadas manualmente recebem flag `manual: true` e não são sobrescritas ao re-traduzir

2. **Backend (geração overlay):** `generate_overlay()` no `claude_service.py`
   - O prompt do Claude NÃO pede CTA — gera apenas gancho + corpo
   - Após geração, o sistema anexa o CTA como última legenda automaticamente
   - Timestamp do CTA calculado conforme duração do vídeo (~20% final, conforme Content Bible §1.5)

3. **Backend (tradução):** Quando traduz overlay para outros idiomas
   - Traduz as legendas narrativas normalmente via Google Translate
   - Substitui a última legenda (CTA) pelo CTA fixo do idioma alvo (do Perfil)
   - NÃO traduz o CTA via Google Translate neste momento — usa o texto já salvo no Perfil

4. **Frontend (Aprovar Overlay):** `approve-overlay.tsx`
   - CTA aparece como última legenda com indicação visual (label "CTA" ou cor diferente)
   - CTA NÃO é editável na aprovação (vem do Perfil, não do projeto)
   - Operador pode remover/reordenar legendas narrativas, mas CTA permanece fixo no final

5. **Backend (redator-config):** `perfil_service.py → build_redator_config()`
   - Incluir `overlay_cta` no payload do redator

**Arquivos a modificar:**

| Arquivo | Mudança |
|---|---|
| `app-editor/backend/app/models/perfil.py` | Novo campo `overlay_cta = Column(JSON, default=dict)` |
| `app-editor/backend/app/main.py` | Migration: adicionar coluna; seed BO e RC com CTAs existentes |
| `app-editor/backend/app/services/perfil_service.py` | Incluir `overlay_cta` no `build_redator_config()` |
| `app-editor/backend/app/routes/admin_perfil.py` | Endpoint para traduzir CTA via Google Translate; incluir campo nos schemas |
| `app-redator/backend/services/claude_service.py` | `generate_overlay()` — não pedir CTA ao Claude; anexar CTA fixo após geração |
| `app-redator/backend/prompts/overlay_prompt.py` | Remover instrução de CTA do prompt (regra 6); adicionar nota "NÃO gere CTA" |
| `app-portal/app/(app)/admin/marcas/[id]/page.tsx` | Nova seção "CTA do Overlay" com campo PT + lista de traduções + botão traduzir |
| `app-portal/app/(app)/admin/marcas/nova/page.tsx` | Mesma seção na criação de marca |
| `app-portal/components/redator/approve-overlay.tsx` | Exibir CTA com label visual; torná-lo não-editável |
| `app-portal/lib/api/editor.ts` | Adicionar `overlay_cta` no tipo `Perfil`; novo método para traduzir CTA |

---

### BLOCO 2 — Idiomas dinâmicos na tradução

**Objetivo:** O serviço de tradução respeitar `idiomas_alvo` do Perfil em vez do hardcoded `ALL_LANGUAGES`.

**Problema atual:**
- `app-redator/backend/services/translate_service.py` tem `ALL_LANGUAGES = ["en", "pt", "es", "de", "fr", "it", "pl"]` hardcoded
- Se uma marca precisa de apenas 3 idiomas, gera 7 traduções

**Solução:**
- `build_redator_config()` já expõe `idiomas_alvo` (verificar — se não, adicionar)
- O serviço de tradução deve receber `idiomas_alvo` da brand config e usar essa lista
- `ALL_LANGUAGES` removido ou transformado em fallback de último recurso

**Arquivos a modificar:**

| Arquivo | Mudança |
|---|---|
| `app-redator/backend/services/translate_service.py` | Receber `idiomas_alvo` como parâmetro; remover `ALL_LANGUAGES` hardcoded |
| `app-redator/backend/routers/generation.py` | Passar `idiomas_alvo` da brand config para o serviço de tradução |
| `app-editor/backend/app/services/perfil_service.py` | Verificar que `idiomas_alvo` está no `build_redator_config()` |

---

### BLOCO 3 — Detecção de idioma respeitar marca

**Objetivo:** `detect_hook_language()` usar `editorial_lang` do Perfil quando o operador usa categoria predefinida, em vez de assumir português sempre.

**Problema atual:**
- `hook_helper.py:33-34` — se o operador usa categoria predefinida, retorna `"português"` hardcoded
- Se uma marca opera em inglês e o operador escolhe "Curiosidade Sobre a Música", o overlay é gerado em português

**Solução:**
- `detect_hook_language()` recebe `brand_config` como parâmetro (já aceita, mas não usa)
- Quando categoria predefinida, usa `brand_config.get("editorial_lang", "português")` em vez de hardcoded
- Mapeamento de código de idioma para nome: `{"pt": "português", "en": "English", "de": "Deutsch", ...}`

**Arquivos a modificar:**

| Arquivo | Mudança |
|---|---|
| `app-redator/backend/prompts/hook_helper.py` | `detect_hook_language()` — usar `editorial_lang` da brand config |
| `app-redator/backend/services/claude_service.py` | Passar `brand_config` para `detect_hook_language()` onde ainda não passa |

---

### BLOCO 4 — Hook categories editáveis no admin

**Objetivo:** Mover as 10 categorias de hooks de hardcoded (`config.py`) para editáveis no admin, mantendo-as iguais para todas as marcas (configuração global, não por marca).

**Problema atual:**
- `config.py:60-208` tem `HOOK_CATEGORIES` hardcoded com 10 categorias e prompts em português
- Para alterar um prompt de categoria, precisa modificar código e fazer deploy
- Frontend `nova/page.tsx:20-32` também tem as categorias hardcoded

**Solução:**
- Criar tabela `hook_categories` no banco (ou JSON em configuração global)
- Admin tem seção "Categorias de Gancho" onde as 10 categorias são listadas e editáveis
- Backend expõe endpoint `/api/hook-categories` que retorna as categorias ativas
- Frontend consome desse endpoint em vez de hardcoded
- Seed popula as 10 categorias existentes como default
- `config.py` mantém as 10 como fallback caso o banco esteja vazio (retrocompatibilidade)

**Nota:** Essa tarefa é de menor prioridade. O hardcoded atual funciona — só impede edição sem deploy.

**Arquivos a modificar:**

| Arquivo | Mudança |
|---|---|
| `app-editor/backend/app/models/` | Nova tabela `hook_categories` ou campo JSON global |
| `app-editor/backend/app/main.py` | Seed das 10 categorias |
| `app-editor/backend/app/routes/admin_perfil.py` | CRUD de hook categories |
| `app-redator/backend/config.py` | `HOOK_CATEGORIES` vira fallback; carrega do banco via API |
| `app-redator/backend/prompts/hook_helper.py` | Carregar categorias do banco/API |
| `app-portal/app/(app)/admin/` | Nova página ou seção para editar categorias |
| `app-portal/components/redator/new-project.tsx` | Carregar categorias do API em vez de hardcoded |
| `app-portal/app/(app)/admin/marcas/nova/page.tsx` | Idem |

---

### BLOCO 5 — Pacote ZIP: incluir posts traduzidos

**Objetivo:** Ao gerar o pacote ZIP para download, incluir arquivos de post/legenda/metadados junto com os vídeos.

**Problema reportado:**
- O ZIP contém apenas os vídeos renderizados por idioma
- Os arquivos `post.txt`, `subtitles.srt` e `youtube.txt` não estão sendo incluídos
- O redator salva esses arquivos no R2 via `save_texts_to_r2()`, mas o `_pacote_task` pode não estar conseguindo buscá-los

**Investigação necessária:**
- Verificar se `save_texts_to_r2()` está salvando nos paths corretos
- Verificar se `_pacote_task` está buscando nos paths corretos (pode haver mismatch de `r2_prefix`)
- Verificar logs do pacote para erros silenciosos ao baixar metadados do R2

**Arquivos relevantes:**
- `app-redator/backend/services/export_service.py` — salva textos no R2
- `app-editor/backend/app/routes/pipeline.py` — `_pacote_task` (~linha 2413)

---

## 4. Ordem de execução

| Ordem | Bloco | Descrição | Impacto |
|---|---|---|---|
| 1º | BLOCO 1 | CTA fixo por marca | ✅ Concluído (simplificado para texto PT-BR) |
| 2º | BLOCO 5 | Pacote ZIP com metadados | Operadores precisam dos posts traduzidos |
| 3º | BLOCO 2 | Idiomas dinâmicos | Tradução correta por marca |
| 4º | BLOCO 3 | Detecção de idioma | Geração no idioma certo |
| 5º | BLOCO 4 | Hooks no admin | Operabilidade sem deploy |

Cada bloco gera um SPEC próprio ou seção dentro de um SPEC único. Executar e validar um antes de iniciar o próximo.

---

## 5. Documentos de referência

| Documento | Localização |
|---|---|
| Brand Definition BO v1.0 | `BestOfOpera-BrandDefinition-v1.txt` (raiz) |
| Brand Definition RC v1.0 | `ReelsClassics-BrandDefinition-v1.txt` (raiz) |
| Content Bible RC v3.4 | `RC_ContentBible_v3_4-_2_ (2).txt` (raiz) |
| Manual do Operador RC | `RC_Manual_Operador.txt` (raiz) |
| Instrução de Projeto RC | `RC_InstrucaoProjeto_v3_4-_1_.txt` (raiz) |
| PRD-009 (isolamento de marcas) | `docs/PRD-009-isolamento-marcas-pipeline-configuravel.md` |

---

## 6. Estado atual dos campos do Perfil (verificado em 30/03/2026)

| Campo | BO | RC | Usado pelo sistema? |
|---|---|---|---|
| `identity_prompt_redator` | ✅ Preenchido | ✅ Preenchido | ✅ Sim — injetado no prompt |
| `tom_de_voz_redator` | ✅ Preenchido | ✅ Preenchido | ✅ Sim — injetado no prompt |
| `escopo_conteudo` | ✅ Preenchido | ✅ Preenchido | ✅ Sim — injetado no prompt |
| `custom_post_structure` | ⚠️ Verificar | ⚠️ Verificar | ✅ Sim — se vazio, usa fallback 5 seções |
| `overlay_cta` | ✅ Preenchido | ✅ Preenchido | ✅ Sim — texto PT-BR, injetado no overlay e traduzido junto |
| `hook_categories_redator` | ❌ NULL | ❌ NULL | ⚠️ Fallback para HOOK_CATEGORIES hardcoded |
| `idiomas_alvo` | ✅ 7 idiomas | ✅ 7 idiomas | ⚠️ Não consultado pela tradução |
| `editorial_lang` | ✅ "pt" | ✅ "pt" | ⚠️ Não consultado pelo hook_helper |
