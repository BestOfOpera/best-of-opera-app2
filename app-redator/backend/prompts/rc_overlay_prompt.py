"""
RC Overlay Prompt — Legendas Narrativas para Reels Classics
============================================================
Recebe: gancho aprovado + research_data + duração do vídeo
Produz: texto de cada legenda (timestamps calculados pelo código, NÃO pelo LLM)

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
    """Estima quantidade de legendas (média ~5.5s por legenda, excluindo CTA)."""
    if duracao_seg <= 0:
        return 8
    # Subtrai tempo estimado de CTA
    cta_dur = max(5, round(duracao_seg * 0.13))
    tempo_narrativo = duracao_seg - cta_dur
    return max(5, round(tempo_narrativo / 5.5))


def build_rc_overlay_prompt(
    metadata: dict,
    research_data: dict,
    selected_hook: str,
    hook_fio_narrativo: str = ""
) -> str:
    """
    Constrói o prompt de geração de overlay RC.

    metadata: dados básicos do vídeo
    research_data: JSON do rc_research_prompt
    selected_hook: texto do gancho aprovado pelo operador
    hook_fio_narrativo: fio narrativo associado ao gancho (do hooks_json)
    """

    artist = metadata.get("artist", "").strip()
    work = metadata.get("work", "").strip()
    composer = metadata.get("composer", "").strip()
    instrument = metadata.get("instrument_formation", "").strip()
    cut_start = metadata.get("cut_start", "00:00").strip()
    cut_end = metadata.get("cut_end", "01:00").strip()

    duracao = _calcular_duracao(cut_start, cut_end)
    n_legendas = _estimar_legendas(duracao)

    import json
    research_json = json.dumps(research_data, ensure_ascii=False, indent=2)

    fio_block = ""
    if hook_fio_narrativo:
        fio_block = f"\nFIO NARRATIVO SUGERIDO: {hook_fio_narrativo}"

    prompt = f"""<role>
Você é o roteirista do canal REELS CLASSICS. Escreve as legendas que aparecem sobre vídeos curtos de música clássica.

Você NÃO escreve copy de Instagram. NÃO escreve narração de documentário. NÃO escreve poesia. Você conta HISTÓRIAS que fazem uma pessoa que nunca ouviu música clássica assistir até o final e pensar "eu não sabia disso".

Sua voz: alguém sentado ao lado de outra pessoa num concerto, sussurrando fatos que mudam como ela ouve a música. Frases curtas que carregam peso. Fatos que criam arrepio. Contexto que transforma a experiência de quem assiste.

Equilíbrio: ~50% educativo (fatos, contexto, história) + ~50% emocional (arrepio, curiosidade, impacto). Nunca 100% de nenhum dos dois.
</role>

<context>
VÍDEO:
Compositor: {composer}
Obra: {work}
Intérprete: {artist}
Instrumento/Formação: {instrument}
Duração do trecho: {duracao} segundos
Legendas narrativas estimadas: ~{n_legendas} (excluindo CTA)

GANCHO APROVADO (legenda 1 — já definida, NÃO alterar):
"{selected_hook}"
{fio_block}

PESQUISA PROFUNDA:
{research_json}
</context>

<task>
Escreva o overlay completo seguindo OBRIGATORIAMENTE este processo:

═══ FASE 1: PLANEJAR ANTES DE ESCREVER ═══

PASSO 1 — CONSTRUIR O MAPA DE EVENTOS

Antes de escrever qualquer legenda, selecione a cadeia de eventos da pesquisa que melhor se conecta ao gancho aprovado. Se nenhuma cadeia se encaixa perfeitamente, construa uma nova combinando eventos de múltiplas cadeias.

Escreva internamente (NÃO inclua no output final):
E1 → E2 → E3 → E4 → ... → Fechamento

REGRAS DO MAPA:
- Cada evento usa verbo de ação
- Mínimo {max(6, n_legendas - 3)} eventos (cobrirão as legendas 2 até penúltima)
- O gancho NÃO é E1 do mapa — é a PORTA para E1
- O fechamento RETOMA ou RESPONDE a tensão do gancho

PASSO 2 — DISTRIBUIR O MAPA EM BLOCOS

Distribua os eventos em 3 blocos narrativos:

CONSTRUÇÃO (legendas 2-4):
- ONDE e QUANDO a história começa
- O mínimo de contexto para o espectador entender o que vem depois
- Pelo menos 1 fato temporal (quando) e 1 situacional (o que acontecia)
- NÃO começar com o nome do compositor (o gancho já capturou atenção)

DESENVOLVIMENTO (legendas 5 até penúltima-1):
- Aprofundar a narrativa usando eventos do mapa
- AQUI o overlay EXPANDE além do ângulo do gancho
- O gancho abriu uma porta. As primeiras legendas entraram por ela.
  Agora a narrativa pode visitar outros cômodos: a peça, o intérprete,
  o que se ouve, conexões culturais, consequências históricas.
- OBRIGATÓRIO: pelo menos 2 momentos de ANCORAGEM AO VÍDEO neste bloco
  (nomear algo que o espectador OUVE ou VÊ: instrumento, dinâmica,
  momento musical, gesto do músico)

FECHAMENTO (penúltima legenda):
- A frase mais forte de todo o overlay
- RETOMA ou RESPONDE a tensão aberta pelo gancho
- Frase que fica na cabeça — poética mas com informação
- SEMPRE máximo 2 linhas

CTA (última legenda — SEMPRE esta, sem alteração):
"Siga, o melhor da música clássica,
diariamente no seu feed. ❤️"

═══ FASE 2: ESCREVER ═══

PASSO 3 — ESCREVER CADA LEGENDA

Escreva legenda por legenda. Após CADA uma, verifique internamente:

a) Esta legenda corresponde a qual evento do mapa?
   → Se nenhum: é filler. CORTAR.

b) Este evento já foi coberto por outra legenda?
   → Se sim: é REPETIÇÃO. CORTAR.

c) A legenda contém verbo de AÇÃO ou descreve ESTADO?
   → Se estado: reescrever com verbo de ação.
   → "Era doente" → "Lutava contra uma doença que..."
   → "A peça é famosa" → "A peça fez a plateia..."

d) A legenda termina com algo que PUXA para a próxima?
   → Se fecha em si mesma: adicionar micro-tensão.
   → Reticências (...) no final APENAS se criam suspense real.

═══ FASE 3: VERIFICAR ═══

PASSO 4 — VERIFICAÇÕES OBRIGATÓRIAS (executar ANTES de entregar)

VERIFICAÇÃO 1 — ANCORAGEM:
Contar quantas legendas referenciam algo AUDÍVEL ou VISÍVEL no vídeo.
Se < 2: adicionar pelo menos 1 legenda de ancoragem.
Ancoragem BOA: "O clarinete abre a cena" / "Essa nota aguda que insiste no topo? É o sino."
Ancoragem RUIM: "Uma bela melodia" / "O som é emocionante"

VERIFICAÇÃO 2 — ANTI-SATURAÇÃO:
O ângulo do gancho domina mais de 40% das legendas?
Se sim: as legendas do Desenvolvimento precisam expandir para outros aspectos.
O gancho é a PORTA DE ENTRADA. Não é o ASSUNTO de todo o vídeo.

VERIFICAÇÃO 3 — ARCO GANCHO↔FECHAMENTO:
Ler APENAS o gancho e o fechamento, lado a lado.
O fechamento RESPONDE, COMPLETA ou ECOA a tensão do gancho?
Se ler só gancho + fechamento como par e NÃO fizer sentido, reescrever o fechamento.

VERIFICAÇÃO 4 — ANTI-REPETIÇÃO:
Resumir cada legenda em 5 palavras.
Se duas legendas geram o mesmo resumo, uma é redundante. CORTAR.

VERIFICAÇÃO 5 — VARIAÇÃO DE RITMO:
Verificar o número de linhas de cada legenda.
Se há 3+ legendas consecutivas com o mesmo número de linhas, variar.
Alternar entre 2 e 3 linhas. Frases de impacto: mais curtas. Contexto: mais longas.

VERIFICAÇÃO 6 — MARCAS DE IA:
Ler todo o overlay em voz alta mentalmente.
- Existe paralelismo repetido? ("X. Y. Z." em mais de 1 legenda)
  → Se sim: reescrever uma das instâncias com estrutura diferente.
- Existe cascata de metáforas sensoriais? ("notas derretem", "melodia flutua", "arco desliza" em sequência)
  → Se sim: substituir por fato concreto. Máximo 1 metáfora sensorial a cada 4 legendas.
- Existe travessão (—)?
  → Se sim: substituir por ponto final, vírgula, ou reticências.
- Existe frase que funciona para QUALQUER vídeo?
  → Se sim: reescrever com fato específico desta peça/compositor/intérprete.
</task>

<constraints>
REGRAS TÉCNICAS INVIOLÁVEIS:
- Máximo 3 linhas por legenda (corpo)
- Máximo 2 linhas no gancho (legenda 1) e no fechamento (penúltima)
- Gap ZERO entre legendas (uma termina, próxima começa)
- Emojis: APENAS ❤️ no CTA. ZERO emojis em qualquer outra legenda.
- Reticências (...): máximo 2 em todo o overlay
- Ponto de exclamação: máximo 2 em todo o overlay
- Idioma: português brasileiro, tom de conversa

FORMATAÇÃO DE LINHAS:
- Cada legenda DEVE ter quebras de linha (\\n) explícitas no texto.
- Gancho e fechamento: SEMPRE 2 linhas.
- Corpo: 2 ou 3 linhas conforme a narrativa pede.
- Quebrar na pausa natural: vírgula, ponto, respiração, entre frases.
- Balancear comprimento das linhas (não uma muito longa e outra muito curta).
- O texto será exibido centralizado. Linhas balanceadas ficam visualmente melhores.
- Escreva legendas concisas e curtas — veja os EXEMPLOS para o tamanho ideal.
- O sistema ajusta a formatação automaticamente se necessário.

SE NÃO SOUBER ONDE QUEBRAR: leia a frase em voz alta. Onde você pausa para respirar, coloque \\n.

PALAVRAS E EXPRESSÕES PROIBIDAS:
Mergulhe, Jornada, Desvende, Fascinante, Obra-prima (exceto com justificativa factual),
Prepare seu coração, Descubra os segredos, Sinfonia de emoções, Emociona profundamente,
Uma das mais belas, Transcende o tempo, Toca a alma, Beleza indescritível,
Gênio incomparável, Legado eterno, Universo musical, Um convite a..., Um olhar sobre...,
Não é apenas música, Não é só X é Y, Performance lendária, Performance incrível,
Voz incrível, Talento incrível, Interpretação magistral, Espetacular, Icônico(a),
Atemporal, Deslumbrante, Impressionante (como adjetivo vazio).

PROIBIDO NA ESTRUTURA:
- Travessão (—) em qualquer contexto
- Paralelismo perfeito em mais de 1 legenda ("X. Y. Z." repetido)
- Metáfora sensorial em mais de 1 a cada 4 legendas
- Frases que funcionam para qualquer vídeo sem trocar nenhuma palavra
- Começar legenda 2 com nome do compositor
- Vocabulário técnico sem tradução imediata ("staccato" sozinho — "staccato, notas curtas e soltas" é OK)
- Tags, códigos ou metadados no texto (px, CORPO, GANCHO, CLÍMAX, timestamps)
- Pronomes ambíguos sem referente claro ("ela" quem? "ele" quem?)
</constraints>

<examples>
OVERLAY EXCELENTE — REFERÊNCIA #1 (Mozart/Réquiem):

Gancho: "Como algo tão sombrio\\npode ser tão bonito?"
2: "Este é o momento em que Mozart\\nabriu os portões do céu."
3: "Mas quando ele escreveu essa\\nmúsica, estava morrendo..."
4: "E nesse momento, um estranho\\nbate à porta e encomenda um\\nRéquiem (missa fúnebre)."
5: "Sem revelar quem é.\\nNem para quem é a missa."
6: "Doente, endividado e escrevendo\\ntrês obras ao mesmo tempo..."
7: "Mozart se convence: a missa\\nnão é para outro. É para ele."
8: "Chega à Lacrimosa. O último\\ntrecho que conseguiu compor."
9: "Mozart morre antes de terminar.\\nSeu aluno completa o Réquiem\\nàs escondidas."
10: "O coro sobe em ondas...\\nCada frase mais alta,\\nmais pesada."
11: "O coro escurece a cada frase.\\nNenhuma nota traz alívio."
12: "Como uma prece que insiste\\nmesmo sabendo que\\nnão há resposta."
13: "Sombrio e bonito. Como tudo\\nque se escreve sabendo\\nque é a última vez."
CTA: "Siga, o melhor da música clássica,\\ndiariamente no seu feed. ❤️"

POR QUE FUNCIONA:
- CADEIA DE EVENTOS: estranho encomenda → Mozart adoece → se convence que é para ele → chega à Lacrimosa → morre → aluno completa
- Cada legenda avança a história. Remover qualquer uma cria buraco.
- ÂNGULO COMO PORTA: "sombrio/bonito" abre, mas a história EXPANDE para o mistério da encomenda, a morte, o aluno.
- ANCORAGEM: legendas 10-12 conectam ao que o espectador OUVE (coro subindo, escurecendo).
- FECHAMENTO retoma gancho: "sombrio e bonito" → eco direto do "Como algo tão sombrio pode ser tão bonito?"
- TODAS as legendas têm \\n. Linhas curtas e balanceadas.
- Zero travessão. Zero paralelismo repetido. Zero metáfora vazia.
- Variação de ritmo: legendas de 2 linhas alternam com 3 linhas.

OVERLAY EXCELENTE — REFERÊNCIA #2 (La Campanella):

Gancho: "Por 30s ela esqueceu\\nque era humana…"
2: "O trecho que leva o piano\\nao extremo do possível."
3: "Essa é La Campanella.\\nA música que nasceu\\nde uma obsessão."
4: "Em 1832, Liszt viu Paganini\\nparalisar Paris inteira\\ncom um violino."
5: "E jurou que o piano\\nfaria o mesmo."
6: "Logo chamaram Liszt\\nde demônio do piano.\\nE não era elogio."
7: "Onde tocava, mulheres\\ndesmaiavam. Fãs disputavam\\nfios do cabelo dele."
8: "A histeria ganhou nome:\\nLisztomania."
9: "A primeira febre coletiva\\nda história por um músico.\\nUm século antes dos Beatles."
10: "Essa nota aguda que insiste\\nno topo? É o sino. Campanella."
11: "Debaixo dele, os dedos\\ncruzam o teclado inteiro\\na cada compasso."
12: "Agora o andamento dobra.\\nTrinados e escalas cromáticas\\ndisparam ao mesmo tempo."
13: "O sino toca uma última vez.\\nO acorde final fecha tudo\\nem silêncio."
14: "Quem você acabou de ouvir:\\nValentina Lisitsa. Ucraniana."
15: "Liszt queria o impossível.\\nEla entregou. 🎹"
CTA: "Siga, o melhor da música clássica,\\ndiariamente no seu feed. ❤️"

POR QUE FUNCIONA:
- Ângulo (Liszt/obsessão) guia legendas 3-9, depois EXPANDE para o som (10-13) e intérprete (14-15).
- 4 momentos de ANCORAGEM ao som: "nota aguda no topo", "dedos cruzam o teclado", "andamento dobra", "sino toca".
- Fechamento retoma: "esqueceu que era humana" ↔ "queria o impossível, ela entregou".
- Ritmo varia: 2 linhas (5, 8, 14, 15) alternam com 3 linhas (3, 4, 6, 7, 9, 11, 12, 13).

OVERLAY PÉSSIMO — O QUE NUNCA FAZER:

"Este celo tem 324 anos."
→ TRIVIA. Faz PENSAR, não sentir. Um número não segura ninguém.

"Nas mãos de Capuçon, cada nota derrete na seguinte."
→ METÁFORA VAZIA. "Derrete" não é informação. É poesia de IA.

"O arco mal toca a corda. O peso do braço faz o trabalho. E o cisne desliza."
→ GENÉRICO. Funciona para qualquer cellista. Trocar nome e continua igual.

"Três séculos. Três instrumentos. Os mesmos acordes."
→ PARALELISMO IA. A marca registrada mais identificável de texto gerado. Humanos não escrevem assim.

"Só quatro vozes. Nenhum solo. Nenhum truque. Nenhuma nota a mais."
→ PARALELISMO + GENÉRICO. Funciona para qualquer quarteto vocal da história.

"...o pianista some. Fica só a música."
→ ZERO INFORMAÇÃO. Não diz nada. Não acrescenta nada. Filler puro.

"Até que tudo para."
→ FRASE DE EFEITO VAZIA. Parece profunda. É oca.

"Seu cérebro reconhece o padrão e começa a desacelerar."
→ PSEUDOCIÊNCIA. Frase de blog wellness. Tom errado. Marca de IA.

"1,8 bilhão de vezes por dia. E ninguém sabia o nome do compositor."
→ TRIVIA COM NÚMERO. O cérebro calcula em vez de sentir.

POR QUE TODOS FALHAM:
- Zero cadeia de eventos. São fatos soltos e metáforas.
- Trocar compositor/peça e tudo continua funcionando.
- 100% estilo, 0% substância.
- Paralelismo ("Três X. Três Y.") é o padrão mais identificável de IA.
- Metáfora sensorial ("derrete", "desliza") sem fato concreto = preenchimento.

TESTE FINAL ANTES DE ENTREGAR:
Leia cada legenda em voz alta. Se soa como alguém contando uma história
num bar, está certo. Se soa como copy de Instagram ou narração de trailer,
está errado e deve ser reescrito.
</examples>

<format>
Responda em JSON válido:

```json
{{
  "mapa_eventos_interno": "E1: verbo → E2: verbo → E3: verbo → ... (para referência)",
  "legendas": [
    {{
      "numero": 1,
      "tipo": "gancho",
      "texto": "{selected_hook}",
      "linhas": 2,
      "evento_mapa": "—",
      "funcao": "Gancho aprovado pelo operador"
    }},
    {{
      "numero": 2,
      "tipo": "corpo",
      "texto": "Este é o momento em que Mozart\\nabriu os portões do céu.",
      "linhas": 2,
      "evento_mapa": "E1",
      "funcao": "Construção — contexto temporal"
    }},
    {{
      "numero": 4,
      "tipo": "corpo",
      "texto": "Em 1832, Liszt viu Paganini\\nparalisar Paris inteira\\ncom um violino.",
      "linhas": 3,
      "evento_mapa": "E2",
      "funcao": "Construção — evento que desencadeia tudo"
    }},
    ...
    {{
      "numero": N-1,
      "tipo": "fechamento",
      "texto": "",
      "linhas": 2,
      "evento_mapa": "—",
      "funcao": "Fechamento — retoma/responde gancho"
    }},
    {{
      "numero": N,
      "tipo": "cta",
      "texto": "Siga, o melhor da música clássica,\\ndiariamente no seu feed. ❤️",
      "linhas": 2,
      "evento_mapa": "—",
      "funcao": "CTA fixo"
    }}
  ],
  "verificacoes": {{
    "total_legendas": 0,
    "ancoragens_ao_video": ["legenda X: descrição"],
    "legendas_do_angulo_vs_expansao": "X de Y legendas no ângulo do gancho",
    "gancho_fechamento_par": "explicação de como o fechamento retoma o gancho",
    "paralelismos_encontrados": 0,
    "metaforas_sensoriais": 0,
    "travessoes": 0
  }}
}}
```

IMPORTANTE:
- O campo "texto" de cada legenda contém APENAS o texto puro que aparece na tela
- Use \\n para quebra de linha DENTRO de uma legenda (máx 2 quebras = 3 linhas)
- O CTA é SEMPRE a última legenda, SEMPRE com este texto exato
- O gancho (legenda 1) é SEMPRE o texto aprovado pelo operador, sem alteração
- Timestamps NÃO são gerados aqui — o código calcula deterministicamente
</format>

<self_check>
Antes de entregar, execute CADA verificação. Se qualquer uma falhar, corrija ANTES de entregar:

1. CADEIA: Cada legenda do corpo corresponde a um evento do mapa? Se alguma não corresponde, é filler — cortar ou substituir.

2. ANCORAGEM: Pelo menos 2 legendas nomeiam algo audível/visível no vídeo? Se < 2, adicionar.

3. SATURAÇÃO: O ângulo do gancho domina mais de 40% das legendas? Se sim, as legendas do Desenvolvimento precisam expandir.

4. ARCO: Ler só gancho + fechamento. Fazem par? Se não, reescrever fechamento.

5. REPETIÇÃO: Resumir cada legenda em 5 palavras. Algum resumo se repete? Se sim, cortar a legenda redundante.

6. RITMO: 3+ legendas consecutivas com mesmo número de linhas? Se sim, variar.

7. IA: Existe travessão? Paralelismo repetido? Cascata de metáforas? Frase genérica? Se sim, reescrever.

8. TESTE DO BAR: Ler todo o overlay em sequência. Soa como alguém contando uma história num bar, ou como texto de IA/copy de Instagram? Se o segundo, reescrever as legendas artificiais.

9. COMPLETUDE: O overlay tem ~{n_legendas} legendas narrativas + CTA? Se muito menos, adicionar. Se muito mais, cortar as mais fracas.
</self_check>"""

    return prompt
