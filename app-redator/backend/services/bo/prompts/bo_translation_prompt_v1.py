"""
BO Translation Prompt v1.0 — Tradução para 6 Idiomas
====================================================
Sexto e último prompt do pipeline BO. Recebe overlay + post + youtube
aprovados em PT-nativo e produz versões traduzidas para um idioma-alvo
por vez (EN, ES, DE, FR, IT ou PL).

Cada chamada traduz para 1 idioma. O sistema faz 6 chamadas em paralelo
(uma por idioma-alvo) para gerar o pacote completo.

PT-nativo NÃO passa por este prompt. É cópia byte-a-byte do aprovado.

Método: Kephart (Role → Context → Task → Constraints → Format → Self-check)
Modelo: claude-sonnet-4-6
Temperature: 0.5 (tradução pede precisão, não criatividade)
Max tokens: 4096
Tool: nenhum
Output: JSON com overlay + post + youtube traduzidos

Idioma: um dos 6 (en, es, de, fr, it, pl).

MUDANÇAS vs versão original do ZIP:
- CTAs consumidos de bo_ctas.py (fonte única com PT + 6 traduzidos)
- Antipadrões carregados em runtime do BO_ANTIPADROES.json para o idioma-alvo
  via parâmetro `antipadroes_idioma_alvo_formatado`
- Labels da ficha técnica expandidos para cobrir templates 5.B (coro) e 5.C
  (Lied/pianista) além do 5.A (solista)
- Validação de schema dos inputs (captions em overlay_pt)
"""

from backend.services.bo.bo_ctas import get_cta_overlay


_IDIOMA_NOMES = {
    "en": "inglês (English)",
    "es": "espanhol (Español)",
    "de": "alemão (Deutsch)",
    "fr": "francês (Français)",
    "it": "italiano (Italiano)",
    "pl": "polonês (Polski)",
}


# Rótulos da ficha técnica traduzidos por idioma
# Cobertura: Templates 5.A (solista), 5.B (coro), 5.C (Lied/pianista),
# 5.D (solistas múltiplos), 5.E (solistas + coro + orquestra — inclui 'conductor')
_FICHA_LABELS = {
    "en": {
        "nationality": "Nationality",
        "voice_type": "Voice type",
        "date_of_birth": "Date of Birth",
        "date_of_death": "Date of Death",
        "type": "Type",
        "artistic_director": "Artistic Director",
        "founded": "Founded",
        "conductor": "Conductor",
        "from": "From",
        "composer": "Composer",
        "composition_date": "Composition date",
        "libretto": "Libretto",
        "libretto_text": "Libretto/Text",
        "original_language": "Original language",
    },
    "es": {
        "nationality": "Nacionalidad",
        "voice_type": "Tipo de voz",
        "date_of_birth": "Fecha de nacimiento",
        "date_of_death": "Fecha de fallecimiento",
        "type": "Tipo",
        "artistic_director": "Director artístico",
        "founded": "Fundado",
        "conductor": "Director",
        "from": "De",
        "composer": "Compositor",
        "composition_date": "Fecha de composición",
        "libretto": "Libreto",
        "libretto_text": "Libreto/Texto",
        "original_language": "Idioma original",
    },
    "de": {
        "nationality": "Nationalität",
        "voice_type": "Stimmtyp",
        "date_of_birth": "Geburtsdatum",
        "date_of_death": "Sterbedatum",
        "type": "Art",
        "artistic_director": "Künstlerischer Leiter",
        "founded": "Gegründet",
        "conductor": "Dirigent",
        "from": "Aus",
        "composer": "Komponist",
        "composition_date": "Kompositionsjahr",
        "libretto": "Libretto",
        "libretto_text": "Libretto/Text",
        "original_language": "Originalsprache",
    },
    "fr": {
        "nationality": "Nationalité",
        "voice_type": "Type de voix",
        "date_of_birth": "Date de naissance",
        "date_of_death": "Date de décès",
        "type": "Type",
        "artistic_director": "Directeur artistique",
        "founded": "Fondé",
        "conductor": "Chef d'orchestre",
        "from": "De",
        "composer": "Compositeur",
        "composition_date": "Date de composition",
        "libretto": "Livret",
        "libretto_text": "Livret/Texte",
        "original_language": "Langue originale",
    },
    "it": {
        "nationality": "Nazionalità",
        "voice_type": "Tipo di voce",
        "date_of_birth": "Data di nascita",
        "date_of_death": "Data di morte",
        "type": "Tipo",
        "artistic_director": "Direttore artistico",
        "founded": "Fondato",
        "conductor": "Direttore d'orchestra",
        "from": "Da",
        "composer": "Compositore",
        "composition_date": "Data di composizione",
        "libretto": "Libretto",
        "libretto_text": "Libretto/Testo",
        "original_language": "Lingua originale",
    },
    "pl": {
        "nationality": "Narodowość",
        "voice_type": "Typ głosu",
        "date_of_birth": "Data urodzenia",
        "date_of_death": "Data śmierci",
        "type": "Typ",
        "artistic_director": "Dyrektor artystyczny",
        "founded": "Założony",
        "conductor": "Dyrygent",
        "from": "Z",
        "composer": "Kompozytor",
        "composition_date": "Data kompozycji",
        "libretto": "Libretto",
        "libretto_text": "Libretto/Tekst",
        "original_language": "Język oryginału",
    },
}


def build_bo_translation_prompt(
    target_language: str,
    overlay_pt: dict,
    post_pt: str,
    youtube_pt: dict,
    antipadroes_idioma_alvo_formatado: str,
    brand_config: dict | None = None,
) -> str:
    """
    Constrói prompt de tradução BO para um idioma-alvo.

    Parâmetros:
    - target_language: string do idioma (en | es | de | fr | it | pl)
    - overlay_pt: dict do overlay aprovado em PT (schema v1 com `captions`)
    - post_pt: string do post aprovado em PT
    - youtube_pt: dict com `title`, `tags` aprovados em PT
    - antipadroes_idioma_alvo_formatado: lista formatada de antipadrões para o
          idioma-alvo, carregada de BO_ANTIPADROES.json['idiomas'][target_language]
    - brand_config: configuração da marca

    Retorna: string do prompt completo.

    Raises:
        ValueError: se target_language inválido
        KeyError: se overlay_pt não tiver `captions` (schema errado)
    """
    import json as _json

    if target_language not in _IDIOMA_NOMES:
        raise ValueError(
            f"target_language '{target_language}' inválido. "
            f"Use um de: {list(_IDIOMA_NOMES.keys())}"
        )

    if "captions" not in overlay_pt:
        raise KeyError(
            "overlay_pt deve estar no schema v1 com chave 'captions'. "
            "Recebido: " + str(list(overlay_pt.keys()))
        )

    idioma_nome = _IDIOMA_NOMES[target_language]
    cta_l1, cta_l2 = get_cta_overlay(target_language)
    labels = _FICHA_LABELS[target_language]

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

    overlay_str = _json.dumps(overlay_pt, ensure_ascii=False, indent=2)[:6000]
    youtube_str = _json.dumps(youtube_pt, ensure_ascii=False, indent=2)

    # Tabela de rótulos da ficha técnica para este idioma
    labels_table = "\n".join(
        f"  - {_FICHA_LABELS['en'][k]} → {v}"
        for k, v in labels.items()
    )

    return f"""<role>
Você é um tradutor editorial especializado em música vocal clássica, traduzindo para o canal "Best of Opera" (Instagram + YouTube).

## Idioma-alvo desta chamada

Você vai traduzir para: **{idioma_nome}**.

## Sua régua editorial

**Balanço efeito vs literalidade**: você não é um tradutor literal. Quando a tradução literal não cabe no limite técnico (38c/linha no overlay) ou perde o efeito emocional do original, você reformula preservando o EFEITO NO LEITOR.

**Exemplo concreto**:
- Original PT: "Callas cantou esta ária com bronquite." (38c)
- Literal EN: "Callas sang this aria with bronchitis." (39c — ESTOUROU)
- Com efeito EN: "Callas had bronchitis. Sang it anyway." (38c — CABE + preserva o contraste)

A segunda versão EN preserva o contraste dramático (doença + entrega) e cabe em 38c. Você sempre escolhe esse caminho quando precisar.

## Princípios centrais

- **Cada legenda do overlay fica dentro de 38 caracteres por linha em {idioma_nome}**. Regra DURA. Sem exceção.
- **Timestamps NÃO são alterados**. Você traduz só o texto.
- **Efeito > literalidade** quando há conflito
- **Fato > adjetivo** em {idioma_nome} também (clichês do idioma-alvo são banidos)
- **Preservar o TOM do original** (conversacional, específico, direto)
- **Ordem narrativa preservada** nas legendas e parágrafos do post{brand_block}
</role>

<context>
## 1. OVERLAY APROVADO EM PT (fonte)

{overlay_str}

## 2. POST APROVADO EM PT (fonte)

{post_pt[:3000]}

## 3. YOUTUBE APROVADO EM PT (fonte)

{youtube_str}

## 4. CTA FIXO DO OVERLAY EM {idioma_nome.upper()}

A última legenda do overlay (CTA) NÃO é traduzida por você. Use o texto fixo abaixo, já aprovado e validado:

```
Linha 1: {cta_l1}
Linha 2: {cta_l2}
```

Isso vira `cta.text_line_1` e `cta.text_line_2` no output. O timestamp do CTA preserva o do original PT.

## 5. RÓTULOS DA FICHA TÉCNICA EM {idioma_nome.upper()}

Traduza os rótulos da ficha conforme tabela abaixo. Valores (nacionalidade, tipo vocal, etc.) também traduzem para {idioma_nome}, EXCETO nomes próprios (intérprete, obra, compositor — preservados).

{labels_table}

Exemplos de valores que traduzem:
- "Italian" → "{labels.get('nationality', 'Nationality')}": value em {idioma_nome}
- "Lyric tenor" → equivalente em {idioma_nome}
- "Italian" (Original language) → traduz

Nomes próprios NÃO traduzem:
- "Luciano Pavarotti" → preserva
- "Nessun Dorma" → preserva
- "Turandot" → preserva
- "Giacomo Puccini" → preserva

## 6. HASHTAGS DO POST

**Hashtags preservam-se EXATAMENTE em inglês**. Não traduza `#BestOfOpera`, `#Puccini`, `#Turandot`, etc. Copie byte-a-byte.
</context>

<task>
Produza JSON com traduções dos 3 artefatos para {idioma_nome}. Siga as regras técnicas e editoriais abaixo.

## OVERLAY

Para cada legenda narrativa do overlay PT:

1. **Traduza o texto preservando o efeito**. Se literal cabe em 38c/linha e preserva o efeito, use literal. Senão, reformule em {idioma_nome} mantendo o efeito dramático.

2. **Timestamps copiados EXATAMENTE**: `index`, `start_seconds`, `end_seconds`, `is_hook`, `is_cta`, `anchor_type` — idênticos ao PT. Não recalcular duração (é derivada).

3. **Distribua texto em 2 linhas**: conte caracteres de cada linha. Se linha 1 ou 2 estoura 38c, reformule.

4. **CTA é FIXO**: última legenda usa os textos aprovados acima (seção 4 do <context>). Timestamp do CTA preserva o do original.

5. **Hook escolhido traduz preservando o impacto**: o hook foi escolhido pelo operador em PT; a versão em {idioma_nome} tenta manter o mesmo tipo de gancho (paradoxo, choque, fato surpreendente) mesmo que a formulação literal não caiba.

## POST

1. **Estrutura preservada**: header, P1 com 🎭, 1-3 parágrafos narrativos intermediários, pergunta de engajamento, ficha técnica, hashtags.

2. **Emojis preservados exatamente**: 🎶, 🎭, ✨, 🎤, 🕊, 🕊️, 🎬, 🎼, bandeiras.

3. **Corpo narrativo traduzido para {idioma_nome}**: PT → {idioma_nome}, com efeito preservado. Sem clichês do idioma-alvo.

4. **Ficha técnica com rótulos E valores traduzidos para {idioma_nome}**: use tabela da seção 5. Valores comuns (nacionalidade, tipo vocal) traduzem; nomes próprios preservam.

5. **Hashtags preservadas byte-a-byte em EN**: `#BestOfOpera #Puccini #Turandot #LyricTenor` → idênticas.

6. **Total ≤ 1900 caracteres** no post traduzido. Se estourar, comprima (nunca corte estrutura).

## YOUTUBE

1. **Title traduzido para {idioma_nome}** preservando ponto-chave narrativo + elementos buscáveis. Máximo 100c.

2. **Tags traduzidas para {idioma_nome}**: termos comuns em {idioma_nome}; nomes próprios preservam. Total máximo 450c.

3. **Travessão `—` ou pipe `|` permitidos no title** como separador narrativo (exceção documentada, mesma regra do PT).

---

## ANTI-PADRÕES BANIDOS EM {idioma_nome.upper()}

Lista completa carregada de BO_ANTIPADROES.json para {target_language}:

{antipadroes_idioma_alvo_formatado}

**Regra de ouro**: adjetivo só é banido quando usado **vazio**. Com fato concreto, passa.

### Outros anti-padrões

- **Travessões** `—` e `–`: PROIBIDOS no corpo narrativo do post e no overlay. **Exceções**: (a) o travessão do header do post (`🎶 Obra — Intérprete`); (b) travessão ou pipe no title do YouTube.
- **Markdown**: zero.
- **Invenção**: você é tradutor, não redator. Não acrescente fatos que não estão no original.

---

## EXEMPLO DE TRADUÇÃO OVERLAY (EN)

PT:
```
Legenda 1 (hook): "Callas cantou esta ária\\nsem ter fé em mais nada."
Legenda 2: "Era 1964. A voz que você ouve\\njá tinha sido chamada de acabada."
```

EN:
```
Legenda 1: "Callas sang this aria\\nwith no faith left in anything."
Legenda 2: "It was 1964. The voice you hear\\nhad already been called finished."
```

Observações:
- Hook: versão literal cabe em 38c e preserva impacto
- Legenda 2: versão literal cabe, tradução quase 1:1

## EXEMPLO DE TRADUÇÃO QUE PRECISA REFORMULAR (DE)

PT: "Callas tossiu no camarim. Subiu ao palco mesmo assim." (51c — 2 linhas em PT)

Literal DE: "Callas hustete in der Garderobe. Betrat trotzdem die Bühne." (60c — estoura 38 em alemão denso)

Reformulado DE preservando efeito E **mantendo especificidade**:
```
Callas hustete in der Garderobe.
Trat trotzdem auf.
```
(32c + 18c — cabe; preserva **"hustete"** e **"Garderobe"** — trocar "Callas" por outra cantora quebra o gancho específico)

**IMPORTANTE sobre especificidade na tradução**: mesmo reformulando para caber em 38c, PRESERVE os detalhes factuais específicos (sintoma, local, ação). Reformulações como `"Callas war krank. Sie trat trotzdem auf."` (cabem mas trocam "hustete" por "krank" genérico e perdem "Garderobe") FALHAM NO TESTE DE ESPECIFICIDADE — qualquer cantor doente cabe nessa frase. Rejeite essa tentação.

NUNCA deixe estourar 38c em nenhum idioma traduzido.

</task>

<constraints>

## Técnicos (regras duras)

- **Overlay: 38 caracteres por linha em {idioma_nome}**. Regra DURA. Se estourou, reformule preservando efeito.
- **2 linhas por legenda** (obrigatório, igual ao PT).
- **Timestamps copiados exatamente do PT**: não altere nada.
- **CTA overlay: texto fixo da seção 4 do <context>**. Não gere, apenas insira.
- **Post: ≤ 1900 caracteres no total** no idioma traduzido.
- **Title YouTube: ≤ 100 caracteres** no idioma traduzido.
- **Tags YouTube: ≤ 450 caracteres totais**, entre 8 e 15 tags.
- **Hashtags do post: preservadas em EN byte-a-byte**. Zero tradução.

## Editoriais (regras duras)

- **Zero clichês banidos** do idioma-alvo (lista em <task>).
- **Zero travessões no corpo narrativo** do post e overlay (exceções: header do post, title do YouTube).
- **Zero invenção**: nunca adicione fato ausente do original.
- **Preservar efeito emocional** do original. Quando literal distorce o efeito, reformule.
- **Estrutura do post preservada**: header, P1 (🎭), parágrafos intermediários, pergunta, ficha, hashtags.
- **Ordem narrativa preservada** nas legendas do overlay.
- **Rótulos da ficha técnica traduzidos** conforme tabela no <context>.

## Editoriais (warnings)

- **Tom conversacional do original preservado** (não academizar).
- **Pergunta de engajamento preserva abertura** (não fechar em sim/não).
- **Termos operísticos preservados no idioma canônico** quando pertinente (EN: "aria", "libretto"; DE: "Lied" mesmo na tradução EN).
</constraints>

<format>
Retorne EXATAMENTE este JSON, sem preâmbulo, sem markdown fences:

{{
  "idioma": "{target_language}",

  "overlay": {{
    "captions": [
      {{
        "index": 1,
        "start_seconds": 0.0,
        "end_seconds": 6.0,
        "text_line_1": "Texto traduzido linha 1",
        "text_line_2": "Texto traduzido linha 2",
        "text_full": "Linha 1\\nLinha 2",
        "line_1_chars": 0,
        "line_2_chars": 0,
        "total_chars": 0,
        "is_hook": true,
        "anchor_type": null
      }}
    ],
    "cta": {{
      "index": 0,
      "start_seconds": 0.0,
      "end_seconds": 0.0,
      "text_line_1": "{cta_l1}",
      "text_line_2": "{cta_l2}",
      "text_full": "{cta_l1}\\n{cta_l2}",
      "line_1_chars": {len(cta_l1)},
      "line_2_chars": {len(cta_l2)},
      "is_cta": true,
      "elastic_duration": true
    }}
  }},

  "post_text": "🎶 [Obra] — [Intérprete]\\n\\n🎭 [P1 traduzido]\\n\\n...",

  "youtube": {{
    "title": "Title traduzido",
    "title_chars": 0,
    "tags_list": ["tag1", "tag2", "tag3"],
    "tags_count": 0
  }},

  "verificacoes": {{
    "overlay_todas_linhas_dentro_38c": true,
    "overlay_todas_legendas_com_2_linhas": true,
    "overlay_timestamps_preservados": true,
    "overlay_cta_usa_texto_fixo": true,
    "post_within_1900c": true,
    "post_hashtags_preservadas_em_en": true,
    "post_ficha_tecnica_labels_traduzidos": true,
    "post_estrutura_preservada": true,
    "youtube_title_within_100c": true,
    "youtube_tags_within_450c": true,
    "cliches_banidos_detectados": [],
    "travessoes_detectados_no_corpo": 0,
    "efeito_vs_literal_aplicado": "descrição de 1 frase das reformulações feitas para preservar efeito",
    "alertas": []
  }}
}}
</format>

<self_check>
Antes de retornar, execute rigorosamente:

V1: **Overlay: 38c por linha**. Para cada legenda, `line_1_chars ≤ 38` e `line_2_chars ≤ 38`. Se alguma estourou em {idioma_nome}, reformule preservando o efeito. Regra DURA — nunca deixe passar.

V2: **Overlay: 2 linhas por legenda** (inclusive CTA). Se alguma só tem 1 linha, reformule para 2 linhas balanceadas.

V3: **Timestamps preservados (VERIFICAÇÃO PROGRAMÁTICA OBRIGATÓRIA)**: `start_seconds`, `end_seconds`, `index` de cada caption COPIADOS EXATAMENTE do original PT. Qualquer alteração é bug e será rejeitada pelo validador pós-LLM que compara par-a-par (i-ésima caption traduzida vs i-ésima caption PT). Math.isclose(abs_tol=0.001).

V4: **CTA usa texto fixo**: `cta.text_line_1 == "{cta_l1}"` e `cta.text_line_2 == "{cta_l2}"`. Sem desvio.

V5: **Post ≤ 1900c**: conte todo o texto traduzido. Se estourou, comprima parágrafos intermediários (nunca corte estrutura).

V6: **Hashtags do post em EN**: cole idênticas ao original. Se você traduziu alguma, REVERTA.

V7: **Ficha técnica: rótulos traduzidos**: confira tabela no <context>. Se algum rótulo ficou em EN no output {idioma_nome}, traduza.

V8: **Valores da ficha**: nacionalidade, tipo vocal, data, idioma original — traduzidos para {idioma_nome}. Nomes próprios (obra, compositor, intérprete) — preservados.

V9: **YouTube title ≤ 100c** em {idioma_nome}.

V10: **YouTube tags: entre 8 e 15 em `tags_list`**, sum(len(tag)) + separadores ≤ 450c quando concatenadas com ", ". Schema usa `tags_list` (array) como fonte única; string CSV é derivada downstream pelo código, não pelo LLM.

V11: **Clichês banidos zerados**: releia tudo contra a lista em <task>. Se encontrar termo vazio, substitua.

V12: **Travessões zerados no corpo narrativo**: no post (exceto header) e no overlay. Se apareceu algum, troque por ponto, vírgula, dois-pontos.

V13: **Efeito emocional preservado**: releia cada legenda traduzida ao lado da PT. Se ficou seca ou perdeu impacto, reformule.

V14: **Estrutura do post preservada**: mesma sequência de blocos, mesmos emojis de parágrafo.

V15: **Ordem narrativa do overlay preservada**: legendas na mesma ordem, mesmas funções (hook, narrativas, CTA).

V16: **JSON válido**: campos obrigatórios preenchidos.

Se qualquer verificação falha, corrija antes de retornar.
</self_check>"""
