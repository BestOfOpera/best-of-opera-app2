# PROMPT 2 — Execução dos Patches RC v3/v3.1

*Sessão de execução. Esta sessão só começa DEPOIS do relatório produzido pelo PROMPT 1 (investigação) ser aprovado pelo operador. Se você está lendo isto sem ter o `RELATORIO_INVESTIGACAO.md` aprovado em mãos, pare e peça o relatório antes de continuar.*

---

## 1. Pré-requisito obrigatório

Antes de qualquer ação:

1. Leia `RELATORIO_INVESTIGACAO.md` (produzido na sessão anterior)
2. Confirme que a seção **20 — Proposta de ordem de patches** foi revisada e aprovada pelo operador
3. Confirme que a seção **19 — Riscos identificados** teve todos os riscos classificados como "crítico" resolvidos ou mitigados antes desta sessão

Se alguma dessas três condições não estiver satisfeita, interrompa e peça o que falta antes de tocar em qualquer arquivo.

---

## 2. Escopo desta sessão

Aplicar no código do site de produção, nesta ordem (sujeita a reordenação conforme seção 20 do relatório):

- **2.1** Substituir os 3 prompts v3/v3.1 no repositório
- **2.2** Atualizar consumidores do JSON de saída (validadores, pós-processadores, persistência) para aceitar campos novos sem quebrar os antigos
- **2.3** Ajustar a renderização final da descrição para incluir o novo campo `save_cta` entre `paragrafo3` e `follow_cta` (a estrutura geral da descrição permanece inalterada — ver seção 5)
- **2.4** Atualizar (se existir) tabela de CTAs hardcoded com os CTAs v3 unificados com pronome em de/fr/it/pl
- **2.5** Rodar smoke tests por etapa
- **2.6** Rodar teste E2E do pipeline
- **2.7** Rodar teste de regressão contra o caso Beethoven/Roman Kim

Cada grupo (2.1 a 2.7) vira um ou mais commits separados. Não acumular tudo num único commit monolítico.

---

## 3. Patches dos prompts

### 3.1 Substituição de `rc_translation_prompt_v3.py`

**Origem**: `docs/rc_v3_migration/rc_translation_prompt_v3.py` (anexo)
**Destino**: path identificado no relatório, seção 4.6

**Mudança**: substituição **integral** do arquivo. Zero merge manual.

**Diff esperado** vs versão atual (conforme Relatório Lote D, anexo):
- Apenas seção `<examples>` do prompt interno mudou
- 3 exemplos de tradução reescritos com contagens de caracteres validadas programaticamente (12/12 corretas no arquivo patched)
- Nenhuma outra seção do prompt foi tocada
- Assinatura da função `build_rc_translation_prompt(metadata, overlay_aprovado, descricao_aprovada)` preservada

**Commit**: `fix(rc): apply D.1 — rewrite translation prompt examples with validated counts (F6.7)`

### 3.2 Substituição de `rc_automation_prompt_v3.py`

**Origem**: `docs/rc_v3_migration/rc_automation_prompt_v3.py` (anexo)
**Destino**: path identificado no relatório, seção 4.5

**Mudança**: substituição integral. Diferenças vs repo:
- Adição de extração de `post_summary` (truncamento em 500 chars) antes do f-string
- Adição de bloco `DESCRIÇÃO APROVADA:` dentro do `<context>` do prompt LLM
- Total: 10 linhas novas, 0 removidas

**Atenção**: se o relatório identificou que o parâmetro `post_text` **não é passado** para `build_rc_automation_prompt` no callsite atual (porque o bug F5.2 fazia o parâmetro ser morto), então o callsite **também** precisa ser atualizado para passar `post_text` (vindo do JSON aprovado da Etapa 4). Verificar seção 4.5 do relatório.

**Commit**: `fix(rc): apply D.2 — integrate post_text in automation prompt (F5.2)`

### 3.3 Substituição/criação de `rc_overlay_prompt_v3_1.py`

**Origem**: `docs/rc_v3_migration/rc_overlay_prompt_v3_1.py` (anexo)
**Destino**: path identificado no relatório, seção 4.3

**Mudança**: depende do que o relatório descobriu. Dois cenários possíveis:

**Cenário A** — repo tem `rc_overlay_prompt_v3.py` (versão anterior):
- Criar arquivo novo `rc_overlay_prompt_v3_1.py` (não substituir o v3)
- Atualizar os callsites para apontar para a nova versão
- Manter o v3 antigo como arquivo órfão por 1-2 sprints, apagar depois em commit separado (rollback mais rápido se surgir problema)

**Cenário B** — repo tem apenas um arquivo `rc_overlay_prompt.py` (sem versioning):
- Renomear para `rc_overlay_prompt_v2.py` (preservar versão anterior)
- Criar `rc_overlay_prompt_v3_1.py` com o novo conteúdo
- Atualizar callsites para v3.1

Diferenças v3 → v3.1 (referência para eventual merge manual se for necessário):
- Nova seção `<duracao_dinamica>` (regra 4-6s por legenda)
- Nova seção `<fio_narrativo_dinamico>` (substitui fio único rígido)
- PASSO 1.1 reescrito (identificar fio + avaliar profundidade)
- Rubric Fase 3 expandida de 7 para 11 dimensões
- 11 verificações V1-V11 na Fase 5
- Schema JSON com campo `verificacoes.cortes_aplicados`
- Instrução `REGISTRO DE CORTES` no bloco `IMPORTANTE` do `<format>`
- Função helper `_estimar_faixa_legendas(duracao) → (min, max)` substitui `_estimar_legendas(duracao) → int`

**Atenção especial**: a função `_estimar_legendas` antiga pode ser chamada em outros lugares além do prompt (pós-processador, teste, frontend). Conferir na seção 4.3 e 6 do relatório. Se for chamada em outro lugar:
- Manter `_estimar_legendas` (antiga) operacional temporariamente
- Adicionar `_estimar_faixa_legendas` (nova) ao lado
- Migrar callsites um a um em commits separados

**Commit**: `feat(rc): apply D.3 — overlay prompt v3.1 with dynamic duration and fio dynamics (F3.1-F3.11)`

---

## 4. Atualização dos consumidores do JSON

Com base nas seções 5 (validadores), 6 (pós-processamento) e 9 (persistência) do relatório, atualizar consumidores para aceitar campos novos **sem quebrar os antigos**.

### 4.1 Overlay — novo campo `verificacoes.cortes_aplicados`

Formato:
```json
"cortes_aplicados": [
  {
    "tipo": "fio_secundario | evidente | cena_generica | repeticao",
    "texto_candidato": "texto que seria legenda se não fosse cortado",
    "motivo": "explicação em 1 linha"
  }
]
```

Ações baseadas no relatório:
- Se há validador pydantic/jsonschema para output do overlay (relatório §5): adicionar o campo como opcional (default `[]`)
- Se há persistência estruturada em colunas separadas (relatório §9): decidir com operador se o campo merece coluna própria ou fica no blob JSON
- Se há UI de debug do pipeline: considerar exibir os cortes aplicados ao operador como insight (não obrigatório nesta sessão)

Recomendação: **persistir** o campo. Ele alimenta `failure-log.md` (auditoria contínua) e permite análise agregada de padrões de corte por intérprete/compositor/categoria.

### 4.2 Hooks — 3 campos novos

- `ganchos[].verbo_principal` (string)
- `ganchos[].estrutura_sintatica` (string)
- `analise_diversidade.todos_diferentes` (boolean)

**Validação crítica no backend**: se chegar JSON com `analise_diversidade.todos_diferentes = false`, rejeitar e **regenerar automaticamente** (ou devolver erro ao operador). A SKILL instrui o modelo a não retornar JSON com `todos_diferentes = false`, mas o backend precisa validar também.

### 4.3 Post — campos novos no JSON de saída

**Nota editorial**: a arquitetura visual da descrição **não muda** — header permanece no topo, 4 hashtags permanecem. A única adição estrutural é o `save_cta` entre `paragrafo3` e `follow_cta` (ver seção 5). Os campos novos abaixo refletem apenas essa adição + rastreamento de qualidade.

Campos novos:
- `save_cta` (string — novo, complementa `follow_cta`)
- `analise_keywords.keywords_primarias_usadas` (array de strings — descreve quantas vezes cada keyword primária apareceu em prosa natural, fora do header)
- `anti_repeticao.fatos_overlay`, `anti_repeticao.temas_overlay`, `anti_repeticao.fatos_descricao`, `anti_repeticao.temas_descricao` (arrays)
- `anti_repeticao.algum_repetido` (boolean)

Schema do campo `hashtags` permanece: array de EXATAMENTE 4 strings.

**Validações críticas**:
- Se `anti_repeticao.algum_repetido = true`: rejeitar ou flag para o operador (relatório §5 dirá se é automático ou manual no sistema atual). Repetição de tema entre overlay e descrição é o problema #1 do canal.
- Se `hashtags.length != 4`: rejeitar. A decisão editorial é exata, não faixa.
- `save_cta` não pode estar vazio nem usar fórmulas genéricas ("Salve este post", "Save for later"). Se o conteúdo reportado parecer genérico, flag para o operador.

### 4.4 Translation — campos novos de rastreamento

- `verificacoes.pt_copiado_identico` (boolean)
- `verificacoes.linhas_reformuladas_por_idioma` (objeto com contagem por idioma)
- `verificacoes.legendas_com_linha_excedendo_38_chars` (objeto com lista por idioma)
- `verificacoes.alertas` (array)

**Validações críticas**:
- `pt_copiado_identico = false`: rejeitar imediatamente. PT é intocável (decisão editorial do operador). O código deve comparar o `overlays.pt` retornado pelo LLM com o `overlay_aprovado` de entrada; se houver qualquer diferença (mesmo de pontuação), rejeitar.
- Linhas traduzidas acima de 38 chars que **não** estão listadas em `legendas_com_linha_excedendo_38_chars`: flag de alerta. Se estão listadas com justificativa em `alertas`, aceitar.

### 4.5 Automation — sem mudanças de schema

O JSON de saída da automation não mudou. Apenas a **entrada** do prompt (agora consumindo `post_text` via extração para `post_summary`). Validadores de saída permanecem iguais.

---

## 5. Frontend/renderização da descrição — adição pontual do save_cta

**Nota editorial**: a arquitetura atual da descrição é mantida. Header no topo, 3 parágrafos separados por `•`, follow-CTA fixo, 4 hashtags. A única mudança é a **inserção do novo campo `save_cta`** entre `paragrafo3` e `follow_cta` na renderização final.

### 5.1 Ordem da renderização — estrutura preservada, adição pontual

```
[header_linha1]
[header_linha2]
[header_linha3] (se não vazio)

•

[paragrafo1]

•

[paragrafo2]

•

[paragrafo3]

•

[save_cta]              ← NOVO, em linha própria
[follow_cta]            ← atual, na linha imediatamente seguinte, sem `•` separando

•

•

•

[hashtags separadas por espaço — EXATAMENTE 4]
```

### 5.2 Mudança específica a aplicar

Com base na seção 7 do relatório de investigação, localizar o código que serializa a descrição em string final (backend Python ou frontend JS) e inserir o `save_cta` no local indicado acima — imediatamente antes do `follow_cta`, na linha anterior, sem `•` entre os dois.

Os dois CTAs (save + follow) formam um **bloco único** visualmente — o save específico abre o follow fixo. Quebra de linha simples entre eles (não linha em branco).

### 5.3 Retrocompatibilidade

Posts antigos (gerados antes deste patch) têm JSON sem o campo `save_cta`. O frontend/renderizador precisa **não quebrar** ao renderizar posts antigos:

- Se `save_cta` está ausente ou é string vazia: pular sua linha, ir direto para `follow_cta` (a renderização degrada para o formato antigo)
- Logar aparição de posts antigos para monitoramento (opcional)

### 5.4 Critério de aceitação

Renderizar com um exemplo v3 (ex: exemplo Beethoven/Roman Kim das SKILLs anexadas) e confirmar:

1. O header ainda é o primeiro elemento (não mudou)
2. O `save_cta` aparece imediatamente antes do `follow_cta`
3. Não há `•` entre save_cta e follow_cta
4. As 4 hashtags aparecem no final, separadas por espaço simples
5. Renderização de exemplo sem `save_cta` (retrocompat) não produz linha em branco sobrando nem artefato visual

---

## 6. CTAs por idioma (decisão F6.8)

Tabela validada programaticamente (14/14 CTAs overlay corretos, todos ≤ 38 chars/linha; 7/7 CTAs descrição corretos):

### 6.1 CTAs de overlay (última legenda, tipo "cta", 2 linhas)

| Idioma | Linha 1 | Linha 2 |
|--------|---------|---------|
| pt | `Siga, o melhor da música clássica,` (34 chars) | `diariamente no seu feed. ❤️` (27 chars) |
| en | `Follow for the best of` (22 chars) | `classical music on your feed` (28 chars) |
| es | `Síguenos para lo mejor de` (25 chars) | `la música clásica en tu feed` (28 chars) |
| de | `Folge uns für das Beste der` (27 chars) | `klassischen Musik in deinem Feed` (32 chars) |
| fr | `Suis-nous pour le meilleur de` (29 chars) | `la musique classique dans ton feed` (34 chars) |
| it | `Seguici per il meglio della` (27 chars) | `musica classica nel tuo feed` (28 chars) |
| pl | `Obserwuj nas, by poznać najlepsze` (33 chars) | `z muzyki klasycznej` (19 chars) |

### 6.2 CTAs de descrição (follow_cta, 1 linha)

| Idioma | Texto |
|--------|-------|
| pt | `👉 Siga, o melhor da música clássica, diariamente no seu feed.` |
| en | `👉 Follow for the best of classical music daily on your feed.` |
| es | `👉 Síguenos para lo mejor de la música clásica en tu feed.` |
| de | `👉 Folge uns für das Beste der klassischen Musik in deinem Feed.` |
| fr | `👉 Suis-nous pour le meilleur de la musique classique dans ton feed.` |
| it | `👉 Seguici per il meglio della musica classica nel tuo feed.` |
| pl | `👉 Obserwuj nas po najlepsze utwory muzyki klasycznej.` |

### 6.3 Ação

Se o relatório §10 identificou que os CTAs estão **hardcoded no código** (constantes Python, JSON de config, banco):

- Atualizar os 14 valores de overlay (7 idiomas × 2 linhas) e os 7 de descrição
- Os CTAs v2 anteriores em de/fr/it/pl não tinham pronome ("Folge für...", "Suis pour...", "Segui per...", "Obserwuj, by...") — substituir com versões com pronome conforme tabelas acima

Se os CTAs são **gerados pelo LLM em cada request** (aparecem no prompt de tradução, não no código do site): os prompts v3 patched já contêm as tabelas corretas, portanto basta a substituição do prompt (seção 3) — nada a mudar aqui.

---

## 7. Smoke tests obrigatórios por etapa

Rodar após cada patch. Se algum falhar, **não avançar** para o próximo commit até resolver.

### 7.1 Research
- [ ] `build_rc_research_prompt(metadata_test)` gera string não-vazia
- [ ] JSON retornado pelo LLM tem as 7 seções estruturais (`compositor_na_epoca`, `por_que_a_peca_existe`, `recepcao_e_historia`, `interprete`, `cadeias_de_eventos`, `conexoes_culturais`, `angulos_narrativos`, `alertas`)
- [ ] `cadeias_de_eventos.length >= 2`
- [ ] `angulos_narrativos.length == 3` com `tipo` ∈ {emocional, cultural, estrutural, especifico}

### 7.2 Hooks
- [ ] JSON tem 5 ganchos ranqueados 1-5
- [ ] Cada gancho tem `verbo_principal` e `estrutura_sintatica` preenchidos
- [ ] `analise_diversidade.todos_diferentes == true`
- [ ] `descartados_e_motivos.length` entre 2 e 3
- [ ] Validador do backend **rejeita** JSON teste com `todos_diferentes = false`

### 7.3 Overlay
- [ ] `build_rc_overlay_prompt(...)` gera string contendo `<duracao_dinamica>`, `<fio_narrativo_dinamico>`, `cortes_aplicados`, `REGISTRO DE CORTES`
- [ ] JSON retornado tem `verificacoes.cortes_aplicados` (mesmo que array vazio)
- [ ] `verificacoes.total_legendas == legendas.length`
- [ ] Última legenda tem `tipo == "cta"` e contém o texto exato do CTA PT
- [ ] Primeira legenda (gancho) tem `texto` idêntico ao `selected_hook` de entrada
- [ ] Cada legenda (exceto CTA) tem duração calculada entre 4.0 e 6.0 segundos — se alguma ficar fora, verificar algoritmo de cálculo de timestamps

### 7.4 Post
- [ ] JSON tem `header_linha1`, `header_linha2`, `paragrafo1`, `paragrafo2`, `paragrafo3`, `save_cta`, `follow_cta`, `hashtags`
- [ ] `hashtags` array tem EXATAMENTE 4 entradas (não 5, não 3 — rejeitar se diferente)
- [ ] `follow_cta` é exatamente `👉 Siga, o melhor da música clássica, diariamente no seu feed.`
- [ ] `save_cta` não-vazio e não genérico (não contém apenas "Salve este post" ou variações sem referência ao vídeo)
- [ ] `anti_repeticao.algum_repetido == false` (se vier `true`, rejeitar e solicitar regeração)
- [ ] **Renderização final**: `header_linha1` é o primeiro elemento, o `save_cta` aparece imediatamente antes do `follow_cta` na linha anterior, as 4 hashtags encerram o post

### 7.5 Automation
- [ ] `build_rc_automation_prompt(metadata, overlay_aprovado, post_text)` com `post_text` longo (>500 chars) gera prompt contendo:
  - Bloco `DESCRIÇÃO APROVADA:`
  - Truncamento com `...` no final do `post_summary`
- [ ] JSON retornado tem 3 `respostas_curtas`, `estrategia_diversidade_aplicada` ∈ {A, B, C}, `dm_fixa`, `comentario_keyword.keyword` em CAIXA ALTA sem acentos

### 7.6 Translation
- [ ] JSON retornado tem `overlays` e `descricoes` com 7 idiomas cada (pt, en, es, de, fr, it, pl)
- [ ] `overlays.pt` é **byte-a-byte idêntico** ao `overlay_aprovado` de entrada (usar `hashlib.sha256` ou comparação direta)
- [ ] Todos os 7 overlays têm mesmo número de legendas
- [ ] Timestamps idênticos entre pt e cada um dos 6 traduzidos
- [ ] Cada linha de cada legenda traduzida: `len(linha) <= 38` **OU** a legenda está registrada em `verificacoes.legendas_com_linha_excedendo_38_chars` com justificativa em `alertas`
- [ ] Última legenda de cada overlay traduzido tem `tipo == "cta"` e contém exatamente o CTA da tabela 6.1 para o idioma correspondente

---

## 8. Teste E2E do pipeline completo

Caso-teste: **Beethoven/Roman Kim** (metadata abaixo). Todos os artefatos de referência estão nas SKILLs anexadas (exemplos canônicos).

### 8.1 Input
```python
metadata = {
    "composer": "Ludwig van Beethoven",
    "work": "5ª Sinfonia em Dó menor, Op. 67",
    "artist": "Roman Kim",
    "instrument_formation": "violino solo",
    "category": "Melhor Clássico",
    "composition_year": "1804-1808",
    "cut_start": "00:00",
    "cut_end": "01:16"
}
```

### 8.2 Execução
1. Rodar research com `metadata` → `research_json`
2. Rodar hooks com `metadata + research_json` → `hooks_json`
3. Escolher `hooks_json.ganchos[0].texto` como `selected_hook` (automatizar: rank 1)
4. Rodar overlay com `metadata + research_json + selected_hook` → `overlay_json`
5. Rodar post com `metadata + research_json + overlay_json` → `post_json`
6. Rodar automation com `metadata + overlay_json + post_json.follow_cta (ou post renderizado)` → `automation_json`
7. Rodar translation com `metadata + overlay_json + post_json` → `translation_json`

### 8.3 Critérios
Cada etapa produz JSON válido (schema v3) e passa nos smoke tests da seção 7. Se qualquer etapa falha, o pipeline E2E falha.

---

## 9. Teste de regressão narrativa — Beethoven/Roman Kim

Este teste valida que o patch do overlay v3.1 resolve os problemas empíricos identificados na Fase 2 da auditoria.

### 9.1 Contexto

A Fase 2 comparou o overlay em produção (`romankin.srt` gerado pelo v2/v3 antigo) com o arco-ouro aprovado por editor humano (`0420.srt`, versão v3.1 correta). Constatou-se que a produção antiga violava 5 das 6 regras narrativas v3.1.

### 9.2 Critério de aceitação do patch

Rodar o overlay v3.1 com os inputs da seção 8.1 (mesmo gancho do arco-ouro: *"Ele toca sozinho o que Beethoven compôs para uma orquestra inteira!"*). O `overlay_json` produzido deve satisfazer todos os critérios abaixo:

**Regras narrativas**:
- [ ] Nenhuma legenda (exceto gancho) menciona "Roman Kim" por nome
- [ ] Nenhuma legenda menciona "Haydn" ou "Bonn" (cortados por serem fio secundário aleatório)
- [ ] Nenhuma legenda descreve Roman Kim tocando sozinho / técnica do polegar (regra do corte do evidente — a imagem já mostra)
- [ ] Pelo menos uma legenda faz ponte explícita entre "angústia/surdez de Beethoven" e "notas que você está ouvindo"
- [ ] Pelo menos uma ancoragem causal (não apenas descritiva) — conecta som a significado estabelecido
- [ ] Vocabulário oral: aparece "contou aos irmãos" (não "escreveu aos irmãos"); "Beethoven regeu a estreia" (não "Estreou em"); verbos de ação dominam
- [ ] Fio único: todas as legendas servem à narrativa "angústia → 5ª → reconhecimento"

**Rastreamento de cortes**:
- [ ] `verificacoes.cortes_aplicados` não está vazio
- [ ] Cortes incluem ao menos: Roman Kim técnica, Haydn, Bonn (os 3 candidatos de fio secundário identificados na Fase 2)

**Ritmo**:
- [ ] Cada legenda tem duração entre 4.0 e 6.5 segundos (4-6s ideal; 6.5s máximo tolerado conforme arco-ouro real)

Se o overlay gerado **não** satisfaz esses critérios, o patch não surtiu efeito. Investigar:
1. O prompt realmente foi substituído pelo v3.1?
2. O callsite realmente está importando o v3.1?
3. O modelo LLM mudou entre versões? (provedor desatualizou)
4. Há algum pós-processador que está sobrescrevendo o JSON retornado pelo LLM?

---

## 10. Commit strategy

Um commit por patch lógico, mensagem no formato convencional:

```
fix(rc): apply D.1 — rewrite translation prompt examples with validated counts (F6.7)
fix(rc): apply D.2 — integrate post_text in automation prompt (F5.2)
feat(rc): apply D.3 — overlay prompt v3.1 with dynamic duration and fio dynamics (F3.1-F3.11)
feat(rc): update JSON validators for new v3 fields
feat(rc-frontend): add save_cta field to description rendering (F4.3)
fix(rc): update hardcoded CTAs with pronoun form for de/fr/it/pl (F6.8)
test(rc): add smoke tests for v3 pipeline stages
test(rc): add Beethoven/Roman Kim regression test for overlay v3.1
```

Cada commit deve passar no smoke test da seção 7 correspondente antes do próximo ser iniciado.

---

## 11. Rollback plan

Se em qualquer ponto durante ou pós-deploy surgir regressão crítica em produção:

1. `git revert` do último commit problemático (identificado pela mensagem de commit da seção 10)
2. Redeploy
3. Investigação (não nesta sessão) sobre causa da regressão
4. Patch corrigido em commit novo, seguindo mesma ordem

Se o problema for no prompt v3.1 substituindo v3, e o v3 ainda existe como arquivo órfão (cenário A da seção 3.3), basta mudar o import no callsite de volta para v3. Por isso manter o v3 por 1-2 sprints — economiza tempo de rollback.

Se o problema for na renderização da descrição com o novo `save_cta`, considerar reverter apenas o trecho de renderização (voltar a ignorar o campo). Os prompts novos continuam gerando o JSON completo com `save_cta`, mas o campo é ignorado até o fix. Não quebra nada.

---

## 12. Critérios de aceitação final da sessão

Esta sessão é considerada concluída quando:

- [ ] Todos os patches da seção 3 estão aplicados e commitados
- [ ] Todos os consumidores da seção 4 foram atualizados e commitados
- [ ] Frontend da descrição foi atualizado (seção 5) e commitado
- [ ] CTAs por idioma estão atualizados (seção 6), se aplicável
- [ ] Smoke tests das 6 etapas passam (seção 7)
- [ ] Teste E2E passa com caso Beethoven/Roman Kim (seção 8)
- [ ] Teste de regressão narrativa passa (seção 9)
- [ ] Todos os commits estão com mensagens padronizadas (seção 10)
- [ ] O operador tem plano de rollback documentado (seção 11)

Nenhum desses itens é opcional. Se um falhar, resolver antes de encerrar.

---

## 13. Regra final

Se durante a execução você encontrar um aspecto do código que não foi coberto pelo relatório de investigação — ou que foi coberto de forma incompleta — **pare**. Não invente. Registre a lacuna, peça complemento ao operador (ou nova investigação pontual) e só continue depois de ter mapa.

A razão: investigação + execução funcionam como par. Se a execução descobre algo que a investigação não viu, a investigação precisa ser atualizada antes de continuar — senão estamos patchando no escuro.
