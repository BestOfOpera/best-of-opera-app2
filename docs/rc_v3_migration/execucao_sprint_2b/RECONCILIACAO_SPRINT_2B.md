# Reconciliação path:linha — Sprint 2B (7 itens confirmados)

**Data:** 2026-04-23
**Branch:** `claude/execucao-sprint-2b-20260423-1537`
**Base:** `main @ 8c7dbe9`

## Legenda de status

- **INTACTO** — path:linha exatos da fonte original batem com código atual
- **DESLOCADO** — existe em linha diferente (Sprint 1/2A adicionou linhas acima)
- **TRANSFORMADO** — estrutura mudou mas problema persiste
- **RESOLVIDO** — sprint anterior já cobriu (registrar e remover do escopo)
- **NÃO ENCONTRADO** — investigar

## Tabela de reconciliação

| # | ID | Path:linha original (fonte) | Path:linha main atual | Status | Observação |
|---|---|---|---|---|---|
| 1 | OB-1 | `docs/rc_v3_migration/execucao_sprint_2a/RELATORIO_EXECUCAO_SPRINT_2A.md:148` | `docs/rc_v3_migration/execucao_sprint_2a/RELATORIO_EXECUCAO_SPRINT_2A.md:148` | **INTACTO** | Conteúdo atual confirmado: `"(decisão 4 operador)"` na frase sobre P1-Ed2 Opção A. Correção: trocar por `"(decisão 7 operador)"`. |
| 2 | R-audit-01 | `claude_service.py:783-786` (PROMPT 10B §1.3.1) | `claude_service.py:855-858` | **DESLOCADO** (+72 linhas) | Regex destrutivo preservado intacto. Função `_sanitize_rc` cobre linhas 840-876. `_rc_logger` disponível (linha 718). Sprint 1+2A adicionaram 72 linhas acima. |
| 3 | R6 | `shared/storage_service.py:64` | `shared/storage_service.py:60-64` (função `sanitize_name`) | **INTACTO** | `return s[:200] if s else 'unknown'` preservado. Função de 5 linhas simples. |
| 4 | P1-UI1 | `app-portal/app/(app)/admin/marcas/nova/page.tsx:450-462` | `app-portal/app/(app)/admin/marcas/nova/page.tsx:450-462` | **INTACTO** | Confirmado via leitura: 4 defaults hardcoded (50/25/40/60) nos mesmos números de linha. |
| 5 | P1-UI2 | `app-portal/app/(app)/admin/marcas/[id]/page.tsx:618-630` | `app-portal/app/(app)/admin/marcas/[id]/page.tsx:618-630` | **INTACTO** | Confirmado: 4 defaults hardcoded (50/25/40/60) nos mesmos números de linha. Arquivo tem um 5º campo em :635 (`overlay_interval_secs ?? 6`) que já usa `??` — fora do escopo P1-UI2. |
| 6 | P4-008 | `app-redator/backend/prompts/rc_automation_prompt.py:57` | `app-redator/backend/prompts/rc_automation_prompt.py:60` | **DESLOCADO** (+3 linhas) | `overlay_resumo = " \| ".join(overlay_temas[:5])` preservado. Sprint 2A P4-001 adicionou logger.warning acima (linhas 66-74). |
| 7 | C1 | `app-curadoria/backend/services/download.py:117` | `app-curadoria/backend/services/download.py:114-117` | **INTACTO** | Função `sanitize_filename` (nome difere de R6: `sanitize_name`). `return s[:200] if s else 'video'` preservado. |
| 8 | T9-spam | `app-editor/backend/app/main.py:77` | `app-editor/backend/app/main.py:77` | **INTACTO** | Schema `editor_perfis`: `anti_spam_terms VARCHAR(500) DEFAULT '...'` preservado exatamente. **Proibição §7:** não alterar schema. Patch deve ser app-level (ver plano de patch abaixo). |

## Agrupamentos propostos para commits

Ordem obrigatória de Fase 3 conforme §3.3:

| # | Commit | Finding(s) | Arquivos |
|---|---|---|---|
| 1 | `docs(sprint-2b): OB-1 corrige referência decisão 4→7` | OB-1 | `docs/rc_v3_migration/execucao_sprint_2a/RELATORIO_EXECUCAO_SPRINT_2A.md` |
| 2 | `fix(sprint-2b): R-audit-01 _rc_logger.warning em _sanitize_rc` | R-audit-01 | `app-redator/backend/services/claude_service.py` |
| 3 | `fix(sprint-2b): R6 logger.warning em sanitize_name (shared)` | R6 | `shared/storage_service.py` |
| 4 | `fix(sprint-2b): C1 logger.warning em sanitize_filename (curadoria)` | C1 | `app-curadoria/backend/services/download.py` |
| 5 | `fix(sprint-2b): P4-008 logger.warning em overlay_temas slice` | P4-008 | `app-redator/backend/prompts/rc_automation_prompt.py` |
| 6 | `fix(sprint-2b): P1-UI1+P1-UI2 explicitar defaults UI hardcoded` | P1-UI1, P1-UI2 | `app-portal/app/(app)/admin/marcas/nova/page.tsx`, `app-portal/app/(app)/admin/marcas/[id]/page.tsx` |
| 7 | `fix(sprint-2b): T9-spam validação app-level para anti_spam_terms` | T9-spam | a determinar (ver plano) |

**Ordem de aplicação:**
1. OB-1 primeiro (doc trivial, zero risco)
2. R-audit-01 (CRÍTICO, maior cobertura)
3. MÉDIAS Python (R6, C1, P4-008, T9-spam) — logger.warning antes de truncamento/slice
4. MÉDIAS UI (P1-UI1+P1-UI2) — único commit agrupado

Observação sobre **P3-Prob:** ver `REANALISE_P3_PROB.md` — sob default parcimônia, nenhuma regra entra em Fase 3 (todas JÁ RESOLVIDAS ou OBSOLETAS/DÉBITO).

## Plano detalhado por patch (para Fase 3)

### OB-1

Arquivo: `docs/rc_v3_migration/execucao_sprint_2a/RELATORIO_EXECUCAO_SPRINT_2A.md:148`

```diff
- - **Patch:** warning `[EDITOR Legenda Slice]` antes do slice silencioso `linhas = linhas[:max_linhas]`. Opção A aprovada (decisão 4 operador).
+ - **Patch:** warning `[EDITOR Legenda Slice]` antes do slice silencioso `linhas = linhas[:max_linhas]`. Opção A aprovada (decisão 7 operador).
```

Zero risco. 1 inserção / 1 remoção.

### R-audit-01

Arquivo: `app-redator/backend/services/claude_service.py:855-858`

Patch template:
```python
# Antes (código atual)
texto = re.sub(
    r'\b(GANCHO|CORPO|CLÍMAX|FECHAMENTO|CTA|CONSTRUÇÃO|DESENVOLVIMENTO)\b\s*',
    '', texto, flags=re.IGNORECASE
)

# Depois (patch proposto)
_marcadores = re.findall(
    r'\b(GANCHO|CORPO|CLÍMAX|FECHAMENTO|CTA|CONSTRUÇÃO|DESENVOLVIMENTO)\b',
    texto, flags=re.IGNORECASE
)
if _marcadores:
    _rc_logger.warning(
        f"[Sanitize RC Strip] Removendo {len(_marcadores)} marcadores estruturais: "
        f"{_marcadores}. Texto antes: '{texto[:80]}...'"
    )
texto = re.sub(
    r'\b(GANCHO|CORPO|CLÍMAX|FECHAMENTO|CTA|CONSTRUÇÃO|DESENVOLVIMENTO)\b\s*',
    '', texto, flags=re.IGNORECASE
)
```

Observação: `re.findall` deve usar os MESMOS flags do `re.sub` (`re.IGNORECASE`) para que contagem bata. Grep de validação pós-patch: `grep -c "\[Sanitize RC Strip\]" app-redator/backend/services/claude_service.py` ≥ 1.

### R6 (shared/storage_service.py:60-64)

Function `sanitize_name`:
```python
# Antes
def sanitize_name(s: str) -> str:
    """Remove caracteres problemáticos para uso como nome de pasta no R2/filesystem."""
    s = re.sub(r'[<>:"/\\|?*]', '', s)
    s = s.strip('. ')
    return s[:200] if s else 'unknown'

# Depois
def sanitize_name(s: str) -> str:
    """Remove caracteres problemáticos para uso como nome de pasta no R2/filesystem."""
    s = re.sub(r'[<>:"/\\|?*]', '', s)
    s = s.strip('. ')
    if len(s) > 200:
        logger.warning(
            f"[Shared Name Truncate] Nome excede 200 chars ({len(s)}): "
            f"'{s[:80]}...' — truncando conservadoramente"
        )
    return s[:200] if s else 'unknown'
```

Observação: verificar se `shared/storage_service.py` já tem `logger` module-level. Se não tem, adicionar import de logging + `logger = logging.getLogger(__name__)` no topo.

### C1 (app-curadoria/backend/services/download.py:114-117)

Function `sanitize_filename` (nome diferente de R6):
```python
# Antes
def sanitize_filename(s: str) -> str:
    s = re.sub(r'[<>:"/\\|?*]', '', s)
    s = s.strip('. ')
    return s[:200] if s else 'video'

# Depois
def sanitize_filename(s: str) -> str:
    s = re.sub(r'[<>:"/\\|?*]', '', s)
    s = s.strip('. ')
    if len(s) > 200:
        logger.warning(
            f"[Curadoria Filename Truncate] Filename excede 200 chars ({len(s)}): "
            f"'{s[:80]}...' — truncando"
        )
    return s[:200] if s else 'video'
```

### P4-008 (rc_automation_prompt.py:60)

Contexto: `overlay_resumo = " | ".join(overlay_temas[:5])` na função `build_rc_automation_prompt`. RC-específico.

```python
# Antes
overlay_resumo = " | ".join(overlay_temas[:5])

# Depois
if len(overlay_temas) > 5:
    logger.warning(
        f"[RC Automation Overlay Temas] Overlay tem {len(overlay_temas)} temas, "
        f"usando apenas primeiros 5 no prompt de automação ManyChat. "
        f"Temas descartados: {overlay_temas[5:]}"
    )
overlay_resumo = " | ".join(overlay_temas[:5])
```

Observação: verificar se arquivo tem `logger` definido. Provavelmente sim (Sprint 2A P4-001 adicionou `logger.warning` no mesmo arquivo — linha 73).

### P1-UI1 + P1-UI2 (TSX, 1 commit agrupado)

4 inputs em cada arquivo com pattern `value={formData.X || DEFAULT}`. Problema: defaults hardcoded divergem do backend, usuário vê 50 quando backend pode ter 70 (RC) ou outro valor por marca.

Estratégia mínima sem criar endpoint novo: adicionar `title` (tooltip HTML) indicando origem do valor:

```tsx
// Antes (nova/page.tsx:450, repete para as 4 linhas)
<Input type="number" value={formData.overlay_max_chars || 50} onChange={...} className="..." />

// Depois
<Input 
  type="number" 
  value={formData.overlay_max_chars || 50} 
  onChange={...} 
  title={formData.overlay_max_chars ? `Valor configurado: ${formData.overlay_max_chars}` : "Padrão UI: 50 (não persistido)"}
  className="..." 
/>
```

Preserva comportamento visual (fallback 50 continua aparecendo), mas tooltip explicita origem: **"Padrão UI: 50"** quando é fallback, ou **"Valor configurado: X"** quando veio do backend. Resolve o problema raiz sem adicionar endpoint.

### T9-spam (editor, app-level patch)

Proibição §7: **não alterar schema**. Schema `anti_spam_terms VARCHAR(500)` fica como está.

Investigação necessária em Fase 3: localizar endpoint que persiste `anti_spam_terms` (provavelmente `PUT /api/perfis/{id}` ou similar em `app-editor/backend`). Adicionar:
1. `logger.warning` quando valor recebido excede 500 chars (antes do DB rejeitar)
2. Resposta de erro apropriada OU truncar conservadoramente com log

Se não houver endpoint editável para esse campo atualmente (configuração hardcoded via migration), registrar como observação: "campo só é setado via migrations, não há caminho de input operador que possa exceder 500 chars — finding é defensivo para uso futuro".

Patch a decidir em Fase 3 com base na investigação.

## Validações pós-patch (por commit)

Cada commit de Fase 3 deve passar:

1. **Python:** `python -c "import ast; ast.parse(open('<path>').read())"` sem erro
2. **TSX:** verificação manual (não há type-check scheduled nesta branch); leitura visual do diff
3. **Grep positivo:** padrão novo adicionado `grep -c "<novo_prefix>" <path>` ≥ 1
4. **Grep negativo:** não introduziu regressão em padrões de Sprint 1/2A
5. **Assinatura preservada:** nenhuma função muda de assinatura em Sprint 2B (§2.2 proibição)
6. **BO filtragem:** `git diff main..HEAD <path>` não toca código `_bo` nem `bo/`
