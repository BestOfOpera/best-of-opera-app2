# WORKFLOW PADRÃO — Todos os Projetos de Bolivar

## Fluxo por tarefa

PASSO 1 — BRIEFING (Claude.ai)
  Bolivar descreve o problema. Claude.ai gera prompt pronto para o Antigravity.

PASSO 2 — EXECUÇÃO (Antigravity + Gemini)
  Colar prompt. Executar com autonomia máxima. Gemini revisa antes de commitar.

PASSO 3 — REVISÃO AUTOMÁTICA
  Após cada implementação, verificar:
  - Inconsistências com o que existia antes?
  - Padrões arquiteturais quebrados?
  - Novos riscos introduzidos?

PASSO 4 — DOCUMENTAÇÃO
  Atualizar HISTORICO-ERROS do projeto. Commit separado só para docs.

PASSO 5 — APROVAÇÃO PARA PUSH
  Perguntar ao Bolivar: "Posso fazer o git push?" Aguardar ok explícito.

PASSO 6 — DEPLOY
  Após ok: git push → deploy automático Railway/Vercel.

## Checklist de revisão automática
- [ ] Sessões de banco fechadas antes de I/O externo?
- [ ] Imports dentro de try-except?
- [ ] Timeouts em operações externas?
- [ ] Sem valores fixos no código?
- [ ] Sem localStorage no frontend?
- [ ] Loading states implementados?
- [ ] Storage em R2/S3, nunca disco local?
