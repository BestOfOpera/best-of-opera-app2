# Frente E — Coerência macro

## E.1 — Sumário executivo bate com tabela consolidada?

### Sumário declarativo (linhas 15-18)
```
34 findings catalogados
19 CRÍTICOS
12 ALTOS
3 MÉDIOS
```

### Contagem real da tabela §4.2 (linhas 362-396)

Extração linha a linha + tabulação por severidade:

| ID | Severidade |
|----|-----------|
| R1, R2, R3, R7, P1-Trans | CRÍTICA |
| R4, R5 | ALTA |
| R6 | MÉDIA |
| P1-Doc | ALTA |
| Ed-MIG1, Ed-MIG2 | CRÍTICA |
| P1-Ed1, P1-Ed2 | ALTA |
| P1-Ed3, P1-Ed4, P1-Ed5, P1-Ed6 | CRÍTICA |
| P1-UI1, P1-UI2 | MÉDIA |
| P2-PathA-1 | ALTA |
| P2-PathA-2 | MÉDIA |
| P3-Prob | ALTA |
| P4-001, P4-005, P4-006a, P4-006b, P4-007a, P4-007b, P4-007c | ALTA |
| P4-008 | MÉDIA |
| BO-001 | CRÍTICA |
| C1 | MÉDIA |
| T9-spam | MÉDIA |

**Total: 33 rows**
- CRÍTICA: 12 (R1, R2, R3, R7, P1-Trans, Ed-MIG1, Ed-MIG2, P1-Ed3, P1-Ed4, P1-Ed5, P1-Ed6, BO-001)
- ALTA: 14 (R4, R5, P1-Doc, P1-Ed1, P1-Ed2, P2-PathA-1, P3-Prob, P4-001, P4-005, P4-006a, P4-006b, P4-007a, P4-007b, P4-007c)
- MÉDIA: 7 (R6, P1-UI1, P1-UI2, P2-PathA-2, P4-008, C1, T9-spam)

### Discrepância consolidada

| Métrica | Sumário declara | Tabela real | Delta |
|---------|------------------|-------------|-------|
| Total | 34 | 33 | -1 |
| CRÍTICAS | 19 | 12 | -7 |
| ALTAS | 12 | 14 | +2 |
| MÉDIAS | 3 | 7 | +4 |

**Discrepância severa. Operador que lê apenas o sumário vê 19 CRÍTICOS; operador que conta a tabela vê 12.** Impacto de planejamento: Sprint 1 dimensionado para "19 críticos" seria super-estimado em 58%.

**Veredito E.1:** ⚠️ **BLOQUEADOR CONFIRMADO**

---

## E.2 — Achado central "150-200 pontos" reproduzível?

### Declaração (linha 562)
"um projeto RC típico (1 overlay × 20 legendas × 7 traduções × post × automation × hooks) atravessa a ordem de **150-200 pontos de truncamento CRÍTICO/ALTO**"

### Cálculo reconstruído a partir de §6 (linhas 488-561)

| Caminho | Cortes por unidade | Unidades típicas | Total |
|---------|---------------------|------------------|-------|
| Overlay RC | 5 por legenda (R1, R2, R4, R5, R7-compartilhado) | 15-20 legendas | 60-100 |
| Overlay → Editor | 2 por render (P1-Ed3, P1-Ed4) | 1 render | 2 |
| Lyrics/Tradução no editor | 1 por evento (P1-Ed5 ou P1-Ed6) | 20 lyrics + 20 trad | 40 |
| Hooks (etapa 2) | 2 (P4-005, R7) | 1 invocação | 2 |
| Post RC (etapa 4) | 1 (R7) | 1 | 1 |
| Automation RC (etapa 5) | 3 (P4-001, P4-008, R7) | 1 | 3 |
| Tradução (etapa 6) × 7 idiomas | 4-6 (P4-007a/b/c, R7, R1+R2 ou R3) | 7 idiomas | 28-42 |
| Export | 0 (não investigado) | — | 0 |

**Soma para N=20 legendas + trad completa:**
100 + 2 + 40 + 2 + 1 + 3 + 35 = **183 pontos** ✓ dentro de 150-200

**Soma para N=15 legendas:**
75 + 2 + 30 + 2 + 1 + 3 + 35 = **148 pontos** ← ligeiramente abaixo de 150

**Soma para N=12 legendas:**
60 + 2 + 24 + 2 + 1 + 3 + 35 = **127 pontos** ← abaixo do range

**Conclusão:** "150-200" é realista para projeto típico de ~15-20 legendas com tradução completa. Abaixo desse tamanho, o número não se sustenta. Declaração é aproximadamente reprodutível mas depende de cenário (não é afirmação absoluta).

**Veredito E.2:** ✅ OK — reprodutível dentro de 10% para cenário típico declarado

---

## E.3 — "Fase 3 vs realidade" factual?

### Relatório §5 declara

| Patch | Estado | SHA citado |
|-------|--------|------------|
| P1 | PARCIAL (4+ superfícies remanescentes) | (90add64 merge) |
| P2 | sem achado | — |
| P3 | Funcional (14 consumidores) | — |
| P4 | Confirmado | (claude_service.py:1188-1193) |
| P5 | Confirmado | d8b6d27 |
| P6 | Confirmado | fd36f92 |

### Validação git

```
105491f fix(redator): limite de 38 chars por linha (v3.1 baseline) em 5 pontos
```

Commit 105491f é o P1. Mensagem: "Troca hardcode 33→38 em toda a cadeia RC - claude_service._enforce_line_breaks_rc: default 33→38; ... translate_service callsites (2 locais): 33→38 passados ... em 5 pontos."

**Relatório declara P1 parcial com 4+ superfícies remanescentes:**
- routers/translation.py:189 (hardcode 33) — ✓ confirmado Frente B
- translate_service.py:533 (docstring) — ✓ confirmado Frente B
- app-editor/ stack (main.py migrations + legendas.py) — ✓ confirmado Frente B
- portal UI defaults — ✓ confirmado Frente B

**105491f tocou "5 pontos"**, relatório achou **4+ superfícies remanescentes** = total ~9 pontos de P1 no codebase, patch original cobriu pouco mais que metade. **Declaração "P1 parcial" é factualmente correta.**

```
d8b6d27 fix(redator): blindagem audit_meta em regenerate-overlay-entry + TODO SPEC-009
fd36f92 fix(redator): filtro defensivo _is_audit_meta in build_rc_automation_prompt
```

P5 e P6 confirmados por SHA. Mensagens batem com declaração do relatório.

P4 (brand_config): commit 750ef6b "feat(redator): aplica D.3 — overlay v3.1 com fio dinâmico ... Assinatura: brand_config removido". Bate com relatório §5 P4.

**Veredito E.3:** ✅ OK — declarações factualmente corretas contra git

---

## E.4 — Priorização Sprint 1 justificável?

### Relatório §7 (linha 587)
"R1+R2+R3+R4+R5+R7+P1-Trans — ~20 linhas de código, risco baixo"

### Estimativa real de LOC (se remediação aplicada literalmente por path:linha)

| Finding | Linhas estimadas |
|---------|-------------------|
| R1 (refactor ou remover truncação) | 5 |
| R2 (remover linha 880) | 1 |
| R3 (idem R1+R2 em _enforce_line_breaks_bo) | 5 |
| R4 (min(7.0) → min(6.0)) | 1 |
| R5 (idem R4) | 1 |
| R7 (em _call_claude_api_with_retry) | 2-5 |
| P1-Trans (remover hardcode 33) | 1 |
| **Total se R7 corrigido em 1 site** | **~16-20** |

**"~20 linhas" é realista se R7 for patched apenas em `_call_claude_api_with_retry`.**

### Problema: R7 patch completo requer 6 SDK sites (Frente D)

Se R7 for corrigido em todos os 6 SDK callsites (linhas 96, 171, 237, 337, 358, 666):
- Por site: 2-5 linhas adicionais
- 6 sites × 2-5 = 12-30 linhas adicionais

**Total Sprint 1 corrigido:** ~28-50 linhas.

Ainda baixo risco, ainda Sprint 1-compatível, mas **não são ~20 linhas**.

### Sobre R4/R5 estarem no Sprint 1 apesar de serem ALTA (não CRÍTICA)

Defensável por duas razões:
1. Esforço trivial (2 linhas)
2. Regra editorial 4-6 é bem definida, sem ambiguidade

Não é inflação de severidade no Sprint 1 — é priorização pragmática de low-hanging fruit.

**Veredito E.4:** ✅ OK com **ressalva** — priorização é justificável, mas estimativa "~20 linhas" subestima em ~50% se R7 for corrigido em todos os sites.

---

## Veredito Frente E

| Check | Resultado |
|-------|-----------|
| E.1 Sumário bate com tabela | ⚠️ **BLOQUEADOR** |
| E.2 Achado #5 reprodutível | ✅ OK |
| E.3 "Fase 3 vs realidade" factual | ✅ OK |
| E.4 Sprint 1 justificável | ✅ OK (ressalva LOC) |

**⚠️ FRENTE E REPROVADA**

**Bloqueador E.1:** sumário declara 34 findings / 19 CRÍTICOS / 12 ALTOS / 3 MÉDIOS, mas tabela consolidada tem 33 findings / 12 CRÍTICOS / 14 ALTOS / 7 MÉDIOS. Operador que lê apenas o sumário recebe número super-estimado de CRÍTICOS (+58%). Integridade documental comprometida.
