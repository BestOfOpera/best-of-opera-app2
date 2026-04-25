"""
BO Detect-Metadata Prompt v1.0 — Pré-classificação multi-dimensional no Gate 0
==============================================================================
Prompt do Gate 0 do pipeline BO. Recebe screenshot do vídeo (ou metadados brutos
do YouTube) e retorna:
  - Identificação básica: artist, work, composer
  - Classificação provisória nas 3 dimensões (Formação / Tipo vocal / Gênero)
  - Confiança da classificação (alta / média / baixa)
  - Duração estimada do corte (se detectável)

Este prompt ALIMENTA o research v1. Sem detect-metadata expandido, o research
recebe dimensões vazias e perde o ganho de pré-classificação.

Método: Kephart (Role → Context → Task → Constraints → Format → Self-check)
Modelo: claude-sonnet-4-6 (multimodal: aceita imagem)
Temperature: 0.3 (precisão factual alta — é classificação, não criatividade)
Max tokens: 1024
Tool: nenhum
Output: JSON estruturado

Idioma: respostas em PT-BR nos campos descritivos. Valores de enum em
snake_case inglês/técnico (dimensões).
"""


# Taxonomia canônica das 3 dimensões — ÚNICA FONTE DA VERDADE.
# Mantida sincronizada com bo_research_prompt_v1.py (ambos lêem de cá).

DIMENSAO_1_FORMACAO = [
    "solo",
    "dueto",
    "trio",
    "quarteto",
    "quinteto_a_octeto",
    "pequeno_conjunto_vocal",
    "coro",
    "solistas_mais_coro",
    "solistas_mais_orquestra_mais_coro",
    "voz_mais_grupo_instrumental",
    "coro_a_cappella",
    "dueto_ou_trio_de_vozes_iguais",
]

DIMENSAO_2_TIPO_VOCAL = [
    "soprano",
    "mezzo_soprano",
    "contralto",
    "contratenor",
    "tenor",
    "baritono",
    "baixo",
    "baixo_baritono",
    "nao_aplicavel",  # coro/ensemble sem solista destacado
]

DIMENSAO_3_PAIS = [
    "formas_dramaticas",
    "formas_sacras_dramaticas",
    "formas_sacras_liturgicas",
    "formas_corais_nao_liturgicas",
    "cancao_de_arte",
    "cancao_popular_tradicional",
    "crossover_vocal",
    "outro",
]

DIMENSAO_3_SUBCATEGORIAS = {
    "formas_dramaticas": [
        "opera_barroca", "opera_classica", "opera_romantica", "bel_canto",
        "opera_verista", "opera_moderna", "opera_contemporanea",
        "opereta", "zarzuela", "musical_theater_crossover",
    ],
    "formas_sacras_dramaticas": ["oratorio", "cantata_sacra", "paixao"],
    "formas_sacras_liturgicas": [
        "missa", "requiem", "motete", "salmo", "hino",
        "magnificat_tedeum_stabatmater", "cantata_de_igreja",
    ],
    "formas_corais_nao_liturgicas": [
        "coro_de_opera_isolado", "madrigal", "canone",
        "coral_secular", "cantata_secular",
    ],
    "cancao_de_arte": [
        "lied_alemao", "melodie_francesa", "cancao_inglesa",
        "cancao_russa", "cancao_brasileira_latinoamericana", "cancao_espanhola",
    ],
    "cancao_popular_tradicional": ["napolitana", "italiana_popular", "folk_arranjada"],
    "crossover_vocal": ["opera_pop", "classico_contemporaneo", "trilha_sonora_operistica"],
    "outro": [],
}


def build_bo_detect_metadata_prompt(
    youtube_url: str = "",
    video_title_raw: str = "",
    video_description_raw: str = "",
    operator_hints: str = "",
) -> str:
    """
    Constrói prompt de detecção de metadados + pré-classificação multi-dimensional.

    Parâmetros:
    - youtube_url: URL do vídeo-fonte (para referência)
    - video_title_raw: título do vídeo no YouTube (quando disponível via API)
    - video_description_raw: descrição do YouTube (quando disponível)
    - operator_hints: observações livres do operador (ex: "é Lied de Schubert",
                      "coro do St. Thomas")

    IMAGEM: a imagem (screenshot da thumbnail ou do vídeo) é passada como anexo
    multimodal na chamada Anthropic, NÃO dentro deste string.

    Retorna: string do prompt completo.
    """
    dim1_lista = "\n".join(f"  - {x}" for x in DIMENSAO_1_FORMACAO)
    dim2_lista = "\n".join(f"  - {x}" for x in DIMENSAO_2_TIPO_VOCAL)
    dim3_pais_lista = "\n".join(f"  - {x}" for x in DIMENSAO_3_PAIS)
    dim3_sub_lista = "\n".join(
        f"  - {pai} → [{', '.join(subs) if subs else 'sem subcategorias (fallback)'}]"
        for pai, subs in DIMENSAO_3_SUBCATEGORIAS.items()
    )

    hints_block = ""
    if operator_hints.strip():
        hints_block = f"\n\nOBSERVAÇÕES DO OPERADOR:\n{operator_hints.strip()}"

    title_block = f"\nTÍTULO DO VÍDEO: {video_title_raw}" if video_title_raw else ""
    desc_block = (
        f"\nDESCRIÇÃO DO VÍDEO (primeiros 500c):\n{video_description_raw[:500]}"
        if video_description_raw
        else ""
    )

    return f"""<role>
Você é um classificador especialista em música vocal clássica, trabalhando na primeira etapa do pipeline editorial do canal "Best of Opera".

Sua função é extrair dos materiais disponíveis (screenshot, título, descrição) a identificação básica do vídeo (intérprete, obra, compositor) E classificá-lo provisoriamente em 3 dimensões taxonômicas independentes que irão alimentar a pesquisa profunda subsequente.

Você domina:
- Reconhecimento visual de contextos operísticos (palco, figurino, ambiente de ópera vs recital vs sacro vs estúdio)
- Leitura de chyrons e overlays com nomes de intérpretes e obras
- Identificação de compositores por título (se "Nessun Dorma" aparece, é Puccini/Turandot)
- Diferenciação entre tipos vocais por contexto visual e textual
- Classificação de formas musicais vocais

Você é rigoroso sobre CONFIANÇA: quando não tem evidência suficiente, preenche a classificação mais abrangente (grupo pai sem subcategoria; Dimensão 2 como `nao_aplicavel` se não dá para afirmar) e marca confiança baixa.
</role>

<context>
URL do vídeo: {youtube_url or "(não informado)"}{title_block}{desc_block}{hints_block}

IMAGEM EM ANEXO: screenshot do vídeo (thumbnail ou frame). Analise visualmente.

Este output alimenta diretamente a Etapa 1 (research profundo). Uma classificação errada aqui propaga para todas as 5 etapas seguintes. Mas uma classificação marcada como "baixa confiança" é corrigida na Etapa 1 com base em pesquisa web. Portanto: prefira baixa confiança a chute errado com alta confiança.
</context>

<task>
Produza JSON com:

## 1. IDENTIFICAÇÃO BÁSICA

- `artist`: nome do intérprete principal OU do coro/ensemble. Se identificado em chyron/overlay do vídeo, copie exatamente. Se inferido do contexto visual, marque em `observacoes`. Se não identificável, retorne string vazia.
- `work`: nome da obra/ária/peça. Idem regra acima.
- `composer`: nome do compositor. Se a obra é canônica (Nessun Dorma → Puccini, Casta Diva → Bellini), pode inferir com alta confiança mesmo sem evidência textual direta.

## 2. CLASSIFICAÇÃO MULTI-DIMENSIONAL

### Dimensão 1 — Formação vocal (obrigatória)

Escolha EXATAMENTE UM dos valores abaixo:

{dim1_lista}

**Heurísticas visuais:**
- 1 cantor em palco ou close individual → `solo`
- 2 cantores em interação de palco → `dueto`
- 3 → `trio`
- 4 → `quarteto`
- 5-8 → `quinteto_a_octeto`
- Grupo pequeno, todos visíveis → `pequeno_conjunto_vocal`
- Coro volumoso sem solista em destaque → `coro` ou `coro_a_cappella` (se não houver instrumentos)
- Coro + 1+ solistas à frente → `solistas_mais_coro`
- Coro + solistas + orquestra completa → `solistas_mais_orquestra_mais_coro`
- Solista + banda/conjunto instrumental não-orquestral → `voz_mais_grupo_instrumental`

### Dimensão 2 — Tipo vocal (quando aplicável)

Escolha EXATAMENTE UM dos valores abaixo:

{dim2_lista}

**Heurísticas:**
- Formação `coro` ou `coro_a_cappella` sem solista → `nao_aplicavel`
- Solo identificável por tessitura aparente + contexto da obra
- Se ambíguo (ex: mezzo ou soprano dramática), marque a escolha mais provável + confiança média

Subtipo opcional (lírico/dramático/coloratura/spinto/etc.) vai em `dimensao_2_subtipo` — preenchível apenas com confiança alta.

### Dimensão 3 — Gênero/tradição (obrigatória para `pai`; opcional para `sub`)

**Grupos pai** (Dimensão 3.pai, obrigatório):

{dim3_pais_lista}

**Subcategorias** (Dimensão 3.sub, preencher apenas se confiança razoável):

{dim3_sub_lista}

**Heurísticas:**
- Palco/figurino de ópera com coros, cenário, ação dramática → `formas_dramaticas`
- Catedral/igreja + coro + orquestra + contexto litúrgico → `formas_sacras_liturgicas`
- Oratório em sala de concerto sem encenação → `formas_sacras_dramaticas`
- Cantor solo + pianista em recital → provável `cancao_de_arte` (subcategoria pela língua)
- Crossover pop/clássico (arranjo contemporâneo, instrumentação não-clássica) → `crossover_vocal`

## 3. METADADOS TÉCNICOS DETECTÁVEIS

- `duracao_total_video_seconds`: se extraível do player/descrição, preencher. Senão, null.
- `idioma_texto_cantado`: se identificável do contexto (obra canônica → idioma canônico), preencher. Senão, null.

## 4. CONFIANÇA

Para cada classificação, registrar confiança: "alta" | "media" | "baixa".

- ALTA: evidência direta + não-ambígua
- MÉDIA: inferido de contexto forte (ex: obra canônica sugere composer mesmo sem texto explícito)
- BAIXA: chute educado sem evidência firme — disparar revisão manual no Gate 0

**Regra**: se qualquer dimensão fica em baixa, mas operador tem alta confiança manual, operador corrige no Gate 0 antes de avançar.
</task>

<constraints>
- **Valores de enum EXATAMENTE como listados**: snake_case, em inglês/técnico, sem variações
- **`artist`, `work`, `composer` em idioma original** (não traduzir — "Nessun Dorma" fica "Nessun Dorma", não "Nenhum Durma")
- **Zero invenção**: se não sabe, deixe vazio e marque em `observacoes`
- **Zero adjetivos**: isto é classificação, não descrição
- **Formato strict JSON**: sem markdown, sem comentários inline
</constraints>

<format>
Retorne EXATAMENTE este JSON, sem preâmbulo, sem markdown fences:

{{
  "identificacao": {{
    "artist": "...",
    "work": "...",
    "composer": "...",
    "confianca_identificacao": "alta | media | baixa"
  }},

  "classificacao": {{
    "dimensao_1_formacao": "...",
    "confianca_dimensao_1": "alta | media | baixa",

    "dimensao_2_tipo_vocal": "... | nao_aplicavel",
    "dimensao_2_subtipo": "... | null",
    "confianca_dimensao_2": "alta | media | baixa",

    "dimensao_3_pai": "...",
    "dimensao_3_sub": "... | null",
    "confianca_dimensao_3": "alta | media | baixa"
  }},

  "metadados_tecnicos": {{
    "duracao_total_video_seconds": 60.0,
    "idioma_texto_cantado": "italiano | alemao | frances | latim | ... | null"
  }},

  "observacoes": "Texto livre em PT-BR explicando: (a) de onde veio cada inferência com baixa confiança, (b) ambiguidades que o operador deve confirmar no Gate 0, (c) alertas. Mantenha ≤300c."
}}
</format>

<self_check>
Antes de retornar:

V1: **Dimensão 1 obrigatória**: preenchida com valor exato da lista. Se falhou, preencha `solo` como fallback + confiança baixa + nota em observações.

V2: **Dimensão 3.pai obrigatória**: preenchida. Se falhou, preencha `outro` + confiança baixa.

V3: **Dimensão 2**: `nao_aplicavel` quando formação não tem solista destacado (coro/coro_a_cappella). Subtipo só com confiança alta.

V4: **Dimensão 3.sub**: só preenchida quando confiança permite. Senão, null.

V5: **Confiança calibrada**: baixa para chutes, média para inferência de contexto, alta só para evidência direta. Honestidade sobre incerteza.

V6: **Identificação não-inventada**: artist, work, composer vazios se não há evidência. Nome completo em idioma original se identificado.

V7: **Valores exatos**: todos os enums batem com as listas acima, sem typos.

V8: **JSON válido**: todos os campos presentes (com null/vazio onde aplicável).

Se algo falha, corrija antes de retornar.
</self_check>"""
