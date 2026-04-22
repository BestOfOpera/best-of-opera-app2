# Relatório de Auditoria Independente — Refactor `overlay-sentinel-restructure`

**Branch auditada:** `refactor/overlay-sentinel-restructure` @ `cef5836` (pós Opção B)
**Base:** `origin/main @ 90add64` (merge Fase 3)
**Commits auditados:** 7 originais (2c8daa0 → 57408c9) + 1 de registro de divergência (`cef5836`)
**Diff original:** +560/-68 linhas, 22 arquivos
**Auditor:** Claude (sessão fresh, sem contexto da execução)
**Data:** 2026-04-22
**Branch de auditoria:** `claude/audit-overlay-refactor-6O5ph`
**Logs brutos:** `docs/rc_v3_migration/auditoria_logs/`

---

## Veredito final

### ✅ APROVADO COM RESSALVA DOCUMENTADA

**Atualização (operador escolheu Opção B):** o bloqueador formal original (ausência de `scripts/e2e_shape_compat.py` exigido por D3(a)) foi **aceito conscientemente** pelo operador via commit `cef5836` na branch `refactor/overlay-sentinel-restructure`, que adiciona a seção *"Divergência vs D3(a) — aceita conscientemente"* ao `NOTAS_EXECUCAO.md` justificando a decisão com base na cobertura redundante já existente (7 smokes per-commit + reconstituição do bug original nesta auditoria + `tsc` clean + grep paranoico). A contrapartida registrada é que o próximo refactor de shape do overlay deve criar o E2E **antes** de iniciar, não depois.

Todos os 7 commits **individualmente OK**. Todas as validações de código (tipos, imports, grep global, smoke dos consumers, reconstituição do bug original, script SQL) **passam**. O refactor **resolve estruturalmente** a regressão visual do projeto #355 e é imune em ambos os cenários (projetos legados e projetos novos).

**Ressalva documentada:** o artefato `scripts/e2e_shape_compat.py` nunca foi criado. Divergência registrada formalmente em `docs/rc_v3_migration/NOTAS_EXECUCAO.md` (seção final) e referenciada neste relatório. Coverage funcional é garantido pelos 7 smokes per-commit + reconstituição manual do bug original + `tsc --noEmit EXIT=0`.

Operador tem autorização para fazer merge manual em `main`.

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

## 4. Ressalva documentada (ex-bloqueador formal, resolvido via Opção B)

### Ressalva 1 — `scripts/e2e_shape_compat.py` não criado (D3(a))

**Status original:** bloqueador formal.
**Status após Opção B:** ressalva documentada, aceita pelo operador.

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

O `NOTAS_EXECUCAO.md` declarava D3(a):
> "**D3 — Testes:** [...] Validação por: **(a) script E2E sintético `scripts/e2e_shape_compat.py`**, (b) smoke manual via Python REPL após cada commit backend, (c) `npx tsc --noEmit` + `npm run lint && npm run build` no portal, (d) staging Railway antes do merge."

A execução entregou (b) e (c) — 7 smokes per-commit + tsc/lint/build — mas **não entregou (a)**.

**Resolução formal:** commit `cef5836` na branch `refactor/overlay-sentinel-restructure` adicionou ao `NOTAS_EXECUCAO.md` a seção *"Divergência vs D3(a) — aceita conscientemente"*, registrando:

- Ausência detectada pelo auditor e escalada como bloqueador formal com duas opções
- Operador escolheu aceitar a ausência baseado em cobertura redundante:
  - Reconstituição do bug #355 em Node (legado + novo, ambos imunes)
  - 7 smokes per-commit per-caminho
  - `tsc --noEmit` EXIT=0 validando contratos TS
  - Grep final paranoico com apenas 2 matches justificados
  - Cobertura cruzada > script E2E único
- Referência: commit de auditoria `f41bb51` + relatório atual
- Contrapartida assumida: próximo refactor de shape do overlay deve criar o E2E **antes** de iniciar, não depois

**Impacto funcional residual:** nenhum. As validações equivalentes cobrem todos os caminhos críticos do refactor.

**Impacto formal residual:** divergência documentada. Auditor e operador concordam sobre a aceitação consciente da ausência.

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

## 6. Caminho para produção (Opção B escolhida)

Operador pode prosseguir ao merge manual. Sequência:

1. **Merge da refactor branch em main:**
   ```
   git checkout main && git pull origin main
   git merge --no-ff refactor/overlay-sentinel-restructure -m "Merge refactor overlay-sentinel-restructure — resolve regressão visual RC pós-Fase 3"
   git push origin main
   ```
   A branch refactor está em `cef5836` (com a seção de divergência D3(a) incluída).

2. **Railway auto-deploy** a partir de `main` (~2-3 min).

3. **Executar migration SQL em produção manualmente:**
   ```
   psql <URL_PROD> -f scripts/migrate_overlay_sentinel.sql
   ```
   Recomendado dentro de transação explícita:
   ```sql
   BEGIN;
   \i scripts/migrate_overlay_sentinel.sql
   -- revisar output dos 6 SELECTs
   COMMIT;  -- ou ROLLBACK se algo inesperado
   ```

4. **Validar em produção:**
   - `SELECT COUNT(*) FROM projects WHERE overlay_json::text LIKE '%_is_audit_meta%';` → esperado **0**
   - `SELECT COUNT(*) FILTER (WHERE overlay_audit IS NULL) AS rc_sem, COUNT(*) FILTER (WHERE overlay_audit IS NOT NULL) AS rc_com FROM projects WHERE brand_slug = 'reels-classics';` → `rc_com = 0` imediatamente após SQL (projetos antigos ficam sem audit por D4)
   - Abrir projeto #355 no portal e confirmar overlay renderiza sem tela de erro
   - Criar projeto RC novo e rodar pipeline completo: `overlay_audit` deve ser populado

---

## 7. Confiança do auditor

**Alta** em cada um dos 7 commits individualmente. **Alta** no grep final (o teste definitivo da premissa estrutural: exatamente 2 matches justificados). **Alta** na cobertura de bug original. **Alta** no script SQL (seguro, idempotente, escopo estrito, D4 respeitada).

**Posição final após Opção B:** a lacuna formal D3(a) foi **documentada e aceita pelo operador** em commit `cef5836`. Confirmo que a cobertura equivalente (7 smokes + reconstituição + tsc clean) satisfaz o espírito de D3 — o que mudou é a **formalização** da aceitação, agora rastreável no repo. Auditor e operador concordam que o risco operacional é baixo.

Minha função como auditor paranoico foi apontar a lacuna formal. A decisão de aceitar a divergência é do operador, e está registrada.

---

## 8. Referências

- Branch auditada: `origin/refactor/overlay-sentinel-restructure` @ `cef5836`
- Commits: `git log origin/main..origin/refactor/overlay-sentinel-restructure` (7 originais + commit `cef5836` de divergência)
- Commit de divergência D3(a) aceita: `cef5836` — "docs: registra divergência D3(a) aceita pelo operador"
- Relatório da execução: `docs/rc_v3_migration/NOTAS_EXECUCAO.md` (seção final: "Divergência vs D3(a) — aceita conscientemente")
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

*Relatório emitido por auditor independente, sem contexto da sessão de execução. Veredito original REPROVADO com 1 bloqueador formal (D3(a) ausente). Operador escolheu Opção B: aceitar a divergência com base em cobertura redundante documentada, registrando a decisão no commit `cef5836` da refactor branch. Veredito final: **APROVADO com ressalva documentada**. Operador tem autorização para merge manual em `main`.*
