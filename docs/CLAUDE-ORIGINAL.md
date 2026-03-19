# CLAUDE.md — Best of Opera (BACKUP ORIGINAL)

> Este é o backup do CLAUDE.md original, antes da reorganização de workflow feita em 19/03/2026.
> Para restaurar: mover este arquivo para a raiz como `CLAUDE.md` e deletar o CLAUDE.md atual.

---

> Lido automaticamente a cada sessão. Mantenha enxuto (<120 linhas).
> Regra de ouro: se a info vive no código, REFERENCIE o arquivo — não copie o valor.

## O que é
Pipeline que transforma vídeos de ópera do YouTube em Reels com legendas ASS (3 tracks) em múltiplos idiomas para redes sociais. Canal principal: Best of Opera (6M+ seguidores).

## Stack
Python 3.11/FastAPI · Next.js · PostgreSQL · Railway (efêmero) · Cloudflare R2 · FFmpeg · Google Gemini · Google Cloud Translation · Claude Sonnet. Para detalhes atuais: ler `app-editor/backend/app/config.py` e `requirements.txt`.

## Monorepo
```
app-curadoria/    — curadoria de vídeos (Backend FastAPI apenas)
app-redator/      — conteúdo editorial (Backend FastAPI apenas)
app-editor/       — edição de vídeo (Backend FastAPI apenas)
app-portal/       — O "APP GERAL". Frontend Next.js para todos os serviços acima.
shared/           — storage_service.py (abstração R2)
dados-relevantes/ — credenciais, planos ATIVOS, configs
arquivo/          — planos concluídos e docs superados
```

## ⚠️ Nomenclatura e Frontend
- **Frontend / App Geral:** É EXCLUSIVAMENTE o `app-portal/`. NUNCA procure, edite ou crie arquivos de frontend dentro das pastas `app-editor`, `app-curadoria` ou `app-redator`.
- **Backend:** É dividido em `app-editor/backend`, `app-curadoria/backend`, e `app-redator/backend`.

## 👥 Agent Teams e Rotinas de Trabalho
A coordenação entre agentes segue a skill `workflow-completo-projetos`:
- **Antigravity (Gerente / Frontend):** Atua com prioridade máxima no desenvolvimento visual e frontend (`app-portal/`).
- **Claude Code (Backend / Infra):** Executa rotinas de backend, regras de negócio, deploy e segurança (`app-*/backend/`).
- **Paralelismo Seguro:** Ao agir em paralelo, os escopos de arquivos **NÃO PODEM** se cruzar. O Antigravity lidera o frontend e o Claude Code foca no backend de forma isolada. Múltiplos agentes no mesmo arquivo causam sobrescritas silenciosas.


## Início de sessão
1. Ler este arquivo (automático)
2. Ler `MEMORIA-VIVA.md` — estado atual do projeto
3. Se for mexer no editor: ler `app-editor/CLAUDE.md`
4. Se precisar de URLs/tokens: ler `dados-relevantes/`
5. **Sentry**: hook bash verifica issues automaticamente na 1ª mensagem do dia e injeta resumo. Se aparecer "SENTRY: N issue(s)", reportar ao Bolivar antes de continuar.

## Regras de operação
- Autonomia total em decisões técnicas — nunca perguntar ao Bolivar sobre código
- **Git push SOMENTE com aprovação explícita** ("pode fazer o push")
- SSH para git — HTTPS trava por Keychain do macOS
- Commits em português
- Variáveis novas DEVEM ter defaults seguros — nunca travar se não configurada
- Credenciais/tokens NUNCA neste arquivo — ficam em `dados-relevantes/`
- Este projeto usa **PLANO-DE-ACAO** (sistema padrão) — BLAST Fase 2 concluído e arquivado em `arquivo/`

## Armadilhas conhecidas (o que o Claude erra neste projeto)
Estas são armadilhas reais, baseadas em 57+ bugs documentados em `HISTORICO-ERROS-CORRECOES.md`:

1. **Imports fora do try em tasks do worker** → status preso pra sempre (ERR-004)
2. **except Exception em vez de BaseException** → CancelledError escapa, status preso (ERR-006)
3. **Sessão de banco aberta durante I/O externo** → conexão morre, task trava
4. **BackgroundTasks do FastAPI** → PROIBIDO. Sem recovery. Usar worker sequencial
5. **Arquivo local sem upload pro R2** → container reinicia, arquivo desaparece (ERR-003)
6. **Railway GraphQL API de dentro do Claude Code** → Cloudflare bloqueia. Usar curl no terminal local
7. **git push via HTTPS** → trava esperando Keychain (ERR-038)
8. **requeue_stale_tasks checando heartbeat no startup** → nada está rodando no startup, heartbeat é mentira (ERR-007)
9. **Copiar valores do código pra documentação** → fica desatualizado. Referenciar o arquivo fonte
10. **Declarar bug "corrigido" sem verificação end-to-end** → bug reaparece na sessão seguinte. REGRA: nunca dizer "corrigido" sem confirmar que o OUTPUT FINAL mudou (não basta ler o código)
11. **Corrigir UMA ponta da cadeia e parar** → dado nasce no banco, passa por API, processamento e chega no output. Corrigir só uma camada não resolve. REGRA: mapear a cadeia completa (origem → transporte → processamento → output) ANTES de corrigir
12. **Uma causa raiz por sessão** → bugs recorrentes têm múltiplas causas simultâneas. REGRA: investigar até não ter mais "e se..." pendentes, documentar TODAS as causas, só depois corrigir
13. **Fix parcial documentado como completo** → se falta dado no banco, ou deploy, ou teste, o bug NÃO está corrigido. REGRA: documentar pendências como BLOCKER, não como "corrigido"

## Auto-atualização (OBRIGATÓRIO)
Ao FINAL de toda sessão que altere código ou tome decisões:
1. Atualizar `MEMORIA-VIVA.md` com: data, o que foi feito, decisões tomadas
2. Se encontrou/corrigiu bug: atualizar `HISTORICO-ERROS-CORRECOES.md`
3. Se descobriu armadilha nova: adicionar à lista acima neste arquivo
4. Se um plano foi concluído: mover de `dados-relevantes/` para `arquivo/`

## Onde buscar contexto
| Preciso de... | Ler... |
|---------------|--------|
| Estado atual do projeto | `MEMORIA-VIVA.md` |
| Regras de código do editor | `app-editor/CLAUDE.md` |
| Bugs conhecidos (57+) | `HISTORICO-ERROS-CORRECOES.md` |
| Planos ativos | `dados-relevantes/` |
| URLs e tokens | `dados-relevantes/` |
| Decisões técnicas pontuais | `DECISIONS.md` |

## Decisões fechadas (não rediscutir)
- Railway horizontal scaling, não Transloadit
- cobalt.tools como primário pra download (cascata: local → R2 → cobalt → curadoria → yt-dlp)
- Google Cloud Translation, não Gemini pra tradução
- Preview sempre em PT (audiência principal)
- Curadoria é autoridade de vídeo — editor não re-baixa

## Glossário (evitar confusão de nomenclatura)
- **app-editor** = pipeline de processamento de vídeo (download→render→pacote). NÃO é um "editor visual"
- **Edição / Edicao** = um "job" de processamento (registro no banco), não o ato de editar
- **app-curadoria** = descoberta e seleção de vídeos no YouTube
- **app-redator** = criação de conteúdo editorial (posts, SEO, hashtags)
- **app-portal** = frontend Next.js ÚNICO para todos os serviços
- **Perfil** = configuração de marca/canal (multi-brand), NÃO perfil de usuário

## Equivalência de documentação obrigatória
Este projeto usa estrutura própria em vez de PRD/ARCHITECTURE/ROADMAP:
- PRD → `CLAUDE.md` (seção "O que é")
- ARCHITECTURE → `app-editor/CLAUDE.md` + código fonte (referenciado, não copiado)
- ROADMAP → `PLANO-DE-ACAO-[data].md` na raiz (plano ativo mais recente)
