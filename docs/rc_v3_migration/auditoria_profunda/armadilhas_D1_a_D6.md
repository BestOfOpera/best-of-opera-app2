# Frente D — Teste das 6 armadilhas

## D1 — Alucinação de path:linha

**Teste:** para os 15 findings da Frente B, `sed -n '<linha>p' <path>` retornou conteúdo coerente.

**Resultado:** 15/15 linhas citadas têm código que bate com a descrição. Zero alucinação.

**Veredito:** ✅ OK (limite de bloqueador: >1 alucinação)

---

## D2 — Severidade inflada

**Teste:** checklist 4/4 (editorial × produção × silencioso × persistente) para 9 findings marcados CRÍTICA na amostra (R1, R2, R3, R7, P1-Trans, Ed-MIG1, P1-Ed5) + 2 tratados como CRÍTICOS no Sprint 1 (R4, R5).

**Resultado:** 
- R1, P1-Ed5 têm log warning (não silencioso absoluto) → 3.5/4. CRÍTICA defensável pelo Princípio 1 estrito (warning ≠ alerta estruturado).
- R4/R5 são ALTA na tabela mas PROMPT 9 os caracteriza como "CRÍTICOS" no Sprint 1. Isso é priorização de execução (timing fácil de corrigir), não inflação do relatório. Nota: PROMPT 9 §2.3 tabela diz "PROMPT 9 chama os 7 de 'CRÍTICOS'; está desalinhado com o próprio relatório" — essa é a falha do PROMPT 9, não do relatório auditado.
- Demais: severidade coerente com mecanismo e princípio.

**Veredito:** ✅ OK (limite: >2 inflações)

---

## D3 — Severidade subestimada (pior que inflação)

**Teste:** checklist 4/4 para 3 ALTAS + 3 MÉDIAS da amostra (P1-Doc, P2-PathA-1, P3-Prob, P1-UI1, C1, T9-spam).

**Análise específica C1** (prioridade alta per PROMPT 9): `s[:200]` em download.py:117.
- Conteúdo afetado: nome de arquivo → NÃO é editorial (filename é metadata, não conteúdo)
- Protetor real: R2/S3 tem limite de 1024 bytes em key; filesystems têm limites por OS
- Severidade MÉDIA justa

**Análise P1-UI1:** defaults UI 50/25/40/60 criam cadeia completa com Ed-MIG1 (migration revert DB para 33). Mas UI só afeta perfis criados via nova interface; perfil existente não é tocado. MÉDIA defensável, mas se Sprint 1 quisesse ser conservador, poderia subir para ALTA. Não é subestimação clara.

**Demais:** T9-spam MÉDIA (VARCHAR(500) não editorial), P1-Doc ALTA/doc (categoria especial), P2-PathA-1 ALTA (timing não conteúdo), P3-Prob ALTA (qualidade não perda).

**Veredito:** ✅ OK (limite: qualquer subestimação 4/4 marcada ALTA/MÉDIA)

---

## D4 — Finding óbvio omitido (6 testes)

### D4.1 — `client.messages.create` callsites vs R7

**Hipótese:** R7 declara "10 callsites LLM", mas pode haver mais.

**Grep:** `grep -rn "client.messages.create" --include="*.py" app-redator/`

Resultado: **7 matches** (6 reais + 1 docstring comentário na linha 660).

Classificação por tipo:
| Linha | Tipo | Status na remediação R7 (§2.7 E) |
|-------|------|-----------------------------------|
| 96 | wrapper `_call_claude` (linhas 84-107) | ❌ NÃO coberto |
| 171 | direto (metadata detection BO) | ❌ NÃO coberto |
| 237 | direto (metadata detection) | ❌ NÃO coberto |
| 337 | direto (detect_metadata_from_text_rc) | ❌ NÃO coberto |
| 358 | direto | ❌ NÃO coberto |
| 666 | wrapper `_call_claude_api_with_retry` | ✅ coberto |

**6 SDK callsites, apenas 1 coberto pela remediação declarada.**

Cada site retorna `message.content[0].text.strip()` sem check `stop_reason`. Veri‌ficados individualmente:
- Linha 96: `message = client.messages.create(**kwargs)` + `return message.content[0].text.strip()` (linha 97)
- Linha 171: `message = client.messages.create(model=MODEL, max_tokens=1024, ...)` + `raw = message.content[0].text.strip()` (linha 176)
- Linha 237: idem com max_tokens=1024 (linha 242)
- Linha 337: idem (linha 342)
- Linha 358: idem (linha 363)
- Linha 666: dentro de `_call_claude_api_with_retry` wrapper

**Impacto:** se operador aplica a remediação declarada em §2.7 E ("em _call_claude_api_with_retry"), apenas 1/6 SDK callsites recebe check `stop_reason`. 5 callsites continuam vulneráveis.

**Business-level invocations:**
- `_call_claude` wrapper (linha 84) é invocado 6× (generation.py:240 + claude_service.py:374/525/538/605/634)
- `_call_claude_json` é invocado 6× (claude_service.py:1152/1167/1217/1238/1258 + **translate_service.py:910**)
- Direct callsites: 4 (171, 237, 337, 358)

Total **16 invocações LLM efetivas**, não 10 como R7 declara.

⚠️ **D4.1 disparado — candidate bloqueador. Registrar B1.**

### D4.2 — Pydantic `Field(max_length=...)` oculto

**Grep:** `grep -rnE "Field\([^)]*max_length" --include="*.py"` em todos os apps backend.

**Resultado:** **0 matches.** Nenhum Pydantic Field com max_length em Optional/Union. Coerente com t10_pydantic_maxlength.txt (0 bytes).

**Veredito:** ✅ OK (zero omissão)

### D4.3 — Funções `_sanitize*/_clean*/_normalize*`

**Grep:** 6 funções encontradas (`funcs_suspeitas.txt` consistente):
- `_strip_json_fences` (claude_service.py:110) — limpa fences de JSON, não remove conteúdo editorial
- `_sanitize_post` (claude_service.py:574) — **remove linhas que batem com `_ENGAGEMENT_BAIT_PATTERNS` + separadores markdown**
- `_strip_markdown_preamble` (claude_service.py:611) — remove preâmbulo
- `_sanitize_rc` (claude_service.py:768) — **remove palavras estruturais (GANCHO|CORPO|CLÍMAX|...) via `re.sub`**
- `_sanitize_filename` (editor/pipeline.py:143) — filename
- `_normalize_categories` (curadoria/config.py:67) — dict manipulation

**Investigação específica:**

- `_sanitize_post` linhas 578-585: loop sobre linhas do post gerado, descarta linhas que batem com `_ENGAGEMENT_BAIT_PATTERNS`. Se padrão for muito amplo, conteúdo legítimo é removido silenciosamente. **Não está catalogado na tabela §4.2.**
- `_sanitize_rc` linhas 783-786: `re.sub(r'\b(GANCHO|CORPO|CLÍMAX|FECHAMENTO|CTA|CONSTRUÇÃO|DESENVOLVIMENTO)\b\s*', '', texto, flags=re.IGNORECASE)`. Remove palavras estruturais via regex. Se LLM usa "clímax" como substantivo legítimo (ex: "o clímax da ópera"), é removido. **Não está catalogado.**

**Severidade dos achados:** MÉDIA (sanitização intencional, edge case de palavras legítimas casando o padrão — baixa probabilidade mas real).

⚠️ **D4.3 disparado — candidato MENOR. Registrar R-audit-01 (não é bloqueador: ≤1 finding novo de severidade MÉDIA).**

### D4.4 — Validação `len(N_input) == len(N_output)` em tradução

**Grep:** em app-redator/backend/, nenhum match para padrão "assert len(x) == len(y)" em traduções.

**Análise:** a tradução `translate_service.py` produz lista de overlays traduzidos. Se LLM retorna N-1 overlays (por stop_reason==max_tokens ou erro), código aceita como completo sem aviso.

**Status no relatório:** R7 cobre este caso *indiretamente* via stop_reason check. Se o check for implementado corretamente em `_call_claude_api_with_retry`, translate_service.py:910 é coberto. Mas a validação estrutural `len(input) == len(output)` não é prescrita como defesa adicional.

**Veredito:** ✅ OK — coberto via R7 se remediação for ampla. Validação adicional seria defense-in-depth mas não é omissão óbvia.

### D4.5 — `export_service.py` ZIP metadata

**Grep:** em `app-redator/backend/services/export_service.py` há `zipfile.ZipFile(buffer, "w", ZIP_DEFLATED)`. 

**Análise manual:** não há truncagem aparente no path examinado (linha 77 é ZipFile construtor, linha 105 é parâmetro). Evidência `export_service_funcoes.txt` do PROMPT 8 existe — pressupõe que PROMPT 8 analisou.

**Veredito:** ✅ OK — sem omissão detectada

### D4.6 — R2 `object_key` / `put_object`

**Grep:** `shared/storage_service.py` linhas 201, 285, 304 — apenas `head_object`/`delete_object`. Não há truncagem em `put_object` ou geração de key.

**Cross-ref com R6:** relatório catalogou `storage_service.py:64` (`s[:200]` em nome pasta R2). Coerente.

**Veredito:** ✅ OK — sem omissão

### Resumo D4

| Teste | Resultado |
|-------|-----------|
| D4.1 callsites LLM | ⚠️ **BLOQUEADOR** — R7 cobre 1/6 SDK callsites |
| D4.2 Pydantic max_length | ✅ zero omissão |
| D4.3 _sanitize_* | ⚠️ MENOR — `_sanitize_post` remove linhas, `_sanitize_rc` remove palavras estruturais |
| D4.4 translation validation | ✅ coberto via R7 |
| D4.5 export ZIP | ✅ sem omissão |
| D4.6 R2 key | ✅ sem omissão |

**Findings novos descobertos pela auditoria:**
- **R-audit-01** (MÉDIA): `_sanitize_rc` em claude_service.py:783-786 remove via regex palavras estruturais (GANCHO|CORPO|CLÍMAX|etc.). Edge case: palavra legítima casa com padrão. Não catalogado.
- **R-audit-02** (MÉDIA/BAIXA): `_sanitize_post` em claude_service.py:578-585 descarta linhas inteiras que casem com `_ENGAGEMENT_BAIT_PATTERNS`. Dependente da especificidade dos padrões.

2 findings → **D4 bloqueador disparado** (threshold: >1).

Porém, ambos são severidade MÉDIA/BAIXA e **não alteram Sprint 1** (focado em críticos + R7). Operador deve considerar como melhorias não-Sprint-1.

**Veredito D4:** ⚠️ **REPROVADA (com qualificação)** — 2 findings novos detectados, ambos severidade MÉDIA. Bloqueador técnico per critério, mas impacto prático pequeno (não são críticos, Sprint 1 não é afetado).

---

## D5 — Cobertura de apps incompleta

**Contagem por app na tabela §4.2:**

| App | Findings | Superfície editorial |
|-----|----------|---------------------|
| redator-RC | 11 | Alta (pipeline principal RC) |
| editor | 9 | Alta (render + lyrics/tradução) |
| redator-BO | 4 | Média (pipeline BO) |
| redator-ambas | 5 (R7, P4-005, P4-007a/b/c) | Média (compartilhado) |
| portal | 2 | Baixa (UI defaults de config, não conteúdo) |
| shared | 1 | Baixa (só storage_service.py) |
| curadoria | 1 | Baixa (download.py filename) |
| redator-RC/BO | 1 (P4-005) | Compartilhado |
| **Total** | **33** | |

**Análise:** portal, shared e curadoria têm 1-2 findings. Checkpoint PROMPT 9: "app com ≤2 findings mas superfície bruta >30".

**Portal tem superfície BRUTA grande** (9 T1-TS + 11 T7 + 30 T8 = ~50 matches), mas maioria é *display visual* (line-clamp, truncate UX, slice display), não corte editorial persistente. A superfície editorial do portal é pequena (só config de perfil em admin/marcas/). Cobertura adequada.

**Curadoria e shared têm superfície bruta pequena** consistente com findings. Cobertura adequada.

**Veredito:** ✅ OK — nenhum app sub-analisado

---

## D6 — Remediação incoerente

**Teste:** cada finding da amostra — "remover" tem função protetora? "regenerar" tem caminho? "alertar" tem infra?

**Análise específica R7:**
- §2.7 E declara: "Implementar stop_reason check em _call_claude_api_with_retry"
- §4.7 declara: "após response = client.messages.create(...), verificar if response.stop_reason == max_tokens"

**Ambiguidade:** §2.7 aponta 1 função específica; §4.7 aponta padrão genérico. Se operador lê §2.7, patcha 1/6 sites. Se lê §4.7, patcha todos.

Em conjunto com D4.1: remediação "em _call_claude_api_with_retry" é **incoerente** — não cobre 5/6 SDK callsites que R7 lista no evidence file. Operador que aplique literalmente ficará com bug residual.

**Impacto prático:** Sprint 1 risk — patch parcial declarado como completo pode virar outro finding "R7 corrigido ≠ bug real resolvido" (armadilha 10 do CLAUDE.md: "nunca dizer corrigido sem confirmar output final mudou").

**Outras remediações da amostra:**
- R1 "(b) regenerar ou (c) alertar": aplicável
- R2 "(a) remover slice": aplicável (redundante se R1 corrige)
- R3 "idem R1+R2 + log mínimo": aplicável
- R4/R5 "trocar para min(6.0, ...)": trivial
- P1-Trans "remover hardcode 33 → usar default 38": trivial
- Ed-MIG1 "remover migration ou versionar": aplicável
- P1-Ed5 "remover; lyrics já vêm pré-formatadas": precisa verificar se REALMENTE lyrics vêm pré-formatadas (depende de upstream editor)
- P1-UI1 "puxar defaults do backend ou remover UI": aplicável
- C1 "erro se > 200": aplicável mas UX-quebrador (operador pode colar título longo legítimo)
- T9-spam "alertar operador em admin UI": aplicável

**Detectadas:**
1. **R7 — INCOERENTE** (crítica): remediação cobre 1/6 SDK callsites
2. Nenhuma outra remediação claramente inaplicável

**Veredito D6:** ⚠️ **REPROVADA** — 1 remediação claramente incoerente (R7). Threshold de bloqueador (>3) não atingido, **mas R7 específica é severa** (afeta Sprint 1 diretamente).

---

## Resumo Frente D

| Armadilha | Resultado |
|-----------|-----------|
| D1 Alucinação | ✅ OK |
| D2 Severidade inflada | ✅ OK |
| D3 Severidade subestimada | ✅ OK |
| D4 Finding omitido | ⚠️ **BLOQUEADOR** (2 findings novos MÉDIA + R7 escopo subdimensionado) |
| D5 Cobertura apps | ✅ OK |
| D6 Remediação incoerente | ⚠️ **BLOQUEADOR** (R7 cobre 1/6 sites) |

**Veredito final Frente D: ⚠️ REPROVADA**

Bloqueadores candidatos para relatório final:
- **B1 (crítico):** R7 remediação declarada em `_call_claude_api_with_retry` cobre apenas 1/6 SDK callsites de `client.messages.create` em claude_service.py. 5 callsites (linhas 96, 171, 237, 337, 358) não são cobertos. Operador que aplique a remediação literalmente terá bug residual.
- **B2 (menor):** R-audit-01 e R-audit-02 — `_sanitize_rc` e `_sanitize_post` têm remoções editoriais não catalogadas. Severidade MÉDIA, não afeta Sprint 1 mas deveria ser registrado.
