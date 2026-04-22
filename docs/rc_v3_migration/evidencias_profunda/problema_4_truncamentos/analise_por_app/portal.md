# Análise de truncamento — `app-portal/` (Next.js frontend único)

Decisão editorial: operador nunca vê JSON cru (Princípio 3). Portal já respeita isso (refactor sentinel em produção). Superfície a verificar: inputs editoriais, previews, exportação.

## Pontos CRÍTICOS — zero matches

Editor visual de overlay ([components/redator/approve-overlay.tsx](app-portal/components/redator/approve-overlay.tsx)): reconhecimento inicial confirmou **nenhum `maxLength` em Textarea** editáveis de overlay. Reaplicação via grep direcionado em `components/redator/`:

- `new-project.tsx:471,476` — `maxLength={5}` em inputs MM:SS (cutStart/cutEnd) — **cosmético**, não-editorial
- Demais componentes `approve-*.tsx` — **sem `maxLength` em conteúdo**

## Pontos MÉDIOS — UX visual (conteúdo preservado no backend)

Portal tem 30 matches de CSS `truncate`, `line-clamp`, `text-overflow` em [t8_ellipsis.txt](docs/rc_v3_migration/evidencias_profunda/problema_4_truncamentos/t8_ellipsis.txt). Todos são **truncamento visual** em cards/sidebars/tabelas — o dado backend está íntegro, apenas a exibição corta com reticências CSS.

Representativos:
- `components/app-sidebar.tsx:142,152,170,171` — labels sidebar
- `components/calendario/add-modal.tsx:135,136,163,164` — nome artista/obra em modal
- `components/curadoria/video-card.tsx:74,75` — cards de vídeo curadoria
- `components/curadoria/search-results.tsx:59,60` — resultados busca
- `components/editor/conclusion.tsx:1389` — `max-w-[150px]` em erro_msg
- `components/finalizados/finalizado-card.tsx:164` — CardTitle
- `components/redator/new-project.tsx:407` — `line-clamp-4` em YouTube description

**Severidade uniforme: MÉDIA.** Usuário pode hover/click para ver completo em todos esses casos. Nenhum viola Princípio 1 (dado íntegro no backend), mas viola expectativa UX.

## Pontos MÉDIOS — ellipsis em dashboards

- `app/dashboard/page.tsx:222` — `JSON.stringify(projeto.progresso_detalhe).slice(0, 40) + "..."` — exibe JSON progresso parcial. T1+T13, mas é display de JSON técnico (não editorial).
- `components/curadoria/video-card.tsx:89` — `r.label.length > 18 ? r.label.slice(0, 18) + "..." : r.label` — trunca razão de recomendação com "...". MÉDIA.

## `maxLength` — 11 matches triados

Lista em [t7_maxlength.txt](docs/rc_v3_migration/evidencias_profunda/problema_4_truncamentos/t7_maxlength.txt). Todos são inputs cosméticos:

- `sigla` (4 chars) — código de marca
- `cor` hex (7 chars) — formato `#FFFFFF`
- `editing-queue.tsx:780` — maxLength=10 em campo curto (revisar contexto)
- `cutStart/cutEnd` (5 chars) — MM:SS

**Nenhum maxLength em textareas/inputs de conteúdo editorial.** ✓

## Slices TSX — 9 matches

[t1_slice_ts.txt](docs/rc_v3_migration/evidencias_profunda/problema_4_truncamentos/t1_slice_ts.txt) — maioria é array slicing (`sessions.slice(0, 20)`), não texto. Exceções:
- `dashboard/page.tsx:222` — já listado acima
- `video-card.tsx:89` — já listado acima

## Admin de marcas — pontos de Problema 1

[admin/marcas/nova/page.tsx:454, [id]/page.tsx:622](app-portal/app/(app)/admin/marcas/nova/page.tsx:454) — defaults visuais 25/50/40/60 para `overlay_max_chars_linha`/`overlay_max_chars`/`lyrics_max_chars`/`traducao_max_chars`. **Já mapeado em Problema 1** (fonte de verdade conflitante com backend).

## Resumo portal

- 0 findings CRÍTICOS
- 30+ findings MÉDIOS (CSS cosmético)
- Editor de overlay já sem `maxLength` em conteúdo ✓
- Superfície de preocupação é UX (perda de contexto em preview), não perda de dado
