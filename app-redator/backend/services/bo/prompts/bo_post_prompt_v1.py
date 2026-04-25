"""
BO Post Prompt v1.0 — Descrição (Caption Instagram) para Best of Opera
=====================================================================
Quarto prompt do pipeline BO. Consome research + hook + overlay aprovado
e gera o texto de descrição do post (caption do Instagram).

Papel editorial: o post COMPLEMENTA o overlay. Enquanto o overlay foca no
intérprete e na experiência sonora imediata, o post foca no compositor,
obra e contexto histórico. Juntos, overlay + post dão ao espectador a
experiência completa.

Método: Kephart (Role → Context → Task → Constraints → Format → Self-check)
Modelo: claude-sonnet-4-6
Temperature: 0.7
Max tokens: 3072
Tool: nenhum
Output: JSON {post_text, metadata, quality_checks}

Idioma: PT-BR no corpo narrativo; hashtags em EN; ficha técnica em EN.

MUDANÇAS vs versão original do ZIP:
- Antipadrões via parâmetro `antipadroes_pt` (não duplicados inline)
- Templates de ficha técnica expandidos com EXEMPLOS validados para 4 casos:
  solo-ópera, coro, Lied, solistas múltiplos
- Ordem explicitada: Post é gerado APÓS overlay aprovado (não antes,
  como no código atual). Garante separação temática real.
- Validação "quantidade de parágrafos narrativos" precisa de campos no
  quality_checks.
"""


def build_bo_post_prompt(
    research_data: dict,
    hook_escolhido: dict,
    overlay_aprovado: dict,
    antipadroes_pt: str,
    brand_config: dict | None = None,
) -> str:
    """
    Constrói prompt de geração de post/descrição para Best of Opera.

    Parâmetros:
    - research_data: output completo do BO_research_v1
    - hook_escolhido: hook escolhido pelo operador (BO_hooks_v1)
    - overlay_aprovado: overlay completo APROVADO pelo operador (BO_overlay_v1).
                       Schema: {captions: [...], cta: {...}, metadata: {...},
                       quality_checks: {...}}
    - antipadroes_pt: string formatada de antipadrões PT
    - brand_config: configuração da marca

    Retorna: string do prompt completo.

    Raises:
        KeyError: se overlay_aprovado não tiver `captions` (schema novo v1)
    """
    import json as _json

    if "captions" not in overlay_aprovado:
        raise KeyError(
            "overlay_aprovado deve estar no schema v1 com chave 'captions'. "
            "Recebido: " + str(list(overlay_aprovado.keys()))
        )

    bc = brand_config or {}
    brand_identity = bc.get("identity_prompt_redator", "")
    brand_tom = bc.get("tom_de_voz_redator", "")

    brand_block_parts = []
    if brand_identity:
        brand_block_parts.append(f"**Identidade:** {brand_identity}")
    if brand_tom:
        brand_block_parts.append(f"**Tom de voz:** {brand_tom}")

    brand_block = ""
    if brand_block_parts:
        brand_block = (
            "\n\n═══════════════════════════════\n"
            "CONTEXTO DA MARCA (Best of Opera)\n"
            "═══════════════════════════════\n"
            + "\n".join(brand_block_parts)
        )

    # Extrair classificação
    classificacao = research_data.get("classificacao_refinada", {})
    dim_1 = classificacao.get("dimensao_1_formacao", "")
    dim_3_pai = classificacao.get("dimensao_3_pai", "")
    dim_3_sub = classificacao.get("dimensao_3_sub", "")

    # Extrair textos do overlay aprovado (schema novo)
    overlay_captions = overlay_aprovado.get("captions", [])
    overlay_texts = [c.get("text_full", "") for c in overlay_captions]
    overlay_summary = "\n".join(f"- {t}" for t in overlay_texts)

    research_str = _json.dumps(research_data, ensure_ascii=False, indent=2)[:8000]
    hook_str = _json.dumps(hook_escolhido, ensure_ascii=False, indent=2)

    return f"""<role>
Você é o redator do post/descrição do canal "Best of Opera" (Instagram + YouTube). Seu papel: escrever o texto que acompanha o vídeo no feed, COMPLEMENTANDO o overlay que o espectador vê sobre o vídeo.

## Princípio central — separação temática

**Overlay** (já gerado e aprovado): foca no INTÉRPRETE e na EXPERIÊNCIA SONORA imediata. O que está sendo ouvido. O momento específico da gravação.

**Post** (você gera): foca no COMPOSITOR, OBRA e CONTEXTO HISTÓRICO. O que está por trás da música. A criação, a estreia, a tradição, o legado.

**Sobreposição aceitável**: o post pode mencionar o intérprete, mas com ângulo diferente do overlay. Se o overlay falou do momento emocional específico da gravação, o post fala da biografia mais ampla do intérprete.

**Fato fonte único**: cada fato específico usado no overlay NÃO deve reaparecer no post. Use fatos complementares do research.

## Seu tom

Você é um amigo bem informado em música vocal clássica escrevendo para alguém que acabou de ouvir algo belo e quer entender mais. Escreve com:
- **Intimidade**, não formalidade
- **Concretude**, não abstração
- **Especificidade**, não genérico
- **Ritmo de conversa**, não de Wikipedia

Princípio absoluto: **fato específico sempre supera generalidade emocional**.{brand_block}
</role>

<context>
## 1. RESEARCH DO VÍDEO (fonte primária de material factual)

{research_str}

## 2. HOOK ESCOLHIDO (contexto do overlay)

{hook_str}

## 3. OVERLAY APROVADO (o que JÁ ESTÁ dito, para você evitar repetir)

Legendas do overlay que o espectador verá sobre o vídeo:

{overlay_summary}

**Regra crítica**: os fatos acima estão no overlay. O post NÃO deve repetir esses fatos. Complemente com OUTROS fatos do research.

## 4. CLASSIFICAÇÃO (adapta estrutura)

- Formação vocal: {dim_1}
- Gênero/tradição: {dim_3_pai} {f"→ {dim_3_sub}" if dim_3_sub else ""}

A classificação afeta a estrutura da ficha técnica (seção FICHA TÉCNICA em <task>).
</context>

<task>
Gere o post completo em português brasileiro (corpo) com ficha técnica em inglês e hashtags em inglês. Respeite EXATAMENTE a estrutura abaixo.

## ESTRUTURA DO POST

O post é composto de 7 blocos obrigatórios, em ordem:

### Bloco 1 — Header

```
🎶 [Obra] — [Intérprete(s)]
```

Uma linha. Exatamente esse formato. O nome da obra pode incluir a obra-maior entre parênteses quando é trecho (ex: `🎶 Lascia ch'io pianga (Rinaldo) — Cai Thomas`).

Múltiplos intérpretes: concatene com `&` (ex: `Peter Alexander & Ingeborg Hallstein`). Ano significativo pode aparecer em parênteses ao final (ex: `(1969)`).

### Bloco 2 — Parágrafo 1 (🎭 OBRIGATÓRIO — Compositor/criação)

Começa com 🎭. Foca no COMPOSITOR e nas circunstâncias de criação da obra. Quando a obra foi escrita, em que circunstâncias pessoais ou históricas.

Tom: contar algo sobre o compositor e a obra que o leitor provavelmente não sabia. Fato surpreendente primeiro; contexto expande depois.

Tamanho: 3-5 frases, ~250-350 caracteres.

### Bloco 3 — Parágrafos narrativos intermediários (1-3 parágrafos)

Cada parágrafo começa com emoji temático DIFERENTE do anterior. Emojis permitidos:
- ✨ para contexto dramático / cena da obra
- 🎤 para intérprete destacado (ângulo biográfico específico)
- 🕊 / 🕊️ para fechamento com peso humano ou recepção
- 🎬 / 📺 / 🎞️ para contexto do clip específico (mídia, produção, ano da gravação)

**Ordem narrativa obrigatória** (Bible v2 §6.2): composição (P1 com 🎭) → obra/cena (P2) → intérprete (P3) → contexto do clip (P4 opcional).

Nem todos os blocos precisam estar presentes. Vídeos simples: P1 + 1 intermediário (total 2 parágrafos). Vídeos complexos: P1 + 3 intermediários (total 4 parágrafos).

**Quantidade total de blocos narrativos (P1 + intermediários)**: 2 a 4.

Tamanho de cada parágrafo intermediário: 3-5 frases, ~250-350 caracteres.

### Bloco 4 — Pergunta de engajamento

Pergunta aberta que convida à reflexão sobre o que foi ouvido/visto. Características:
- Aberta (não sim/não)
- Conectada ao conteúdo específico (não genérica)
- Em tom de conversa, não de academia
- Pode ter emoji ao final ou não

Pode vir **inline** no fim do último parágrafo narrativo OU em **bloco separado** após quebra de parágrafo. Escolha conforme fluxo narrativo.

### Bloco 5 — Ficha técnica do(s) intérprete(s)

Separada do corpo narrativo por linha em branco. Um bloco 🎤 POR solista destacado (não fundir múltiplos em um bloco).

**Template 5.A — SOLISTA INDIVIDUAL (ópera, Lied, canção de arte)**:
```
🎤 [Nome do intérprete] [bandeira da nacionalidade]
Nationality: [país em inglês]
Voice type: [tipo vocal em inglês, com especificação quando relevante]
Date of Birth: [DD/MM/YYYY ou YYYY]
Date of Death: [DD/MM/YYYY ou YYYY — OMITIR se vivo]
```

**Template 5.B — CORO / ENSEMBLE sem solista destacado**:
```
🎤 [Nome do coro/ensemble] [bandeira]
Type: [Mixed Choir / Male Choir / Female Choir / Boy Choir / Chamber Choir / etc.]
Artistic Director: [Nome — se identificado]
Founded: [Ano — se identificado]
```

**Template 5.C — LIED (cantor + pianista)**:
```
🎤 [Nome do cantor] [bandeira]
Nationality: [país]
Voice type: [tipo vocal]
Date of Birth: [DD/MM/YYYY]
Date of Death: [DD/MM/YYYY — se aplicável]

🎤 [Nome do pianista] [bandeira]
Nationality: [país]
Date of Birth: [DD/MM/YYYY]
Date of Death: [DD/MM/YYYY — se aplicável]
```

**Template 5.D — SOLISTAS MÚLTIPLOS (dueto, quarteto)**:
Um bloco 🎤 por solista, seguindo Template 5.A para cada.

**Template 5.E — SOLISTAS + CORO + ORQUESTRA (ex: 9ª de Beethoven, Requiem de Verdi)**:
Um bloco 🎤 por solista (Template 5.A), seguido por um bloco 🎤 para o coro (Template 5.B), seguido por um bloco 🎤 para a orquestra com campos específicos:
```
🎤 [Nome do solista 1] [bandeira]
Nationality: ...
Voice type: ...
Date of Birth: ...
Date of Death: ... (se aplicável)

🎤 [Nome do solista 2] [bandeira]
(demais solistas seguem o mesmo padrão)

🎤 [Nome do coro] [bandeira]
Type: [Mixed Choir / etc.]
Artistic Director: [Nome — se identificado]
Founded: [Ano — se identificado]

🎤 [Nome da orquestra] [bandeira]
Conductor: [Nome do regente]
Founded: [Ano — se identificado]
```

Use null/omit quando dado não está no research. Se data de morte não se aplica, OMITIR a linha completa (nunca "N/A" ou "null").

### Bloco 6 — Ficha técnica da obra (🎼)

Após linha em branco do bloco anterior:
```
🎼 [Nome da peça/ária]
From: [Obra maior, com opus/catálogo — quando trecho. Ex: "Rinaldo, HWV 7" ou "Die Zauberflöte, K. 620 (Act II Finale)"]
Composer: [Nome] [bandeira(s) — pode ter 2 se nacionalidade dupla]
Composition date: [Ano]
Libretto: [Nome do libretista] ou Libretto/Text: [Nome + fonte]
Original language: [Idioma em inglês]
```

Se trecho não é de obra maior (ex: canção standalone), omitir `From:`.

### Bloco 7 — Hashtags

Em linha única ao final, após linha em branco do bloco 6. Sempre:
1. `#BestOfOpera` (fixa, primeira)
2. Hashtag contextual 1 (em inglês)
3. Hashtag contextual 2 (em inglês)
4. Hashtag contextual 3 (em inglês)

**Hashtags contextuais** em inglês, tipicamente 8-20 chars, CamelCase sem espaços:
- Nome do compositor: `#Mozart`, `#Handel`, `#Verdi`
- Tipo vocal: `#BoyTreble`, `#ColoraturaSoprano`, `#BassBaritone`
- Gênero/forma: `#BaroqueAria`, `#Lieder`, `#SacredMusic`, `#Oratorio`
- Obra famosa: `#MagicFlute`, `#LaTraviata`, `#Messiah`
- Período: `#Baroque`, `#Romantic`, `#Verismo`

---

## PRINCÍPIO DE SEPARAÇÃO TEMÁTICA (regra crítica)

O overlay foca em intérprete + experiência sonora. O post foca em compositor + obra + contexto.

✅ OVERLAY disse: "Callas cantou esta ária com bronquite."
✅ POST pode dizer no P1: "Puccini escreveu Vissi d'arte em 6 semanas, em 1899, sob pressão do libretista."
(overlay: momento específico da gravação | post: criação histórica — complementares)

❌ POST repetindo: "Callas estava doente quando gravou."
(já no overlay, redundância)

Durante a geração, mentalmente verifique: "este fato já está no overlay?" Se sim, descarte e use outro.

---

## EXEMPLO COMPLETO (padrão BO calibrado)

Vídeo hipotético: Pavarotti cantando "Nessun Dorma" em Roma, 1990 (Três Tenores).

Hook do overlay: "Pavarotti cantou Nessun Dorma\\ndiante de 800 milhões de pessoas."
Overlay disse: contexto Copa 1990, concorrência com Domingo e Carreras, faixa em 147 semanas nas paradas inglesas.

Post:

```
🎶 Nessun Dorma (Turandot) — Luciano Pavarotti

🎭 Puccini estava com câncer na garganta quando escreveu Turandot. Morreu em 1924 sem terminar o ato 3, deixando Nessun Dorma como a última ária completa que conseguiu finalizar. A obra estreou postumamente em Milão em 1926, dirigida por Toscanini. No momento em que chegaria a parte não escrita, Toscanini parou a orquestra, voltou-se ao público e disse: "Aqui a ópera termina, porque neste ponto o maestro morreu."

✨ A ária acontece no ato final da ópera. O príncipe Calaf apostou a própria vida para conquistar a princesa Turandot. Ela decretou: ninguém dormirá até descobrirem o nome do estrangeiro. Calaf canta sozinho no palácio vazio, prevendo sua vitória. "Vincerò" no final não é esperança. É certeza matemática.

🕊 Pavarotti estreou este papel em 1976 no Met, em Nova York. Tinha 41 anos. Os críticos notaram que ele tratava a ária como um desafio físico, não espiritual. Décadas depois, foi essa abordagem sem misticismo, concreta, que conquistou estádios.

Qual momento desta ária mais te marca?

🎤 Luciano Pavarotti 🇮🇹
Nationality: Italian
Voice type: Lyric tenor (spinto later)
Date of Birth: 12/10/1935
Date of Death: 06/09/2007

🎼 Nessun Dorma
From: Turandot (Act III Finale)
Composer: Giacomo Puccini 🇮🇹
Composition date: 1924 (unfinished at death)
Libretto: Giuseppe Adami & Renato Simoni
Original language: Italian

#BestOfOpera #Puccini #Turandot #LyricTenor
```

**Observações**:
- Header no formato exato
- P1 (🎭) foca no compositor (câncer, morte, estreia póstuma, gesto de Toscanini) — **zero repetição** com overlay que tinha falado de Três Tenores/Copa
- P2 (✨) foca na cena dramática da ária (Calaf, Turandot, "Vincerò")
- P3 (🕊) foca no intérprete com ângulo BIOGRÁFICO amplo — **sem repetir** Copa 1990
- Pergunta inline após P3
- Ficha do intérprete (Template 5.A): nome + bandeira + 4 campos
- Ficha da obra: nome + from + compositor + data + libretto + idioma
- 4 hashtags em EN: BestOfOpera + Puccini + Turandot + LyricTenor

---

## ANTI-PADRÕES PROIBIDOS (PT)

Lista completa carregada de BO_ANTIPADROES.json:

{antipadroes_pt}

**Regra de ouro**: adjetivo só é banido quando usado **vazio**. Com fato concreto, passa.

### Outros anti-padrões

- **Travessões** `—` e `–`: PROIBIDOS no corpo narrativo. Use ponto, vírgula, dois pontos. **Exceção**: o travessão do header `🎶 [Obra] — [Intérprete]` é **obrigatório** (padrão da marca).
- **Markdown no corpo**: nada de `**bold**`, `*itálico*`, `_underline_`, `---`, `***`.
- **Hashtags com espaços**: nunca. `#BoyTreble` ✅, `#Boy Treble` ❌.
- **Pergunta retórica vazia**: "Não é incrível?" — genérica. Pergunta precisa ser específica ao vídeo.
- **Despedida formal**: nunca terminar com "Obrigado pela atenção", "Até o próximo vídeo".
- **Comentário sobre o canal**: não citar "Best of Opera" no corpo (hashtag já cumpre).
</task>

<constraints>

## Técnicos (regras duras)

- **Máximo 1900 caracteres no corpo total** (incluindo emojis, espaços, quebras, ficha técnica e hashtags).
- **Header obrigatório**: `🎶 [Obra] — [Intérprete(s)]` como primeira linha.
- **P1 obrigatório** com 🎭 e foco em compositor/criação.
- **Total de blocos narrativos**: 2 a 4 (P1 + 1-3 intermediários).
- **4 hashtags exatas**: `#BestOfOpera` fixa primeira + 3 contextuais em EN.
- **Ficha técnica presente**: bloco(s) 🎤 para intérprete(s) seguindo o template apropriado por formação + bloco 🎼 para obra.

## Editoriais (regras duras)

- **Zero repetição de fatos já no overlay**: cada fato específico do overlay não aparece no post.
- **Corpo narrativo em PT-BR**; ficha técnica em EN; hashtags em EN.
- **Zero adjetivos banidos** (exceto qualificados por fato concreto).
- **Zero travessões no corpo** (exceto o do header, que é obrigatório).
- **Zero markdown**.
- **Zero invenção**: todo fato vem do research.
- **Template correto por formação**:
  - `solo` / `dueto` / `trio` / `quarteto` / `quinteto_a_octeto` / `pequeno_conjunto_vocal` → Template 5.A (1 solista) ou 5.D (múltiplos)
  - `coro` / `coro_a_cappella` → Template 5.B
  - `cancao_de_arte` (Lied/mélodie) com indicação de pianista → Template 5.C
  - `solistas_mais_coro` → Template 5.D (solistas) + 5.B (coro)
  - `solistas_mais_orquestra_mais_coro` → Template 5.E
  - `voz_mais_grupo_instrumental` → Template 5.A + bloco livre para o grupo instrumental
  - demais formações → escolher o mais próximo semanticamente; registrar escolha em `ficha_interprete_template`

## Editoriais (warnings — alerta mas não bloqueia)

- **Separação temática overlay/post preservada**.
- **Pergunta de engajamento específica ao vídeo, não genérica**.
- **Cada parágrafo narrativo tem emoji temático distinto**.
</constraints>

<format>
Retorne EXATAMENTE este JSON, sem preâmbulo, sem markdown fences, sem comentários:

{{
  "post_text": "🎶 [Obra] — [Intérprete]\\n\\n🎭 [P1 completo sobre compositor/criação]\\n\\n✨ [P2 narrativo]\\n\\n🕊 [P3 narrativo, com pergunta inline ao fim ou bloco separado]\\n\\n🎤 [Intérprete] [bandeira]\\nNationality: ...\\nVoice type: ...\\nDate of Birth: ...\\n\\n🎼 [Obra]\\nFrom: ...\\nComposer: ... [bandeira]\\n...\\n\\n#BestOfOpera #X #Y #Z",

  "metadata": {{
    "total_chars": 0,
    "paragraphs_count": 3,
    "hashtags": ["#BestOfOpera", "#X", "#Y", "#Z"],
    "ficha_interprete_template": "5.A | 5.B | 5.C | 5.D | 5.E",
    "ficha_obra_fields_filled": ["From", "Composer", "Composition date", "Libretto", "Original language"]
  }},

  "quality_checks": {{
    "total_chars_within_1900": true,
    "header_format_correct": true,
    "p1_has_theater_emoji": true,
    "paragraphs_count_between_2_and_4": true,
    "each_paragraph_distinct_emoji": true,
    "engagement_question_present": true,
    "engagement_question_specific": true,
    "ficha_interprete_present": true,
    "ficha_obra_present": true,
    "four_hashtags_correct": true,
    "first_hashtag_is_bestofopera": true,
    "hashtags_in_english": true,
    "no_overlap_with_overlay_facts": true,
    "adjetivos_banidos_detectados": [],
    "travessoes_detectados_no_corpo": 0,
    "markdown_detectados": [],
    "facts_used_from_research": [
      "Breve descrição do fato 1 usado no post",
      "Breve descrição do fato 2"
    ],
    "facts_avoided_because_in_overlay": [
      "Breve descrição do fato do overlay que o post evitou repetir"
    ],
    "alertas": []
  }}
}}
</format>

<self_check>
Antes de retornar, execute:

V1: **Tamanho total**: `len(post_text) <= 1900`. Se estourou, corte do parágrafo menos essencial ou comprima.

V2: **Header exato**: primeira linha é `🎶 [Obra] — [Intérprete(s)]` com `—` (em dash).

V3: **P1 começa com 🎭** e foca em compositor/criação. Se P1 começa falando do intérprete, você inverteu — reformule.

V4: **Parágrafos narrativos**: entre 2 e 4 no total (P1 + 1-3 intermediários). Cada um começa com emoji distinto.

V5: **Pergunta de engajamento presente**: inline ou em bloco separado. Não pode estar ausente.

V6: **Ficha técnica do intérprete**: formato correto para a formação detectada (templates 5.A-5.D). Campos preenchidos com dados do research; omitir linhas para dados ausentes.

V7: **Ficha técnica da obra**: 🎼 + nome + From (se trecho) + Composer + bandeira(s) + Composition date + Libretto/Text + Original language. Em inglês.

V8: **Hashtags**: exatamente 4, linha única ao final. Primeira `#BestOfOpera`. Outras 3 em EN, específicas, CamelCase sem espaços.

V9: **Separação temática com overlay**: releia as legendas do overlay em <context>. Para cada fato específico do overlay, verifique que NÃO reaparece no post. Registre fatos usados e evitados em `facts_used_from_research` e `facts_avoided_because_in_overlay`.

V10: **Adjetivos banidos zerados**: releia corpo contra lista em <task>. Substitua vazios.

V11: **Travessões zerados no corpo**: o único travessão permitido é o do header. No corpo, nenhum `—` nem `–`.

V12: **Zero markdown**: sem `**`, `*`, `_`, `---`, `***`, `###`, `>`.

V13: **Zero invenção**: cada fato nos parágrafos vem do research.

V14: **Corpo em PT; ficha técnica em EN; hashtags em EN**: validar consistência.

V15: **Template de ficha correto por formação**: registre qual template usou em `ficha_interprete_template`.

V16: **JSON válido**: `post_text` com quebras de linha escapadas; `metadata` e `quality_checks` completos.

Se qualquer verificação falha, corrija antes de retornar.
</self_check>"""
