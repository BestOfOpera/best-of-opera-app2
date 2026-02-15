# Arias Conteudo — Design System Guide

> Guia completo da identidade visual e sistema de design da plataforma **Arias Conteudo**.
> Qualquer novo aplicativo (Organizador, futuras marcas, etc.) deve seguir estas especificacoes para manter coerencia visual.

---

## 1. Visao Geral da Plataforma

**Arias Conteudo** e a holding proprietaria de marcas ligadas a musica erudita. A plataforma unifica 4 ferramentas (apps) numa interface coesa:

| App | Funcao | Cor indicativa |
|---|---|---|
| **Curadoria** | Busca e selecao de conteudo no YouTube | `Search` icon |
| **Redator** | Geracao de conteudo editorial (overlay, post, YouTube SEO) | `PenTool` icon |
| **Editor** | Pipeline de edicao de video (9 etapas) | `Film` icon |
| **Organizador** | *(novo)* Organizacao e gestao de projetos | *(a definir)* |

Cada app aparece como uma **secao colapsavel** na sidebar esquerda. O usuario navega entre apps sem trocar de pagina — tudo convive no mesmo shell.

---

## 2. Stack Tecnica

| Camada | Tecnologia |
|---|---|
| Framework | **Next.js 16** (App Router) |
| Estilizacao | **Tailwind CSS v4** (via `@theme inline` + CSS variables) |
| Componentes | **shadcn/ui** (Radix primitives + Tailwind) |
| Icones | **Lucide React** (somente) |
| Fontes | **Inter** (sans-serif, corpo) + **Playfair Display** (serif, titulos de marca) |
| Linguagem UI | **Portugues (PT-BR)** |

### Configuracao de Fontes

```tsx
import { Inter, Playfair_Display } from 'next/font/google'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })
const playfair = Playfair_Display({ subsets: ['latin'], variable: '--font-playfair' })
```

```html
<html lang="pt-BR" className={`${inter.variable} ${playfair.variable}`}>
  <body className="font-sans antialiased">
```

- `font-sans` → Inter (todo o corpo de texto, labels, botoes)
- `font-serif` → Playfair Display (apenas logotipo "Arias Conteudo" na sidebar)

---

## 3. Paleta de Cores

### 3.1 Cores Primarias

Todas as cores sao definidas em **HSL** como CSS custom properties no `:root`.

| Token | HSL | Hex aprox. | Uso |
|---|---|---|---|
| `--primary` | `hsl(263, 55%, 48%)` | `#7C3AED` | Botoes principais, links ativos, ring de foco, sidebar ativo |
| `--primary-foreground` | `hsl(0, 0%, 100%)` | `#FFFFFF` | Texto sobre primary |
| `--accent` | `hsl(40, 40%, 52%)` | `#C9A84C` | Destaques dourados, acentos decorativos |
| `--accent-foreground` | `hsl(0, 0%, 100%)` | `#FFFFFF` | Texto sobre accent |

### 3.2 Cores de Fundo

| Token | HSL | Hex aprox. | Uso |
|---|---|---|---|
| `--background` | `hsl(40, 33%, 97%)` | `#FAF8F5` | Fundo geral da pagina (creme claro) |
| `--card` | `hsl(0, 0%, 100%)` | `#FFFFFF` | Cards, popovers, header |
| `--muted` | `hsl(40, 15%, 93%)` | `#EDE9E3` | Fundos desabilitados, hover sutil |
| `--secondary` | `hsl(40, 20%, 95%)` | `#F3EFE8` | Botoes secundarios |

### 3.3 Cores de Texto

| Token | HSL | Hex aprox. | Uso |
|---|---|---|---|
| `--foreground` | `hsl(220, 20%, 16%)` | `#212833` | Texto principal (quase preto azulado) |
| `--muted-foreground` | `hsl(220, 10%, 50%)` | `#737B8B` | Texto secundario, placeholders, labels menores |

### 3.4 Bordas e Inputs

| Token | HSL | Hex aprox. | Uso |
|---|---|---|---|
| `--border` | `hsl(40, 15%, 89%)` | `#E3DED6` | Bordas de cards, dividers |
| `--input` | `hsl(40, 15%, 89%)` | `#E3DED6` | Borda de inputs e selects |
| `--ring` | `hsl(263, 55%, 48%)` | `#7C3AED` | Ring de foco (mesma cor do primary) |

### 3.5 Cores Semanticas

| Token | HSL | Hex aprox. | Uso |
|---|---|---|---|
| `--success` | `hsl(152, 55%, 42%)` | `#30A66B` | Sucesso, concluido, aprovado |
| `--warning` | `hsl(38, 80%, 50%)` | `#E6A817` | Alerta, em andamento |
| `--info` | `hsl(215, 70%, 55%)` | `#4A90D9` | Informativo, download |
| `--destructive` | `hsl(0, 60%, 50%)` | `#CC3333` | Erro, exclusao, danger |

Todas as semanticas tem `*-foreground: hsl(0, 0%, 100%)` (texto branco).

### 3.6 Sidebar

| Token | HSL | Uso |
|---|---|---|
| `--sidebar-background` | `hsl(40, 25%, 97%)` | Fundo da sidebar |
| `--sidebar-foreground` | `hsl(220, 15%, 35%)` | Texto inativo |
| `--sidebar-primary` | `hsl(263, 55%, 48%)` | Item ativo |
| `--sidebar-accent` | `hsl(263, 40%, 95%)` | Fundo hover/ativo (roxo claro) |
| `--sidebar-accent-foreground` | `hsl(263, 55%, 40%)` | Texto ativo |
| `--sidebar-border` | `hsl(40, 15%, 90%)` | Bordas |

### 3.7 Charts

Para graficos e visualizacoes de dados, usar sempre nesta ordem:

| Token | Cor | Uso |
|---|---|---|
| `--chart-1` | Purple (primary) | Serie 1 |
| `--chart-2` | Gold (accent) | Serie 2 |
| `--chart-3` | Green (success) | Serie 3 |
| `--chart-4` | Blue (info) | Serie 4 |
| `--chart-5` | Amber (warning) | Serie 5 |

---

## 4. Tipografia

### Escala de Tamanhos

| Classe Tailwind | Tamanho | Uso |
|---|---|---|
| `text-xl` | 20px | Titulo de pagina (h1) |
| `text-sm` | 14px | Corpo, labels, nomes em listas |
| `text-xs` | 12px | Subtitulos, metadata, badges |
| `text-[11px]` | 11px | Labels de secao na sidebar, chips |
| `text-[10px]` | 10px | Sub-labels minusculos |
| `text-[9px]` | 9px | Timestamps, anotacoes minimas |

### Pesos

| Classe | Uso |
|---|---|
| `font-semibold` | Titulos de pagina, nomes de projeto |
| `font-medium` | Labels de form, items de nav ativos, nomes em tabelas |
| `font-normal` (default) | Corpo de texto, descricoes |
| `font-bold` | Numeros de destaque (scores, percentuais) |

### Convencoes

- **Titulos de pagina**: `text-xl font-semibold text-foreground`
- **Subtitulo/contexto**: `text-sm text-muted-foreground`
- **Labels de secao (uppercase)**: `text-xs font-semibold uppercase tracking-wider text-muted-foreground`
- **Logotipo sidebar**: `font-serif text-lg tracking-tight` — "Arias" em `text-foreground`, "Conteudo" em `text-muted-foreground`
- **Fonte mono** para letras/poesia/codigo: `font-mono`
- **Numeros tabulares** (scores, %, timestamps): adicionar `tabular-nums`

---

## 5. Espacamento e Layout

### Border Radius

| Token | Valor | Uso |
|---|---|---|
| `--radius` | `0.5rem` (8px) | Base |
| `rounded-sm` | 4px | Chips, mini-badges |
| `rounded-md` | 6px | Inputs, botoes |
| `rounded-lg` | 8px | Cards |
| `rounded-xl` | 12px | Modais, cards grandes |
| `rounded-full` | 50% | Avatares, dots de status |

### Espacamento Padrao

| Contexto | Classe | Valor |
|---|---|---|
| Gap entre cards | `space-y-3` | 12px |
| Gap entre secoes | `space-y-6` | 24px |
| Padding de card | `p-4` ou `p-3` | 16px ou 12px |
| Padding do header | `px-8 h-12` | 32px horizontal, 48px altura |
| Padding do main content | `px-8 py-6` | 32px horizontal, 24px vertical |
| Sidebar width | `w-56` | 224px |

### Estrutura do Shell

```
┌──────────────────────────────────────────────┐
│ Sidebar (w-56)  │  Header (h-12, border-b)   │
│                 │  [Breadcrumb] [BrandSelect] │
│  Logo           ├────────────────────────────│
│  ───────        │                             │
│  > Curadoria    │  Main Content               │
│    Dashboard    │  (px-8 py-6, overflow-auto)  │
│    Resultados   │                             │
│    Downloads    │                             │
│  > Redator      │                             │
│    ...          │                             │
│  > Editor       │                             │
│    ...          │                             │
│  > Organizador  │                             │
│    ...          │                             │
│  ───────        │                             │
│  [Avatar] Admin │                             │
└──────────────────────────────────────────────┘
```

---

## 6. Componentes Compartilhados

### 6.1 AppShell

Container principal. Recebe `activeTool`, `activePage`, `breadcrumb[]`, `children`.

```tsx
<AppShell activeTool="redator" activePage="/redator/novo" breadcrumb={["Redator", "Novo Projeto"]}>
  {/* conteudo da pagina */}
</AppShell>
```

### 6.2 AppSidebar

- Secoes colapsaveis por app (Curadoria, Redator, Editor, Organizador)
- Cada secao: icone + label uppercase + chevron
- Items: icone 3.5x3.5 + label 13px
- Item ativo: `bg-muted font-medium text-foreground`
- Item inativo: `text-muted-foreground hover:bg-muted/40`
- Footer: avatar circular + nome + email + settings icon

**Para adicionar o Organizador**, basta adicionar uma nova entrada no array `tools`:

```tsx
{ id: "organizador", label: "Organizador", icon: FolderKanban, items: [
  { label: "Painel", href: "/organizador", pageKey: "organizador-painel", icon: LayoutDashboard },
  // ... mais items
]}
```

### 6.3 BrandSelector

Dropdown no canto superior direito do header. Mostra:
- Iniciais da marca (2 letras) em badge `bg-primary/10 text-primary`
- Nome da marca
- Check na marca selecionada

Para adicionar nova marca:
```tsx
const brands = [
  { id: "best-of-opera", name: "Best of Opera", initials: "BO" },
  { id: "nova-marca", name: "Nova Marca", initials: "NM" },
]
```

### 6.4 AppBreadcrumb

Recebe `items: string[]`. Renderiza como: `Item1 / Item2 / Item3`

```tsx
<AppBreadcrumb items={["Editor", "Validar Letras"]} />
```

### 6.5 ScoreRing

Indicador circular SVG de 0-100.

```tsx
<ScoreRing score={85} size={48} strokeWidth={3} />
```

**Cores por faixa:**
| Faixa | Cor HSL | Significado |
|---|---|---|
| >= 80 | `hsl(152, 55%, 42%)` (green) | Excelente |
| >= 60 | `hsl(38, 80%, 50%)` (amber) | Bom |
| >= 40 | `hsl(215, 70%, 55%)` (blue) | Medio |
| < 40 | `hsl(0, 60%, 50%)` (red) | Baixo |

### 6.6 StatusBadge

Badge com dot colorido + label.

```tsx
<StatusBadge status="generating" />
```

**Status disponiveis:**

| Status | Label PT-BR | Cor do dot | Cor do texto |
|---|---|---|---|
| `pending` | Pendente | `gray-300` | `gray-500` |
| `in_progress` | Em Andamento | `amber-400` | `amber-700` |
| `input_complete` | Input Completo | `blue-400` | `blue-700` |
| `generating` | Gerando | `purple-400` | `purple-700` |
| `awaiting_approval` | Aguardando Aprovacao | `amber-400` | `amber-700` |
| `translating` | Traduzindo | `cyan-400` | `cyan-700` |
| `export_ready` | Pronto p/ Exportar | `emerald-400` | `emerald-700` |
| `success` | Concluido | `emerald-400` | `emerald-700` |
| `error` | Erro | `red-400` | `red-700` |
| `downloaded` | Baixado | `blue-400` | `blue-700` |
| `posted` | Publicado | `emerald-400` | `emerald-700` |

Para adicionar novos status, inserir no objeto `statusConfig`.

### 6.7 PipelineStepper

Indicador de progresso do pipeline de edicao (9 etapas).

```tsx
<PipelineStepper currentStep={4} />
```

**Etapas fixas:** Download → Letras → Transcricao → Alinhamento → Corte → Traducao → Preview → Render → Exportar

**Estados visuais:**
- Completo: `bg-emerald-100 text-emerald-700` + icone Check
- Atual: `bg-primary text-primary-foreground` + numero
- Futuro: `bg-muted text-muted-foreground` + numero
- Conector completo: `bg-emerald-300`
- Conector futuro: `bg-border`

---

## 7. Padroes de Pagina

### 7.1 Header de Pagina

Toda pagina segue este padrao no topo:

```tsx
<div className="flex items-center justify-between">
  <div>
    <h1 className="text-xl font-semibold text-foreground">Titulo da Pagina</h1>
    <p className="text-sm text-muted-foreground">Contexto · Detalhe</p>
  </div>
  <div className="flex gap-2">
    <Button variant="outline" size="sm">
      <Icon className="mr-2 h-3.5 w-3.5" />
      Acao Secundaria
    </Button>
    <Button size="sm">
      <Icon className="mr-2 h-3.5 w-3.5" />
      Acao Principal
    </Button>
  </div>
</div>
```

### 7.2 Cards

```tsx
<Card>
  <CardHeader>
    <CardTitle className="text-sm">Titulo do Card</CardTitle>
  </CardHeader>
  <CardContent className="space-y-3">
    {/* conteudo */}
  </CardContent>
</Card>
```

- Card com header: usar `CardHeader` + `CardContent`
- Card simples: apenas `CardContent` com `p-4`
- Card clicavel: adicionar `cursor-pointer transition-colors hover:bg-muted/20`

### 7.3 Labels de Secao

```tsx
<span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
  Nome da Secao
</span>
```

### 7.4 Grids

| Contexto | Classes |
|---|---|
| Cards de categoria (selecao) | `grid grid-cols-2 gap-3` |
| Cards de estatistica | `flex gap-4` com `flex-1` em cada |
| Lista vertical | `space-y-3` |
| Comparacao lado a lado | `grid grid-cols-2 gap-4` |
| Checkboxes de selecao | `grid grid-cols-4 gap-3` |

---

## 8. Botoes

### Variantes

| Variante | Aparencia | Uso |
|---|---|---|
| `default` | Fundo roxo, texto branco | Acao principal (salvar, aprovar, criar) |
| `outline` | Borda, fundo transparente | Acao secundaria (cancelar, filtrar, re-fazer) |
| `ghost` | Sem borda/fundo | Acoes terciarias inline |
| `destructive` | Fundo vermelho | Excluir, cancelar destrutivo |

### Tamanhos

| Size | Uso |
|---|---|
| `sm` | Botoes no header de pagina, acoes rapidas |
| `default` | Botoes principais de acao (footer de pagina) |

### Padrao de Icone em Botao

```tsx
<Button size="sm">
  <Icon className="mr-2 h-3.5 w-3.5" />   {/* size sm */}
  Label
</Button>

<Button>
  <Icon className="mr-2 h-4 w-4" />         {/* size default */}
  Label
</Button>
```

---

## 9. Formularios

### Campos de Input

```tsx
<div className="space-y-1.5">
  <label className="text-sm font-medium text-foreground">
    Nome do Campo <span className="text-destructive">*</span>
  </label>
  <Input placeholder="Placeholder..." />
</div>
```

### Textarea

```tsx
<Textarea
  className="min-h-[200px] text-sm leading-relaxed"
  placeholder="Texto..."
/>
```

Para poesia/letras: adicionar `font-mono`

### Select

```tsx
<Select>
  <SelectTrigger><SelectValue placeholder="Selecione..." /></SelectTrigger>
  <SelectContent>
    <SelectItem value="opcao1">Opcao 1</SelectItem>
  </SelectContent>
</Select>
```

### Cards Selecionaveis (como categorias de gancho)

```tsx
<button
  onClick={() => setSelected(key)}
  className={cn(
    "flex flex-col items-start gap-1 rounded-lg border p-3 text-left transition-colors",
    selected === key
      ? "border-primary bg-primary/5 ring-1 ring-primary"
      : "border-border hover:border-primary/30 hover:bg-muted/30"
  )}
>
  <span className="text-base">{emoji}</span>
  <span className="text-sm font-medium text-foreground">{label}</span>
  <span className="text-xs text-muted-foreground line-clamp-2">{descricao}</span>
</button>
```

---

## 10. Tabelas

```tsx
<Table>
  <TableHeader>
    <TableRow>
      <TableHead className="text-xs">Coluna</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    <TableRow className="cursor-pointer hover:bg-muted/30">
      <TableCell className="text-sm">Valor</TableCell>
    </TableRow>
  </TableBody>
</Table>
```

---

## 11. Cores por Contexto (Editor)

### Alinhamento de Palavras

| Match | Background | Texto | Borda |
|---|---|---|---|
| Exato | `bg-emerald-100` | `text-emerald-800` | `border-emerald-200` |
| Parcial | `bg-amber-100` | `text-amber-800` | `border-amber-200` |
| Erro | `bg-red-100` | `text-red-800` | `border-red-200` |

### Status do Pipeline (fila de edicao)

| Status | Classes |
|---|---|
| aguardando | `bg-gray-100 text-gray-600` |
| baixando | `bg-blue-100 text-blue-700` |
| letra | `bg-purple-100 text-purple-700` |
| transcricao | `bg-indigo-100 text-indigo-700` |
| alinhamento | `bg-amber-100 text-amber-700` |
| corte | `bg-orange-100 text-orange-700` |
| traducao | `bg-cyan-100 text-cyan-700` |
| montagem | `bg-teal-100 text-teal-700` |
| renderizando | `bg-pink-100 text-pink-700` |
| concluido | `bg-emerald-100 text-emerald-700` |
| erro | `bg-red-100 text-red-700` |

---

## 12. Icones

**Biblioteca:** Lucide React (`lucide-react`). NAO usar outra biblioteca de icones.

### Tamanhos Padrao

| Contexto | Classe |
|---|---|
| Dentro de botao sm | `h-3.5 w-3.5` |
| Dentro de botao default | `h-4 w-4` |
| Icone de nav na sidebar | `h-4 w-4` (secao), `h-3.5 w-3.5` (item) |
| Icone decorativo em card | `h-4 w-4` dentro de div `h-9 w-9` |
| Icone de status inline | `h-4 w-4` |

### Icones Recorrentes

| Conceito | Icone Lucide |
|---|---|
| Dashboard | `LayoutDashboard` |
| Busca/Pesquisa | `Search` |
| Download | `Download` |
| Upload/Exportar | `Upload` |
| Novo/Adicionar | `Plus` |
| Salvar/Aprovar | `Check` |
| Editar | `PenTool` |
| Excluir | `Trash2` |
| Atualizar/Refazer | `RefreshCw` |
| Video/Film | `Film` |
| Musica/Letras | `Music` |
| Alinhamento | `AlignLeft` |
| Configuracoes | `Settings` |
| Pasta/Arquivo | `FolderOpen`, `FileText` |
| Lista ordenada | `ListOrdered` |
| Globo (idiomas/web) | `Globe` |
| Play | `Play` |
| Chevron (expandir) | `ChevronDown` |
| Concluido (check circle) | `CheckCircle` |
| Enviar/Post | `Send` |

---

## 13. Idiomas (i18n)

### 7 Idiomas Suportados

| Codigo | Nome | Bandeira |
|---|---|---|
| `en` | English | flag_gb |
| `pt` | Portugues | flag_br |
| `es` | Espanol | flag_es |
| `fr` | Francais | flag_fr |
| `de` | Deutsch | flag_de |
| `it` | Italiano | flag_it |
| `pl` | Polski | flag_pl |

**Nota:** A UI da plataforma e sempre em PT-BR. Os idiomas acima sao para o conteudo gerado (traducoes de overlay, post, etc.).

---

## 14. CSS Completo (globals.css)

Copiar este arquivo integralmente para novos projetos:

```css
@import "tailwindcss";
@import "tw-animate-css";
@import "shadcn/tailwind.css";

@custom-variant dark (&:is(.dark *));

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --font-sans: var(--font-inter);
  --font-serif: var(--font-playfair);
  --color-sidebar-ring: var(--sidebar-ring);
  --color-sidebar-border: var(--sidebar-border);
  --color-sidebar-accent-foreground: var(--sidebar-accent-foreground);
  --color-sidebar-accent: var(--sidebar-accent);
  --color-sidebar-primary-foreground: var(--sidebar-primary-foreground);
  --color-sidebar-primary: var(--sidebar-primary);
  --color-sidebar-foreground: var(--sidebar-foreground);
  --color-sidebar: var(--sidebar-background);
  --color-chart-5: var(--chart-5);
  --color-chart-4: var(--chart-4);
  --color-chart-3: var(--chart-3);
  --color-chart-2: var(--chart-2);
  --color-chart-1: var(--chart-1);
  --color-ring: var(--ring);
  --color-input: var(--input);
  --color-border: var(--border);
  --color-destructive: var(--destructive);
  --color-destructive-foreground: var(--destructive-foreground);
  --color-accent-foreground: var(--accent-foreground);
  --color-accent: var(--accent);
  --color-muted-foreground: var(--muted-foreground);
  --color-muted: var(--muted);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-secondary: var(--secondary);
  --color-primary-foreground: var(--primary-foreground);
  --color-primary: var(--primary);
  --color-popover-foreground: var(--popover-foreground);
  --color-popover: var(--popover);
  --color-card-foreground: var(--card-foreground);
  --color-card: var(--card);
  --color-success: var(--success);
  --color-success-foreground: var(--success-foreground);
  --color-warning: var(--warning);
  --color-warning-foreground: var(--warning-foreground);
  --color-info: var(--info);
  --color-info-foreground: var(--info-foreground);
  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) + 4px);
  --radius-2xl: calc(var(--radius) + 8px);
  --radius-3xl: calc(var(--radius) + 12px);
  --radius-4xl: calc(var(--radius) + 16px);
}

:root {
  --radius: 0.5rem;
  --background: hsl(40, 33%, 97%);
  --foreground: hsl(220, 20%, 16%);
  --card: hsl(0, 0%, 100%);
  --card-foreground: hsl(220, 20%, 16%);
  --popover: hsl(0, 0%, 100%);
  --popover-foreground: hsl(220, 20%, 16%);
  --primary: hsl(263, 55%, 48%);
  --primary-foreground: hsl(0, 0%, 100%);
  --secondary: hsl(40, 20%, 95%);
  --secondary-foreground: hsl(220, 20%, 16%);
  --muted: hsl(40, 15%, 93%);
  --muted-foreground: hsl(220, 10%, 50%);
  --accent: hsl(40, 40%, 52%);
  --accent-foreground: hsl(0, 0%, 100%);
  --destructive: hsl(0, 60%, 50%);
  --destructive-foreground: hsl(0, 0%, 100%);
  --border: hsl(40, 15%, 89%);
  --input: hsl(40, 15%, 89%);
  --ring: hsl(263, 55%, 48%);
  --success: hsl(152, 55%, 42%);
  --success-foreground: hsl(0, 0%, 100%);
  --warning: hsl(38, 80%, 50%);
  --warning-foreground: hsl(0, 0%, 100%);
  --info: hsl(215, 70%, 55%);
  --info-foreground: hsl(0, 0%, 100%);
  --chart-1: hsl(263, 55%, 48%);
  --chart-2: hsl(40, 40%, 52%);
  --chart-3: hsl(152, 55%, 42%);
  --chart-4: hsl(215, 70%, 55%);
  --chart-5: hsl(38, 80%, 50%);
  --sidebar-background: hsl(40, 25%, 97%);
  --sidebar-foreground: hsl(220, 15%, 35%);
  --sidebar-primary: hsl(263, 55%, 48%);
  --sidebar-primary-foreground: hsl(0, 0%, 100%);
  --sidebar-accent: hsl(263, 40%, 95%);
  --sidebar-accent-foreground: hsl(263, 55%, 40%);
  --sidebar-border: hsl(40, 15%, 90%);
  --sidebar-ring: hsl(263, 55%, 48%);
}

@layer base {
  * {
    @apply border-border outline-ring/50;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

---

## 15. Componentes shadcn/ui Utilizados

Instalar via `npx shadcn@latest add <componente>`:

| Componente | Uso |
|---|---|
| `button` | Todas as acoes |
| `card` | Containers de conteudo |
| `input` | Campos de texto simples |
| `label` | Labels de formulario |
| `textarea` | Campos multiline |
| `select` | Dropdowns de selecao |
| `dialog` | Modais |
| `table` | Tabelas de dados |
| `tabs` | Navegacao por abas (idiomas, etc.) |
| `badge` | Tags e categorias |
| `checkbox` | Selecao multipla |
| `progress` | Barras de progresso |
| `slider` | Controles de range |
| `dropdown-menu` | Menus contextuais, brand selector |

---

## 16. Regras Gerais

1. **Sem dark mode** — o design e exclusivamente light com fundo creme
2. **Sem emojis na UI** — exceto nas bandeiras de idioma e nos cards de categoria de gancho
3. **Sem animacoes pesadas** — apenas `transition-colors`, `transition-opacity`, e `animate-pulse` para loading
4. **Labels sempre em PT-BR** — botoes, titulos, placeholders, status
5. **Numeros sempre `tabular-nums`** — para alinhamento visual em tabelas e scores
6. **Icones com `mr-2`** dentro de botoes — padrao consistente
7. **Cards clicaveis** com `cursor-pointer hover:bg-muted/20 transition-colors`
8. **Bordas sutis** — usar `border-border` (nunca preto)
9. **Hierarquia de texto** — maximo 3 niveis: `foreground` → `muted-foreground` → nunca cinza mais claro
10. **Breakpoints** — design desktop-first; sidebar colapsa em mobile (a implementar)

---

## 17. Como Adicionar o App Organizador

1. **Sidebar**: adicionar entrada no array `tools` em `app-sidebar.tsx`
2. **Pages**: criar pasta `components/organizador/` com os componentes de pagina
3. **Page router**: adicionar PageKeys no `page.tsx`
4. **Estilo**: usar EXATAMENTE os mesmos tokens, componentes e padroes deste guia
5. **Icone sugerido**: `FolderKanban` (Lucide) para o Organizador

---

## 18. Referencia Visual

O projeto `app-design/` contem uma implementacao funcional de todas as telas. Para visualizar:

```bash
cd app-design
npm install
npm run dev
# Abrir http://localhost:3000
```

Navegue pela sidebar para ver cada tela como referencia de como aplicar este design system.
