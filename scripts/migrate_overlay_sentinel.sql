-- migrate_overlay_sentinel.sql
-- =============================================================================
-- Migração one-shot: remove sentinel `_is_audit_meta` do array `overlay_json`
-- em projetos Reels Classics existentes. Não popular `overlay_audit` — por
-- decisão editorial (PROMPT 6B, D4), o conteúdo histórico de cortes_aplicados
-- não tem valor editorial preservável.
-- =============================================================================
--
-- Contexto
-- --------
-- Entre o merge da Fase 3 (commit 90add64, 2026-04-22) e o merge do refactor
-- `overlay-sentinel-restructure`, projetos RC novos persistiam em
-- `projects.overlay_json` um array heterogêneo: legendas reais + um item final
-- `{_is_audit_meta: true, fio_unico_identificado, pontes_planejadas, verificacoes}`.
--
-- Após o refactor:
--   - Projetos novos já gravam `overlay_json` como lista homogênea de legendas
--     e `overlay_audit` (coluna nova) como dict separado.
--   - Projetos antigos continuam com o sentinel dentro do array até este script
--     rodar.
--
-- Este script:
--   1. Identifica projetos RC com sentinel dentro de `overlay_json`.
--   2. Remove o item sentinel do array (mantém todas as legendas reais).
--   3. Deixa `overlay_audit` como NULL (projetos antigos não terão auditoria).
--   4. NÃO toca em projetos de outras marcas (brand_slug != 'reels-classics')
--      para minimizar surface de risco — essas marcas nunca usaram o sentinel
--      (vide RELATORIO_INVESTIGACAO_REGRESSAO.md Bloco A: o sentinel só é
--      emitido por _process_overlay_rc, que só roda para RC).
--
-- Execução
-- --------
-- MANUAL. Supervisionada pelo operador. Rodar SOMENTE após:
--   1. Branch `refactor/overlay-sentinel-restructure` mergeada em main.
--   2. Deploy do redator + portal concluído.
--   3. Smoke test em staging Railway validando 1 projeto RC novo + 1 legado.
--
-- Recomendado rodar dentro de uma transação explícita (BEGIN/SELECT/COMMIT ou
-- ROLLBACK) para poder validar antes de confirmar:
--
--     BEGIN;
--     \i scripts/migrate_overlay_sentinel.sql
--     -- revisar output dos SELECTs antes de decidir
--     -- se OK: COMMIT;   se não: ROLLBACK;
--
-- Banco alvo: Postgres (Railway). Tipo da coluna `overlay_json` é JSON.
-- Cast para jsonb é necessário para usar jsonb_array_elements / jsonb_agg.
-- =============================================================================

-- 1. Pré-visualização: quantos projetos RC têm sentinel no array?
--    (Roda ANTES do UPDATE. Não muda nada.)
SELECT
    COUNT(*) AS rc_projects_with_sentinel
FROM projects p
WHERE p.brand_slug = 'reels-classics'
  AND p.overlay_json IS NOT NULL
  AND EXISTS (
      SELECT 1
      FROM jsonb_array_elements(p.overlay_json::jsonb) AS item
      WHERE (item->>'_is_audit_meta')::boolean IS TRUE
  );

-- 2. Amostra de projetos afetados (id, artist, work, brand_slug) — inspeção manual.
SELECT
    p.id,
    p.artist,
    p.work,
    p.brand_slug,
    jsonb_array_length(p.overlay_json::jsonb) AS array_len_antes
FROM projects p
WHERE p.brand_slug = 'reels-classics'
  AND p.overlay_json IS NOT NULL
  AND EXISTS (
      SELECT 1
      FROM jsonb_array_elements(p.overlay_json::jsonb) AS item
      WHERE (item->>'_is_audit_meta')::boolean IS TRUE
  )
ORDER BY p.id
LIMIT 20;

-- 3. UPDATE: remover itens com _is_audit_meta do array.
--    jsonb_agg sobre a subquery filtrada reconstrói o array sem o sentinel.
--    WHERE clause garante que só tocamos em RC com sentinel presente.
UPDATE projects p
SET overlay_json = COALESCE(
    (
        SELECT jsonb_agg(item)
        FROM jsonb_array_elements(p.overlay_json::jsonb) AS item
        WHERE (item->>'_is_audit_meta') IS NULL
           OR (item->>'_is_audit_meta')::boolean IS NOT TRUE
    ),
    '[]'::jsonb
)
WHERE p.brand_slug = 'reels-classics'
  AND p.overlay_json IS NOT NULL
  AND EXISTS (
      SELECT 1
      FROM jsonb_array_elements(p.overlay_json::jsonb) AS item
      WHERE (item->>'_is_audit_meta')::boolean IS TRUE
  );

-- 4. Pós-validação: nenhum projeto (de QUALQUER marca) deve ter sentinel.
SELECT
    COUNT(*) AS any_project_still_with_sentinel
FROM projects p
WHERE p.overlay_json IS NOT NULL
  AND EXISTS (
      SELECT 1
      FROM jsonb_array_elements(p.overlay_json::jsonb) AS item
      WHERE (item->>'_is_audit_meta')::boolean IS TRUE
  );
-- Esperado: 0.

-- 5. Pós-validação: overlay_audit continua NULL para projetos antigos
--    (script NÃO popula — decisão editorial D4).
SELECT
    COUNT(*) FILTER (WHERE overlay_audit IS NULL) AS rc_sem_audit,
    COUNT(*) FILTER (WHERE overlay_audit IS NOT NULL) AS rc_com_audit,
    COUNT(*) AS rc_total
FROM projects
WHERE brand_slug = 'reels-classics';
-- Esperado imediatamente após script: rc_com_audit = 0 (nenhum projeto antigo
-- tem audit; apenas projetos gerados DEPOIS do deploy do refactor terão).

-- 6. Pós-validação: projetos de outras marcas intactos (smoke de escopo).
SELECT
    brand_slug,
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE overlay_json IS NOT NULL) AS com_overlay
FROM projects
GROUP BY brand_slug
ORDER BY brand_slug;
