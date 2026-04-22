# Relatório de Investigação Profunda — Limites, Timing, Line-Breaks, Truncamento Sistêmico

**Data de início:** 2026-04-22
**Branch de investigação:** `claude/investigacao-profunda-20260422-1730`
**Base:** `main @ 90add64` (merge RC v3/v3.1 migration — Fase 3 concluída)
**Escopo:** mapeamento read-only. Zero modificação em código de produção.
**Sessão:** PROMPT 8 em Claude Code, modo max effort / ultrathink.

---

## Sumário executivo

> Atualizado progressivamente conforme cada problema é concluído. Seção final consolidada após Problema 4.

**Status no momento do último commit:** Problemas 1 concluído. Problemas 2, 3, 4 pendentes.

**Findings pré-investigação (reconhecimento):** 6 pontos de truncamento CRÍTICO identificados antes da varredura sistemática (R1-R6, ver §1 e §4 quando redigido).

**Nota operacional sobre validação:** o projeto não tem suite de testes automatizada. Verificação das remediações na fase posterior (PROMPT 10) será manual — rerun de pipeline completo em projeto RC/BO teste com comparação de output.

---

## Problema 1 — Limite de caracteres por linha

### 1.1 Estado atual

O limite declarado oficialmente v3.1 é **38 chars/linha** (PT/EN base, DE/PL +5=43, FR/IT/ES +3=41). A migração P1 da Fase 3 alterou o parâmetro default de `_enforce_line_breaks_rc` de 33 para 38 em [app-redator/backend/services/claude_service.py:819](app-redator/backend/services/claude_service.py:819). **A migração foi parcial**: o caminho de geração RC ficou coerente, mas quatro superfícies independentes permanecem fora de sincronia — uma delas com `33` hardcoded em produção.

### 1.2 Inconsistências detectadas

Cruzamento completo entre prompt LLM (declarativo) e código pós-processador (imperativo) em [evidencias_profunda/problema_1_limite_chars/prompt_vs_codigo.md](docs/rc_v3_migration/evidencias_profunda/problema_1_limite_chars/prompt_vs_codigo.md). Resumo das inconsistências:

| # | Onde | Valor esperado | Valor real | Severidade |
|---|------|----------------|------------|------------|
| 1 | [app-redator/backend/routers/translation.py:189](app-redator/backend/routers/translation.py:189) — callsite regenerar tradução RC | 38 | **33 hardcoded** | **CRÍTICA** |
| 2 | [app-redator/backend/services/translate_service.py:533](app-redator/backend/services/translate_service.py:533) — docstring | "≤38 chars/linha" | "**≤33 chars/linha**" | ALTA (doc, mas confunde futuros patches) |
| 3 | [app-editor/backend/app/main.py:363-370](app-editor/backend/app/main.py:363) — migration startup | n/a (editor não deve limitar) | **UPDATE RC → 66/33** a cada startup | **CRÍTICA** |
| 4 | [app-editor/backend/app/main.py:737-740](app-editor/backend/app/main.py:737) — migration v8/v9 | n/a | **UPDATE RC → overlay_max_chars=99** (3×33) | **CRÍTICA** (duplicada com #3, sobrescreve em startup) |
| 5 | [app-editor/backend/app/services/legendas.py:49](app-editor/backend/app/services/legendas.py:49) — constante `OVERLAY_MAX_CHARS_LINHA` | n/a | **35** | ALTA (viola Princípio 2) |
| 6 | [app-editor/backend/app/models/perfil.py:35](app-editor/backend/app/models/perfil.py:35) — Column default | n/a | 35 | ALTA |
| 7 | [app-editor/backend/app/schemas.py:24](app-editor/backend/app/schemas.py:24) — Pydantic default | n/a | 35 | ALTA |
| 8 | [app-editor/backend/app/services/perfil_service.py:45](app-editor/backend/app/services/perfil_service.py:45) | n/a | 35 | ALTA |
| 9 | [app-portal/app/(app)/admin/marcas/nova/page.tsx:454](app-portal/app/(app)/admin/marcas/nova/page.tsx:454) — UI default criação marca | n/a | **25** | MÉDIA (UX inconsistente) |
| 10 | [app-portal/app/(app)/admin/marcas/[id]/page.tsx:622](app-portal/app/(app)/admin/marcas/[id]/page.tsx:622) — UI default edição | n/a | **25** | MÉDIA |

**Inconsistência-chave:** existem **DUAS migrations SQL conflitantes** rodando em startup do `app-editor` ([main.py:363](app-editor/backend/app/main.py:363) e [main.py:737](app-editor/backend/app/main.py:737)) que escrevem valores diferentes no mesmo registro de perfil RC:
- Migration 1 força `66/33` (Content Bible v3.4)
- Migration 2 força `overlay_max_chars=99` (3×33)

A segunda migration roda DEPOIS da primeira (estão em blocos `try` sequenciais), então o estado final é `overlay_max_chars=99, overlay_max_chars_linha=33`. **O valor 33 persiste no banco a cada deploy** — e qualquer lógica do editor que use `perfil.overlay_max_chars_linha` receberá 33, não 38.

### 1.3 Causa-raiz do limite antigo persistir em produção

O log `[RC LineBreak] Texto truncado: sobrou 'esquece....'` tem **dois vetores plausíveis**:

**Vetor A — Regenerar tradução RC com limite 33 hardcoded.** Callsite [translation.py:189](app-redator/backend/routers/translation.py:189):
```python
t_text = _enforce_line_breaks_rc(t_text, tipo, 33, lang=lang)
```
Este endpoint é chamado quando o operador regenera uma entrada traduzida. O prompt do LLM é gerado com limite 38, mas o pós-processador re-wrap a resposta em 33, criando corte quando o LLM gera linha de 35 chars obedecendo ao prompt.

**Vetor B — Mecanismo intrínseco de `_enforce_line_breaks_rc`.** Mesmo com limite 38, se o texto excede `max_linhas × 38` chars, o código descarta o resto em [claude_service.py:869-873](app-redator/backend/services/claude_service.py:869):
```python
if len(novas_linhas) >= max_linhas:
    resto = " ".join(palavras[idx:])
    _rc_logger.warning(f"[RC LineBreak] Texto truncado: sobrou '{resto[:50]}...'")
    truncado = True
    break
```
Aqui o log emite **literalmente** a string `[RC LineBreak] Texto truncado: sobrou '...'` — coincide exatamente com a evidência de produção. Este é o bug estrutural R1.

Segundo corte silencioso (sem log) em [claude_service.py:880](app-redator/backend/services/claude_service.py:880):
```python
novas_linhas = novas_linhas[:max_linhas]
```
Se o build principal termina ok mas por qualquer razão gera >max_linhas, este slice corta sem avisar (R2).

### 1.4 Mapa de localizações

Ver tabela completa em §1.2 + [callsites_enforce_line_breaks.txt](docs/rc_v3_migration/evidencias_profunda/problema_1_limite_chars/callsites_enforce_line_breaks.txt) (grep bruto) + [prompt_vs_codigo.md](docs/rc_v3_migration/evidencias_profunda/problema_1_limite_chars/prompt_vs_codigo.md) (análise de 27 pontos).

**Fontes de verdade conflitantes, por ordem de severidade:**

1. **Código redator RC (geração):** 38 ✓ (coerente após P1)
2. **Código redator RC (tradução regenerate):** 33 hardcoded — **REGRESSÃO**
3. **Editor stack inteiro:** 35 default (constantes, Column, schema) + 33 forçado por migration SQL + 99 total forçado por migration v8/v9
4. **UI admin portal:** 25 default inputs

### 1.5 Achado colateral — BO está pior que RC

`_enforce_line_breaks_bo` em [claude_service.py:890-929](app-redator/backend/services/claude_service.py:890) trunca em silêncio **sem log warning** ([claude_service.py:921](app-redator/backend/services/claude_service.py:921) `break` + [claude_service.py:928](app-redator/backend/services/claude_service.py:928) `novas_linhas[:max_linhas]`). Snippet anotado em [enforce_line_breaks_bo.snippet](docs/rc_v3_migration/evidencias_profunda/problema_1_limite_chars/enforce_line_breaks_bo.snippet).

Operador não descobrirá que conteúdo BO foi truncado exceto por comparação manual output-vs-entrada. **Severidade CRÍTICA — é o pior tipo de corte silencioso do pipeline.**

Callsites BO afetados:
- [app-redator/backend/routers/translation.py:191](app-redator/backend/routers/translation.py:191) — regenerar tradução BO
- [app-redator/backend/services/translate_service.py:563](app-redator/backend/services/translate_service.py:563) — fallback tradução Google BO quando texto > 70 chars
- [app-redator/backend/services/translate_service.py:1006](app-redator/backend/services/translate_service.py:1006) — Claude path BO quando texto > 70 chars

### 1.6 Achado colateral — Editor viola Princípio Editorial 2

[app-editor/backend/app/services/legendas.py](app-editor/backend/app/services/legendas.py) tem **5 funções** que analisam/truncam chars, em violação direta do princípio "Editor não faz análise de caracteres":

| Linha | Função | Comportamento |
|-------|--------|---------------|
| [109](app-editor/backend/app/services/legendas.py:109) | `quebrar_texto_overlay` | Quebra em 2 linhas balanceadas se `len > max_chars`. Não trunca. |
| [134](app-editor/backend/app/services/legendas.py:134) | `_formatar_texto_legenda` | Word-wrap. `linhas[:max_linhas]` silencioso na linha 164. |
| [169](app-editor/backend/app/services/legendas.py:169) | `_formatar_overlay` | Chama `_truncar_texto` em 4 pontos (lines 202, 210, 235, 237). Linha 210: `return texto[:max_por_linha - 1].rstrip() + "…"` (reticências unicode). |
| [241](app-editor/backend/app/services/legendas.py:241) | **`_truncar_texto`** | **Trunca explicitamente** com "..." no final. Nome da função anuncia a violação. |
| [315-325](app-editor/backend/app/services/legendas.py:315) | callsites de `_truncar_texto` via `perfil.overlay_max_chars_linha` ou constantes | leitura das configurações que, por virtude das migrations, são 33/99. |

Callsites críticos adicionais:
- [legendas.py:512](app-editor/backend/app/services/legendas.py:512) — `_formatar_overlay(texto, overlay_max_linha, pre_formatted=_pre_fmt)` — quando `pre_formatted=False`, overlay completo passa por `_truncar_texto`.
- [legendas.py:653](app-editor/backend/app/services/legendas.py:653) — **lyrics** truncadas por `_truncar_texto(texto, lyrics_max)` com log warning interno (mas operador não vê no UI).
- [legendas.py:670](app-editor/backend/app/services/legendas.py:670) — **tradução** truncada por `_truncar_texto(texto_trad, traducao_max)` com log warning interno.

**Mitigação parcial já existente:** [main.py:875-877](app-editor/backend/app/main.py:875) explicita que BO roda com flag `overlay_pre_formatted=True` precisamente para **pular** `_formatar_overlay` e evitar truncamento. O comentário reconhece: "_formatar_overlay() trunca linhas >35 chars com '...' via _truncar_texto()". Ou seja — o bug é **conhecido** e há workaround via flag, mas o código de truncamento permanece executável e pode atingir qualquer marca/fluxo que não tenha a flag setada.

**Arquivo de evidência adicional:** [verify_fix.py](app-editor/backend/tests/verify_fix.py) é um teste manual que valida `_truncar_texto` como **comportamento correto**. Isso precisa ser removido/ajustado na fase de execução.

### 1.7 Proposta de remediação (sem implementar)

Ordem sugerida, ativar cada um na sessão PROMPT 10:

| # | Ação | Arquivo:linha | Tipo |
|---|------|----------------|------|
| A | Remover hardcoded `33` em callsite regenerate tradução | [routers/translation.py:189](app-redator/backend/routers/translation.py:189) | Substituir por default (38) ou import de constante central |
| B | Atualizar docstring | [translate_service.py:533](app-redator/backend/services/translate_service.py:533) | "≤38 chars/linha" |
| C | **Eliminar truncamento** em `_enforce_line_breaks_rc:869-873` + `:880` | [claude_service.py:869-880](app-redator/backend/services/claude_service.py:869) | Converter em: (a) rejeitar+regenerar quando excede, ou (b) alertar operador com entrada original preservada. Nunca descartar. |
| D | **Eliminar truncamento** em `_enforce_line_breaks_bo:921, :928` | [claude_service.py:921-928](app-redator/backend/services/claude_service.py:921) | Idem C + adicionar log warning mínimo (atualmente não loga) |
| E | Remover migrations SQL conflitantes em startup editor | [main.py:363-370](app-editor/backend/app/main.py:363) + [main.py:737-740](app-editor/backend/app/main.py:737) | Backfill só para corrigir estado inicial é aceitável, mas não deve rodar a cada startup. Uma migration versionada deveria zerar a necessidade. |
| F | **Remover funções de análise de chars do editor** (violação Princípio 2) | [legendas.py:109, 134, 169, 241](app-editor/backend/app/services/legendas.py) + callsites | Editor deve consumir overlay pré-formatado pelo redator. Lyrics/traducao precisam de contrato explícito (pré-formatados ou não?). |
| G | Decidir política de `overlay_max_chars_linha` configurável por marca | [models/perfil.py:35](app-editor/backend/app/models/perfil.py:35), schemas, UI admin | Se política é "constante por versão editorial", remover do schema de perfil e UI. Se "configurável", centralizar em um ponto, não 8. |
| H | UI admin — remover defaults 25/50/40/60 inconsistentes | [app-portal/app/(app)/admin/marcas/nova/page.tsx:450-462](app-portal/app/(app)/admin/marcas/nova/page.tsx:450) + `[id]/page.tsx:618-630` | Se mantido, puxar default do backend via API. |
| I | Remover teste `verify_fix.py` ou ajustar para testar "não trunca" | [tests/verify_fix.py](app-editor/backend/tests/verify_fix.py) | Assertion atual valida comportamento que viola princípio. |

---

## Problema 2 — Timestamps / Durações

> Pendente. Será preenchido no próximo commit.

## Problema 3 — Quebra de linhas (qualidade)

> Pendente. Será preenchido no próximo commit.

## Problema 4 — Erradicação sistêmica de truncamento

> Pendente. Será preenchido no próximo commit.

---

## Metadados de investigação

> Preenchido ao final da sessão.
