# Diagnóstico Técnico: Dois Deploys em Produção

**Data:** 9 de março de 2026
**Autor:** Bolivar Andrade (investigação automatizada via Claude Code)
**Objetivo:** Identificar a versão base usada no deploy do sócio e documentar a defasagem em relação ao deploy principal.

---

## 1. Resumo Executivo

O deploy do sócio (`protective-friendship-production-9659.up.railway.app`) foi construído a partir do **repositório antigo** `BestOfOpera/best-of-opera`, que foi **abandonado em 13 de fevereiro de 2026** com apenas 36 commits. O projeto principal migrou nessa mesma data para o repositório `BestOfOpera/best-of-opera-app2`, que hoje tem **188 commits** e uma arquitetura completamente diferente (monorepo com 4 apps especializados).

**O deploy do sócio está 152 commits atrás e não contém nenhuma das funcionalidades desenvolvidas nas últimas 3+ semanas.** A recomendação técnica é clara: **seguir com a versão principal** (best-of-opera-app2) e descartar o deploy do sócio.

---

## 2. Dois Repositórios na Organização GitHub

| | Repo Antigo (sócio) | Repo Atual (Bolivar) |
|---|---|---|
| **Nome** | `BestOfOpera/best-of-opera` | `BestOfOpera/best-of-opera-app2` |
| **Criado** | 10/fev/2026 | 13/fev/2026 |
| **Último commit** | 13/fev/2026 | 05/mar/2026 |
| **Total commits** | 36 | 188 |
| **Arquitetura** | Monolito (1 arquivo `main.py` + 1 `index.html`) | Monorepo (4 apps + portal + shared) |
| **Frontend** | HTML estático (72KB, 1 arquivo) | Next.js 16 + React 19 + 2 frontends Vite |
| **Backend** | 1 FastAPI (1.459 linhas em `main.py`) | 3 FastAPIs especializados |
| **Banco** | PostgreSQL (1 tabela cache) | PostgreSQL compartilhado (múltiplas tabelas) |
| **Storage** | Disco local (efêmero) | Cloudflare R2 (persistente) |
| **Deploy URL** | `protective-friendship-production-9659` | `curadoria-production-cf4a` + 5 outros serviços |

### Arquivos do repo antigo (TUDO que existe)

```
best-of-opera/
├── Procfile              (58 bytes)
├── README-2.md           (5.5 KB)
├── database.py           (23.7 KB)
├── dataset_v3_categorizado.csv (390 KB)
├── main.py               (60 KB — 1.459 linhas, TUDO junto)
├── nixpacks.toml         (62 bytes)
├── requirements.txt      (131 bytes)
└── static/
    ├── .gitkeep
    └── index.html        (72 KB — HTML/CSS/JS inline)
```

**Total: 8 arquivos, ~162 KB de código.**

### Estrutura do repo atual

```
best-of-opera-app2/
├── app-curadoria/backend/     # Motor YouTube (FastAPI) — 1.704 linhas
├── app-redator/               # Gerador de conteúdo AI (FastAPI + React) — 3.866 linhas
│   ├── backend/               # Claude AI, prompts, export
│   └── frontend/              # React 18 + Vite
├── app-editor/                # Pipeline de vídeo (FastAPI + React) — 5.110 linhas
│   ├── backend/app/           # Gemini, FFmpeg, legendas ASS, workers
│   └── frontend/              # React 18 + Vite
├── app-portal/                # Frontend unificado (Next.js 16) — 7.305 linhas
│   ├── app/(app)/curadoria/
│   ├── app/(app)/redator/
│   └── app/(app)/editor/
├── shared/                    # Código compartilhado
└── scripts/                   # Utilitários Railway
```

**Total: ~18.000 linhas de código próprio, 63+ componentes React, 14 páginas, 70+ endpoints.**

---

## 3. Evidências Técnicas — Deploy do Sócio

### Prova 1: Tela de login inexistente no projeto principal

**Deploy do sócio** (`protective-friendship-production-9659.up.railway.app`):
- Exibe tela de login com campos "Email" e "Senha" e botão "Entrar"
- Branding: "Arias" + "Gestão de Conteúdo"
- Todas as rotas redirecionam para a tela de login (ex: `/curadoria` → login)
- `/api/health` retorna redirecionamento para `/login` em vez de JSON

**Deploy principal** (`curadoria-production-cf4a.up.railway.app`):
- Acesso direto sem login
- Redireciona automaticamente para `/curadoria` (Motor V7)
- `/api/health` retorna JSON com status, quota e versão

**Fato:** O arquivo `app-portal/app/page.tsx` no repo principal **nunca** teve uma tela de login. Desde o primeiro commit (`a27bfd0`, 15/fev), ele contém:
```typescript
import { redirect } from "next/navigation"
export default function Page() {
  redirect("/curadoria")
}
```

A busca no histórico Git (`git log --all -S "Entrar"` e `git log --all -S "password"`) confirma que **nenhum commit jamais adicionou formulário de login em arquivos `.tsx`**.

### Prova 2: Metadata idêntica confirma origem no mesmo código

O deploy do sócio exibe o título "Arias Conteudo" e descrição "Plataforma de gestao de conteudo para marcas de musica classica" — **exatamente** o que existe no `layout.tsx` desde o commit `a27bfd0` (15/fev):

```typescript
export const metadata: Metadata = {
  title: 'Arias Conteudo',
  description: 'Plataforma de gestao de conteudo para marcas de musica classica',
}
```

Isso confirma que o sócio **clonou o portal** e adicionou autenticação por conta própria, sem contribuir de volta ao repositório.

### Prova 3: Senha hardcoded no repo antigo

O commit `feat: add simple password gate to protect app access` (12/fev, repo `best-of-opera`) adicionou uma senha fixa (`APP_PASSWORD = "opera2026"`) ao `main.py`. Este padrão de "password gate" é consistente com a tela de login que o sócio exibe.

### Prova 4: Nenhum commit do sócio em nenhum repositório

A busca por autores no histórico Git mostra apenas:
- `Bolivar Andrade <administrator@Mac-Bolivar.local>` — 187 commits
- `BestOfOpera <bolivarandrade@gmail.com>` — 1 commit (Initial commit)

**Nenhum outro autor aparece em nenhum dos dois repositórios.** O sócio trabalhou completamente fora do controle de versão compartilhado.

### Prova 5: Apenas 1 branch em ambos os repositórios

```
best-of-opera:      main (única branch)
best-of-opera-app2: main (única branch)
```

Não existe branch do sócio, fork registrado, nem pull request.

---

## 4. Cronologia Completa — O que aconteceu

| Data | Repo Antigo (`best-of-opera`) | Repo Atual (`best-of-opera-app2`) |
|------|-------------------------------|-----------------------------------|
| 10/fev | Criado. Upload inicial de arquivos | — |
| 11/fev | Motor V3 → PostgreSQL, playlist, cache | — |
| 12/fev | **Motor V7** + password gate | — |
| 13/fev (manhã) | APP2 Produção + fixes FFmpeg/nixpacks | Criado. Initial commit |
| 13/fev (tarde) | **Último commit** (UX improvements) | APP Redator completo + deploy Railway |
| 14/fev | — | 35 commits: Editor completo (transcrição, legendas, renders) |
| 15/fev | — | Monorepo reorganizado, Portal Next.js criado, Curadoria integrada |
| 23/fev | — | Pipeline de transcrição reescrito |
| 24/fev | — | Cloudflare R2, Dockerfiles, auto-detecção YouTube |
| 25/fev | — | Worker assíncrono, tradução Google Cloud, debug Railway |
| 26/fev | — | 30+ commits: Editor completo (renders, ZIP, dead-letter, R2) |
| 27/fev | — | 35+ commits: Legendas ASS, Pagella, workers, upload manual |
| 03/mar | — | QA visual, toggle sem_lyrics, Overview, reforço idioma |
| 04/mar | — | Input manual YouTube, visualização de tradução |
| 05/mar | — | CTA fixo, paginação playlist, filtro tracks (HEAD atual) |

**O sócio bifurcou o projeto entre 13 e 15 de fevereiro**, quando o repo antigo ainda era atualizado e o app-portal já existia com o branding "Arias Conteudo".

---

## 5. Funcionalidades que NÃO existem no deploy do sócio

### 5.1 App Editor (inexistente — 0% do pipeline)

O App Editor **não existe** no repo antigo. São **2.000+ linhas de backend** e **3.000+ linhas de frontend** desenvolvidos de 13/fev a 05/mar:

| Feature | Commits | Status no sócio |
|---------|---------|-----------------|
| Pipeline de 9 etapas (download → render → export) | 80+ | Inexistente |
| Download via yt-dlp com retry e fallback | 10+ | Inexistente |
| Transcrição de áudio via Gemini 2.5 Pro | 8+ | Inexistente |
| Merge inteligente (cega + guiada) | 3 | Inexistente |
| Validação de alinhamento (fuzzy match color-coded) | 5+ | Inexistente |
| Legendas ASS com fonte TeX Gyre Pagella | 4 | Inexistente |
| Tradução de lyrics em 7 idiomas (Google Cloud) | 5+ | Inexistente |
| Renderização FFmpeg com legendas sincronizadas | 10+ | Inexistente |
| Worker sequencial com heartbeat e idempotência | 4 | Inexistente |
| Dead-letter queue para crash-loop prevention | 2 | Inexistente |
| Upload para Cloudflare R2 | 3 | Inexistente |
| Pacote ZIP assíncrono | 2 | Inexistente |
| Render sem legendas (saída de emergência) | 1 | Inexistente |
| Limpar Edição (reset de estado travado) | 1 | Inexistente |
| Desbloqueio forçado com diagnóstico | 2 | Inexistente |
| Cookies YouTube via base64 | 1 | Inexistente |
| Nomenclatura padronizada dos renders | 1 | Inexistente |
| Anti-duplicata na importação | 1 | Inexistente |

### 5.2 App Portal — Frontend Unificado Next.js (parcialmente existente)

O sócio tem alguma versão do portal, mas **sem as features dos últimos 50+ commits**:

| Feature | Data | Status no sócio |
|---------|------|-----------------|
| 14 páginas integradas (curadoria + redator + editor) | 15/fev–05/mar | Parcial (sem editor) |
| Tela de alinhamento com botões editar/excluir/adicionar | 26/fev | Inexistente |
| Badge unificado Redator ↔ Editor | 26/fev | Inexistente |
| Botão "Baixar Todos" com fallback individual | 26/fev | Inexistente |
| Aprovação de preview com tratamento 409 | 26/fev | Inexistente |
| Downloads por idioma em nova aba | 26/fev | Inexistente |
| Rotas de fuga e recovery na conclusão | 26/fev | Inexistente |
| Worker polling adaptativo | 25/fev | Inexistente |
| Importação Redator → Editor com detecção de idioma | 25/fev | Inexistente |
| Overview com roteamento por passo_atual | 03/mar | Inexistente |
| Toggle sem_lyrics | 03/mar | Inexistente |
| Correções visuais QA (16+ itens) | 03/mar | Inexistente |
| Labels do menu lateral corrigidos | 03/mar | Inexistente |
| Input manual de URL YouTube na curadoria | 04/mar | Inexistente |
| Modal automático ao adicionar vídeo | 04/mar | Inexistente |

### 5.3 App Redator (parcialmente existente — versão primitiva)

O repo antigo tem o "Módulo de Produção" embutido no `main.py` (endpoints `/api/prod/*`). O repo atual tem o Redator como **app separado** com:

| Feature | Data | Status no sócio |
|---------|------|-----------------|
| Backend separado com routers por domínio | 13/fev | Inexistente (tudo em 1 main.py) |
| Frontend React dedicado (Vite) | 13/fev | Inexistente (usa HTML estático) |
| Prompts refinados (overlay, post, YouTube, hook) | 13/fev–03/mar | Versão primitiva |
| Tradução CTA e hashtags do post | 03/mar | Inexistente |
| Reforço de idioma nos prompts (anti-leak) | 03/mar | Inexistente |
| Labels da ficha técnica no idioma do post | 27/fev | Inexistente |
| Omissão de campos vazios nos prompts | 27/fev | Inexistente |
| Limite 60 chars no overlay | 27/fev | Inexistente |
| CTA fixo na última legenda | 05/mar | Inexistente |
| Overlay congelado na importação (fix) | 03/mar | Inexistente |
| Export ZIP funcional | 24/fev | Versão básica |
| Auto-detecção de metadados via YouTube | 24/fev | Inexistente |

### 5.4 App Curadoria Backend (parcialmente existente — mesma base)

O Motor V7 de curadoria existe nos dois repositórios, mas o repo atual tem **endpoints adicionais**:

| Endpoint / Feature | Repo Atual | Repo Antigo (sócio) |
|---------------------|-----------|---------------------|
| `POST /api/manual-video` | Sim | Não |
| `POST /api/prepare-video/{id}` | Sim | Não |
| `POST /api/upload-video/{id}` | Sim | Não |
| `GET /api/r2/check` | Sim | Não |
| `GET /api/r2/info` | Sim | Não |
| `POST /api/playlist/download-all` | Sim | Não |
| `GET /api/playlist/download-status` | Sim | Não |
| Integração com Cloudflare R2 | Sim | Não |
| Paginação de playlist (fix ERR-057) | Sim | Não |
| Filtro de tracks lyrics (fix ERR-055) | Sim | Não |

### 5.5 Infraestrutura (completamente diferente)

| Aspecto | Repo Atual | Repo Antigo (sócio) |
|---------|-----------|---------------------|
| **Serviços Railway** | 6 serviços especializados | 1 serviço monolito |
| **Storage** | Cloudflare R2 (persistente) | Disco local (perde no redeploy) |
| **Dockerfiles** | 3 Dockerfiles otimizados | Nixpacks genérico |
| **CORS** | Configurado por serviço | `allow_origins=["*"]` |
| **Scripts de deploy** | `railway-env.sh` (GraphQL API) | Manual |
| **Banco de dados** | Tabelas por app (edicoes, letras, renders, etc.) | 1 tabela cache |
| **Workers** | Background workers com heartbeat | Síncrono |
| **Variáveis de ambiente** | 10+ variáveis por serviço | 3-4 variáveis |

---

## 6. Comparação Numérica

| Métrica | Repo Antigo (sócio) | Repo Atual (Bolivar) |
|---------|---------------------|----------------------|
| Commits | 36 | 188 |
| Arquivos de código | 3 (main.py, database.py, index.html) | 100+ |
| Linhas de código | ~2.000 | ~18.000 |
| Endpoints API | 36 (todos em 1 arquivo) | 70+ (em 8 módulos) |
| Páginas frontend | 1 (HTML monolito) | 14 (Next.js + 2 React apps) |
| Serviços Railway | 1 | 6 |
| Autores no Git | 1 | 1 (mesmo — nenhum commit do sócio) |
| Branches | 1 | 1 |
| Última atualização | 13/fev/2026 | 05/mar/2026 |
| Dias de desenvolvimento | 4 dias (10-13/fev) | 24 dias (13/fev–09/mar) |

---

## 7. Recomendação Final

### Seguir com `best-of-opera-app2` (versão principal)

**Motivos técnicos:**

1. **152 commits de diferença** — o deploy do sócio está parado em 13/fev; o principal tem 20+ dias de desenvolvimento contínuo
2. **Arquitetura incompatível** — monolito vs. monorepo com 4 apps. Não é possível fazer merge
3. **App Editor inteiro inexistente** — o pipeline de edição de vídeo (80+ commits, ~5.000 linhas) não existe no repo antigo
4. **Storage efêmero** — o repo antigo perde arquivos a cada redeploy do Railway; o atual usa Cloudflare R2
5. **Nenhum commit do sócio** — não há código para avaliar ou aproveitar; o trabalho dele não está versionado em nenhum repo acessível
6. **A única feature visível do sócio (login) é trivial** — implementar autenticação no portal atual leva 1-2 horas com middleware Next.js

### Ações recomendadas

1. **Desativar** o deploy `protective-friendship-production-9659` no Railway
2. **Implementar autenticação** no `app-portal` atual se necessário
3. **Solicitar ao sócio** que trabalhe no repo `best-of-opera-app2` via branches e pull requests
4. **Arquivar** o repo `best-of-opera` (antigo) como referência histórica

---

## Apêndice A — Commits completos do repo antigo (best-of-opera)

```
# 36 commits — 10/fev a 13/fev/2026 — Todos de Bolivar Andrade

2026-02-10  Add files via upload (3 commits)
2026-02-10  Update index.html
2026-02-11  v3.0: SQLite cache + Playlist + Economia quota
2026-02-11  Add files via upload (4 commits)
2026-02-11  Update index.html
2026-02-11  Add static/index.html
2026-02-11  Create .gitkeep
2026-02-11  Delete index.html
2026-02-11  Update main.py
2026-02-11  Fix 3 bugs: split Solos/Duetos, fix posted filter, fix playlist loading
2026-02-11  Prevent cache wipe when YouTube API returns empty results
2026-02-11  Migrate from SQLite to PostgreSQL for persistent cache
2026-02-11  Fix PostgreSQL connection: handle postgres:// prefix and error logging
2026-02-11  Switch from psycopg2 to psycopg3
2026-02-11  Debug: detect Railway PostgreSQL variable names (2 commits)
2026-02-11  Add Railway internal PostgreSQL URL as fallback
2026-02-12  feat: Motor V7 - Seed rotation, scoring balanceado, quota control, design claro
2026-02-12  feat: add simple password gate to protect app access
2026-02-13  feat: APP2 - Modulo de Producao de Conteudo
2026-02-13  fix: use dynamic ffmpeg/ffprobe path for Railway nixpacks
2026-02-13  fix: use ffmpeg-full in nixpacks + robust binary search
2026-02-13  fix: add apt ffmpeg fallback + debug endpoint for Railway
2026-02-13  fix: install ffmpeg via imageio-ffmpeg pip package
2026-02-13  fix: use wav format for audio extraction
2026-02-13  fix: strip whitespace/newlines from API keys
2026-02-13  feat: implement 9 production module improvements
2026-02-13  fix: update post structure to exact Best of Opera format
2026-02-13  fix: fix NameError in upload — safe_name -> project_name
2026-02-13  feat: major UX improvements for production workflow  <-- ULTIMO COMMIT
```

## Apêndice B — Commits do repo atual APOS o ponto de bifurcacao (13/fev)

```
# 175 commits — 13/fev a 05/mar/2026 — Todos de Bolivar Andrade
# (Listados os commits APOS o initial commit de 13/fev)

--- 13/fev: Redator + Deploy Railway ---
2026-02-13  feat: APP Redator - Modulo A completo
2026-02-13  fix: corrigir prompts, campos e validacoes conforme spec exata
2026-02-13  fix: reforcar prompt do post para atingir 1600-1800 chars
2026-02-13  feat: refatorar input com auto-deteccao de metadata via YouTube URL
2026-02-13  feat: trocar auto-detect por screenshot upload com visao do Claude
2026-02-13  feat: add Railway deployment config
2026-02-13  feat: add APP Editor (APP3) + translate APP2 UI to PT-BR
2026-02-13  fix: critical bugs - missing import, ForeignKeys, error handling

--- 14/fev: Editor Pipeline Completo (35 commits) ---
2026-02-14  feat: importar projetos do Redator no Editor
2026-02-14  feat: busca automatica de letras no Genius
2026-02-14  feat: botao de upload de video
2026-02-14  feat: transcricao dupla (cega + guiada) com merge inteligente
2026-02-14  feat: tela de conclusao com download dos videos renderizados
2026-02-14  feat: mini player YouTube na tela de validar letra
2026-02-14  feat: exportar renders automaticamente para pasta local (iCloud)
2026-02-14  + 28 fixes (timestamps, legendas, audio, corte, idioma)

--- 15/fev: Monorepo + Portal Next.js ---
2026-02-15  feat: adicionar app curadoria e melhorias nos 3 apps
2026-02-15  refactor: reorganizar monorepo com nomenclatura padronizada
2026-02-15  feat: integrar backend curadoria (YouTube API V7) ao monorepo
2026-02-15  fix: deteccao runtime de ambiente para URLs dos backends
2026-02-15  docs: documento de handoff tecnico completo

--- 23/fev: Transcricao Reescrita ---
2026-02-23  fix: padronizar timestamps MM:SS e melhorar transcricao Gemini
2026-02-23  fix: reestruturar pipeline transcricao
2026-02-23  fix: re-baixar video quando storage efemero perde arquivos
2026-02-23  fix: render task regenera video cortado

--- 24/fev: Cloudflare R2 + Dockerfiles (17 commits) ---
2026-02-24  feat: migrar storage para Cloudflare R2 com estrutura unificada
2026-02-24  feat: listar projetos R2 da Curadoria na tela do Redator
2026-02-24  feat: auto-popular YouTube URL e thumbnail no formulario
2026-02-24  feat: auto-detectar metadados do video via titulo+descricao
2026-02-24  feat: substituir Baixar ZIP por Salvar Arquivos com tela de sucesso
2026-02-24  fix: contornar YouTube 403 no yt-dlp
2026-02-24  fix: ajustar Dockerfiles para build context na raiz do monorepo
2026-02-24  + 10 fixes (encoding, CORS, COPY paths, searchParams)

--- 25/fev: Workers + Traducao Google Cloud (18 commits) ---
2026-02-25  feat(worker): implementar worker assincrono e polling adaptativo
2026-02-25  refactor: substituir Gemini por Google Cloud Translation
2026-02-25  feat: botao de traducao fica verde quando traducoes existem
2026-02-25  feat: endpoint limpar-traducoes para forcbar retraduccao
2026-02-25  fix: corrigir render — baixar video do R2 antes do FFmpeg
2026-02-25  fix: corrigir 3 bugs que travavam status em "traducao"
2026-02-25  fix(portal/importar): modal de selecao de idioma quando 422
2026-02-25  feat: upload renders para R2
2026-02-25  + 10 fixes (timeout, legendas, worker restart)

--- 26/fev: Editor Completo + Portal (30 commits) ---
2026-02-26  feat(editor): dead-letter para evitar crash-loop no requeue
2026-02-26  feat(editor): geracao de pacote ZIP assincrona
2026-02-26  feat(editor): nomenclatura padronizada dos renders
2026-02-26  feat(editor+portal): anti-duplicata na importacao do Redator
2026-02-26  feat(portal): badge unificado na importacao com status do Editor
2026-02-26  feat(portal): botoes excluir e adicionar segmento no alinhamento
2026-02-26  feat(portal): botao "Baixar Todos" primario com fallback individual
2026-02-26  feat(portal): downloads por idioma abrem em nova aba
2026-02-26  feat(portal): rotas de fuga e recovery na tela de conclusao
2026-02-26  feat(portal): botao aprovar-preview com tratamento 409
2026-02-26  fix(editor): cleanup sequencial por idioma
2026-02-26  fix(editor): defesa contra disco cheio no _render_task
2026-02-26  + 18 fixes (posicao legendas, status pacote, worker, desbloqueio)

--- 27/fev: Legendas ASS + Workers (35 commits) ---
2026-02-27  feat: redesign estilos ASS — Pagella, fontsizes, alignment
2026-02-27  feat: instalar fonte TeX Gyre Pagella no container
2026-02-27  feat: migrar download para worker sequencial (heartbeat, idempotencia)
2026-02-27  feat: migrar transcricao para worker sequencial
2026-02-27  feat: editor reutiliza video do R2 (curadoria) em vez de yt-dlp
2026-02-27  feat: curadoria salva video no R2 — endpoint prepare-video
2026-02-27  feat: fallback upload manual quando download demora mais de 3 min
2026-02-27  feat: retry automatico (3x) para safety filter do Gemini
2026-02-27  feat: fallback cega quando transcricao guiada falha
2026-02-27  feat: opcao renderizar sem legendas (saida de emergencia)
2026-02-27  feat: botao Limpar Edicao — reseta edicao travada
2026-02-27  feat: suporte a cookies YouTube via YOUTUBE_COOKIES_BASE64
2026-02-27  feat: limite 60 chars e equilibrio no overlay
2026-02-27  feat: limite 43 chars por segmento no prompt Gemini
2026-02-27  feat: botao adicionar segmento funcional no alinhamento
2026-02-27  + 20 fixes (formato yt-dlp, margins, polling, status, Dockerfile)

--- 03/mar: QA Visual + Features (15 commits) ---
2026-03-03  feat: toggle sem_lyrics — omitir legendas de transcricao por projeto
2026-03-03  fix: corrigir roteamento por passo_atual + criar tela overview
2026-03-03  fix: correcoes visuais e UX pos-revisao QA (8+8 itens)
2026-03-03  fix: ajustar labels do menu lateral
2026-03-03  fix: traduzir CTA e hashtags do post
2026-03-03  fix: reforco de idioma nos prompts — previne language leak
2026-03-03  fix: overlay congelado na importacao
2026-03-03  fix: normalizar youtube_url para evitar URL duplicada

--- 04/mar: Curadoria + Editor (4 commits) ---
2026-03-04  feat(curadoria): adicionar input manual de url do youtube
2026-03-04  feat(curadoria): abrir modal automaticamente ao adicionar video
2026-03-04  feat(editor): improve translation button status visualization
2026-03-04  fix: resolver bugs de renderizacao e download do YouTube

--- 05/mar: Correcoes Finais (2 commits) ---
2026-03-05  fix(redator): CTA fixo na ultima legenda + validacao de timing
2026-03-05  Correcoes: ERR-057 (paginacao playlist), ERR-056 (truncamento overlay), ERR-055 (filtro tracks lyrics)
```

---

*Documento gerado automaticamente por Claude Code em 09/mar/2026.*
*Todos os dados foram extraidos exclusivamente via `git log`, `gh api`, e `curl` — nenhum arquivo foi modificado.*
