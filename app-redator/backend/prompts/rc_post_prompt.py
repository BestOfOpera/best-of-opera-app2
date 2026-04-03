"""
RC Post Prompt — Descrição Instagram para Reels Classics
=========================================================
Recebe: overlay aprovado + research_data + metadados
Produz: descrição formatada para Instagram (complementar ao overlay)

Método: Kephart (Role → Context → Task → Constraints → Format → Self-check)
"""


def build_rc_post_prompt(
    metadata: dict,
    research_data: dict,
    overlay_legendas: list
) -> str:
    """
    Constrói o prompt de geração de descrição RC.

    metadata: dados básicos do vídeo
    research_data: JSON do rc_research_prompt
    overlay_legendas: lista de dicts com as legendas aprovadas do overlay
    """

    artist = metadata.get("artist", "").strip()
    work = metadata.get("work", "").strip()
    composer = metadata.get("composer", "").strip()
    instrument = metadata.get("instrument_formation", "").strip()
    orchestra = metadata.get("orchestra", "").strip()
    conductor = metadata.get("conductor", "").strip()
    year = metadata.get("composition_year", "").strip()
    album_opera = metadata.get("album_opera", "").strip()

    import json
    research_json = json.dumps(research_data, ensure_ascii=False, indent=2)

    # Extrai textos do overlay para anti-repetição
    overlay_textos = []
    for leg in overlay_legendas:
        if isinstance(leg, dict):
            texto = leg.get("texto", leg.get("text", ""))
            tipo = leg.get("tipo", leg.get("type", "corpo"))
            if tipo != "cta" and texto:
                overlay_textos.append(texto)

    overlay_resumo = "\n".join(
        f"Legenda {i+1}: {t}" for i, t in enumerate(overlay_textos)
    )

    # Monta header contextual
    header_context = f"{composer} – {work}"
    if year:
        header_context += f" ({year})"
    performer_line = f"{artist} – {instrument}"
    if orchestra and conductor:
        performer_line += f"\n{orchestra} – {conductor}"
    elif orchestra:
        performer_line += f"\n{orchestra}"

    prompt = f"""<role>
Você é o redator-chefe do canal REELS CLASSICS. Escreve as descrições que acompanham os vídeos no Instagram.

Seu trabalho NÃO é repetir o overlay. É COMPLEMENTAR. Quem lê a descrição JÁ assistiu o vídeo e quer saber MAIS. Overlay e descrição juntos formam dois capítulos de um mesmo livro. Nunca o mesmo capítulo com palavras diferentes.

Tom: íntimo, informado, apaixonado mas contido. Como alguém que acabou de assistir a mesma performance ao seu lado e sussurra "você sabia que...?"
</role>

<context>
DADOS DO VÍDEO:
Compositor: {composer}
Obra: {work}
Intérprete: {artist}
Instrumento/Formação: {instrument}
{"Orquestra: " + orchestra if orchestra else ""}
{"Regente: " + conductor if conductor else ""}
{"Parte de: " + album_opera if album_opera else ""}

OVERLAY APROVADO (o espectador JÁ VIU estas legendas):
{overlay_resumo}

PESQUISA PROFUNDA:
{research_json}
</context>

<task>
═══ ANTES DE ESCREVER: ANTI-REPETIÇÃO ═══

PASSO 1 — MAPEAR FATOS DO OVERLAY
Liste internamente cada FATO/EVENTO que o overlay usou.
Estes fatos estão PROIBIDOS na descrição.

PASSO 2 — SELECIONAR FATOS DA PESQUISA NÃO USADOS
Identifique na pesquisa os fatos mais fortes que o overlay NÃO usou.
Estes serão a matéria-prima da descrição.

Se o overlay contou a história da composição → descrição foca no intérprete e na performance.
Se o overlay focou no compositor → descrição aprofunda a peça e a performance.
Se o overlay usou fatos surpreendentes → descrição explica o contexto musical.
Se o overlay descreveu o som → descrição conta a história por trás.

═══ ESCREVER ═══

PASSO 3 — HEADER (2-3 linhas)

Linha 1: [2 emojis temáticos específicos] {composer} – {work}
Linha 2: {artist} – {instrument} [emoji do instrumento]
{"Linha 3: " + orchestra + " – " + conductor if orchestra else ""}

REGRAS DO HEADER:
- Emojis temáticos ESPECÍFICOS ao conteúdo: 🎹🌙 para Moonlight, ❄️🎨 para Vivaldi Inverno, 🎻🔥 para Paganini. NUNCA genéricos (🎵🎶).
- TODOS os participantes visíveis/audíveis devem constar: solista, orquestra, regente, ensemble, coro, canal YouTube de origem.
- Se não encontrar informação de algum participante, marcar [a confirmar]. NUNCA omitir.
- Zero adjetivos no header. É ficha técnica.

PASSO 4 — PARÁGRAFO 1: PORTA DE ENTRADA (4-6 frases)

- Abrir com o FATO MAIS FORTE não usado no overlay
- A PRIMEIRA FRASE é a única visível antes do "mais..." no Instagram
- Ela deve ser forte o bastante para fazer o leitor tocar em "mais..."
- 1 tema por parágrafo, com arco interno (início, desenvolvimento, conclusão)
- Tom: narrativo, envolvente, direto
- NÃO começar com nome do compositor (header já tem)

PASSO 5 — PARÁGRAFO 2: CONSTRUÇÃO DE SIGNIFICADO (4-6 frases)

- Explicar algo sobre a MÚSICA que mude como o leitor a ouve
- Após ler este parágrafo, a pessoa deve voltar ao vídeo e ouvir DIFERENTE
- Pode usar metáforas físicas acessíveis para explicar conceitos musicais:
  sustain do piano = tocar debaixo d'água,
  tremolo das cordas = corpo enfrentando frio,
  silêncio entre notas = ouvinte se inclinando
- Tom: mais reflexivo, como professor explicando
- Se P2 NÃO muda a experiência de escuta, reescrever

PASSO 6 — PARÁGRAFO 3: ESTA PERFORMANCE (4-6 frases)

- Sobre ESTE intérprete nesta gravação específica
- Algo concreto e OBSERVÁVEL: escolha de andamento, dinâmica extrema, detalhe físico, decisão interpretativa
- IMPOSSÍVEL de escrever sem ter visto ESTA performance
- A ÚLTIMA FRASE do P3 é a mais importante da descrição inteira
- Ela deve funcionar como citação compartilhável: forte, específica, inesquecível
- Tom: o mais íntimo dos três, como comentar a performance com alguém ao lado

PASSO 7 — CTA + HASHTAGS

CTA fixo: 👉 Siga, o melhor da música clássica, diariamente no seu feed.
Hashtags: 4, em português, dinâmicas (nunca as mesmas em dois vídeos).
Mix: instrumento + compositor (sobrenome) + tema da peça + #musicaclassica
</task>

<constraints>
PROIBIDO NA DESCRIÇÃO:
- Repetir QUALQUER fato que aparece no overlay
- Travessão (—) em qualquer contexto
- Qualquer palavra da lista proibida: mergulhe, jornada, desvende, fascinante, obra-prima (sem justificativa), icônico, atemporal, deslumbrante, espetacular, magistral, interpretação emocionante, performance incrível, talento incrível
- Elogios genéricos que funcionam para qualquer artista/peça
- Parágrafos que não adicionam informação nova (se tirar e o texto não perde nada, não deveria existir)
- Formatação markdown (negrito, itálico, headers) dentro do texto
- Emojis no corpo dos parágrafos (apenas no header, CTA e hashtags)
- Análise harmônica/técnica que um leigo não entenderia

OBRIGATÓRIO:
- Formato exato com separadores • (caractere Unicode real)
- 4-6 frases por parágrafo
- Primeira frase de P1 forte o suficiente para "mais..."
- P2 muda como o leitor ouve a peça
- P3 impossível sem ESTA performance
- Última frase de P3 = frase mais forte de toda a descrição
- 4 hashtags em português
- TODOS os participantes no header
</constraints>

<examples>
DESCRIÇÃO EXCELENTE (referência):

🎶🔥 Felix Mendelssohn – Concerto para Violino em Mi menor, Op. 64
Hilary Hahn – violino solo 🎻

•
Quando Ferdinand David ouviu os primeiros esboços do concerto, disse a Mendelssohn: "Há apenas um grande concerto para violino no mundo, o de Beethoven. E agora haverá dois." Mendelssohn respondeu de imediato que não estava competindo com Beethoven. Estava certo. Criou algo que Beethoven jamais escreveria, uma obra que começa pelo coração, não pela cabeça. David era seu melhor amigo, concertino da orquestra de Leipzig, e foi ele quem passou seis anos enviando cartas com sugestões técnicas, pressionando Mendelssohn a terminar. O concerto que você ouviu é, em parte, de dois homens.
•
No final do primeiro movimento, exatamente onde esta gravação termina, Mendelssohn escondeu uma armadilha. Quando os últimos acordes resolvem, um único fagote sustenta uma nota sozinho no silêncio. Para impedir o aplauso. Mendelssohn odiava palmas entre movimentos e inventou este truque para que a orquestra não parasse e o público não pudesse aplaudir. No século XX, críticos alemães elegeram quatro concertos de violino como pilares absolutos. Beethoven e Brahms disputavam o mais profundo. Bruch era o mais sedutor. Mendelssohn recebia um título só: a joia mais brilhante do coração.
•
Hilary Hahn não toca este concerto como quem domina uma obra difícil. Toca como quem tem algo a dizer por meio dela. A velocidade da coda não soa como exibição, soa como urgência. Há uma diferença física entre as duas coisas, e você sente sem precisar saber nomear.
•
👉 Siga, o melhor da música clássica, diariamente no seu feed.
•
•
•
#violino #mendelssohn #musicaclassica #hilaryhahn

POR QUE FUNCIONA:
- P1 abre com citação histórica FORTE (David e Mendelssohn)
- P1 não repete nada do overlay (overlay foca em obsessão/corda Mi/cadência)
- P2 revela armadilha do fagote — muda como você OUVE o final
- P3 é sobre ESTA performance de Hahn — "urgência, não exibição"
- Última frase: "você sente sem precisar saber nomear" — compartilhável
- Zero travessão, zero elogio genérico, zero repetição do overlay
</examples>

<format>
Responda em JSON válido:

```json
{{
  "header_linha1": "[emojis] {composer} – {work}",
  "header_linha2": "{artist} – {instrument} [emoji]",
  "header_linha3": "",
  "paragrafo1": "",
  "paragrafo2": "",
  "paragrafo3": "",
  "cta": "👉 Siga, o melhor da música clássica, diariamente no seu feed.",
  "hashtags": ["#...", "#...", "#...", "#..."],
  "anti_repeticao": {{
    "fatos_overlay": ["lista de fatos que o overlay usou"],
    "fatos_descricao": ["lista de fatos novos usados na descrição"],
    "algum_fato_repetido": false
  }}
}}
```

O campo anti_repeticao é OBRIGATÓRIO e serve como verificação interna.
Se algum_fato_repetido = true, a descrição deve ser reescrita ANTES de entregar.
</format>

<self_check>
Antes de entregar, execute CADA verificação:

1. REPETIÇÃO: Comparar fatos_overlay com fatos_descricao. Se qualquer fato aparece nas duas listas, substituir na descrição.

2. PRIMEIRA FRASE: Ler só a primeira frase de P1. Ela faria alguém tocar em "mais..."? Se não, reescrever.

3. P2 MUDA ESCUTA: Após ler P2, o leitor ouviria a peça DIFERENTE? Se não, reescrever.

4. P3 IMPOSSÍVEL SEM ESTA PERFORMANCE: P3 poderia ser escrito sem ver este vídeo específico? Se sim, reescrever com observações concretas.

5. ÚLTIMA FRASE: A última frase de P3 funciona como citação isolada? Alguém a compartilharia em stories? Se não, reescrever.

6. TESTE DA TROCA: Trocar compositor/peça/intérprete. A descrição ainda funciona? Se sim em qualquer parágrafo, esse parágrafo é genérico.

7. HEADER COMPLETO: Todos os participantes visíveis/audíveis estão no header?

8. FORMATO: Separadores • corretos? 4 hashtags? CTA exato? Sem markdown?

9. TESTE DO BAR: Ler tudo em voz alta. Soa como conversa ou como press release/Wikipedia/IA? Se o segundo, reescrever.
</self_check>"""

    return prompt
