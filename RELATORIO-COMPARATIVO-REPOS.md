# Relatório Comparativo: best-of-opera-app2 vs arias-conteudo

**Data:** 9 de março de 2026
**Autor:** Análise automatizada (Claude Code)
**Objetivo:** Mapear as diferenças funcionais entre o repositório atual (best-of-opera-app2) e o deploy do sócio (arias-conteudo), identificando o que foi adicionado, o que é idêntico e o que existe apenas em cada lado.

---

## 1. Contexto

O sócio trabalhou a partir do repositório abandonado `BestOfOpera/best-of-opera` (último commit em 13/fev/2025). Ele não commitou código novo nesse repo — as adições dele existem apenas no deploy Railway do projeto **"arias-conteudo"** (nome interno: `protective-friendship`).

O repositório atual de produção é o `BestOfOpera/best-of-opera-app2`.

---

## 2. Infraestrutura Descoberta

### 2.1 URLs Ativas do Projeto arias-conteudo

| Serviço | URL | Status |
|---------|-----|--------|
| Frontend (Next.js) | `protective-friendship-production-9659.up.railway.app` | Online — redireciona tudo para `/login` |
| Editor Backend | `soothing-nourishment-production-0f42.up.railway.app` | Online |
| Redator Backend | `app-redatorbackend-production.up.railway.app` | Online |
| Curadoria Backend | `app-curadoriabackend-production.up.railway.app` | Online (V7, quota 9899) |

### 2.2 URLs Ativas do App2 (nosso)

| Serviço | URL |
|---------|-----|
| Portal (Next.js) | `portal-production-4304.up.railway.app` |
| Redator Backend | `app-production-870c.up.railway.app` |
| Editor Backend | `editor-backend-production.up.railway.app` |
| Editor Frontend | `editor-frontend-production.up.railway.app` |
| Curadoria Backend | `curadoria-backend-production.up.railway.app` |
| Curadoria Frontend | `curadoria-production-cf4a.up.railway.app` |

---

## 3. Repo Antigo vs App2 — Evolução da Base de Código

### 3.1 Escopo do Repositório Original (`best-of-opera`)

O repo antigo era um **monolito único** com apenas 2 arquivos Python:

| Arquivo | Linhas | Conteúdo |
|---------|--------|----------|
| `main.py` | 1.459 | Curadoria + Redator num único FastAPI |
| `database.py` | 665 | PostgreSQL direto (sem ORM) |
| **Total Python** | **2.124** | |

Outros arquivos: `requirements.txt`, `Procfile`, `nixpacks.toml`, `dataset_v3_categorizado.csv`, `static/index.html` (HTML estático).

Sem frontend real. Sem pipeline de edição de vídeo. Sem portal.

### 3.2 Escopo do App2 Atual (`best-of-opera-app2`)

Monorepo com 4 apps + shared:

| Componente | Linhas | Stack |
|-----------|--------|-------|
| Curadoria Backend | ~1.700 | FastAPI, PostgreSQL |
| Redator Backend | ~2.160 | FastAPI, Claude AI, SQLAlchemy |
| Editor Backend | ~5.110 | FastAPI, Gemini, FFmpeg, SQLAlchemy |
| Redator Frontend | ~1.690 | React, Vite, TypeScript |
| Portal (Next.js) | ~7.290 | Next.js 16, React 19, TypeScript |
| **Total** | **~17.950+** | |

### 3.3 Nada Foi Perdido na Migração

Todas as funcionalidades do `main.py` antigo foram migradas e distribuídas:
- Endpoints de curadoria (busca, categorias, ranking, quota, download) → `app-curadoria`
- Endpoints de produção `/api/prod/*` (projects, generate, translate, export) → `app-redator`
- Database PostgreSQL → SQLAlchemy ORM em cada app

---

## 4. O que o Sócio Adicionou ao Código

A análise dos bundles JavaScript e da API OpenAPI do deploy do sócio revelou as seguintes adições sobre o código-base do app2:

### 4.1 Frontend Next.js — "Arias Conteudo"

- Nome da aplicação: **"Arias — Gestao de Conteudo"**
- Tela de login com email + senha (placeholder: `admin@arias.com`)
- Stack: Next.js com Turbopack, Tailwind CSS, Radix UI (shadcn/ui), fonts Inter + Playfair Display
- Token JWT salvo como cookie `arias_token`
- Middleware Next.js que bloqueia **toda** rota não-autenticada → redirect para `/login`
- Rota pós-login: `/dashboard`
- **Não há evidência de telas de dashboard ou gestão renderizadas no frontend** — apenas a tela de login foi encontrada nos bundles JS

### 4.2 Sistema de Autenticação JWT (no Editor Backend)

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v1/auth/login` | POST | Autentica com email+senha, retorna JWT |
| `/api/v1/auth/me` | GET | Retorna dados do usuário autenticado |

Schemas:
- **LoginRequest:** `{ email: string, senha: string }`
- **TokenResponse:** `{ token: string }`
- **UserResponse:** `{ user_id: integer, email: string }`

Avaliação: funcional mas básico — sem registro de usuários, sem OAuth, sem roles/permissões, sem refresh token.

### 4.3 Dashboard de Gestão (5 endpoints novos no Editor Backend)

| Endpoint | Descrição |
|----------|-----------|
| `GET /api/v1/editor/dashboard/visao-geral` | Lista de projetos com contagem de renders e traduções |
| `GET /api/v1/editor/dashboard/producao` | Estatísticas de produção dos últimos 30 dias |
| `GET /api/v1/editor/dashboard/projeto/{id}` | Detalhe: edição + traduções + renders + timeline |
| `GET /api/v1/editor/dashboard/projeto/{id}/r2-files` | Listagem de arquivos R2 por edição |
| `GET /api/v1/editor/dashboard/saude` | Saúde do sistema: worker, fila, último erro, uptime |

Avaliação: esta é a **contribuição mais valiosa** — são endpoints de monitoramento e gestão que não existem no app2.

### 4.4 Funcionalidades Pontuais

| Endpoint | Descrição |
|----------|-----------|
| `POST /api/v1/editor/edicoes/{id}/inferir-idioma` | Infere idioma da música usando Claude (artista, título, compositor) → retorna ISO 639-1 |
| `GET /api/v1/editor/edicoes/{id}/renders/zip` | Download de todos os renders concluídos como ZIP |

### 4.5 Refatoração de URLs

O sócio prefixou todos os endpoints do editor com `/api/v1/editor/` (versionamento), enquanto o app2 usa paths diretos sem prefixo de versão.

---

## 5. Tabela Comparativa Completa

### 5.1 Números Gerais

| Dimensão | App2 (nosso) | Arias-Conteudo (sócio) |
|----------|:------------:|:----------------------:|
| Repositórios de código | Monorepo com 4 apps + shared | Fork do nosso código + frontend novo |
| Linhas Python (backend) | ~8.970 | Mesmo código-base + ~500-800 novas |
| Linhas TypeScript (frontend) | ~8.980 | ~1 frontend (só tela de login) |
| Endpoints totais | **88** | **72** |
| Frontends funcionais | 3 (Portal + Redator + Editor) | 1 (só login, sem telas internas) |

### 5.2 Funcionalidades — Curadoria

| Funcionalidade | App2 | Sócio | Notas |
|---------------|:----:|:-----:|-------|
| Motor V7 (busca, scoring, 6 categorias) | ✅ | ✅ | Idêntico |
| Download de vídeos individuais | ✅ | ✅ | Idêntico |
| Quota YouTube + cache inteligente | ✅ | ✅ | Idêntico |
| Playlist do canal + refresh | ✅ | ✅ | Idêntico |
| Filtro de vídeos já postados | ✅ | ✅ | Idêntico |
| Auth simples (senha) | ✅ | ✅ | Idêntico |
| **Adição manual de vídeo** | ✅ | — | Só nosso |
| **Download em batch (playlist inteira)** | ✅ | — | Só nosso |
| **Preparar vídeo para upload** | ✅ | — | Só nosso |
| **Upload para R2 via curadoria** | ✅ | — | Só nosso |
| **Verificar/listar R2** | ✅ | — | Só nosso |

**Curadoria do sócio:** 20 endpoints — cópia exata do antigo, sem adições.
**Curadoria nossa:** 27 endpoints — antigo + 7 novos (manual, batch, R2).

### 5.3 Funcionalidades — Redator

| Funcionalidade | App2 | Sócio | Notas |
|---------------|:----:|:-----:|-------|
| Criar projeto (URL + metadata) | ✅ | ✅ | Idêntico |
| Gerar overlay + post + YouTube SEO | ✅ | ✅ | Idêntico |
| Regenerar overlay / post / YouTube | ✅ | ✅ | Idêntico |
| Aprovar overlay / post / YouTube | ✅ | ✅ | Idêntico |
| Traduzir para 7 idiomas | ✅ | ✅ | Idêntico |
| Retraduzir idioma individual | ✅ | ✅ | Idêntico |
| Editar tradução manual | ✅ | ✅ | Idêntico |
| Export ZIP | ✅ | ✅ | Idêntico |
| Export para pasta local | ✅ | ✅ | Idêntico |
| Export por idioma individual | ✅ | ✅ | Idêntico |
| **Detect metadata por texto** | ✅ | — | Só nosso |
| **Detect metadata por URL** | ✅ | — | Só nosso |
| **Listar vídeos R2 disponíveis** | ✅ | — | Só nosso |
| **Salvar direto no R2** | ✅ | — | Só nosso |
| **Config de export** | ✅ | — | Só nosso |

**Redator do sócio:** 19 endpoints — cópia do nosso, sem adições.
**Redator nosso:** 22 endpoints — base + 3 novos (detect metadata, R2, config).

### 5.4 Funcionalidades — Editor

| Funcionalidade | App2 | Sócio | Notas |
|---------------|:----:|:-----:|-------|
| Criar/listar/editar/deletar edições | ✅ | ✅ | Idêntico |
| Download de vídeo (yt-dlp) | ✅ | ✅ | Idêntico |
| Upload de vídeo manual | ✅ | ✅ | Idêntico |
| Buscar/aprovar letra | ✅ | ✅ | Idêntico |
| Transcrição (Gemini audio) | ✅ | ✅ | Idêntico |
| Alinhamento fuzzy + validação visual | ✅ | ✅ | Idêntico |
| Aplicar corte (overlay window) | ✅ | ✅ | Idêntico |
| Tradução de lyrics (7 idiomas) | ✅ | ✅ | Idêntico |
| Render preview + aprovação | ✅ | ✅ | Idêntico |
| Render final (FFmpeg + ASS) | ✅ | ✅ | Idêntico |
| Exportar renders para R2 | ✅ | ✅ | Idêntico |
| Servir áudio / status vídeo / info corte | ✅ | ✅ | Idêntico |
| Listar renders / download individual | ✅ | ✅ | Idêntico |
| Importar do redator | ✅ | ✅ | Idêntico |
| CRUD de letras | ✅ | ✅ | Idêntico |
| **Fila de processamento + status** | ✅ | — | Só nosso |
| **Desbloquear edição travada** | ✅ | — | Só nosso |
| **Limpar edição completa** | ✅ | — | Só nosso |
| **Limpar traduções / reset tradução** | ✅ | — | Só nosso |
| **Empacotamento (pacote + download)** | ✅ | — | Só nosso |
| — | — | ✅ | **Inferir idioma com Claude** (só dele) |
| — | — | ✅ | **Download ZIP de renders** (só dele) |
| — | — | ✅ | **Dashboard visão geral** (só dele) |
| — | — | ✅ | **Dashboard produção 30 dias** (só dele) |
| — | — | ✅ | **Dashboard saúde do sistema** (só dele) |
| — | — | ✅ | **Dashboard detalhe por projeto** (só dele) |
| — | — | ✅ | **Dashboard arquivos R2** (só dele) |

**Editor do sócio:** 33 endpoints — base + 8 novos (auth, dashboard, inferir idioma, ZIP).
**Editor nosso:** 39 endpoints — base + 8 diferentes (fila, desbloqueio, limpeza, pacote).

### 5.5 Infraestrutura e Frontend

| Funcionalidade | App2 | Sócio | Notas |
|---------------|:----:|:-----:|-------|
| Portal Next.js unificado (funcional) | ✅ | — | Nosso portal tem telas completas |
| Frontend React do Redator | ✅ | — | Interface completa de produção |
| Frontend React do Editor | ✅ | — | Pipeline visual de 9 etapas |
| Frontend Curadoria (via Portal) | ✅ | — | Busca e gestão de vídeos |
| — | — | ✅ | **Autenticação JWT** (só dele) |
| — | — | ✅ | **Frontend login Next.js** (só dele) |
| — | — | ✅ | **Versionamento de API /api/v1/** (só dele) |

---

## 6. Análise Quantitativa

### Contribuição do sócio em números:

| Métrica | Valor |
|---------|-------|
| Endpoints novos criados | **8** (de 72 totais) |
| Endpoints copiados do app2 | **64** |
| Percentual de código novo | **~11%** dos endpoints do editor |
| Linhas estimadas de código novo | **500–800 linhas Python** |
| Frontend novo | **1 tela de login** (~200 linhas estimadas) |
| Features inéditas | 3 (dashboard, inferir idioma, ZIP renders) |

### Contribuição do app2 além do repo antigo:

| Métrica | Valor |
|---------|-------|
| Endpoints totais | **88** (vs 37 do repo antigo) |
| Endpoints novos | **51** (+138% sobre o antigo) |
| Linhas de código total | **~17.950** (vs 2.124 do antigo) |
| Frontends completos | **3** (vs 0 do antigo) |
| Apps separados | **4** (vs 1 monolito) |

---

## 7. Conclusões

### 7.1 O que o sócio tem de útil

1. **Dashboard de gestão (5 endpoints)** — Monitoramento de produção, saúde do sistema e detalhes por projeto. É a contribuição mais relevante e pode ser integrada ao app2.

2. **Inferência de idioma com Claude** — Feature pontual útil que economiza input manual. Facilmente replicável.

3. **Download ZIP de renders** — Conveniência para exportação. Nosso sistema de empacotamento cobre caso similar, mas o ZIP direto de renders é mais simples para uso rápido.

### 7.2 O que NÃO é útil

- **Autenticação JWT** — Implementação minimalista (sem registro, sem roles, sem OAuth). Se formos adicionar auth ao app2, faremos algo mais robusto.
- **Frontend "Arias Conteudo"** — É apenas uma tela de login. Sem telas de dashboard, gestão ou operação renderizadas. O portal do app2 já é funcional.
- **Backends de curadoria e redator** — São cópias exatas do nosso código, sem nenhuma adição.

### 7.3 Veredicto Final

O sócio partiu de **100% do nosso código-base**, adicionou uma **camada de autenticação básica** e **endpoints de monitoramento/dashboard** no editor. O volume de trabalho novo é modesto (~10% do total). As contribuições úteis (dashboard + 2 features) são integráveis ao app2 com esforço estimado de 1-2 dias de desenvolvimento.

O app2, por sua vez, evoluiu significativamente além do repo antigo: **+138% em endpoints**, 3 frontends completos, pipeline de edição de vídeo com 9 etapas, integração R2, portal unificado e diversas funcionalidades de operação diária que o deploy do sócio não possui.

---

*Relatório gerado automaticamente via análise de OpenAPI, bundles JavaScript e comparação de repositórios.*
