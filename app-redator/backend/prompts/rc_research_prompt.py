"""
RC Research Prompt — Pesquisa Profunda para Reels Classics
==========================================================
Prompt interno (operador NÃO vê o output).
Alimenta: hooks, overlay, descrição, automação.

Método: Kephart (Role → Context → Task → Constraints → Format → Self-check)
"""


def _calcular_duracao(cut_start: str, cut_end: str) -> int:
    """Converte MM:SS para segundos e retorna duração."""
    def to_sec(t: str) -> int:
        parts = t.strip().split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return 0
    return max(0, to_sec(cut_end) - to_sec(cut_start))


def _estimar_legendas(duracao_seg: int) -> int:
    """Estima quantidade de legendas pelo tempo (média ~5.5s por legenda)."""
    if duracao_seg <= 0:
        return 8
    return max(5, round(duracao_seg / 5.5))


def build_rc_research_prompt(metadata: dict) -> str:
    """
    Constrói o prompt de pesquisa profunda para RC.

    metadata esperado:
    {
        "artist": str,           # Intérprete(s)
        "work": str,             # Nome da obra
        "composer": str,         # Compositor
        "composition_year": str, # Ano (pode ser "")
        "nationality": str,     # Nacionalidade do compositor
        "instrument_formation": str,  # Piano solo, quarteto, orquestra...
        "orchestra": str,       # Orquestra/Ensemble (pode ser "")
        "conductor": str,       # Regente (pode ser "")
        "category": str,        # Orchestral, Chamber, Piano Solo...
        "album_opera": str,     # Se a obra é parte de algo maior
        "cut_start": str,       # MM:SS
        "cut_end": str,         # MM:SS
    }
    """

    artist = metadata.get("artist", "").strip()
    work = metadata.get("work", "").strip()
    composer = metadata.get("composer", "").strip()
    year = metadata.get("composition_year", "").strip()
    nationality = metadata.get("nationality", "").strip()
    instrument = metadata.get("instrument_formation", "").strip()
    orchestra = metadata.get("orchestra", "").strip()
    conductor = metadata.get("conductor", "").strip()
    category = metadata.get("category", "").strip()
    album_opera = metadata.get("album_opera", "").strip()
    cut_start = metadata.get("cut_start", "00:00").strip()
    cut_end = metadata.get("cut_end", "01:00").strip()

    duracao = _calcular_duracao(cut_start, cut_end)
    n_legendas = _estimar_legendas(duracao)

    # Monta bloco de dados do vídeo
    dados_video = f"""Compositor: {composer}"""
    if nationality:
        dados_video += f"\nNacionalidade: {nationality}"
    dados_video += f"\nObra: {work}"
    if album_opera:
        dados_video += f"\nParte de: {album_opera}"
    if year:
        dados_video += f"\nAno de composição: {year}"
    dados_video += f"\nIntérprete(s): {artist}"
    dados_video += f"\nInstrumento/Formação: {instrument}"
    if orchestra:
        dados_video += f"\nOrquestra/Ensemble: {orchestra}"
    if conductor:
        dados_video += f"\nRegente: {conductor}"
    dados_video += f"\nCategoria: {category}"
    dados_video += f"\nDuração do trecho: {duracao}s (~{n_legendas} legendas)"

    prompt = f"""<role>
Você é um pesquisador-historiador de música erudita com especialização em transformar conhecimento enciclopédico em HISTÓRIAS.

Você NÃO é um enciclopedista que lista fatos. Você é um CONTADOR DE HISTÓRIAS que encontra os fatos que fazem pessoas pararem o que estão fazendo para ouvir.

Sua habilidade central: olhar para uma peça musical e encontrar a CADEIA DE EVENTOS por trás dela. Não "o que é", mas "o que ACONTECEU". Não o estado das coisas, mas as ações que mudaram as coisas.

Você sabe que um fato como "Beethoven ficou surdo" é um estado. Mas "Beethoven quebrava martelos do piano tentando ouvir as notas à medida que a surdez avançava" é um EVENTO — algo que ele FAZIA, com consequência visível. Seu trabalho é encontrar os eventos.
</role>

<context>
Esta pesquisa alimentará a produção de conteúdo do canal REELS CLASSICS — vídeos curtos de música clássica para redes sociais. O público é leigo: nunca ouviu uma sinfonia, não conhece compositores, não sabe ler partitura.

O conteúdo que esta pesquisa vai gerar precisa FAZER SENTIR antes de fazer pensar. Precisa de fatos que criam arrepio, curiosidade ou vontade de assistir até o fim.

O vídeo em questão:
{dados_video}
</context>

<task>
Execute a pesquisa em 7 etapas, na ordem indicada. Para cada etapa, use APENAS seu conhecimento factual. Se não souber algo com certeza, marque como [INCERTO]. NUNCA invente fatos.

ETAPA 1 — O COMPOSITOR NA ÉPOCA DA COMPOSIÇÃO

Não escreva uma biografia geral. Responda APENAS estas perguntas sobre o momento em que esta peça foi composta:

- Quantos anos tinha o compositor?
- O que estava vivendo pessoalmente? (saúde, finanças, relacionamentos, exílio, reconhecimento, crise)
- Onde estava geograficamente?
- O que mais estava compondo na mesma época?
- Algo importante tinha acabado de acontecer na vida dele?

IMPORTANTE: Cada resposta deve conter um VERBO DE AÇÃO. Não "estava doente" (estado). Sim "lutava contra uma doença que o impedia de..." (ação com consequência).

ETAPA 2 — POR QUE ESTA PEÇA EXISTE

Não descreva a peça. Conte COMO ela nasceu:

- Quem encomendou, ou o que motivou a composição?
- Houve dedicatória? A quem? Qual era a relação?
- O compositor gostava dela? Tinha orgulho ou vergonha?
- Quanto tempo levou para compor? Houve interrupções?
- Houve mudanças radicais durante a composição? (versões, revisões, abandonos)
- Existe alguma instrução original do compositor que hoje é ignorada ou impossível de seguir?

ETAPA 3 — O QUE ACONTECEU QUANDO O MUNDO OUVIU

- Quando e onde foi a estreia?
- Qual foi a reação da plateia? (sucesso, escândalo, indiferença, tumulto)
- Houve críticas famosas (positivas ou negativas)?
- A peça ficou esquecida e foi redescoberta? Por quem, quando?
- Existe alguma performance histórica marcante? (evento, tragédia, celebração)

ETAPA 4 — QUEM TOCA NESTE VÍDEO

Sobre {artist} especificamente:

- De onde vem? Qual sua trajetória em 2-3 frases?
- O que o/a torna diferente de outros intérpretes do mesmo instrumento?
- Existe alguma história pessoal marcante? (superação, polêmica, ativismo, recorde)
- Qual é a relação dele/a com ESTA peça específica? (gravou várias vezes? tocou em momento importante? é a obra pela qual é mais conhecido/a?)
- O que nesta performance específica é observável e diferente? (andamento, dinâmica, escolha técnica)

ETAPA 5 — FATOS SURPREENDENTES

Liste de 8 a 12 fatos que fariam um LEIGO dizer "não sabia disso!" ou "como assim?!".

Para CADA fato, classifique:
- TIPO: [evento] se algo ACONTECEU, [estado] se algo É VERDADE, [conexão] se liga a algo fora da música clássica
- VERIFICÁVEL: [confirmado] ou [incerto]
- POTENCIAL_EMOCIONAL: [alto], [médio] ou [baixo] — um leigo se importaria?

REGRAS DOS FATOS:
- Mínimo 3 sobre o compositor
- Mínimo 3 sobre a peça
- Mínimo 2 sobre o intérprete ou a performance
- Fatos do tipo [evento] são SEMPRE preferíveis a [estado]
- Fatos com potencial_emocional [baixo] devem ser cortados se você já tem 8+ fatos [alto] ou [médio]
- Se um fato funciona para QUALQUER obra/compositor, ele é genérico e não entra

ETAPA 6 — CONEXÕES COM O MUNDO FORA DA MÚSICA CLÁSSICA

- Esta peça aparece em algum filme, série, jogo, propaganda, meme ou evento famoso?
- Existe alguma versão/cover/remix famoso fora do mundo erudito?
- Esta peça é usada em contextos não-musicais? (cerimônias, esportes, política, toques de celular)
- Existe algum recorde mensurável? (mais tocada, mais gravada, mais longa, mais curta, mais difícil)
- Algo conecta esta peça ao presente? (aniversário, redescoberta recente, viralização)

Para cada conexão, inclua dados verificáveis (ano, nome do filme, número concreto). Sem conexão = campo vazio. NÃO INVENTE.

ETAPA 7 — CADEIAS DE EVENTOS NARRATIVOS

Esta é a etapa mais importante. A partir de TUDO que você pesquisou, construa no mínimo 2 cadeias de eventos diferentes.

REGRAS DA CADEIA:
- Cada evento usa VERBO DE AÇÃO: compôs, fugiu, encomendou, insistiu, proibiu, escandalizou, escolheu, morreu, perdeu, ganhou, recusou, dedicou, destruiu.
- NÃO USE verbos de estado: era, tinha, existia, ficou, parecia.
- Cada evento DEPENDE do anterior. Se trocar a ordem, a história QUEBRA.
- Mínimo 6 eventos por cadeia.
- Se dois eventos dizem a mesma coisa com verbos diferentes, FUNDIR em 1.
- A cadeia forma uma HISTÓRIA com começo, meio e fim — NÃO uma lista de fatos sobre o mesmo assunto.

Formato de cada cadeia:
CADEIA [N] — [NOME DESCRITIVO]
E1: [verbo] → E2: [verbo] → E3: [verbo] → E4: [verbo] → E5: [verbo] → E6: [verbo] → ...
[Escreva cada evento como frase completa em seguida]

EXEMPLO DE CADEIA BOA:
CADEIA 1 — A missa que Mozart escreveu para si mesmo
E1: recebe encomenda → E2: não sabe de quem → E3: adoece → E4: se convence que é para ele → E5: chega à Lacrimosa → E6: morre antes de terminar → E7: aluno completa às escondidas
E1: Um estranho bate à porta de Mozart e encomenda um Réquiem.
E2: Não revela quem é, nem para quem é a missa.
E3: Mozart adoece enquanto escreve três obras ao mesmo tempo.
E4: Convence-se de que a missa fúnebre não é para outro — é para ele próprio.
E5: Chega à Lacrimosa, o trecho mais doloroso da missa.
E6: Morre antes de terminar. A Lacrimosa parou no compasso 8.
E7: Seu aluno Süssmayr completa o Réquiem às escondidas para a família receber o pagamento.

EXEMPLO DE CADEIA RUIM:
E1: Mozart era um gênio. (ESTADO — não é evento)
E2: O Réquiem é uma das obras mais famosas. (ESTADO)
E3: Foi composta em 1791. (DADO — não é história)
E4: A Lacrimosa é especialmente bonita. (OPINIÃO)
Diagnóstico: 4 itens, zero eventos, zero causalidade. Isso é uma LISTA DE FATOS, não uma cadeia.
</task>

<constraints>
PROIBIDO:
- Inventar fatos. Se não sabe, marque [INCERTO] ou omita.
- Incluir fatos genéricos que funcionam para qualquer compositor/peça (ex: "foi um dos maiores compositores da história").
- Usar adjetivos como informação (ex: "uma obra magistral" não é pesquisa — "a obra que levou 6 anos para ser terminada" é).
- Incluir análise harmônica/teórica que um leigo não entenderia.
- Listar fatos isolados sem conexão narrativa.
- Repetir o mesmo fato em seções diferentes com palavras diferentes.

OBRIGATÓRIO:
- Verbo de ação em toda frase das Etapas 1-4.
- Mínimo 8 fatos surpreendentes na Etapa 5.
- Mínimo 2 cadeias de 6+ eventos na Etapa 7.
- Marcar [INCERTO] em qualquer informação da qual não tenha certeza absoluta.
- Cada cadeia de eventos deve gerar uma HISTÓRIA que um leigo seguiria com interesse.
</constraints>

<format>
Responda em JSON válido, seguindo EXATAMENTE esta estrutura:

```json
{{
  "compositor_na_epoca": {{
    "idade_na_composicao": "",
    "situacao_pessoal": "",
    "local": "",
    "outras_obras_periodo": "",
    "evento_recente_marcante": ""
  }},
  "por_que_a_peca_existe": {{
    "motivacao": "",
    "dedicatoria": "",
    "opiniao_do_compositor": "",
    "tempo_de_composicao": "",
    "instrucao_original_ignorada": ""
  }},
  "recepcao_e_historia": {{
    "estreia": "",
    "reacao_publica": "",
    "criticas_famosas": "",
    "redescoberta": "",
    "performance_historica_marcante": ""
  }},
  "interprete": {{
    "origem_trajetoria": "",
    "diferencial": "",
    "historia_pessoal": "",
    "relacao_com_esta_peca": "",
    "observavel_nesta_performance": ""
  }},
  "fatos_surpreendentes": [
    {{
      "fato": "",
      "tipo": "evento|estado|conexao",
      "verificavel": "confirmado|incerto",
      "potencial_emocional": "alto|medio|baixo",
      "sobre": "compositor|peca|interprete|performance"
    }}
  ],
  "conexoes_culturais": [
    {{
      "conexao": "",
      "dados_verificaveis": "",
      "tipo": "filme|serie|jogo|propaganda|meme|cerimonia|recorde|viralizacao|outro"
    }}
  ],
  "cadeias_de_eventos": [
    {{
      "nome": "",
      "resumo_cadeia": "E1: verbo → E2: verbo → E3: verbo → ...",
      "eventos": [
        {{
          "id": "E1",
          "evento": ""
        }}
      ]
    }}
  ],
  "angulos_narrativos": [
    {{
      "nome": "",
      "tipo": "emocional|cultural|estrutural|especifico",
      "fio_narrativo": "",
      "fato_central": "",
      "potencial_hook": ""
    }}
  ],
  "alertas": []
}}
```

No campo "alertas", inclua qualquer observação importante:
- Fatos que precisam de confirmação
- Dados que você não encontrou
- Possíveis conflitos entre fontes
- Se o intérprete é pouco conhecido e há escassez de informação
</format>

<self_check>
Antes de entregar, verifique internamente:

1. CADEIAS: Cada cadeia tem 6+ eventos com verbos de ação? Se trocar a ordem dos eventos, a história quebra?
2. FATOS: Tenho mínimo 8 fatos surpreendentes? Quantos são [evento] vs [estado]? Se mais de 30% são [estado], converter os mais fracos em eventos ou substituir.
3. ESPECIFICIDADE: Trocar o nome do compositor/peça torna algum fato falso? Se não, o fato é genérico — cortar.
4. LEIGO: Um leigo que nunca ouviu música clássica acharia estes fatos interessantes? Se só um especialista se importaria, substituir.
5. COMPLETUDE: Tenho material suficiente para escrever ~{n_legendas} legendas + 3 parágrafos de descrição SEM repetir? Se não, buscar mais fatos.
6. INTÉRPRETE: Tenho informação específica sobre {artist} ou genérica sobre "bons intérpretes"? Se genérica, aprofundar ou marcar lacuna em alertas.
7. ANCORAGEM: Pelo menos 2-3 fatos/eventos se conectam ao que o espectador VAI OUVIR no vídeo? (instrumentos audíveis, momentos musicais, dinâmicas)
</self_check>"""

    return prompt
