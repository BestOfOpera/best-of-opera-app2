# Histórico Completo de Erros e Correções — App-Editor (Best of Opera)

**Gerado em:** 03 de março de 2026
**Projeto:** Best of Opera — App-Editor (APP3) + App-Redator (APP2)

---

## Fase 12 — Erros Reportados por Operador (03/03/2026)

### ERR-052 · Overlay renderizado diferente do aprovado (CRÍTICO)

- **Sintoma:** O texto de overlay exibido no vídeo final era diferente do texto aprovado — em casos onde `aplicar_corte` não havia rodado, o overlay saía vazio ou causava crash
- **Causa raiz:** `_render_task` lia `overlay.segmentos_reindexado` sem fallback. Quando esse campo era NULL, a expressão `overlay.segmentos_reindexado if overlay else []` retornava `None` em vez de `[]`, causando overlay vazio ou exceção silenciosa. O campo `segmentos_original` existia como fonte imutável mas não era usado como fallback
- **Arquivos corrigidos:** pipeline.py, importar.py, DECISIONS.md
- **Correção aplicada (03/03/2026):**
  - `_render_task`: fallback em cascata `segmentos_reindexado → segmentos_original → erro explícito "Reimporte o projeto"`
  - Log do texto exato do overlay antes de cada render por idioma
  - Erro por overlay ausente registrado como Render com status "erro" + mensagem legível
  - `aplicar_corte`: alerta de log se `normalizar_segmentos` alterar texto inesperadamente
  - `importar.py`: `redator_project_id` agora salvo corretamente na importação (era omitido)
  - `importar.py`: log do overlay congelado no momento da importação
  - `DECISIONS.md`: Decisão nº 11 documentando causa raiz e correção
- **Status: ✅ CORRIGIDO E DEPLOYADO**

### ERR-053 · Toggle de lyrics ausente — duplicata em músicas instrumentais

- **Sintoma:** Em músicas com texto mínimo repetitivo (ex: "Ave Maria"), a legenda aparecia em loop e a tradução duplicava o mesmo texto. Sem forma de desativar as tracks de lyrics/tradução
- **Causa:** Campo `sem_lyrics` não existia no modelo. Sistema sempre renderizava as 3 tracks de legenda independente do conteúdo
- **Arquivos corrigidos (8):** edicao.py, main.py, schemas.py (2 alterações), legendas.py, pipeline.py (2 alterações), editor.ts, conclusion.tsx
- **Correção aplicada (03/03/2026):**
  - Banco: campo `sem_lyrics Boolean DEFAULT FALSE` adicionado via migration automática no startup
  - Schemas: campo exposto em `EdicaoOut` e `EdicaoUpdate`
  - `gerar_ass()`: parâmetro `sem_lyrics=False` — quando True, retorna SSAFile com apenas a track de overlay
  - `_render_task`: lê `sem_lyrics_val` no Passo A e passa para `gerar_ass()`
  - Frontend: toggle "Sem legendas de transcrição" com tooltip, persistido via PATCH
- **Distinção preservada:**
  - `sem_lyrics=True` → overlay editorial permanece, lyrics + tradução omitidos
  - `sem_legendas=True` (campo pré-existente) → remove TODAS as legendas incluindo overlay
- **Status: ✅ CORRIGIDO E DEPLOYADO**

### ERR-054 · Última frase gerada pelo Redator em português

- **Sintoma:** Texto gerado pelo Claude no app-redator fechava com a última frase em português, mesmo em projetos configurados em outro idioma
- **Causa:** Instrução de idioma aparecia apenas no início do prompt; Claude relaxava a restrição ao final da geração. System prompt não reforçava o idioma. Sem validação pós-geração
- **Arquivos corrigidos:** hook_helper.py (novo), claude_service.py
- **Correção aplicada (03/03/2026):**
  - `hook_helper.py`: função `build_language_reinforcement(project)` gera bloco `ATENÇÃO FINAL` dinamicamente, aplicado no final dos 6 prompts (overlay, post, youtube + variantes `_with_custom`)
  - `hook_helper.py`: função `detect_hook_language(project)` com categorias predefinidas em PT e heurística para EN, DE, IT, FR, ES, PL
  - `claude_service.py`: `_call_claude()` aceita parâmetro `system`; todas as 3 funções `generate_*` passam system message explícita: "You must write ALL output exclusively in {idioma}. Never switch to Portuguese, even in the final sentence."
  - `claude_service.py`: `_check_language_leak()` detecta se última frase contém >= 3 palavras PT — loga ALERTA sem bloquear, para revisão manual
- **Status: ✅ CORRIGIDO E DEPLOYADO**
