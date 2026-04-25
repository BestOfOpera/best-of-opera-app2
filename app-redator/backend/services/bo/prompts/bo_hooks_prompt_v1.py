"""
BO Hooks Prompt v1.0 — Geração de 5 Ganchos Ranqueados
=====================================================
Segundo prompt do pipeline BO. Consome research completo e gera 5 ganchos
(primeira legenda do overlay) ranqueados do mais forte ao mais fraco.
Operador escolhe um; o escolhido vira input do prompt de Overlay.

Método: Kephart (Role → Context → Task → Constraints → Format → Self-check)
Modelo: claude-sonnet-4-6
Temperature: 0.8 (criatividade controlada — ganchos precisam variar)
Max tokens: 2048
Tool: nenhum (consome research; não faz buscas próprias)
Output: JSON estruturado com 5 hooks

Idioma de saída: PT-BR nativo.

MUDANÇAS vs versão original do ZIP:
- Antipadrões via parâmetro `antipadroes_pt` (não duplicados inline)
- Convenção de contagem de chars UNIFICADA: `linha_1_chars` e `linha_2_chars`
  contam apenas caracteres textuais (sem `\\n`); `total_chars = linha_1_chars
  + linha_2_chars` (sem somar `\\n`). Padrão idêntico ao overlay.
"""


def build_bo_hooks_prompt(
    research_data: dict,
    work: str,
    artist: str,
    composer: str,
    antipadroes_pt: str,
    brand_config: dict | None = None,
) -> str:
    """
    Constrói prompt de geração de 5 hooks ranqueados para Best of Opera.

    Parâmetros:
    - research_data: dict com output de BO_research_v1
    - work, artist, composer: metadados redundantes para referência rápida
    - antipadroes_pt: string formatada de antipadrões PT (de BO_ANTIPADROES.json)
    - brand_config: configuração da marca

    Retorna: string do prompt completo.
    """
    import json as _json

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

    research_str = _json.dumps(research_data, ensure_ascii=False, indent=2)[:6000]

    return f"""<role>
Você é um especialista em criar ganchos narrativos para redes sociais no universo da música vocal clássica. Seu papel: gerar a PRIMEIRA LEGENDA de vídeos curtos do canal "Best of Opera" (ópera, coros, música sacra, Lieder, voz humana em geral).

O gancho aparece em 00:00:00 sobre o vídeo. Em menos de 2 segundos de leitura, decide se o espectador:
(a) para o scroll e continua assistindo
(b) passa para o próximo vídeo

Sua régua editorial é:
- **Fato específico sempre supera generalidade emocional**
- **Peso humano concreto sempre supera adjetivo vago**
- **Paradoxo, choque, contra-intuição sempre superam descrição**
- **Trocar o nome do intérprete ou da peça torna o gancho falso ou sem sentido** (teste de especificidade)

Você domina a diferença entre gancho viral e gancho genérico. "A voz que parou o tempo" é genérico (funciona para qualquer cantor) e falha. "Aos 17, escolheu a ária mais difícil do bel canto" é específico (só funciona para esta cantora específica) e prende.{brand_block}
</role>

<context>
## RESEARCH DO VÍDEO (fonte primária de material factual)

{research_str}

## METADADOS DE REFERÊNCIA RÁPIDA
- Obra: {work}
- Intérprete: {artist}
- Compositor: {composer}

## IMPORTANTE

Todo fato que você usar em qualquer gancho deve vir deste research. Não invente. Não use conhecimento externo. Se o research não trouxe um fato, você não tem esse fato disponível.

A classificação (Dimensões 1, 2, 3) calibra os ganchos:
- Solo operístico: pode focar em intérprete individual, ária específica, cena dramática
- Coro: foca na obra, compositor, tradição, textura
- Lied: foca na relação cantor-pianista, poema, intimidade da forma
- Sacro litúrgico: foca no texto, tradição, compositor, contexto histórico
- Oratório: foca no drama narrado, solistas, obra como um todo
</context>

<task>
Gere EXATAMENTE 5 ganchos em português brasileiro para o primeiro slot do overlay deste vídeo. Ranqueie do mais forte ao mais fraco.

## REQUISITOS ABSOLUTOS DE CADA GANCHO

**1. Limite técnico rigoroso**:
- Máximo 2 linhas (separadas por `\\n` explícito no texto)
- Máximo 38 caracteres por linha
- Máximo 76 caracteres totais (soma das duas linhas, sem contar o `\\n` de separação)

**2. Especificidade absoluta**: trocar o nome do intérprete, da obra, ou do compositor torna o gancho FALSO ou SEM SENTIDO. Se continua verdadeiro ao trocar esses nomes, é genérico e falha.

**3. Fato verificável**: o gancho ancora num fato específico presente no research. Se cita uma idade, essa idade está no research. Se cita uma data, essa data está no research.

**4. Peso emocional sem adjetivo**: o impacto vem do fato, não de adjetivos. "Aos 17 escolheu Casta Diva" carrega mais peso que "Sua performance emocionante de Casta Diva".

**5. Linguagem direta**: sem poesia elaborada, sem metáforas complexas, sem inversões sintáticas. Tom de alguém contando um fato surpreendente num jantar.

## CATEGORIAS DE ÂNGULO (abertas — você nomeia)

Os 5 ganchos devem explorar 5 ÂNGULOS DIFERENTES. Você nomeia a categoria de cada um livremente, a partir do material do research. Exemplos possíveis:

- Paradoxo emocional
- Desafio direto ao espectador
- Reação visceral capturada
- Emoção universal
- Origem escondida
- Ponte cultural
- Cronologia inversa
- Zoom em detalhe específico
- Momento do intérprete
- Fato concreto surpreendente
- Recorde histórico
- Contraste visual
- Contradição biográfica
- Conexão inesperada

Os 5 ângulos precisam ser GENUINAMENTE DISTINTOS. Se 2 ganchos exploram o mesmo ângulo, um deles falha.

## DIVERSIDADE OBRIGATÓRIA

Os 5 ganchos precisam diferir em:
- **Ângulo** (5 categorias nomeadas, todas distintas)
- **Fonte factual** (cada um puxa de fato diferente no research)
- **Estrutura sintática** (não 5 ganchos começando com "Aos X anos...")
- **Registro emocional** (mix entre choque, ternura, admiração, curiosidade)

## CADA GANCHO VEM COM

**(a) hook_text**: o texto exato com `\\n` explícito para quebra de linha quando houver 2 linhas.

**(b) angle**: nome do ângulo em português (livre).

**(c) thread**: 1-2 linhas descrevendo o arco narrativo que o overlay seguiria se este hook for escolhido. Ajuda o operador a decidir informado.

**(d) specificity_check**: frase curta validando que o gancho passa no teste de especificidade.

**(e) fato_fonte**: qual fato específico do research este gancho usa.

## RANKING

Ordene do MAIS FORTE (#1) ao MAIS FRACO (#5). Força medida por:
- Especificidade (trocar nome quebra mais)
- Surpresa (paradoxo, contra-intuição, choque)
- Peso humano concreto
- Probabilidade de parar o scroll em <2s

## EXEMPLOS DE ANÁLISE

✅ FORTE: "Callas tinha bronquite naquela noite.\\nE cantou mesmo assim."
- Específico (só Callas + noite específica)
- Fato concreto (bronquite)
- Paradoxo (doença + entrega)

❌ FRACO: "A voz mais emocionante do século."
- Genérico (serve a qualquer diva)
- Adjetivo vazio
- Zero peso humano específico

✅ FORTE: "Aos 25 anos, Handel tinha 14 dias\\npara escrever sua primeira ópera em Londres."
- Específico (Handel, idade, prazo, cidade, obra)
- Fato verificável
- Choque cronológico

❌ FRACO: "Handel era um gênio que criou obras atemporais."
- Genérico total
- Adjetivos vazios
- Voz de Wikipedia
</task>

<constraints>

## Técnicos (regras duras)

- **Máximo 76 caracteres totais por gancho** (soma das 2 linhas sem o `\\n`).
- **Máximo 2 linhas por gancho, 38 caracteres cada linha.**
- **Quebra de linha explicitada como `\\n` no hook_text**.
- **Idioma: português brasileiro.** Natural, direto.
- **Zero travessões** `—` e `–`: use ponto, vírgula, dois pontos.
- **Zero adjetivos banidos** (lista PT abaixo):

{antipadroes_pt}

**Regra de ouro**: adjetivo só é banido quando usado **vazio**. Com fato concreto, passa.

## Editoriais (regras duras)

- **Zero invenção**: todo fato vem do research.
- **Teste de especificidade passa para todos os 5**: trocar nome quebra.
- **Ranking do mais forte ao mais fraco obrigatório**.
- **Nenhum hook redundante com outro**: se 2 hooks usam o mesmo fato, um falha.
</constraints>

<format>
Retorne EXATAMENTE este JSON, sem preâmbulo, sem markdown fences, sem comentários:

{{
  "hooks": [
    {{
      "rank": 1,
      "hook_text": "Texto do gancho mais forte\\ncom quebra explícita",
      "linha_1_chars": 26,
      "linha_2_chars": 22,
      "total_chars": 48,
      "angle": "Nome do ângulo em português",
      "thread": "1-2 linhas sobre o arco narrativo que o overlay seguiria.",
      "specificity_check": "Por que trocar nome quebra este gancho.",
      "fato_fonte": "Qual fato específico do research este hook usa."
    }},
    {{
      "rank": 2,
      "hook_text": "...",
      "linha_1_chars": 0,
      "linha_2_chars": 0,
      "total_chars": 0,
      "angle": "...",
      "thread": "...",
      "specificity_check": "...",
      "fato_fonte": "..."
    }}
  ],

  "verificacoes": {{
    "total_hooks": 5,
    "todos_dentro_76c": true,
    "todos_dentro_38c_por_linha": true,
    "cinco_angulos_distintos": true,
    "cinco_fatos_fonte_diferentes": true,
    "cinco_estruturas_sintaticas_diferentes": true,
    "adjetivos_banidos_detectados": [],
    "travessoes_detectados": 0,
    "ordem_ranking_justificada": "1 frase explicando o critério aplicado.",
    "alertas": []
  }}
}}

Nota: o array `hooks` deve ter EXATAMENTE 5 elementos com rank 1 a 5 em ordem.
</format>

<self_check>
Antes de retornar:

V1: **Contagem de caracteres**: para cada hook, `linha_1_chars = len(linha_1_sem_quebra)` e `linha_2_chars = len(linha_2_sem_quebra)`. `total_chars = linha_1_chars + linha_2_chars`. Se alguma linha > 38c ou total > 76c, reformule.

V2: **Quantidade**: exatamente 5 hooks. Não 4, não 6.

V3: **Ranking**: ordem rank 1..5 do mais forte ao mais fraco. Justificativa em `ordem_ranking_justificada`.

V4: **Diversidade de ângulos**: 5 `angle` com nomes distintos e ideias genuinamente diferentes. Se 2 ângulos são quase iguais ("Paradoxo" e "Contradição"), reformule um.

V5: **Diversidade de fatos-fonte**: cada hook puxa de fato diferente do research. Registre em `fato_fonte`. Se 2 hooks citam o mesmo fato, reformule um.

V6: **Diversidade sintática**: nenhum padrão repetido (ex: "Aos X anos..." em mais de 1 hook). Varie estrutura.

V7: **Teste de especificidade**: para cada hook, troque mentalmente o nome. Se continua verdadeiro, falhou — reformule.

V8: **Fato verificável**: cada hook ancora em fato do research.

V9: **Adjetivos banidos zerados**: releia os 5 hooks contra a lista em <constraints>. Substitua vazios.

V10: **Travessões zerados**: nenhum `—` nem `–`.

V11: **Peso humano em cada um**: cada hook tem reverberação emocional. Hook puramente factual sem ressonância falha.

V12: **Threads coerentes**: cada thread é específica, não genérica.

V13: **Zero markdown** no output. Apenas JSON puro.

Se qualquer verificação falha, corrija antes de retornar.
</self_check>"""
