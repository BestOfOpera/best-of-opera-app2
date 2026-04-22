# Lote D — Relatório de Entrega

*Três patches aplicados em prompts v3/v3.1. Todos validados programaticamente. Arquivos finais em `/mnt/user-data/outputs/lote_d/`.*

---

## Sumário executivo

| Patch | Ficha | Arquivo | Linhas alteradas | Status |
|---|---|---|---:|---|
| D.1 | F6.7 (escopo ampliado) | `rc_translation_prompt_v3.py` | 22 adicionadas / 22 removidas (±0 líquido) | ✓ validado |
| D.2 | F5.2 | `rc_automation_prompt_v3.py` | 10 adicionadas (+10 líquido) | ✓ validado |
| D.3 | F3.11 | `rc_overlay_prompt_v3_1.py` | 9 adicionadas / 1 removida (+8 líquido) | ✓ validado |

**Total: 3 arquivos alterados, 41 linhas adicionadas, 23 removidas (+18 líquido).** Bem dentro da regra "até 30 linhas por arquivo sem aprovação extra" que o sistema estabelece.

---

## D.1 — `rc_translation_prompt_v3.py` (F6.7 expandida)

### Escopo

Ficha original F6.7 previa corrigir Exemplo 1 da seção `<examples>`. Ao rodar validação programática em toda a seção, identifiquei que **13 de 20 contagens** tinham erros, sendo **3 em quebra de lógica pedagógica** (ensinavam modelo a rejeitar traduções que cabem em 38 chars). O 3º bug estava no Exemplo 3 FR — não apontado pela F6.7 original. Escopo ampliado para cobrir os 3 exemplos, justificado pela instrução da Parte 2 do documento de fechamento: "recontar todos os exemplos com rigor programático".

### Mudanças

- **Exemplo 1** reescrito integralmente. Nova tradução inicial (`At that moment, it had been six years / since he began fighting a worsening deafness.`) genuinamente estoura 38 chars na linha 2 (45 chars reais). Reformulação (`By that point, six years had passed / with his deafness only getting worse.`) cabe (35/37). Pedagogia preservada.
- **Exemplo 2** (alemão): contagem L2 corrigida de 35 → 34.
- **Exemplo 3** reescrito. Removida a falsa "Tentativa 2" que existia só por causa do bug de contagem. Nova versão mostra ES e FR "aceita direto", com nota sobre alternativas idiomáticas quando ambas cabem.

### Validação

12 declarações `Linha N: X chars` no arquivo patched, contadas programaticamente: **12/12 corretas**. Nenhum erro off-by-1, nenhum erro grave. Smoke test do `build_rc_translation_prompt()`: prompt gerado de 19511 chars, Exemplo 1 novo presente, strings corretas.

### Risco colateral

Zero. Apenas os 3 exemplos mudaram. Toda a lógica de task, constraints, quebra_de_linha, vocabulário banido, CTAs e format permaneceu intocada. Os CTAs da Decisão 5 F6.8 (com pronome em de/fr/it/pl) **não** foram aplicados neste patch — entram no Lote C conforme planejado.

---

## D.2 — `rc_automation_prompt_v3.py` (F5.2)

### Escopo

Parâmetro `post_text` era recebido em `build_rc_automation_prompt()` mas não entrava no prompt LLM — parâmetro morto. Decisão do operador: usar.

### Mudanças

Dois trechos adicionados:

1. Antes do f-string, cálculo do `post_summary` com truncamento em 500 chars e reticências se necessário:
   ```python
   post_clean = (post_text or "").strip()
   if len(post_clean) > 500:
       post_summary = post_clean[:500].rstrip() + "..."
   else:
       post_summary = post_clean
   ```
2. Dentro do `<context>` do prompt, bloco novo logo após `OVERLAY (contexto narrativo)`:
   ```
   DESCRIÇÃO APROVADA (para consistência de tom, emojis e temas complementares):
   {post_summary}
   ```

### Validação

Smoke test: `build_rc_automation_prompt()` invocado com `post_text` longo (600+ chars); prompt gerado inclui `DESCRIÇÃO APROVADA` e o truncamento `...` aparece. Quando `post_text` vem vazio ou curto, o bloco ainda aparece (vazio ou com texto inteiro), sem quebrar renderização.

### Risco colateral

O prompt LLM cresce em ~50-500 chars dependendo do tamanho da descrição. Estimativa de token cost no briefing era 2000-3000 input para automation; agora sobe para até ~3500 no pior caso. Dentro do budget mas bom registrar.

---

## D.3 — `rc_overlay_prompt_v3_1.py` (F3.11)

### Escopo

Fase 5 do overlay contém verificações V1 (fio), V4 (cena), V5 (evidente) que podem **remover legendas candidatas** sem registrar no output. Isso é corte consciente, mas sem rastreamento vira corte silencioso na prática — viola regra inviolável de texto nunca cortado sem intervenção humana registrada.

### Mudanças

1. Campo `cortes_aplicados` adicionado ao schema de `verificacoes` no `<format>`:
   ```json
   "cortes_aplicados": [
     {
       "tipo": "fio_secundario | evidente | cena_generica | repeticao",
       "texto_candidato": "texto que seria legenda se não fosse cortado",
       "motivo": "explicação em 1 linha de por que foi cortado"
     }
   ]
   ```
2. Instrução operacional adicionada ao bloco `IMPORTANTE:` do `<format>`, explicando que qualquer corte pelas V1/V4/V5 ou por repetição deve ser registrado no campo. Se nenhum corte foi feito, array vazio.

### Validação

Smoke test: `build_rc_overlay_prompt()` gera prompt de 31194 chars; contém `cortes_aplicados`, `REGISTRO DE CORTES`, `<fio_narrativo_dinamico>`, `<duracao_dinamica>`. Nenhuma seção preexistente foi perdida.

### Risco colateral

Zero funcional. Todos os consumidores do JSON de saída (já especificados no briefing como `process_overlay_rc()` e validadores) só precisam aceitar o campo novo; campos existentes não foram alterados. O modelo pode agora emitir `cortes_aplicados: []` quando não houver cortes — é o caso default, não quebra nada.

---

## O que vem a seguir (não executado neste turno)

Este relatório cobre apenas o Lote D. Ainda pendentes para execução conforme autorização do documento de fechamento v2:

- **Lote A** (SKILL overlay) — referência: v3.1 agora disponível. Draft em elaboração.
- **Lote B** (SKILL post) — referência: prompt v3 post. Draft em elaboração (foi interrompido pelo upload do v3.1; retomo em seguida).
- **Lote C** (SKILL translation) — inclui CTAs Decisão 5.
- **Lote F** (SKILLs research + hooks + automation).

Conforme o fluxo acordado: entrego os drafts dos 4 lotes via `present_files`, operador aprova em bloco, aplico.

---

## Protocolo de validação usado nesta rodada

Cada afirmação numérica neste relatório passou por validação programática via Python antes de ser escrita. Script de validação e outputs reproduzíveis em `/home/claude/rc_audit/tools/` e inline nos turnos de conversa.

Qualquer dúvida sobre contagem específica, o operador pode rodar `len()` no texto correspondente para reproduzir o número.
