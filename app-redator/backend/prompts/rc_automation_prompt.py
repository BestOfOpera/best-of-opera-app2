"""
RC Automation Prompt v3 — Automação ManyChat para Reels Classics
==================================================================

Recebe: metadata + overlay + post_text
Produz: 3 respostas curtas + DM fixa + comentário keyword
Método: Kephart + estratégias A/B/C explícitas de diversidade

MUDANÇAS v2 → v3:
1. Estratégias A/B/C nomeadas e obrigatoriamente declaradas
2. Exemplos bons/ruins de diversidade
"""


def build_rc_automation_prompt(
    metadata: dict,
    overlay_legendas: list,
    post_text: str,
) -> str:
    """
    Constrói o prompt v3 de automação RC.
    """
    artist = metadata.get("artist", "").strip()
    work = metadata.get("work", "").strip()
    composer = metadata.get("composer", "").strip()
    instrument = metadata.get("instrument_formation", "").strip()
    orchestra = metadata.get("orchestra", "").strip()
    album_opera = metadata.get("album_opera", "").strip()
    category = metadata.get("category", "").strip()

    # Mapeamento categoria → gênero descritivo
    genre_map = {
        "Piano Solo": "do repertório pianístico",
        "Orchestral": "do repertório orquestral",
        "Chamber": "de música de câmara",
        "Strings": "para cordas",
        "Winds": "para sopros",
        "Choral/Sacred": "do repertório coral e sacro",
        "Ballet": "do repertório de ballet",
        "Contemporary": "da música contemporânea",
        "Crossover": "do repertório clássico",
        "Opera": "do repertório operístico",
    }
    genero_descritivo = genre_map.get(category, "do repertório clássico")

    # Extrai contexto do overlay (filtra _is_cta e sentinel _is_audit_meta v3.1)
    overlay_temas = []
    for leg in overlay_legendas:
        if not isinstance(leg, dict):
            continue
        if leg.get("_is_audit_meta") or leg.get("_is_cta"):
            continue
        texto = leg.get("texto", leg.get("text", ""))
        tipo = leg.get("tipo", leg.get("type", "corpo"))
        if tipo != "cta" and texto:
            overlay_temas.append(texto)
    overlay_resumo = " | ".join(overlay_temas[:5])

    obra_ref = work
    if album_opera:
        obra_ref = f"{work} (de {album_opera})"

    # Truncar descrição para contexto (evita inflar o prompt; o essencial — header + início do P1 — cabe).
    post_clean = (post_text or "").strip()
    if len(post_clean) > 500:
        post_summary = post_clean[:500].rstrip() + "..."
    else:
        post_summary = post_clean

    prompt = f"""<role>
Você gera as mensagens automáticas do ManyChat para o canal Reels Classics.

Tom: contido, poético mas informado. NUNCA vendedor, NUNCA excessivo.

Cada palavra deve ter relação com o vídeo específico. Genericidade quebra a sensação de resposta humana.
</role>

<context>
VÍDEO:
Compositor: {composer}
Obra: {work}
Intérprete: {artist}
Instrumento: {instrument}
{"Orquestra: " + orchestra if orchestra else ""}
Categoria: {category}
Gênero descritivo: {genero_descritivo}

OVERLAY (contexto narrativo):
{overlay_resumo}

DESCRIÇÃO APROVADA (para consistência de tom, emojis e temas complementares):
{post_summary}

Três componentes para configurar no ManyChat:
1. Três respostas curtas que rotacionam quando alguém comenta a keyword
2. Uma DM fixa enviada com o link da performance
3. Um comentário pinned do canal explicando como obter o link
</context>

<task>
═══ COMPONENTE 1 — 3 RESPOSTAS CURTAS ═══

Cada resposta:
- 1 linha
- Máximo ~80 caracteres
- Formato: [emoji temático] [frase curta conectada ao vídeo]

DIVERSIDADE — aplicar UMA destas três estratégias EXPLICITAMENTE:

ESTRATÉGIA A (por tom):
- Uma informativa (fato)
- Uma poética (imagem)
- Uma provocadora (pergunta/desafio)

ESTRATÉGIA B (por aspecto):
- Cada uma referencia aspecto diferente do overlay (compositor / peça / intérprete)

ESTRATÉGIA C (por verbo):
- Cada uma usa verbo de envio diferente (te enviei / link enviado / já está no seu direct)

Trocar 1-2 palavras entre respostas NÃO é diversidade. Será rejeitado.

REGRAS DE TOM:
- Emojis temáticos do vídeo, NUNCA genéricos (🎵🎶📻)
- Tom contido. Sem exclamações excessivas. Sem vendedor.
- Cada uma deve ter RELAÇÃO DIRETA com algo do overlay ou da performance

═══ COMPONENTE 2 — DM FIXA ═══

Template EXATO (preencher os campos):

[2 emojis temáticos] Aqui está o link da performance da {obra_ref}, de {composer}, com {artist}:

👉 [link]

💛 No nosso site, você encontra as grandes obras {genero_descritivo} e análises aprofundadas sobre música clássica.

🔗 Acesse e explore as playlists:

REGRAS:
- [link] permanece placeholder
- Emojis temáticos específicos (mesmos do header da descrição idealmente)
- NÃO alterar estrutura do template

═══ COMPONENTE 3 — COMENTÁRIO KEYWORD ═══

Formato:
Comente "[KEYWORD]" e receba o link completo dessa performance [adjetivo/contexto]! [1-2 emojis]

REGRAS DA KEYWORD:
- 1 palavra simples, ligada ao vídeo
- Sem acentos
- CAIXA ALTA
- Fácil de digitar
- Exemplos: PIANO, VIOLINO, MOZART, REQUIEM, BACH, LISZT, VALSA, MOONLIGHT, CAMPANELLA

REGRAS DO COMENTÁRIO:
- 1-2 linhas máximo
- Tom de curiosidade, não de vendas
- Adjetivo/contexto específico ao vídeo (fenomenal, histórica, rara, intensa)
</task>

<constraints>
PROIBIDO:
- Tom de vendedor
- Exclamações excessivas (máximo 1 por componente)
- Emojis genéricos (🎵🎶📻)
- Frases que funcionam para qualquer vídeo
- Travessão (—) no comentário keyword
- Mais de 1 emoji na keyword comment

OBRIGATÓRIO:
- 3 respostas genuinamente diferentes (estratégia A, B ou C declarada)
- DM fixa seguindo template exato
- Keyword em CAIXA ALTA, 1 palavra, sem acentos
- Cada resposta curta referencia algo do conteúdo do vídeo
</constraints>

<examples>
BOM — Liszt/La Campanella (estratégia B: por aspecto):

🎹 Te enviei. Virtuosidade que habita, não exibe.        [foca na performance]
🎼 Link enviado. Dois pulsos, uma só verdade.            [foca na peça/estrutura]
🔔 Já está no seu direct. O sino que Paganini nunca ouviu. [foca na obsessão/Liszt]

═══════════════════════════════════════════════

BOM — Mendelssohn/Hilary Hahn (estratégia A: por tom):

🎻 Te enviei. Uma obra que começa antes de você estar pronto.  [informativa]
🔥 Direct enviado. Virtuosismo imediato, dois séculos depois.   [provocadora]
✨ Link enviado. O coração antes da cabeça, sempre.             [poética]

═══════════════════════════════════════════════

RUIM — falha de diversidade:

🎵 Aqui está o link!
🎶 Te enviei o vídeo!
📻 Confere no direct!

Por que falha: emojis genéricos, frases intercambiáveis, sem referência ao vídeo, troca de 1 palavra entre elas.
</examples>

<format>
Responda em JSON válido:

```json
{{
  "respostas_curtas": [
    "[emoji] frase 1",
    "[emoji] frase 2",
    "[emoji] frase 3"
  ],
  "estrategia_diversidade_aplicada": "A|B|C",
  "dm_fixa": "texto completo da DM com [link] como placeholder",
  "comentario_keyword": {{
    "texto_completo": "Comente \\"KEYWORD\\" e receba...",
    "keyword": "KEYWORD"
  }}
}}
```
</format>

<self_check>
1. As 3 respostas são genuinamente diferentes (não trocar 1-2 palavras)?
2. Cada resposta referencia algo do vídeo (não genérica)?
3. Estratégia A, B ou C explicitamente declarada?
4. DM fixa segue o template exato?
5. Gênero descritivo correto para a categoria ({genero_descritivo})?
6. Keyword simples, sem acentos, CAIXA ALTA?
7. Comentário específico ao vídeo?
8. Tom contido em tudo? Sem vendedor?
</self_check>
"""
    return prompt
