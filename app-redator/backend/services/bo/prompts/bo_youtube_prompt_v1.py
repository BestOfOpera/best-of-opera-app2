"""
BO YouTube Prompt v1.0 — Title + Tags para YouTube Shorts
========================================================
Quinto prompt do pipeline BO. Consome research + hook + overlay + post
e gera title + tags para YouTube Shorts.

Não gera descrição própria — YouTube reusa o post do Instagram (traduzido
conforme o canal por idioma).

Método: Kephart (Role → Context → Task → Constraints → Format → Self-check)
Modelo: claude-sonnet-4-6
Temperature: 0.7
Max tokens: 1024
Tool: nenhum
Output: JSON {title, tags, metadata, quality_checks}

Idioma nativo: PT-BR (traduzido nos 6 idiomas na Etapa 6).

MUDANÇAS vs versão original do ZIP:
- Antipadrões via parâmetro `antipadroes_pt`
- Travessão/pipe no title YouTube declarados EXPLICITAMENTE como exceção
  documentada no Bible v2 §6.3 (atualização de Bible prevista no plano)
- Valida que overlay_aprovado e hook_escolhido estão no schema v1 (captions +
  hook_text); raise se não.
"""


def build_bo_youtube_prompt(
    research_data: dict,
    hook_escolhido: dict,
    overlay_aprovado: dict,
    post_aprovado: str,
    antipadroes_pt: str,
    brand_config: dict | None = None,
) -> str:
    """
    Constrói prompt de geração de title + tags YouTube para Best of Opera.

    Parâmetros:
    - research_data: output completo do BO_research_v1
    - hook_escolhido: dict com `hook_text` (schema v1)
    - overlay_aprovado: dict com `captions` (schema v1)
    - post_aprovado: string do post completo já aprovado (PT)
    - antipadroes_pt: string formatada de antipadrões PT
    - brand_config: configuração da marca

    Raises:
        KeyError: se overlay_aprovado ou hook_escolhido não estão no schema v1
    """
    import json as _json

    if "captions" not in overlay_aprovado:
        raise KeyError(
            "overlay_aprovado deve estar no schema v1 com chave 'captions'. "
            "Recebido: " + str(list(overlay_aprovado.keys()))
        )
    if "hook_text" not in hook_escolhido:
        raise KeyError(
            "hook_escolhido deve ter chave 'hook_text' (schema v1 dos hooks). "
            "Recebido: " + str(list(hook_escolhido.keys()))
        )

    bc = brand_config or {}
    brand_identity = bc.get("identity_prompt_redator", "")

    brand_block = ""
    if brand_identity:
        brand_block = (
            "\n\n═══════════════════════════════\n"
            "CONTEXTO DA MARCA (Best of Opera)\n"
            "═══════════════════════════════\n"
            f"{brand_identity}"
        )

    # Extrair classificação
    classificacao = research_data.get("classificacao_refinada", {})
    dim_1 = classificacao.get("dimensao_1_formacao", "")
    dim_3_pai = classificacao.get("dimensao_3_pai", "")
    dim_3_sub = classificacao.get("dimensao_3_sub", "")

    # Overlay summary (primeiras 5 legendas indicam ponto-chave)
    overlay_captions = overlay_aprovado.get("captions", [])
    overlay_texts = [c.get("text_full", "") for c in overlay_captions[:5]]
    overlay_summary = "\n".join(f"- {t}" for t in overlay_texts)

    research_str = _json.dumps(research_data, ensure_ascii=False, indent=2)[:5000]
    hook_str = _json.dumps(hook_escolhido, ensure_ascii=False, indent=2)

    return f"""<role>
Você é o especialista em SEO e title de YouTube Shorts para o canal "Best of Opera". Seu papel: gerar um title de até 100 caracteres e um conjunto de tags de até 450 caracteres no total, em português brasileiro.

## Diferenças entre YouTube e Instagram

O YouTube Shorts tem descoberta DIFERENTE do Instagram:
- **YouTube**: descoberta por busca textual + algoritmo de recomendações; title é gancho primário
- **Instagram**: descoberta por feed/explore; overlay sobre o vídeo é gancho primário

Implicação: no YouTube, o TITLE carrega peso crítico. Precisa capturar curiosidade E conter termos buscáveis (obra, intérprete, compositor).

## Sua régua editorial

Title híbrido: combina **ponto-chave narrativo** (gera clique) + **elementos buscáveis** (obra e/ou intérprete). Nem só SEO (seco, genérico) nem só narrativa (sem searchability).

Tags: mix de **genéricas** (música clássica, ópera, etc. — atingem cauda larga) + **específicas** (nome do compositor, obra, intérprete — atingem cauda curta).

## Seu tom

Conciso. Específico. Sem clichês. Fato concreto acima de adjetivo vago.{brand_block}
</role>

<context>
## 1. RESEARCH (fonte factual)

{research_str}

## 2. HOOK ESCOLHIDO PELO OPERADOR

{hook_str}

## 3. PRIMEIRAS LEGENDAS DO OVERLAY (indicam o ponto-chave narrativo)

{overlay_summary}

## 4. POST APROVADO (referência de tom e escopo temático)

{post_aprovado[:1500]}

## 5. CLASSIFICAÇÃO

- Formação: {dim_1}
- Gênero: {dim_3_pai} {f"→ {dim_3_sub}" if dim_3_sub else ""}
</context>

<task>
Gere title e tags conforme especificação.

## TITLE — Estrutura híbrida

O title combina:
- **Ponto-chave narrativo**: o ângulo editorial (alinhado ao hook e overlay)
- **Elementos buscáveis**: nome da obra e/ou intérprete e/ou compositor

### Padrão recomendado

**Forma A** — Pivô narrativo primeiro, obra/intérprete depois:
```
[Ponto-chave em 3-6 palavras] — [Obra] ([Intérprete])
```
Ex: "Cantou com bronquite e não cancelou — Vissi d'arte (Callas)"

**Forma B** — Obra/intérprete primeiro, ponto-chave depois:
```
[Obra], [Intérprete]: [Ponto-chave]
```
Ex: "Nessun Dorma, Pavarotti: a última ária de Puccini"

**Forma C** — Fato surpreendente + identificação (usa pipe):
```
[Fato condensado] | [Obra] — [Intérprete]
```
Ex: "Escrita em 6 semanas sob pressão | Vissi d'arte — Callas"

### Características do title

- **Máximo 100 caracteres absolutos**
- Em português brasileiro
- Inclui ao menos o nome da obra OU do intérprete (elementos buscáveis)
- Inclui ao menos 1 elemento de curiosidade (ponto-chave, paradoxo, fato surpreendente)
- Sem clickbait vazio ("Você não vai acreditar...")
- Sem adjetivos banidos (lista em <constraints>)
- Sem emojis (YouTube Shorts: emojis em title ficam estranhos)
- Sem pontos de exclamação (cheira a clickbait)
- Sem ALL CAPS

**EXCEÇÃO DOCUMENTADA**: diferente das legendas do overlay (onde travessões são banidos), no title YouTube o travessão `—` e o pipe `|` são **permitidos como separadores narrativos** entre ponto-chave e elementos identificadores. Esta é a única exceção à regra geral de travessões no pipeline BO (Bible v2 §6.3).

## TAGS — Mix genéricas + específicas

Separadas por vírgula + espaço. Total máximo 450 caracteres (contando vírgulas e espaços).

### Estrutura do mix

**Tags genéricas** (cauda larga):
- música clássica
- ópera / opera
- voz lírica
- canto lírico
- arte vocal
- best of opera
- música erudita

**Tags específicas** (cauda curta):
- Nome completo do compositor (Giuseppe Verdi, Wolfgang Amadeus Mozart)
- Nome da obra (La Traviata, Die Zauberflöte, Winterreise)
- Nome do intérprete (Maria Callas, Luciano Pavarotti)
- Tipo vocal (soprano coloratura, tenor spinto, contratenor)
- Período/estilo (ópera barroca, bel canto, verismo, Lied alemão)
- Tema dramático (tragédia, comédia, amor, morte)

### Quantidade e proporção

- Entre 8 e 15 tags
- Mix natural: 3-5 genéricas + 5-10 específicas
- Tags em PT quando termo é comum em PT (música clássica, ópera, tenor)
- Tags em idioma original para nomes próprios (Die Zauberflöte, Winterreise, Nessun Dorma)
- Termos bilíngues quando pertinente (classical music + música clássica)

### O que EVITAR em tags

- Tags muito longas (>40c)
- Tags repetitivas de significado (soprano + soprano lírica + lírica) — use 1 só
- Tags irrelevantes (entertainment, viral, trending)
- Hashtags com `#` — tags do YouTube não usam #
- Adjetivos vazios como tag

## EXEMPLO COMPLETO

Vídeo: Callas cantando Vissi d'arte de Tosca, 1964 Paris.
Hook: "Callas cantou esta ária\\nsem ter fé em mais nada."

Title (87c):
```
Cantou sem fé em mais nada — Vissi d'arte (Callas, Paris 1964)
```

tags_list (15 tags, soma + separadores = 382c):
```
[
  "Maria Callas", "Vissi d'arte", "Tosca", "Puccini",
  "soprano dramática", "ópera italiana", "verismo", "ópera romântica",
  "Paris 1964", "Giacomo Puccini", "Callas ao vivo", "ária de soprano",
  "best of opera", "música clássica", "ópera"
]
```

**Observações**:
- Title: ponto-chave narrativo ("sem fé em mais nada") + obra + intérprete + contexto (Paris 1964). Dentro de 100c. Usa `—` como separador (exceção permitida).
- 15 tags no `tags_list`. Quando concatenadas: `", ".join(...)` resulta em 382c, dentro do limite 450c. Código downstream faz essa concatenação — você NÃO retorna a string CSV.
</task>

<constraints>

## Técnicos (regras duras)

- **Title: máximo 100 caracteres**. Conte antes de retornar.
- **Tags: máximo 450 caracteres totais** (somando tags + vírgulas + espaços).
- **Entre 8 e 15 tags**.
- **Tags separadas por vírgula + espaço**: `tag1, tag2, tag3`.
- **Zero emojis no title e tags**.
- **Zero pontos de exclamação no title**.
- **Zero ALL CAPS no title** (exceto siglas como BBC, NYC, HD).
- **Zero hashtags no title e tags** (não é padrão YouTube).
- **Travessão `—` ou pipe `|` permitidos no title** como separador narrativo (exceção documentada em Bible v2 §6.3). Nenhum outro lugar do pipeline BO permite.

## Editoriais (regras duras)

- **Title em PT-BR** (nativo; traduzido na Etapa 6).
- **Tags em PT-BR principalmente**, nomes próprios em idioma original.
- **Zero adjetivos banidos no title** (lista PT abaixo):

{antipadroes_pt}

- **Zero invenção**: todo fato no title vem do research.
- **Title coerente com hook escolhido e overlay**: o ponto-chave do title está alinhado ao que o overlay desenvolve.
- **Sem clickbait vazio**: "Você não vai acreditar", "Ninguém esperava", "O segredo por trás de" — banidos.
</constraints>

<format>
Retorne EXATAMENTE este JSON, sem preâmbulo, sem markdown fences, sem comentários:

{{
  "title": "Texto do title, máximo 100c",

  "tags_list": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8"],

  "metadata": {{
    "title_forma_usada": "A | B | C",
    "ponto_chave_narrativo": "Qual é o ponto-chave expresso no title",
    "elementos_buscaveis": ["obra", "intérprete", "compositor"],
    "tags_genericas_count": 0,
    "tags_especificas_count": 0
  }},

  "quality_checks": {{
    "no_emojis": true,
    "no_exclamation_in_title": true,
    "no_all_caps_in_title": true,
    "no_hashtags": true,
    "adjetivos_banidos_detectados": [],
    "alertas": []
  }}
}}

**Nota sobre schema**: `tags_list` (array) é a ÚNICA fonte da verdade para as tags. O código downstream calcula `tags_csv = ", ".join(tags_list)` e `tags_chars = len(tags_csv)`; NÃO retorne esses campos (eram fonte de divergência entre LLM e realidade). Validadores pós-LLM recomputam `title_chars = len(title)` e `tags_count = len(tags_list)` — também não reportados por você.
</format>

<self_check>
Antes de retornar:

V1: **Title ≤ 100c**: conte `len(title)` mentalmente. Se estourou, comprima sem perder a ideia. O código downstream recomputa `title_chars = len(title)`; você não reporta esse número — se o texto estourar, só o operador vê via validador.

V2: **Tags: sum dos chars + separadores ≤ 450c**: para cada tag em `tags_list`, confira `sum(len(t) for t in tags_list) + 2 * (len(tags_list) - 1) ≤ 450`. O `2 *` é o `", "` entre cada tag.

V3: **Tags entre 8 e 15**: `len(tags_list)` ∈ [8, 15].

V4: **Zero adjetivos banidos no title**: releia contra lista em <constraints>. Substitua vazios.

V5: **Title coerente com hook e overlay**: o ponto-chave do title reflete o ângulo que o overlay desenvolve. Se divergir, realinhe.

V6: **Zero invenção**: obra, intérprete, compositor, ano no title estão no research.

V7: **Formato tags**: tags em `tags_list` (array). Sem vírgulas dentro de uma tag individual (ex: não `"Callas, Paris"` como UMA tag). Sem hashtags, sem emojis.

V8: **Travessão/pipe permitido só no title**: se algum apareceu em alguma tag de `tags_list`, remova.

Se alguma verificação falha, corrija antes de retornar.
</self_check>"""
