"""
RC Automation Prompt — Automação ManyChat para Reels Classics
==============================================================
Recebe: metadados + overlay + descrição
Produz: 3 respostas curtas + DM fixa + comentário keyword

Método: Kephart (Role → Context → Task → Constraints → Format → Self-check)
"""


def build_rc_automation_prompt(
    metadata: dict,
    overlay_legendas: list,
    post_text: str
) -> str:
    """
    Constrói o prompt de automação RC.

    metadata: dados básicos do vídeo
    overlay_legendas: legendas aprovadas do overlay
    post_text: descrição aprovada
    """

    artist = metadata.get("artist", "").strip()
    work = metadata.get("work", "").strip()
    composer = metadata.get("composer", "").strip()
    instrument = metadata.get("instrument_formation", "").strip()
    orchestra = metadata.get("orchestra", "").strip()
    album_opera = metadata.get("album_opera", "").strip()
    category = metadata.get("category", "").strip()

    # Mapeia categoria para gênero descritivo para a DM
    genre_map = {
        "Piano Solo": "repertório pianístico",
        "Orchestral": "repertório orquestral",
        "Chamber": "música de câmara",
        "Strings": "repertório para cordas",
        "Winds": "repertório para sopros",
        "Choral/Sacred": "repertório coral e sacro",
        "Ballet": "repertório de ballet",
        "Contemporary": "música contemporânea",
        "Crossover": "repertório clássico",
        "Opera": "repertório operístico",
    }
    genero_descritivo = genre_map.get(category, "repertório clássico")

    # Extrair textos relevantes do overlay para contexto
    overlay_temas = []
    for leg in overlay_legendas:
        if isinstance(leg, dict):
            texto = leg.get("texto", leg.get("text", ""))
            tipo = leg.get("tipo", leg.get("type", "corpo"))
            if tipo not in ("cta",) and texto:
                overlay_temas.append(texto)

    overlay_resumo = " | ".join(overlay_temas[:5])  # primeiras 5 legendas como contexto

    # Monta referência da obra
    obra_ref = work
    if album_opera:
        obra_ref = f"{work} (de {album_opera})"

    prompt = f"""<role>
Você escreve as mensagens automáticas do canal REELS CLASSICS para o ManyChat.
Tom: contido, poético mas informado. Nunca vendedor, nunca excessivo.
Cada palavra deve ter relação com o vídeo específico, não ser genérica.
</role>

<context>
VÍDEO:
Compositor: {composer}
Obra: {work}
Intérprete: {artist}
Instrumento: {instrument}
{"Orquestra: " + orchestra if orchestra else ""}
Categoria: {category}

OVERLAY (contexto narrativo):
{overlay_resumo}
</context>

<task>
Gere os 3 componentes de automação:

═══ COMPONENTE 1: 3 RESPOSTAS CURTAS (rotação ManyChat) ═══

Quando alguém comenta a keyword, recebe UMA destas respostas (o ManyChat rotaciona).
Cada resposta = 1 linha, máximo ~80 caracteres.

Formato de cada resposta:
[emoji temático] [frase curta conectada ao conteúdo do vídeo]

REGRAS:
- As 3 devem ser GENUINAMENTE diferentes (não trocar 1 palavra entre elas)
- Emojis temáticos do vídeo (não genéricos 🎵🎶)
- Tom contido. Sem exclamações excessivas. Sem linguagem de vendedor.
- Cada uma deve ter RELAÇÃO DIRETA com algo do overlay ou da performance
- Frases que um humano escreveria, não um bot

EXEMPLO BOM (Chopin/Fantaisie Impromptu):
✨ Te enviei — virtuosidade que habita, não exibe.
🎹 Link enviado — dois pulsos, uma só verdade.
🕯️ Já está no seu direct — Chopin que não deveria existir, mas existe.

POR QUE FUNCIONA: Cada frase referencia algo específico da peça (dois pulsos = polimetria, virtuosidade que habita = interpretação de Trifonov). São poéticas mas carregam informação.

EXEMPLO BOM (Mendelssohn/Hilary Hahn):
🎶 Te enviei — uma obra que começa antes de você estar pronto.
🎻 Direct enviado — virtuosismo imediato, dois séculos depois.
✨ Link enviado! O coração antes da cabeça, sempre.

═══ COMPONENTE 2: MENSAGEM FIXA DM ═══

Template EXATO (preencher os campos entre colchetes):

[2 emojis temáticos] Aqui está o link da performance da {obra_ref}, de {composer}, com {artist}:

👉 [link]

💛 No nosso site, você encontra as grandes obras {genero_descritivo} e análises aprofundadas na Coleção Dourada, com curadoria especializada.

🔗 Acesse e explore as playlists:

REGRAS:
- O [link] é placeholder — o operador insere depois
- O gênero descritivo deve ser específico ao tipo do vídeo: "{genero_descritivo}"
- Emojis temáticos ESPECÍFICOS (mesmos do header da descrição se possível)
- NÃO alterar a estrutura do template, apenas preencher os campos

═══ COMPONENTE 3: COMENTÁRIO KEYWORD ═══

Formato:
Comente "[KEYWORD]" e receba o link completo dessa performance [adjetivo/contexto]! [1-2 emojis]

REGRAS DA KEYWORD:
- 1 palavra simples, ligada ao vídeo
- Sem acentos complicados
- CAIXA ALTA
- Fácil de digitar
- Exemplos: PIANO, VIOLINO, MOZART, REQUIEM, BACH, LISZT, VALSA

REGRAS DO COMENTÁRIO:
- 1-2 linhas máximo
- Tom de curiosidade, não de vendas
- O adjetivo/contexto deve ser específico ao vídeo, não genérico
</task>

<constraints>
PROIBIDO:
- Tom de vendedor ou marketing
- Exclamações excessivas (máximo 1 por componente)
- Emojis genéricos (🎵🎶🎼) — usar sempre temáticos
- Frases que funcionam para qualquer vídeo
- Travessão (—) no comentário keyword
- Mais de 1 emoji na keyword comment (1-2 no máximo)

OBRIGATÓRIO:
- 3 respostas genuinamente diferentes
- DM fixa seguindo template exato
- Keyword em CAIXA ALTA, 1 palavra, sem acentos
- Cada resposta curta referencia algo do conteúdo do vídeo
</constraints>

<format>
Responda em JSON válido:

```json
{{
  "respostas_curtas": [
    "[emoji] frase 1",
    "[emoji] frase 2",
    "[emoji] frase 3"
  ],
  "dm_fixa": "texto completo da DM com [link] como placeholder",
  "comentario_keyword": {{
    "texto_completo": "Comente \\"KEYWORD\\" e receba...",
    "keyword": "KEYWORD"
  }}
}}
```
</format>

<self_check>
1. As 3 respostas são genuinamente diferentes? (não apenas trocar 1 palavra)
2. Cada resposta referencia algo do vídeo? (não genérica)
3. A DM fixa segue o template exato?
4. O gênero descritivo está correto para esta categoria?
5. A keyword é simples, sem acentos, em CAIXA ALTA?
6. O comentário keyword é específico ao vídeo?
7. Tom contido em tudo? Sem vendedor?
</self_check>"""

    return prompt
