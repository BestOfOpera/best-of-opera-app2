# PRD-009 — UX: Fila de Edição, Lista do Redator e Importação RC

**Data:** 26/03/2026
**Sessão:** Continuação do SPEC-008 + melhorias de UX descobertas em uso
**Status:** PARCIALMENTE CONCLUÍDO

---

## Contexto

Sessão focada em melhorias de UX na Fila de Edição (Editor) e na Lista de Projetos (Redator), além de correção de bugs no fluxo de importação RC. Todas as tarefas partiram de problemas identificados em uso real da plataforma.

---

## Arquivos Modificados

| Arquivo | Mudanças |
|---|---|
| `app-editor/backend/app/main.py` | Cleanup automático de edições concluídas > 24h; remoção do backfill sem_lyrics RC |
| `app-editor/backend/app/routes/importar.py` | T7 filtro brand_slug; reversão auto-set sem_lyrics RC; fix idioma RC (PENDENTE) |
| `app-editor/backend/app/services/gemini.py` | Retry em resposta vazia do Gemini |
| `app-redator/backend/routers/projects.py` | Filtro r2_prefix; endpoints DELETE /{id} e DELETE /bulk; fix cascade |
| `app-portal/lib/api/redator.ts` | `deleteProject`, `deleteProjects`, `deleteR2Items`; r2_prefix em listR2Available |
| `app-portal/components/editor/editing-queue.tsx` | Concluídos ocultos por padrão; "Limpar lista"; RC pré-seleciona Sem Lyrics no modal |
| `app-portal/components/redator/project-list.tsx` | Reescrita completa: 3 views + dropdown + modo seleção + tag de marca |
| `docs/SPEC-008-rc-workflow-plataforma.md` | Status atualizado para CONCLUÍDO; todas as tarefas marcadas ✅ |

---

## Tarefas Concluídas ✅

### 1. SPEC-008 — Verificação e conclusão
Verificado no código que T1, T2, T3, T5, T6 já estavam implementados. T7 e T8 foram implementados nesta sessão. SPEC-008 marcado como CONCLUÍDO.

### 2. Fila de Edição — Projetos do Redator
- **Projetos concluídos ocultos por padrão** — filtro permanente no frontend (`editing-queue.tsx:289`)
- **Cleanup automático** — migration de startup deleta `editor_edicoes` com `status='concluido'` há mais de 24h (`main.py`)
- **Botão "Limpar lista"** — limpa o estado `projetosRedator` sem deletar dados (`editing-queue.tsx`)
- **Toggle "Mostrar todos os status"** — por padrão mostra só `export_ready`

### 3. Filtro por marca na lista do Redator (T7)
- Backend `listar_projetos_redator` aceita `perfil_id`, busca `slug` do perfil, passa `?brand_slug=slug` ao Redator
- Filtro de `mapa_edicoes` por `perfil_id` — cruzamento só da marca correta
- **Arquivo:** `app-editor/backend/app/routes/importar.py:57-84`

### 4. Lista do Redator — "Prontos para o Redator" filtrado por marca
- Endpoint `/r2-available` aceita `r2_prefix` — chama `storage.list_files(r2_prefix)` em vez de raiz
- Frontend passa `selectedBrand.r2_prefix` na chamada
- **Arquivos:** `app-redator/backend/routers/projects.py:33-71` · `app-portal/lib/api/redator.ts:99-102` · `app-portal/components/redator/project-list.tsx`

### 5. Lista do Redator — Reestruturação completa
- **3 views via dropdown:** "Em andamento" (`input_complete | generating | awaiting_approval | translating`), "Prontos p/ Exportar" (`export_ready`), "Prontos para o Redator" (R2)
- **Modo seleção:** botão "Selecionar" → checkboxes por item + "Selecionar tudo" + "Excluir (N)"
- **Deletar projetos:** endpoints `DELETE /projects/{id}` e `DELETE /projects/bulk` no Redator backend
- **Tag de marca** (RC/BO com cor_secundaria) em cada projeto
- **Arquivo:** `app-portal/components/redator/project-list.tsx` (reescrito)

### 6. Fix Gemini — resposta vazia
Gemini retornava string vazia para músicas instrumentais → `json.loads("")` → JSONDecodeError não retryável. Corrigido: `_extract_response_text` levanta `RuntimeError` para resposta vazia, acionando retry automático.
- **Arquivo:** `app-editor/backend/app/services/gemini.py:42-65`

### 7. Reversão auto-set sem_lyrics RC
T3 do SPEC-008 forçava `sem_lyrics=True` para todo RC, quebrando peças vocais (oratórios, réquiens). Revertido — operador controla via checkbox na importação.
- **Arquivo:** `app-editor/backend/app/routes/importar.py:210`

### 8. Modal de importação — RC pré-seleciona Sem Lyrics
Quando a marca selecionada é RC, o modal abre com "Sem Lyrics" já marcado e mostra dica contextual. Não bloqueia — operador pode trocar para "Com Lyrics" em peças vocais.
- **Arquivo:** `app-portal/components/editor/editing-queue.tsx:353-357, 535-548`

### 9. RC — Importar direto sem modal (parcial)
Quando RC + Sem Lyrics, botão "Importar" chama `handleImportar` diretamente sem abrir o modal de idioma.
- **Arquivo:** `app-portal/components/editor/editing-queue.tsx:352-365`

---

## Tarefas Pendentes ⚠️

### P1 — RC importação direta: backend ainda lança 422 quando idioma não detectado
**Problema:** Quando RC importa direto (sem modal), o backend ainda lança 422 se não consegue detectar o idioma da música — mesmo sendo instrumental (idioma irrelevante para instrumental).

**Solução acordada:** No backend, quando `eh_instrumental=True` e `music_lang is None`, pular o 422 — idioma não é usado no pipeline instrumental.

**Arquivo:** `app-editor/backend/app/routes/importar.py:167-175`

**Padrão esperado:**
```python
music_lang = idioma or _detect_music_lang(proj, _idiomas_set)
if music_lang is None:
    if eh_instrumental_final:
        music_lang = proj.get("language") or "und"  # placeholder, não usado
    else:
        raise HTTPException(422, detail={"idioma_necessario": True, ...})
```

**Nota:** O usuário questionou o fallback "it" (italiano) — usar `"und"` ou o campo `language` do projeto se disponível. O idioma para instrumental é puramente cosmético no banco.

### P2 — Vídeos RC já renderizados com tarja "Esta peça é instrumental e não contém letra."
**Problema:** Vídeos importados como "Com Lyrics" por engano e renderizados contêm uma legenda falsa no track de lyrics. O texto foi gerado pelo Gemini ao tentar transcrever uma peça instrumental.

**Solução:** Re-renderizar via "Limpar Edição" → reimportar com "Sem Lyrics".

**Não requer código** — é operacional. Os vídeos afetados precisam ser identificados e re-renderizados manualmente.

### P3 — "Selecionar tudo" na lista do Redator (R2) — verificar funcionamento após reestruturação
A lógica de seleção foi reescrita no contexto das 3 views. Validar que "Selecionar tudo" e "Excluir selecionados" funcionam corretamente para projetos (views Em andamento / Prontos) e para itens R2.

---

## Decisões Tomadas

- **RC sem lyrics → importar direto sem modal** — para peças vocais RC raras, operador clica em "Com Lyrics" manualmente
- **Cleanup de edições concluídas → 24h** — suficiente para o fluxo de trabalho atual
- **Idioma para instrumental → não exigir** — idioma é irrelevante quando não há transcrição
- **Fallback "it" rejeitado** — usar campo `language` do projeto Redator ou `"und"`, nunca hardcoded

---

## Notas para Próxima Sessão

1. Implementar P1 (backend fix idioma RC instrumental) — é pequeno, ~5 linhas
2. Confirmar P3 (teste das views de seleção no Redator)
3. Verificar se P2 (vídeos com tarja) precisam de ação adicional ou é só re-render manual
