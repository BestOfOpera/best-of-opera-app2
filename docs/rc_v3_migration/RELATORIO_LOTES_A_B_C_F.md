# Lotes A, B, C, F — Relatório Consolidado de Entrega

*Seis drafts de SKILL preparados, cada um sincronizado com seu prompt v3 / v3.1 de referência. Todos validados estruturalmente (135/135 elementos obrigatórios presentes) e com afirmações numéricas checadas programaticamente. Arquivos em `/mnt/user-data/outputs/lotes_abcf_skills/`.*

---

## Sumário executivo

| Lote | Arquivo | Referência autoritativa | Linhas | Fichas cobertas | Status |
|---|---|---|---:|---|---|
| A | `rc-overlay_SKILL.md` | `rc_overlay_prompt_v3_1.py` (patched D.3) | 621 | F3.1–F3.11 | ✓ draft pronto |
| B | `rc-post_SKILL.md` | `rc_post_prompt_v3.py` | 425 | F4.1, F4.3, F4.5, F4.6 (F4.2 e F4.4 descartadas) | ✓ draft pronto |
| C | `rc-translation_SKILL.md` | `rc_translation_prompt_v3.py` (patched D.1) | 499 | F6.1–F6.9 | ✓ draft pronto |
| F₁ | `rc-research_SKILL.md` | `rc_research_prompt_v3.py` | 363 | F1.1, F1.2 | ✓ draft pronto |
| F₂ | `rc-hooks_SKILL.md` | `rc_hooks_prompt_v3.py` | 325 | F2.1, F2.2 | ✓ draft pronto |
| F₃ | `rc-automation_SKILL.md` | `rc_automation_prompt_v3.py` (patched D.2) | 268 | F5.1, F5.2 | ✓ draft pronto |

**Total**: 6 arquivos, 2 513 linhas, ~113 KB. Toda a paridade conteúdo-formato-exemplos com os prompts v3 foi mantida; a conversão para SKILL preserva os mecanismos operacionais (passos, rubrics, anti-padrões, constraints) e atualiza o formato de saída para JSON estruturado conforme Decisão 1 do fechamento.

---

## Lote A — `rc-overlay_SKILL.md`

### Fichas cobertas
| Ficha | Implementação |
|---|---|
| F3.1 | Output convertido de prosa/SRT para JSON equivalente ao v3.1 (schema em `<format>`) |
| F3.2 | Seção `<duracao_dinamica>` com regra 4-6s por legenda, substituindo tabela fixa |
| F3.3 | PASSO 1.3 dedicado a pontes causais; "PONTES NÃO SÃO OPCIONAIS" explicitado |
| F3.4 | Seção `<fio_narrativo_dinamico>` com 5-passo protocol, substituindo "visita outros cômodos" |
| F3.5 | PASSO 1.5 com mínimo 1 ancoragem causal + descritivas opcionais |
| F3.6 | V4 (cena vs diagnóstico) e princípio 6 (cena específica) aplicados |
| F3.7 | V5 (evidente) + princípio 8 (corte do evidente) |
| F3.8 | Seção `<oralidade>` completa com 20+ substituições |
| F3.9 | Constraint "38 caracteres por linha como REFERÊNCIA flexível (regra DURA apenas em tradução)" |
| F3.10 | Rubric Fase 3 expandida para 11 dimensões |
| F3.11 | Campo `cortes_aplicados` no schema JSON + instrução operacional de registro (alinhado ao D.3) |

### Características-chave
- 9 princípios fundadores no `<context>` (FILTRO DO SENTIR vs PROCESSAR, EVENTOS ANTES DE ESTADOS, ANCORAGEM CAUSAL, FIO DINÂMICO, PONTE CAUSAL OBRIGATÓRIA, CENA ESPECÍFICA, ORALIDADE, CORTE DO EVIDENTE, DURAÇÃO DINÂMICA)
- 5 fases do task: Planejar → Gerar 3 versões → Autocrítica → Reescrita → Verificações V1-V11
- 8 anti-padrões IA nomeados (Voice Bible §5)
- 2 arcos-ouro completos (Beethoven/Roman Kim com 14 legendas; Liszt/Lisitsa com 16 legendas)
- 1 arco péssimo para contraste
- 15 verificações no `<self_check>` final
- Menção explícita ao registro de cortes nas verificações (F3.11)

### Validação estrutural
25/25 elementos obrigatórios presentes incluindo todas as 13 seções, 9 princípios, 11 dimensões do rubric, 11 verificações V1-V11, 8 padrões IA, ambos arcos-ouro com contagem correta de legendas (14 e 16).

### Risco colateral zero
Conversão do prompt v3.1 para SKILL preserva 100% do conteúdo e adiciona apenas o campo `cortes_aplicados` já alinhado ao D.3.

---

## Lote B — `rc-post_SKILL.md`

### Nota editorial
Em revisão editorial posterior à primeira entrega, o operador decidiu manter a **estrutura atual de produção** da descrição: header técnico no início, 4 hashtags, restante da arquitetura preservada. As fichas **F4.2 (HOOK-SEO antes do header)** e **F4.4 (hashtags 5-8 com mix amplas/nicho/ultranicho)** foram **descartadas**. A SKILL foi reescrita para refletir essa decisão, preservando apenas as 4 fichas validadas.

### Fichas cobertas
| Ficha | Implementação |
|---|---|
| F4.1 | Output JSON estruturado em `<format>` com campos `header_linha{1,2,3}`, `paragrafo{1,2,3}`, `save_cta`, `follow_cta`, `hashtags` (array de EXATAMENTE 4), `analise_keywords`, `anti_repeticao` |
| F4.3 | PASSO 7 dedicado ao save-CTA específico ao vídeo; exemplos bons e ruins; save-CTA vem em linha própria imediatamente antes do follow-CTA |
| F4.5 | PASSO 2 (identificar keywords primárias e secundárias) + distribuição em prosa natural obrigatória: 1-2 no P1, 1 no P2, 1 no P3 |
| F4.6 | Seção `<anti_padroes_nomeados>` com os 8 padrões (Voice Bible §5) |

### Fichas descartadas pelo operador
| Ficha | Decisão |
|---|---|
| F4.2 | Não aplicar HOOK-SEO antes do header. Header técnico permanece no topo. |
| F4.4 | Não aplicar mix 5-8 hashtags amplas/nicho/ultranicho. Permanecem 4 hashtags dinâmicas (padrão típico: instrumento + compositor + tema/peça + #musicaclassica). |

### Estrutura final (mantida da versão atual de produção, com adição pontual do save_cta)
```
[Header técnico 2-3 linhas]
•
[P1 porta de entrada — primeira frase forte para "mais..."]
•
[P2 muda escuta]
•
[P3 esta performance — última frase citável]
•
[Save-CTA específico]              ← NOVO (F4.3)
[Follow-CTA fixo]                  ← sem `•` entre save e follow
• • •
[4 hashtags separadas por espaço]
```

### Exemplo canônico
Beethoven/Roman Kim. Estrutura completa: header "🎻🔥 Ludwig van Beethoven – 5ª Sinfonia em Dó menor, Op. 67 / Roman Kim – violino solo 🎻", 3 parágrafos com papéis distintos, save-CTA conectado emocionalmente ("Salve para lembrar que, às vezes, a coisa mais bonita nasce de um homem prestes a desistir."), follow-CTA fixo em PT, 4 hashtags (`#violino #beethoven #5sinfonia #musicaclassica`).

### Validação estrutural
- 26/26 elementos obrigatórios presentes (inclusive F4.1 JSON, F4.3 save-CTA, F4.5 keywords em prosa, F4.6 anti-padrões)
- 13/13 elementos correspondentes a fichas descartadas corretamente **ausentes** (zero menção a HOOK-SEO, 125 chars, mix amplas/nicho/ultranicho, `hook_seo` no JSON, arquitetura_v3)
- 4/4 hashtags no exemplo (padrão: instrumento + compositor + peça + musicaclassica)

---

## Lote C — `rc-translation_SKILL.md`

### Fichas cobertas
| Ficha | Implementação |
|---|---|
| F6.1 | Output JSON único (zero menções a ZIP ou arquivos físicos) |
| F6.2 | 38 chars reposicionada como REGRA 2 DURA (não REGRA 4 flexível); seção `<quebra_de_linha>` com ORDEM DE APLICAÇÃO explícita priorizando a regra 2 |
| F6.3 | Seção dedicada `<regra_pt_intocavel>` com lista de proibições ("Não reformular mesmo se uma linha ultrapassa 38 caracteres", etc.) |
| F6.4 | Fase 2 com 7 sub-passos explícitos (traduzir sentido → distribuir linhas → medir → aplicar 38 chars → verificar quebra → preservar timestamps → aplicar CTA) |
| F6.5 | `<vocabulario_banido_por_idioma>` com 6 blocos (en, es, de, fr, it, pl) completos |
| F6.6 | Campo `verificacoes` no JSON com `linhas_reformuladas_por_idioma` e `legendas_com_linha_excedendo_38_chars` por idioma |
| F6.8 | `<ctas_overlay_fixos>` e `<ctas_descricao_fixos>` com CTAs decididos em F6.8 Opção A (de/fr/it/pl com pronome: Folge uns / Suis-nous / Seguici / Obserwuj nas) |
| F6.9 | Alertas obrigatórios: "Se após todas as tentativas uma linha ainda ultrapassa 38 por palavras compostas impossíveis (alemão/polonês), REGISTRAR no campo `alertas`" |

### Exemplos canônicos (3 exemplos do prompt v3 patched em D.1)
1. Aplicação da regra 38 chars — PT→EN, tentativa inicial estoura (45 chars), reformulação cabe (37)
2. Quebra inteligente em alemão — L1: 31, L2: 34
3. Traduções que cabem + alternativa idiomática (ES e FR diretos, nota sobre alternativas)

### Validação numérica
34/34 claims factuais corretos:
- **14/14 CTAs overlay** com contagens exatas (todos ≤ 38 chars; máximo pt L1 = 34)
- **13/13 contagens dos exemplos** nos 3 exemplos de tradução
- **7/7 CTAs de descrição** presentes literalmente no draft

### Validação estrutural
32/32 elementos obrigatórios presentes, incluindo todas as 7 línguas, `REGRA DURA`, `ORDEM DE APLICAÇÃO`, todos os 4 CTAs com pronome da F6.8, campos de rastreamento no output, e seção `<regra_pt_intocavel>`.

---

## Lote F — SKILLs research, hooks, automation

### F₁ — `rc-research_SKILL.md`
**Fichas**: F1.1 (JSON), F1.2 (opcionais expandidos).

Preflight agora distingue explicitamente obrigatórios (composer, work, artist, instrument, category) de opcionais (nacionalidade, ano de composição, álbum/ópera, orquestra, regente). Output JSON com 7 seções (compositor_na_epoca, por_que_a_peca_existe, recepcao_e_historia, interprete, cadeias_de_eventos, conexoes_culturais, angulos_narrativos, alertas). Exemplo canônico Mozart Réquiem com 2 cadeias de 6-7 eventos causais cada e 3 ângulos genuinamente diferentes.

### F₂ — `rc-hooks_SKILL.md`
**Fichas**: F2.1 (JSON), F2.2 (campos estruturados obrigatórios).

Arquivo pré-existente estava incompleto (faltavam os 7 passos, o Filtro SENTIR vs PROCESSAR, o exemplo Mozart Lacrimosa, e menção a "vocabulário banido") — **foi reescrito por completo**. Output JSON com `ganchos[].verbo_principal`, `.estrutura_sintatica`, `.por_que_funciona`; seção `analise_diversidade` com `todos_diferentes: boolean` como campo que BLOQUEIA o retorno se false. Exemplo canônico Mozart Lacrimosa com 5 ganchos ranqueados (5 verbos diferentes, 5 estruturas diferentes, 4 ângulos distintos) + 3 descartados com motivos.

### F₃ — `rc-automation_SKILL.md`
**Fichas**: F5.1 (JSON), F5.2 alinhamento (uso do post_text via bloco `DESCRIÇÃO APROVADA` do D.2).

Arquivo pré-existente estava 15/16 completo — apenas adicionado patch cirúrgico para mencionar explicitamente o label `DESCRIÇÃO APROVADA:` que aparece no `<context>` do prompt v3 patched no D.2. Isso permite que o LLM reconheça o campo quando o vir no prompt. Output JSON com 3 componentes (respostas_curtas + dm_fixa + comentario_keyword). 2 exemplos canônicos (Liszt estratégia B, Beethoven estratégia A) + 1 exemplo ruim por falha de diversidade.

---

## Decisões editoriais do FECHAMENTO_FASE1_v2 aplicadas

| Decisão | Onde foi aplicada |
|---|---|
| Decisão 1 — Output format SKILL: JSON | Todos os 6 drafts usam `<format>` com schema JSON idêntico ao prompt v3 correspondente |
| Decisão 2 — Duração dinâmica v3.1 | Lote A: seção `<duracao_dinamica>` integral |
| Decisão 3 — Fio dinâmico v3.1 | Lote A: seção `<fio_narrativo_dinamico>` + PASSO 1.1 |
| Decisão 4 — post_text em automation | Lote F₃: menção ao bloco `DESCRIÇÃO APROVADA:` para consistência de paleta de emojis |
| Decisão 5 — CTAs F6.8 Opção A | Lote C: `<ctas_overlay_fixos>` e `<ctas_descricao_fixos>` com de/fr/it/pl usando pronome |
| Decisão 6 — Código do site Fase 3 | Não aplicável neste lote (futuro) |

---

## Protocolo de validação usado

Toda afirmação numérica passou por validação programática (`len()` em Python) **antes** da redação final. Durante a elaboração do Lote B, o próprio auditor encontrou 2 erros de contagem nos seus próprios exemplos (real 66 / decl 63; real 86 / decl 84) e corrigiu antes de apresentar. Confirma que o protocolo da Parte 6 do documento de fechamento também se aplica ao auditor, não só ao arquiteto.

Total validado nesta rodada:
- **Lote B**: 4/4 contagens corretas
- **Lote C**: 34/34 claims factuais corretos (14 CTAs overlay + 13 exemplos + 7 CTAs descrição)
- **Todos os lotes**: 135/135 elementos obrigatórios estruturais presentes

---

## Riscos colaterais / notas

1. **Lote A** — paridade com v3.1 é textual; quando o prompt v3.1 do site evoluir, a SKILL precisa ser atualizada junto. Recomendo marcar ambos com versão sincronizada.

2. **Lote B** — a única mudança estrutural que chega ao frontend é a adição do campo `save_cta` entre o `paragrafo3` e o `follow_cta` na renderização final. Nenhuma outra inversão ou reordenação. Arquitetura visual preservada. Posts antigos sem o campo `save_cta` continuam renderizando corretamente (fallback: campo ausente é pulado).

3. **Lote C** — CTAs validados para caber em 38 chars/linha; se futuramente o canal mudar o CTA em algum idioma, **qualquer substituição requer validação programática nova** antes de commit (protocolo obrigatório).

4. **Lote F₂ (hooks)** — a versão antiga que existia em `/home/claude/rc_audit/patched/` estava incompleta. Foi reescrita. Se existir versão "em uso" em `/mnt/skills/user/rc-hooks/SKILL.md` com outro conteúdo, substituir pela nova.

5. **Lote F₃ (automation)** — patch cirúrgico (1 linha alterada) para alinhamento textual com D.2. Nada mais foi tocado — o arquivo pré-existente já estava funcionalmente correto.

---

## Ordem recomendada para instalação

Quando o operador aprovar em bloco, a ordem recomendada para substituir as SKILLs em `/mnt/skills/user/rc-*/SKILL.md` é A → B → C → F, conforme o fluxo do documento de fechamento. Não há dependências entre elas que impeçam ordem diferente, mas a ordem A → B → C → F reflete o fluxo do pipeline em operação.

Após aprovação, o auditor pode:
1. Substituir os 6 arquivos nas pastas `/mnt/skills/user/rc-*/`
2. Rodar uma passagem do pipeline completo em um caso-teste (recomendo Beethoven/Roman Kim, que já tem artefatos de referência)
3. Validar que o output de cada etapa é JSON válido e consumível pela etapa seguinte
4. Iniciar Fase 2 (validação das 6 regras narrativas contra o caso Beethoven/Roman Kim descrito em `RESPOSTAS_AUDITOR.md §3.2`)

Fase 3 (patches no código do site) permanece reservada para quando o operador iniciar a implementação no Claude Code.
