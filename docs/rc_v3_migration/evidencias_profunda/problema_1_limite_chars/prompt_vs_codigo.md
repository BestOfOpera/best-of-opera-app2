# Prompt LLM vs código pós-processador — cruzamento (Problema 1)

## Resumo

O LLM é instruído a usar **38 chars/linha como referência** e tratar o limite como "regra dura apenas na etapa de tradução". O código pós-processador tem múltiplas fontes de verdade conflitantes: 38 na geração, **33 hardcoded na tradução**, 35 no fluxo BO (e também no editor), mais UI admin com defaults 50/25 e backfill SQL que força 66/33 ou 99 nos perfis do editor a cada startup.

## Tabela de declaração por ponto

| # | Path:linha | O que declara | Valor | Coerência com v3.1 (38)? |
|---|------------|---------------|-------|---------------------------|
| 1 | `app-redator/backend/prompts/rc_overlay_prompt.py:400` | Texto do prompt LLM (constraints) | **38** chars como REFERÊNCIA, hard em tradução | ✓ |
| 2 | `app-redator/backend/prompts/rc_overlay_prompt.py:655` | Texto do prompt LLM (IMPORTANTE) | ~**38** chars referência | ✓ |
| 3 | `app-redator/backend/services/claude_service.py:819` | Default da função `_enforce_line_breaks_rc` | **38** | ✓ |
| 4 | `app-redator/backend/services/claude_service.py:822-823` | Docstring com margens por idioma | 38 base, DE/PL +5=43, FR/IT/ES +3=41, PT/EN 38 | ✓ |
| 5 | `app-redator/backend/services/claude_service.py:949` | Callsite `_process_overlay_rc` | usa default (38) | ✓ |
| 6 | `app-redator/backend/routers/generation.py:213` | Prompt de **regenerar** entrada | "Máximo **38** caracteres por linha" | ✓ |
| 7 | `app-redator/backend/routers/generation.py:251` | Callsite regenerar | usa default (38) | ✓ |
| 8 | **`app-redator/backend/routers/translation.py:189`** | Callsite **regenerar tradução RC** | **33** hardcoded | ✗ **REGRESSÃO** |
| 9 | `app-redator/backend/services/translate_service.py:533` | **Docstring** de `translate_overlay_json` | "RC: aplica re-wrap pós-tradução (≤**33** chars/linha)" | ✗ **documentação desatualizada** |
| 10 | `app-redator/backend/services/translate_service.py:559` | Callsite tradução Google RC | **38** explícito | ✓ |
| 11 | `app-redator/backend/services/translate_service.py:637` | `_OVERLAY_LINE_LIMIT` por idioma | PT/EN: **38** | ✓ |
| 12 | `app-redator/backend/services/translate_service.py:656-690, 802` | Prompt de tradução Claude (instrução) | 38 chars per line | ✓ |
| 13 | `app-redator/backend/services/translate_service.py:1004` | Callsite translation Claude path RC | **38** explícito | ✓ |
| 14 | `app-redator/backend/services/claude_service.py:890` | Default `_enforce_line_breaks_bo` | **35** (BO, distinto) | — (BO tem regra própria) |
| 15 | `app-redator/backend/routers/translation.py:191` | BO regenerate tradução | **35** | — (BO) |
| 16 | `app-redator/backend/services/translate_service.py:563, 1006` | BO fallback tradução | **35** | — (BO) |
| 17 | `app-redator/backend/prompts/hook_prompt.py:14,92` | Prompt hook BO (usa brand_config) | genérico, lê de bc | contextual |
| 18 | `app-redator/backend/prompts/overlay_prompt.py:104-105, 229-235` | Prompt overlay BO (genérico) | lê `overlay_max_chars_linha` do brand_config | contextual |
| 19 | **`app-editor/backend/app/services/legendas.py:49`** | Constante `OVERLAY_MAX_CHARS_LINHA` (editor) | **35** | ✗ (deveria ser irrelevante — editor não deve wrap) |
| 20 | `app-editor/backend/app/models/perfil.py:35` | SQLAlchemy `overlay_max_chars_linha` Column default | **35** | ✗ (idem) |
| 21 | `app-editor/backend/app/schemas.py:24` | Pydantic schema | **35** default | ✗ |
| 22 | `app-editor/backend/app/services/perfil_service.py:45, 54` | Service default | **35** | ✗ |
| 23 | **`app-editor/backend/app/main.py:363-370`** | Migration startup SQL | UPDATE perfis RC → **66/33** | ✗✗ **FORÇA RETROGRADE v3.4** |
| 24 | **`app-editor/backend/app/main.py:737-740`** | Migration v8/v9 startup SQL | UPDATE perfis RC → `overlay_max_chars=99` | ✗ (3×33 = 99, calcado em 33) |
| 25 | `app-editor/backend/app/main.py:60` | CREATE TABLE default `overlay_max_chars_linha INTEGER DEFAULT 35` | **35** | ✗ |
| 26 | **`app-portal/app/(app)/admin/marcas/nova/page.tsx:454`** | Input UI defaults novo perfil | **25** (!) | ✗ **valor completamente distinto** |
| 27 | **`app-portal/app/(app)/admin/marcas/[id]/page.tsx:622`** | Input UI edição perfil | **25** default | ✗ |

## Conclusões

### Geração RC (Etapa 3) — coerente
Prompt pede 38, código força 38, regenerate usa 38. Patch P1 cumpriu o papel neste caminho.

### Tradução RC (Etapa 6) — INCOERENTE
- `translate_service.py:559, 1004` aplicam 38 ✓
- **`translation.py:189` aplica 33 (hardcoded) ✗** — caminho de regenerar tradução específica foi esquecido pelo patch P1
- Docstring em `translate_service.py:533` ainda diz "≤33 chars/linha" — documentação desatualizada

### Editor de vídeo (app-editor) — CONFLITA ESTRUTURALMENTE
- Todas as defaults do editor (constantes, Column, schema, service) apontam para **35**
- Migration SQL **sobrescreve** os perfis de RC para **33** (na linha 367) ou **99 = 3×33** (na linha 738) a cada startup do app-editor. Existem DUAS migrations conflitantes que competem pelo mesmo registro.
- Editor tem funções `quebrar_texto_overlay`, `_formatar_overlay`, `_formatar_texto_legenda`, `_truncar_texto` que analisam e truncam chars — violação direta do Princípio Editorial 2 ("Editor não faz análise de caracteres").

### Portal admin UI — CONFLITA UX
- Inputs de `overlay_max_chars_linha` com **default visual 25** (`app-portal/app/(app)/admin/marcas/.../page.tsx:454,622`) — operador vê 25 e pode salvar qualquer número.
- Operador pode **reconfigurar o limite** por marca via UI. Isso é ortogonal à LEI editorial: o limite deveria ser constante v3.1 (38), não configurável por marca.

## Veredito

Patch P1 foi **parcial**. Migrou geração RC mas deixou 4 superfícies não tocadas:
1. Callsite hardcoded 33 em `routers/translation.py:189` (regenerate tradução)
2. Docstring desatualizada em `translate_service.py:533`
3. Stack editor inteiro (constantes, schema, migrations SQL) operando em 33/35/66/99
4. UI admin com defaults 25 e superfície de configuração por marca

O log `[RC LineBreak] Texto truncado: sobrou 'esquece....'` em produção provavelmente vem de:
- (a) Tradução RC cuja regeração passou em `translation.py:189` com limite 33 (verifica)
- (b) OU do mecanismo de truncamento intrínseco de `_enforce_line_breaks_rc:869-873` + `:880` aplicado mesmo com limite 38 quando texto excede 3 linhas × 38 = 114 chars
