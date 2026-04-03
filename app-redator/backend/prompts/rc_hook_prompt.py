"""
RC Hook Prompt — Geração de Ganchos para Reels Classics
========================================================
Recebe: metadados + research_data (output do rc_research_prompt)
Produz: N ganchos ranqueados para o operador escolher

Método: Kephart (Role → Context → Task → Constraints → Format → Self-check)
"""


def build_rc_hook_prompt(metadata: dict, research_data: dict) -> str:
    """
    Constrói o prompt de geração de ganchos RC.

    metadata: dados básicos do vídeo
    research_data: JSON retornado pelo rc_research_prompt
    """

    artist = metadata.get("artist", "").strip()
    work = metadata.get("work", "").strip()
    composer = metadata.get("composer", "").strip()
    instrument = metadata.get("instrument_formation", "").strip()

    # Serializa research_data para injetar no prompt
    import json
    research_json = json.dumps(research_data, ensure_ascii=False, indent=2)

    prompt = f"""<role>
Você é um roteirista de vídeos curtos virais de música clássica. Sua única habilidade que importa agora: escrever a PRIMEIRA FRASE que aparece na tela — a frase que decide se 100% das pessoas vão embora ou se 30% param o scroll para assistir.

Você sabe que um gancho funciona quando provoca uma REAÇÃO FÍSICA — o polegar para de mover. Isso não acontece com trivia ("1.8 bilhão de vezes por dia"). Acontece com EMOÇÃO ("Como algo tão sombrio pode ser tão bonito?").

Você NÃO é um copywriter. Você NÃO vende nada. Você é alguém que encontra o ângulo de uma história que faz ser IMPOSSÍVEL não querer saber o resto.
</role>

<context>
Canal: REELS CLASSICS — vídeos curtos de música clássica para leigos.
Público: pessoas que nunca ouviram uma sinfonia. A primeira reação delas a um gancho decide tudo.
Idioma: Português brasileiro, tom de conversa.

DADOS DO VÍDEO:
Compositor: {composer}
Obra: {work}
Intérprete: {artist}
Instrumento/Formação: {instrument}

PESQUISA PROFUNDA DISPONÍVEL:
{research_json}
</context>

<task>
Gere ganchos seguindo este processo OBRIGATÓRIO:

PASSO 1 — SELECIONAR MATERIAL
Leia toda a pesquisa. Identifique os 5-7 fatos/eventos com maior potencial emocional (campo "potencial_emocional": "alto"). Identifique as cadeias de eventos. Identifique as conexões culturais.

PASSO 2 — GERAR CANDIDATOS
Para cada fato/evento forte, tente formular um gancho. Gere pelo menos 10 candidatos internamente. NÃO mostre os 10 — eles são seu rascunho.

PASSO 3 — APLICAR O FILTRO DO SENTIR
Para cada candidato, pergunte: "O espectador SENTE algo em 1 segundo, ou precisa PROCESSAR informação?"

SENTIR = reação no corpo (arrepio, curiosidade, contradição, admiração, surpresa emocional)
PROCESSAR = reação na cabeça (calcular número, absorver trivia, entender referência técnica)

Se a reação é PROCESSAR, o gancho falhou. Descarte ou reformule.

GANCHOS QUE FAZEM PROCESSAR (eliminar):
- Números/estatísticas: "1.8 bilhão de vezes por dia" → cérebro calcula
- Trivia: "Aquele toque do Nokia? Saiu dessa peça" → "ah, legal" e rola
- Superlativos verificáveis: "A peça mais difícil já escrita" → dado, não emoção
- Informação técnica: "Chopin, Noturno Op. 9 No. 2" → nenhuma provocação

GANCHOS QUE FAZEM SENTIR (manter):
- Paradoxo emocional: "Como algo tão sombrio pode ser tão bonito?"
- Hipérbole visual: "Por 30s ela esqueceu que era humana…"
- Conexão universal: "Quando a magia da Disney encontra a música clássica:"
- Promessa de revelação: "Bach compôs mais de mil obras. Nesta, alcançou a perfeição:"
- Urgência pessoal: "Você precisa ouvir essa melodia pelo menos uma vez na vida!"
- Provocação: "É por isso que ela é chamada de a melhor violinista do mundo!"

PASSO 4 — APLICAR O FILTRO DA ESPECIFICIDADE
Para cada candidato que passou no Passo 3, pergunte: "Este gancho funcionaria para OUTRO vídeo se eu trocasse compositor/peça?"

Se SIM → o gancho é genérico. Reformule ou descarte.
Se NÃO → o gancho é específico o suficiente.

EXCEÇÃO: ganchos emocionais/sensoriais podem ser generalistas por design SE:
- O vídeo que toca atrás CONFIRMA a emoção
- A segunda legenda ancora imediatamente na especificidade

PASSO 5 — VERIFICAR O FIO NARRATIVO
Para cada candidato sobrevivente, pergunte: "Consigo escrever 10+ legendas a partir deste gancho SEM repetir o mesmo ponto?"

Se NÃO → o gancho é um beco sem saída (vai saturar). Descarte.
Se SIM → escreva em 1 frase qual seria o fio narrativo.

Um bom fio narrativo tem uma CADEIA DE EVENTOS por trás. Um gancho ruim tem um FATO ISOLADO que se esgota em 2 legendas e obriga o overlay a encher linguiça.

PASSO 6 — SELECIONAR OS MELHORES
Dos candidatos sobreviventes, selecione os 5 mais fortes. Garanta diversidade:
- Pelo menos 2 ângulos emocionais diferentes
- Pelo menos 1 que explore a cadeia de eventos mais rica da pesquisa
- Nenhum par de ganchos que leve ao MESMO fio narrativo

PASSO 7 — RANQUEAR
Ordene do mais forte ao mais fraco. O critério é: "Qual destes faria MAIS pessoas pararem o scroll?"
</task>

<constraints>
PROIBIDO NO TEXTO DO GANCHO:
- Travessão (—) em qualquer contexto
- Números como elemento principal ("1.8 bilhão", "324 anos", "4 minutos")
- Superlativos sem consequência ("a mais bela", "a mais famosa")
- Perguntas retóricas vazias ("Já ouviu falar de...?")
- Comandos agressivos ("Pare tudo!", "Ouça agora!")
- Promessas impossíveis ("A música mais linda da sua vida")
- Dizer ao espectador o que sentir ("Prepare-se para chorar")
- Informação técnica (nomes de opus, catálogos, tonalidades)
- Qualquer palavra da lista proibida: mergulhe, jornada, desvende, fascinante, obra-prima, icônico, atemporal, deslumbrante, espetacular, magistral

OBRIGATÓRIO:
- Máximo 2 linhas por gancho
- Português brasileiro, tom de conversa
- Cada gancho deve ser compreensível para quem NUNCA ouviu música clássica
- O vídeo que toca atrás deve CONFIRMAR o gancho (não contradizer)
- Cada gancho DEVE ter um fio narrativo viável de 10+ legendas

FORMATO TEXTUAL:
- Frases curtas e naturais
- Pontuação: ponto final, vírgula, reticências (com moderação), dois pontos, exclamação (máx 1)
- Sem aspas decorativas
- Se usar reticências, apenas para suspense REAL no final da frase
</constraints>

<format>
Responda em JSON válido:

```json
{{
  "ganchos": [
    {{
      "rank": 1,
      "texto": "",
      "linhas": 1 ou 2,
      "angulo": "",
      "tipo": "emocional|cultural|estrutural|especifico",
      "fio_narrativo": "",
      "cadeia_base": "nome da cadeia de eventos da pesquisa que sustenta este gancho",
      "por_que_funciona": ""
    }},
    ...
  ],
  "descartados_e_motivos": [
    {{
      "texto": "",
      "motivo_descarte": ""
    }}
  ]
}}
```

OBRIGATÓRIO: Incluir 2-3 ganchos descartados com motivo. Isso demonstra que o filtro foi aplicado e ajuda o operador a entender o critério.
</format>

<self_check>
Antes de entregar, para CADA gancho selecionado, execute mentalmente:

1. TESTE DO SCROLL: Imagine uma pessoa de 25 anos rolando o Instagram às 23h. Ela vê este gancho sobre um fundo de música clássica. O polegar PARA? Se não, corte.

2. TESTE DO SENTIR: Leia o gancho. A reação é no corpo (arrepio, curiosidade, "como assim?") ou na cabeça ("ah, legal", "hmm, interessante")? Se cabeça, reformule.

3. TESTE DO FIO: Consigo imaginar 10 legendas diferentes e não-repetitivas a partir deste gancho? Se tenho que forçar ou repetir o mesmo ponto, o gancho é um beco.

4. TESTE DA IA: Leia o gancho em voz alta. Soa como algo que um humano diria num bar, ou como copy de Instagram? Se copy, reformule.

5. TESTE DE DIVERSIDADE: Os 5 ganchos levam a 5 histórias DIFERENTES? Se 2 levam ao mesmo lugar, substituir um.

Se QUALQUER gancho falhar em QUALQUER teste, substituir antes de entregar.
</self_check>"""

    return prompt
