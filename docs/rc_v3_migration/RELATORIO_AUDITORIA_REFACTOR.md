# Relatório de Auditoria Independente — Refactor `overlay-sentinel-restructure`

**Branch auditada:** `refactor/overlay-sentinel-restructure`
**Base:** `origin/main @ 90add64` (merge Fase 3)
**Commits auditados:** 7 (2c8daa0 → 57408c9), +560/-68 linhas, 22 arquivos
**Auditor:** Claude (sessão fresh, sem contexto da execução)
**Data:** 2026-04-22
**Branch de auditoria:** `claude/audit-overlay-refactor-6O5ph`
**Logs brutos:** `docs/rc_v3_migration/auditoria_logs/`

---

## Veredito final

### 🟡 REPROVADO COM 1 BLOQUEADOR FORMAL

Todos os 7 commits **individualmente OK**. Todas as validações de código (tipos, imports, grep global, smoke dos consumers, reconstituição do bug original, script SQL) **passam**. O refactor **resolve estruturalmente** a regressão visual do projeto #355 e é imune em ambos os cenários (projetos legados e projetos novos).

**O bloqueador é formal, não funcional:** o artefato `scripts/e2e_shape_compat.py` exigido pela decisão D3(a) do PROMPT 6B **não foi criado**. A cobertura funcional equivalente está distribuída nos 7 smokes per-commit e na reconstituição manual do bug que fiz nesta auditoria — mas o artefato explicitamente exigido pela decisão editorial não existe no repo.

Decisão operacional cabe ao operador: pedir à execução criar o E2E e re-auditar (rigor máximo), ou aceitar a ausência como divergência documentada de D3 dado que as outras validações cobrem equivalentemente o comportamento crítico.

---

## 1. Auditoria commit-por-commit

| # | SHA | Título | Arquivos | Veredito | Evidência |
|---|-----|--------|----------|----------|-----------|
| 1 | 2c8daa0 | refactor(db): adiciona coluna `overlay_audit` | models.py, main.py | ✅ OK | Padrão idempotente v13-v16 respeitado, tipo JSON nullable, D5 Translation intocado, smoke reproduzido (schema + idempotência 3x + roundtrip) |
| 2 | 73f5ebe | refactor(claude_service): `_process_overlay_rc` retorna tupla | claude_service.py | ✅ OK | Assinatura `tuple[list, dict]`, callsite desestrutura e persiste em ambos os campos, `audit or None` → NULL quando vazio, smoke reproduzido com 3 cases |
| 3 | 8f98eb7 | refactor(consumers): remove filtros em 9 pontos | 7 arquivos, 9 pontos | ✅ OK | Consumer #9 (`generation.py`) estruturalmente saneado — `raw_overlay` **completamente eliminado**, variável única `overlay`. Zero hits de `_is_audit_meta` e `raw_overlay` em Python. Smoke dos 4 consumers puros + source inspection dos outros 5 reproduzido |
| 4 | f0b8d1e | refactor(api): `ProjectOut` expõe `overlay_audit` | schemas.py | ✅ OK | Campo `Optional[dict] = None` em linha 116, `from_attributes=True` herda do ORM, `TranslationOut` não tocado (D5), ~10 endpoints que usam `response_model=ProjectOut` automaticamente expõem o campo. Smoke reproduzido com 3 cases |
| 5 | 93673d7 | refactor(portal): types TS + `approve-overlay.tsx` | redator.ts, approve-overlay.tsx, export-page.tsx | ✅ OK | Types `OverlayEntry`/`OverlayAudit`, função `sanitizeOverlay` com type predicate (sem `any`), 6 pontos de ingestão no approve-overlay usando sanitize, linha 250 com fallback `entry.text \|\| ""`. `tsc --noEmit` EXIT=0, lint -1 net. Exatamente 2 matches `_is_audit_meta` em redator.ts (comentário + predicate), ambos registrados |
| 6 | a5228e0 | refactor(editor): remove filtro morto | importar.py | ✅ OK | `segmentos_validos` list-comp removida, `segmentos` passa direto para `db.add(Overlay)`. Git blame confirma origem do filtro em `ef10797` (2026-04-09, pré-Fase 3) — era filtro editorial genuíno, não defesa contra sentinel. Grep `_is_audit_meta\|segmentos_validos` em `app-editor/` = 0 hits |
| 7 | 57408c9 | feat(db): SQL migração legados | migrate_overlay_sentinel.sql | ✅ OK | 5 SELECT + 1 UPDATE, `WHERE brand_slug = 'reels-classics'` estrito, **UPDATE não popula `overlay_audit`** (D4 respeitada), zero DROP/DELETE/ALTER/TRUNCATE, idempotente por design (EXISTS sentinel na WHERE). Parse sintático OK |

**Todos os 7 commits: OK individualmente.**

---

## 2. Verificações holísticas

| Verificação | Resultado | Detalhe |
|-------------|-----------|---------|
| Grep final absoluto `_is_audit_meta` | ✅ OK | Exatamente 2 matches, ambos em `app-portal/lib/api/redator.ts` (linha 16 comentário JSDoc, linha 23 type predicate do `sanitizeOverlay`). Ambos registrados em `NOTAS_EXECUCAO.md` como defesa transitória |
| Grep remanescentes `raw_overlay`, `audit_item`, `segmentos_validos` em código executável | ✅ OK | Zero hits — artefatos pré-refactor completamente removidos |
| E2E sintético `scripts/e2e_shape_compat.py` | 🔴 **FALHA** | **Arquivo não existe**. D3(a) declarada no NOTAS_EXECUCAO.md mas não implementada. **Ver Bloqueador 1 abaixo** |
| Bug original (projeto #355) reconstituído | ✅ OK | Reconstituição manual em Node.js: payload legado (com sentinel) filtrado por `sanitizeOverlay` → 2/3 itens; payload novo (sem sentinel) idempotente; linha 250 `(entry.text \|\| "").split("\n")` não lança TypeError em nenhum dos dois shapes. Log: `docs/rc_v3_migration/auditoria_logs/bug_original_reconstituicao.log` |
| Cruzamento NOTAS × código | 🟡 PASS com ressalva | D1 (tupla), D2 (JSON dict livre), D4 (SQL não popula overlay_audit), D5 (TranslationOut sem overlay_audit), D6 (9 consumers no commit 3) todos confirmados. **Ressalva:** declaração "zero infra de testes" é imprecisa — existe `app-editor/backend/tests/` com pytest + conftest + 2 arquivos de teste, mas não testa nenhum arquivo tocado pelo refactor (test_multi_brand.py, test_perfil_unificado.py). Em espírito correto para o escopo afetado |
| Decisões editoriais D1-D6 aplicadas | ✅ OK | Confirmadas via inspeção de código (não só via declaração em NOTAS) |

---

## 3. Validação ambiental compensatória

| Check | Resultado | Detalhe |
|-------|-----------|---------|
| `npx tsc --noEmit` (portal) | ✅ EXIT=0 | Zero erros TypeScript — types coerentes ponta-a-ponta (backend schema → TS type → componente) |
| `npm run lint` (portal) | ✅ 136 errors + 77 warnings | 1 erro a **menos** que baseline pré-refactor (removeu um `any` implícito em `sanitizeOverlay` via type predicate). Zero novos erros |
| `npm run build` (portal) | ⚠️ FALHA AMBIENTAL | Turbopack SSR + route collection + type-check passaram. Build final falha por `Failed to fetch 'Inter'/'Playfair Display' from Google Fonts` — sandbox sem egress HTTP. Idêntico ao reportado pela execução. **Não-bloqueador** (de infra, não de código) |
| Backend imports críticos | ✅ OK | `models`, `claude_service._process_overlay_rc/generate_overlay_rc/_validate_overlay_rc`, `srt_service.generate_srt`, `translate_service.*` (4 funções), `routers.projects/generation`, `prompts.rc_post_prompt/rc_automation_prompt`, `schemas.ProjectOut/TranslationOut` — **todos importam sem erro** |
| `git status` limpo | ✅ OK | Working tree clean na refactor branch. Apenas `docs/rc_v3_migration/auditoria_logs/` untracked (diretório criado por mim durante auditoria) |

---

## 4. Bloqueador formal

### Bloqueador 1 — `scripts/e2e_shape_compat.py` ausente (D3(a))

**Onde:** `scripts/` (não existe no repo em nenhuma branch)
**Evidência:**
```
$ ls /home/user/best-of-opera-app2/scripts/
configure-railway-r2.sh
gerar_relatorio_word.py
migrate_overlay_sentinel.sql
migrate_r2_to_brand_prefix.py
railway-env.sh
```

O NOTAS_EXECUCAO.md declara explicitamente em D3:
> "**D3 — Testes:** [...] Validação por: **(a) script E2E sintético `scripts/e2e_shape_compat.py`**, (b) smoke manual via Python REPL após cada commit backend, (c) `npx tsc --noEmit` + `npm run lint && npm run build` no portal, (d) staging Railway antes do merge."

A execução entregou (b) e (c) — 7 smokes per-commit + tsc/lint/build — mas **não entregou (a)**.

**Impacto funcional prático:** baixo. As validações equivalentes existem:
- 7 smokes per-commit cobrem cada componente individualmente
- Minha reconstituição manual do bug original em Node.js (nesta auditoria) prova imunidade ponta-a-ponta
- `tsc --noEmit EXIT=0` garante que os types propagam corretamente através de todos os boundaries

**Impacto formal:** alto. O PROMPT 6B_AUDIT (seção 4.2) é explícito:
> "Se o script não existir: é bloqueador (D3 exigiu criação)."

**Ação corretiva sugerida (duas opções para o operador):**

**Opção A — rigor máximo (recomendada se houver dúvida):**
Sessão de execução cria `scripts/e2e_shape_compat.py` cobrindo:
1. Mock de response do LLM com campos de auditoria
2. Chamar `_process_overlay_rc` + destructure
3. Iterar pelos 9 consumers (ou os "puros backend" — validate, srt, post_prompt, automation_prompt, translate_overlay_json, validate_translation, translate_one_claude, translate_project_parallel; `generation.py` é endpoint)
4. Simular serialização `ProjectOut` + confirmar shape recebido pelo frontend
5. Assert que nenhum item do array final contém `_is_audit_meta`
6. Assert que `overlay_audit` é dict populado independente

Re-auditoria incremental (só D3) depois de criado.

**Opção B — aceitar a ausência como divergência documentada:**
Operador registra em NOTAS_EXECUCAO.md uma seção "D3(a) omitida intencionalmente — coverage equivalente em commit_*.log + auditoria independente" e avança ao merge. A decisão é do operador porque o risco prático é baixo dado o coverage redundante confirmado por mim.

---

## 5. Observações não-bloqueadoras

### Obs 1 — Declaração "zero infra de testes" imprecisa
`NOTAS_EXECUCAO.md` declara:
> "3. **Zero infra de testes no repo.** Sem `tests/`, sem `pytest.ini`, sem jest/vitest."

Na verdade existe `app-editor/backend/tests/` com pytest + conftest + `test_multi_brand.py` + `test_perfil_unificado.py`. Tentei executar os testes — falham no ambiente da auditoria por dependências externas ausentes (psycopg2, pysubs2), mas essa é questão ambiental. **Nenhum dos testes existentes cobre arquivos tocados pelo refactor** (só `importar.py` foi tocado no editor, e nenhum teste existente o cobre). Então a declaração é imprecisa mas em espírito correta para o escopo do refactor.

### Obs 2 — Build ambiental (já registrado pela execução)
`npm run build` falha por fetch de Google Fonts bloqueado. Infra, não código. Execução real em Railway não reproduz.

### Obs 3 — Campos no sentinel original vs esperados no prompt
O prompt do operador listava como "campos que antes estavam no sentinel": `cortes_aplicados`, `fio_unico_identificado`, `pontes_planejadas`, `ancoragens_causais`, `cenas_especificas`, `gancho_fechamento_ecoam`, `verificacoes.*`. A realidade do código pré-refactor é que o sentinel tinha apenas 4 chaves: `_is_audit_meta`, `fio_unico_identificado`, `pontes_planejadas`, `verificacoes` (com `cortes_aplicados` dentro). Os outros campos existem apenas como keys do template no prompt LLM (`rc_overlay_prompt.py:634-637`), nunca foram extraídos para o sentinel. **A execução preservou fielmente todos os campos que estavam no sentinel real** — o aparente "desalinhamento" é do prompt do operador, não do refactor. Não é observação crítica, só clareza.

---

## 6. Consequências do veredito

### Se o operador optar pela Opção A (criar E2E, re-auditar)
1. Sessão de execução re-aberta para criar `scripts/e2e_shape_compat.py`
2. Commit adicional na branch `refactor/overlay-sentinel-restructure`
3. Push
4. Re-auditoria focada apenas no novo commit (rápida, ~5 min)
5. Após aprovação: merge em main

### Se o operador optar pela Opção B (aceitar ausência)
1. Merge direto da branch atual em `main`:
   ```
   git checkout main && git pull origin main
   git merge --no-ff refactor/overlay-sentinel-restructure -m "Merge refactor overlay-sentinel-restructure — resolve regressão visual RC pós-Fase 3"
   git push origin main
   ```
2. Railway faz deploy automático (~2-3 min)
3. Executar migration SQL em produção manualmente:
   ```
   psql <URL_PROD> -f scripts/migrate_overlay_sentinel.sql
   ```
   Recomendado dentro de `BEGIN; \i ... ; -- revisar ; COMMIT;`
4. Validar em produção:
   - `SELECT COUNT(*) FROM projects WHERE overlay_json::text LIKE '%_is_audit_meta%';` → esperado **0**
   - `SELECT COUNT(*) FILTER (WHERE overlay_audit IS NULL) AS rc_sem, COUNT(*) FILTER (WHERE overlay_audit IS NOT NULL) AS rc_com FROM projects WHERE brand_slug = 'reels-classics';` → `rc_com = 0` imediatamente após SQL (projetos antigos ficam sem audit por D4)
   - Abrir projeto #355 no portal e confirmar overlay renderiza sem tela de erro
   - Criar projeto RC novo e rodar pipeline completo: `overlay_audit` deve ser populado

---

## 7. Confiança do auditor

**Alta** em cada um dos 7 commits individualmente. **Alta** no grep final (o teste definitivo da premissa estrutural: exatamente 2 matches justificados). **Alta** na cobertura de bug original. **Alta** no script SQL (seguro, idempotente, escopo estrito, D4 respeitada).

A única razão do veredito não ser APROVADO é a ausência formal de D3(a). Se o operador considerar que a cobertura equivalente (7 smokes + minha reconstituição + tsc clean) é suficiente para satisfazer o espírito de D3, o refactor pode avançar ao merge com risco operacional baixo.

Minha função como auditor paranoico é apontar a lacuna formal. A decisão sobre severidade prática é do operador.

---

## 8. Referências

- Branch auditada: `origin/refactor/overlay-sentinel-restructure`
- Commits: `git log origin/main..origin/refactor/overlay-sentinel-restructure`
- Relatório da execução: `docs/rc_v3_migration/NOTAS_EXECUCAO.md`
- Investigação original: `docs/rc_v3_migration/RELATORIO_INVESTIGACAO.md` (Bloco A)
- Smokes da execução: `docs/rc_v3_migration/smoke_test_results/commit_{1..7}.log`
- Logs da auditoria: `docs/rc_v3_migration/auditoria_logs/`
  - `tsc.log` — TypeScript compilation (EXIT=0)
  - `lint.log` — ESLint (136 errors + 77 warnings, -1 net)
  - `build.log` — Next.js build (falha ambiental Google Fonts)
  - `grep_final.log` — grep `_is_audit_meta` final (2 matches em redator.ts)
  - `imports.log` — Backend imports OK
  - `notas_vs_codigo.log` — Cross-check D1-D6
  - `sql_parse.log` — SQL syntactic validation
  - `bug_original_reconstituicao.log` — Reconstituição do bug #355

---

*Relatório emitido por auditor independente, sem contexto da sessão de execução. Critério binário (APROVADO/REPROVADO) aplicado. Bloqueador único documentado com ação corretiva sugerida em duas opções. Operador tem a palavra final sobre severidade prática.*
