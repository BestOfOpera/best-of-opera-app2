# SPEC-005c — Corrigir fluxo de seleção de idioma no Import

**Status:** CONCLUÍDO
**PRD de origem:** `docs/PRD-005-diagnostico-erros-plataforma.md` (problema #1)
**Data:** 23/03/2026

---

## Contexto

Quando o usuário clica "Iniciar Importação" com "Detectar automaticamente" selecionado, o backend tenta inferir o idioma. Como o modelo do Redator não possui campo `language`, a detecção falha quase sempre e retorna HTTP 422 com `idioma_necessario: true`.

Hoje o frontend trata esse erro assim:
```typescript
setIdiomaEscolhido("")
toast.error("Não foi possível detectar o idioma. Por favor, selecione um manualmente.")
// ← modal nunca abre
```

O toast aparece e some. O usuário não tem nenhuma ação disponível — precisa abrir o modal manualmente do zero clicando no botão do projeto novamente.

**Arquivo a modificar:** 1 (`app-portal/components/editor/editing-queue.tsx`)

---

## Tarefa 1 — Abrir modal automaticamente quando detecção falha

**Arquivo:** `app-portal/components/editor/editing-queue.tsx`

**Localizar** o handler de erro 422 dentro de `handleImportar` (~linha 183):

**Antes:**
```typescript
if (err instanceof ApiError && err.status === 422 && (err.detail as Record<string, unknown>)?.idioma_necessario === true) {
  setIdiomaEscolhido("")
  toast.error("Não foi possível detectar o idioma. Por favor, selecione um manualmente.")
}
```

**Depois:**
```typescript
if (err instanceof ApiError && err.status === 422 && (err.detail as Record<string, unknown>)?.idioma_necessario === true) {
  const projeto = projetosRedator.find(p => p.id === projectId)
  setModalIdioma({
    projectId,
    artist: projeto?.artist || "",
    work: projeto?.work || "",
    category: projeto?.category,
  })
  setIdiomaEscolhido("auto")
  setOutroIdioma("")
  setTemLetraImport(null)
  toast.error("Idioma não detectado automaticamente. Selecione abaixo.")
}
```

**O que muda:**
- O modal de seleção de idioma abre imediatamente, sem o usuário precisar clicar de novo
- O toast ainda aparece, mas agora é um aviso contextual (o modal já está visível)
- Os campos do modal são resetados para estado limpo (`auto`, sem texto customizado)

**Critério de feito:** ao clicar "Iniciar Importação" com "Detectar automaticamente" em um projeto sem traduções completas, o modal de seleção de idioma abre automaticamente.

---

## Tarefa 2 — Renomear opção "Detectar automaticamente" para deixar clara a expectativa

**Arquivo:** `app-portal/components/editor/editing-queue.tsx`

**Localizar** o `SelectItem` com value `"auto"` (~linha 450):

**Antes:**
```tsx
<SelectItem value="auto">Detectar automaticamente</SelectItem>
```

**Depois:**
```tsx
<SelectItem value="auto">Detectar automaticamente (se possível)</SelectItem>
```

**Por que:** deixa claro que é uma tentativa, não uma garantia — alinha a expectativa do usuário com o comportamento real do sistema.

**Critério de feito:** o dropdown exibe "Detectar automaticamente (se possível)" como primeira opção.

---

## Ordem de execução

1. Tarefa 1 — correção do handler de erro (impacto principal)
2. Tarefa 2 — renomear label (cosmético)

---

## Verificação pós-execução

- [ ] Abrir modal de import em um projeto novo (sem traduções) → selecionar "Detectar automaticamente" → clicar "Iniciar Importação" → modal deve reabrir automaticamente para seleção manual
- [ ] Selecionar um idioma manualmente (ex: Italiano) → clicar "Iniciar Importação" → deve importar normalmente sem erro
- [ ] Confirmar que o label no dropdown exibe "(se possível)"
