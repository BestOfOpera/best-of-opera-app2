# Pacote Fase 3 — Implementação RC v3/v3.1 no Site de Produção

Este pacote contém tudo necessário para a Fase 3 do projeto Reels Classics: integrar no código do site os novos prompts v3/v3.1 e as decisões editoriais validadas pela auditoria.

---

## Ordem de uso dos prompts

A Fase 3 é executada em **duas sessões sequenciais** do Claude Code:

### Sessão 1 — Investigação

1. Copie todo o conteúdo deste pacote para um diretório no repositório do site (sugestão: `docs/rc_v3_migration/`)
2. Abra uma sessão Claude Code na raiz do repositório
3. Mensagem inicial: *"Leia `docs/rc_v3_migration/PROMPT_1_INVESTIGACAO.md` e siga as instruções."*
4. O Claude Code:
   - Confirma leitura (1 parágrafo)
   - Propõe plano de investigação (5-10 itens)
   - **Pausa** aguardando sua confirmação
5. Você aprova o plano
6. Claude Code executa investigação completa (15 dimensões)
7. Claude Code entrega `RELATORIO_INVESTIGACAO.md`
8. **Você revisa o relatório cuidadosamente**. Se precisar aprofundar alguma seção, peça ajuste.
9. Quando o relatório estiver aprovado, encerre a sessão.

**Não avance para a Sessão 2 sem o relatório aprovado.**

### Sessão 2 — Execução

1. Abra nova sessão Claude Code na raiz do repositório
2. Mensagem inicial: *"Leia `docs/rc_v3_migration/PROMPT_2_EXECUCAO.md` e `docs/rc_v3_migration/RELATORIO_INVESTIGACAO.md` e siga as instruções."*
3. O Claude Code aplica os patches na ordem proposta na seção 20 do relatório
4. Cada patch vira commit isolado
5. Smoke tests são rodados após cada patch
6. Teste E2E e teste de regressão narrativa ao final
7. Relatório de execução resume o que foi feito

---

## Por que duas sessões

Misturar investigação com execução tem dois problemas:

- A investigação fica enviesada pelo patch já planejado (confirmação em vez de descoberta)
- O contexto se torna grande demais, diluindo precisão

Separar força o Claude Code a **mapear o sistema como ele é** antes de considerar como ele deveria ser. O relatório entre as duas sessões é o contrato: ele captura o mundo real no qual o patch será aplicado.

---

## Conteúdo do pacote

### Prompts de trabalho (foco da Fase 3)

- `PROMPT_1_INVESTIGACAO.md` — sessão 1: mapeamento completo do repositório, 15 dimensões de investigação
- `PROMPT_2_EXECUCAO.md` — sessão 2: patches, atualização de consumidores, frontend, testes

### Anexos de código (para a sessão de execução)

- `rc_translation_prompt_v3.py` — prompt v3 patched (D.1)
- `rc_automation_prompt_v3.py` — prompt v3 patched (D.2)
- `rc_overlay_prompt_v3_1.py` — prompt v3.1 novo (D.3)

### Anexos de referência cruzada (SKILLs do app Claude)

Estes arquivos **não entram no código do site** — eles são a versão do app Claude (interface de chat separada) que vive em `/mnt/skills/user/rc-*/`. Estão aqui para o Claude Code consultar como **referência de comportamento esperado** do pipeline:

- `rc-overlay_SKILL.md`
- `rc-post_SKILL.md`
- `rc-translation_SKILL.md`
- `rc-research_SKILL.md`
- `rc-hooks_SKILL.md`
- `rc-automation_SKILL.md`

### Relatórios históricos

- `RELATORIO_LOTE_D.md` — contexto dos 3 patches v3/v3.1
- `RELATORIO_LOTES_A_B_C_F.md` — contexto das 6 SKILLs reescritas

---

## Observações

**SRTs do caso Beethoven/Roman Kim** (`romankin.srt` e `0420.srt`) **não fazem parte deste pacote** — eles são artefatos finais do sistema (saída pós-timestamps), não input de investigação nem de execução. Ficaram separados; use-os como material de validação empírica se quiser comparar manualmente o comportamento antigo vs esperado.

**Segurança de deploy**: a Sessão 2 (execução) aplica patches direto no código. Recomendado rodar em branch separado, revisar via pull request, e só fazer merge depois de smoke tests + teste E2E + regressão narrativa passarem.

**Em caso de dúvida durante qualquer sessão**: o Claude Code tem instrução para **parar e perguntar** em vez de inventar. Se ele fizer uma pausa e pedir esclarecimento, responda explicitamente — não autorize "faça do seu jeito" sem saber o que está autorizando.
