# CLAUDE.md — Best of Opera

> Lido automaticamente a cada sessão. Mantenha enxuto (<120 linhas).
> Regra de ouro: se a info vive no código, REFERENCIE o arquivo — não copie o valor.

## O que é
Pipeline que transforma vídeos de ópera do YouTube em Reels com legendas ASS (3 tracks) em múltiplos idiomas para redes sociais. Canal principal: Best of Opera (6M+ seguidores).

## Stack
Python 3.11/FastAPI · Next.js · PostgreSQL · Railway (efêmero) · Cloudflare R2 · FFmpeg · Google Gemini · Google Cloud Translation · Claude Sonnet. Para detalhes atuais: ler `app-editor/backend/app/config.py` e `requirements.txt`.

## Monorepo
```
app-curadoria/    — curadoria de vídeos
app-redator/      — conteúdo editorial
app-editor/       — edição de vídeo (FOCO) → tem seu próprio CLAUDE.md
app-portal/       — frontend Next.js compartilhado
shared/           — storage_service.py (abstração R2)
dados-relevantes/ — credenciais, planos ATIVOS, configs
arquivo/          — planos concluídos e docs superados
```

## Início de sessão
1. Ler este arquivo (automático)
2. Ler `MEMORIA-VIVA.md` — estado atual do projeto
3. Se for mexer no editor: ler `app-editor/CLAUDE.md`
4. Se precisar de URLs/tokens: ler `dados-relevantes/`

## Regras de operação
- Autonomia total em decisões técnicas — nunca perguntar ao Bolivar sobre código
- **Git push SOMENTE com aprovação explícita** ("pode fazer o push")
- SSH para git — HTTPS trava por Keychain do macOS
- Commits em português
- Variáveis novas DEVEM ter defaults seguros — nunca travar se não configurada
- Credenciais/tokens NUNCA neste arquivo — ficam em `dados-relevantes/`

## Armadilhas conhecidas (o que o Claude erra neste projeto)
Estas são armadilhas reais, baseadas em 57+ bugs documentados em `HISTORICO-ERROS-CORRECOES-APP-EDITOR.md`:

1. **Imports fora do try em tasks do worker** → status preso pra sempre (ERR-004)
2. **except Exception em vez de BaseException** → CancelledError escapa, status preso (ERR-006)
3. **Sessão de banco aberta durante I/O externo** → conexão morre, task trava
4. **BackgroundTasks do FastAPI** → PROIBIDO. Sem recovery. Usar worker sequencial
5. **Arquivo local sem upload pro R2** → container reinicia, arquivo desaparece (ERR-003)
6. **Railway GraphQL API de dentro do Claude Code** → Cloudflare bloqueia. Usar curl no terminal local
7. **git push via HTTPS** → trava esperando Keychain (ERR-038)
8. **requeue_stale_tasks checando heartbeat no startup** → nada está rodando no startup, heartbeat é mentira (ERR-007)
9. **Copiar valores do código pra documentação** → fica desatualizado. Referenciar o arquivo fonte

## Auto-atualização (OBRIGATÓRIO)
Ao FINAL de toda sessão que altere código ou tome decisões:
1. Atualizar `MEMORIA-VIVA.md` com: data, o que foi feito, decisões tomadas
2. Se encontrou/corrigiu bug: atualizar `HISTORICO-ERROS-CORRECOES-APP-EDITOR.md`
3. Se descobriu armadilha nova: adicionar à lista acima neste arquivo
4. Se um plano foi concluído: mover de `dados-relevantes/` para `arquivo/`

## Onde buscar contexto
| Preciso de... | Ler... |
|---------------|--------|
| Estado atual do projeto | `MEMORIA-VIVA.md` |
| Regras de código do editor | `app-editor/CLAUDE.md` |
| Arquitetura detalhada | `CONTEXTO-CODIGO-FINAL.md` |
| Histórico de decisões | `MEMORIAL-REVISAO-EDITOR.md` |
| Bugs conhecidos (57+) | `HISTORICO-ERROS-CORRECOES-APP-EDITOR.md` |
| Planos ativos | `dados-relevantes/` |
| URLs e tokens | `dados-relevantes/` |
| Decisões técnicas pontuais | `DECISIONS.md` |

## Decisões fechadas (não rediscutir)
- Railway horizontal scaling, não Transloadit
- cobalt.tools planejado como primário pra download (yt-dlp atual como backup)
- Google Cloud Translation, não Gemini pra tradução
- Preview sempre em PT (audiência principal)
- Curadoria é autoridade de vídeo — editor não re-baixa
