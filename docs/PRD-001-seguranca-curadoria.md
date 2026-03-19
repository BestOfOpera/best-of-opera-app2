# PRD-001 — Segurança e Curadoria Multi-brand

**Data:** 19/03/2026
**Baseado em:** `dados-relevantes/RESUMO-DIAGNOSTICO-190326.md`
**SPEC derivado:** `docs/SPEC-001-seguranca-curadoria.md`

---

## 1. O que foi pesquisado

Leitura completa de `RESUMO-DIAGNOSTICO-190326.md`, `CLAUDE.md`, `MEMORIA-VIVA.md` e `HISTORICO-ERROS-CORRECOES.md`. Três problemas foram selecionados para este ciclo com base em criticidade e localização no código.

---

## 2. Problemas confirmados (escopo deste ciclo)

### #1 — Endpoint `admin/reset-total` exposto (segurança)
- **Origem:** TODO explícito na MEMORIA-VIVA sessão 10/03
- **Commit que criou:** `96d45ea`
- **Status:** nunca usado, nunca removido
- **Risco:** endpoint destrutivo acessível sem proteção adequada
- **Localização provável:** `app-editor/backend/app/routes/` (não verificado diretamente no código — verificar na SPEC)

### #3 — BUG-C: `"opera live"` hardcoded na busca da curadoria
- **Arquivo confirmado:** `app-curadoria/backend/routes/curadoria.py` linha 94
- **Código:** `full_query = f"{q} opera live {ANTI_SPAM}"`
- **Impacto:** buscas manuais de qualquer marca não-ópera (ex: Reels Classics) retornam resultados de ópera. Curadoria inutilizável para RC em buscas manuais.
- **Fix:** remover `opera live` do query — usar apenas `{q}` limpo

### #4 — BUG-D: `ANTI_SPAM` global não respeita configuração da marca
- **Arquivo confirmado:** `app-curadoria/backend/routes/curadoria.py` linhas 40, 94, 133, 157
- **Problema:** `Perfil.anti_spam_terms` existe no banco mas nunca é lido pela curadoria — usa filtro genérico BO para todas as marcas
- **Impacto:** bloqueia vídeos válidos para RC com termos que só fazem sentido para Best of Opera
- **Fix:** ler `anti_spam_terms` do perfil carregado via `load_brand_config()`
- **Risco identificado:** campo pode estar NULL no banco para todos os perfis — verificação obrigatória antes de declarar concluído

---

## 3. Dependências e riscos

| Risco | Mitigação |
|---|---|
| `admin/reset-total` usado no frontend | Grep em `app-portal/` antes de deletar |
| `anti_spam_terms` NULL no banco | SELECT no banco como critério de "feito" do #4 — se NULL, documentar como BLOCKER |
| BUG-C e BUG-D no mesmo arquivo | Editar em sequência, não em paralelo |

---

## 4. O que NÃO está no escopo deste ciclo

- Relogin 401 (#2)
- Brand config NULL para redator (#5)
- Reorganização da MEMORIA-VIVA (#6)
- Tarefas HARDENING 05/06/10

---

## 5. Estado do sistema antes deste ciclo

- 4 serviços Railway ativos (`portal`, `editor-backend`, `curadoria-backend`, `app`)
- Último deploy relevante: 13/03/2026 (correção YOUTUBE_COOKIES typo)
- Curadoria deployada e ativa, mas com BUG-C e BUG-D ativos em produção
- Endpoint `admin/reset-total` presumivelmente ativo em produção

---

## 6. Arquivos a ler na sessão de SPEC

1. `app-editor/backend/app/routes/` — localizar e confirmar existência de `admin/reset-total`
2. `app-curadoria/backend/routes/curadoria.py` — linhas 40, 94, 133, 157 e contexto de `load_brand_config()`
3. `app-portal/` — grep por `reset-total` para confirmar que não é chamado no frontend
