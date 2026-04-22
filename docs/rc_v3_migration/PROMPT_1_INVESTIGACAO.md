# PROMPT 1 — Investigação Completa do Código do Site Reels Classics

*Sessão de investigação. Você NÃO patcha nada nesta sessão. O único output é um relatório. Mudanças vêm numa sessão posterior (PROMPT 2), só depois deste relatório ser aprovado.*

---

## 1. Seu papel e os limites dele

Você é um auditor de código lendo um repositório pela primeira vez. Sua missão única: **mapear o sistema** com precisão suficiente para que, em uma sessão posterior, patches possam ser aplicados sem regressão.

Você **não pode**:
- Editar nenhum arquivo do repositório
- Executar refatorações, mesmo que pequenas
- Propor implementações específicas durante a investigação
- Adivinhar comportamento quando não há evidência no código
- Inferir arquitetura por analogia com outros projetos

Você **deve**:
- Ler código
- Executar comandos read-only (grep, find, git log, git blame, cat, ls, wc)
- Rodar o código em modo dry-run (invocar funções com inputs fake, observar outputs) **somente se** isso não alterar estado (sem DB, sem chamadas externas)
- Citar paths exatos e números de linha
- Reportar ambiguidade como ambiguidade, não preencher lacuna com suposição
- Produzir um relatório estruturado no formato definido na seção 7

Se em algum momento você achar que precisa patchar algo para continuar investigando, **pare** e registre a dependência no relatório. Não resolva.

---

## 2. Contexto do projeto (leitura obrigatória antes de começar)

**Reels Classics (RC)** é um canal Instagram de música clássica para leigos. O operador publica vídeos curtos diários (30-90 segundos) com três artefatos produzidos pelo sistema que você vai investigar:

1. **Overlay**: 10-16 legendas narrativas sincronizadas com o áudio do vídeo, aparecem como texto em cima da imagem
2. **Descrição**: caption do post no Instagram (texto longo abaixo do vídeo)
3. **Automação**: 3 respostas em rotação, 1 DM fixa e 1 comentário pinned do ManyChat, acionados quando alguém comenta uma palavra-chave

O sistema gera esses artefatos através de um **pipeline de 6 etapas**, cada uma implementada (segundo conhecimento prévio fora deste repositório — a ser validado) como uma função Python `build_rc_*_prompt(metadata, ...)` que monta um prompt para um LLM. A saída de cada etapa é JSON (ou variação). A saída de uma etapa alimenta a seguinte:

```
Etapa 1: rc-research     → pesquisa profunda sobre peça, compositor, intérprete
Etapa 2: rc-hooks        → 5 ganchos ranqueados; operador escolhe 1
Etapa 3: rc-overlay      → legendas do overlay sincronizadas
Etapa 4: rc-post         → descrição do Instagram
Etapa 5: rc-automation   → respostas ManyChat
Etapa 6: rc-translation  → internacionalização (pt, en, es, de, fr, it, pl)
```

O canal é regido por uma **Voice Bible** interna (documento editorial). Os prompts v3/v3.1 anexados a esta sessão são a versão validada pela auditoria — eles ainda não estão no repositório; sua investigação descobrirá a **versão atualmente em produção** e como ela difere.

---

## 3. Contexto da auditoria prévia (o que já foi decidido fora deste repositório)

Entre fevereiro e abril de 2026, uma auditoria estática de 4 meses identificou 32 defeitos sistemáticos no pipeline RC. Todos foram endereçados em artefatos anexados a esta sessão:

- **3 prompts v3/v3.1 patched** (`rc_translation_prompt_v3.py`, `rc_automation_prompt_v3.py`, `rc_overlay_prompt_v3_1.py`) — são a **nova versão autoritativa** desses prompts. Serão aplicados na sessão de execução (PROMPT 2), não agora.
- **6 SKILLs** (formato Markdown com frontmatter YAML, `rc-*_SKILL.md`) — são a versão do **app Claude** (interface de chat separada do site); vivem em `/mnt/skills/user/rc-*/` no app, não dentro deste repositório. Estão aqui como **referência cruzada do comportamento esperado** que os prompts do site devem produzir.
- **2 relatórios** (`RELATORIO_LOTE_D.md`, `RELATORIO_LOTES_A_B_C_F.md`) — contextualizam o que mudou e por quê.

Durante sua investigação, **não pressuponha** que o código do site espelha os prompts anexados. Você está investigando **o que existe no repositório hoje** — o que é potencialmente várias versões atrás dos anexos. A diferença entre o que existe e o que deveria existir é justamente o escopo do patch futuro.

**Decisões editoriais já fixadas** (fora do escopo desta investigação, registradas aqui só para que você entenda vocabulário que pode aparecer nos anexos):

- Output de todas as 6 etapas é JSON estruturado
- 38 caracteres por linha é regra dura apenas na Etapa 6 (tradução); nas outras é referência flexível
- Duração de legenda no overlay é 4-6s por legenda (distribuição dinâmica), substituindo tabela fixa antiga
- Fio narrativo dinâmico no overlay (pode virar para fio complementar se o principal esgotar) substitui fio único rígido
- CTAs de tradução em alemão/francês/italiano/polonês usam pronome explícito (Folge uns / Suis-nous / Seguici / Obserwuj nas) — PT e EN permanecem sem pronome
- `post_text` (descrição aprovada) deve ser consumido pelo prompt de automação para manter consistência de tom e emojis

Isso é tudo o que você precisa saber sobre *o que foi decidido*. Sua missão é descobrir *o que está implementado*.

---

## 4. Por que esta fase existe (metodologia)

A tentação natural é ler o repositório rapidamente, identificar onde mudar, e mudar. Em sistemas maduros isso produz regressão. A razão é simples: o patch que parece óbvio num arquivo pode depender de um contrato que outro arquivo assume silenciosamente. Descobrir esse contrato requer leitura metódica.

Você investiga **antes** de patchar porque:

- Funções Python com o mesmo nome podem existir em múltiplos lugares (ex: uma versão de produção e uma de desenvolvimento)
- O output de um prompt LLM pode ser pós-processado em várias camadas antes de virar o artefato final
- O mesmo campo JSON pode ser consumido por backend, frontend, banco de dados e processos assíncronos simultaneamente
- Adicionar um campo novo ao schema que um validador não conhece pode quebrar silenciosamente em uma camada que você não olhou
- O frontend pode ter lógica de montagem que assume ordem específica dos campos

O relatório que você produzirá serve como **mapa cirúrgico** — permite à sessão de execução saber exatamente onde cortar, em que ordem, e o que verificar depois.

---

## 5. Escopo da investigação

15 dimensões abaixo. Cada dimensão tem perguntas específicas. Toda pergunta precisa de resposta no relatório. Resposta aceitável inclui "não encontrado" — desde que acompanhada do que foi procurado e como.

Ordem sugerida: começar por 5.1 (arquitetura), depois 5.4 (prompts) e 5.2 (fluxo de dados). Os outros podem ser investigados em qualquer ordem, mas todos precisam ser cobertos.

### 5.1 Arquitetura de alto nível

- Stack Python: qual framework web? (Django, FastAPI, Flask, Starlette, Litestar, AIOHTTP, outro)
- Versão da linguagem (Python 3.10/3.11/3.12)
- Frontend: SSR puro (templates Django/Jinja2)? SPA separado (React/Vue/Svelte)? Híbrido (HTMX, Turbo)?
- Estrutura do repositório: monorepo (frontend e backend juntos)? Backend isolado com frontend em repo separado?
- Organização de módulos: por camada (models/views/services)? Por domínio (rc/, users/, billing/)? Flat?
- Estrutura de diretórios relevantes ao pipeline RC: listar cada pasta com 1 linha descrevendo função
- Linguagens adicionais presentes (JS/TS no frontend, SQL em migrations, shell em scripts, Dockerfile, etc.)

### 5.2 Fluxo de dados do pipeline

- Qual a entrada do pipeline? (upload manual? API externa? formulário web?)
- Quem dispara cada etapa? (usuário clica botão? dispatcher automático ao concluir anterior? cron?)
- Cada etapa é síncrona (bloqueia usuário até terminar) ou assíncrona (queue/worker)?
- Se assíncrona: qual fila (Celery, RQ, Dramatiq, Arq, custom)? Qual broker (Redis, RabbitMQ, SQS)?
- Output de uma etapa vira input da seguinte por: passagem direta de objeto? persistência em DB e releitura? cache Redis? variáveis de contexto?
- Há persistência intermediária (cada etapa salva seu JSON bruto)?
- Há rollback automático se uma etapa falha? Reprocessamento manual?
- Há possibilidade de regenerar uma etapa individual depois (ex: "refaz só o overlay com outro gancho")?

### 5.3 Integração com LLM

- Provedor(es) LLM usado(s): Anthropic, OpenAI, Google, local?
- Biblioteca cliente: SDK oficial (`anthropic`, `openai`), wrapper (`langchain`, `litellm`), chamada HTTP crua?
- Modelo(s) específico(s) usado(s) em cada etapa: há diferenciação por etapa? Configurável? Hardcoded?
- Parâmetros: temperature, max_tokens, top_p etc. — onde são definidos? (constantes Python, config file, env var, banco)
- System prompt extra (além do prompt construído pelas funções `build_rc_*_prompt`)?
- Tratamento de JSON inválido do LLM (malformed, truncated, não-JSON)
- Retry policy: tentativas automáticas? backoff?
- Timeout por request
- Streaming de resposta habilitado?
- Logging dos request/response (para auditoria, debug, re-análise)?
- Contabilização de tokens/custo por etapa?

### 5.4 Estado atual dos prompts do pipeline

Esta é a seção central. Faça um mapeamento **completo** das 6 funções de prompt:

Para cada uma de `build_rc_research_prompt`, `build_rc_hook_prompt` (ou `hooks`), `build_rc_overlay_prompt`, `build_rc_post_prompt`, `build_rc_automation_prompt`, `build_rc_translation_prompt` (nomes podem variar — verificar convenção):

- **Path exato** do arquivo onde a função está definida
- **Linhas** da definição (início e fim)
- **Tamanho** (linhas) e **SHA256** do arquivo (para comparação posterior com anexos)
- **Assinatura completa**: parâmetros, tipos (se anotados), valores default
- **Versionamento**: o arquivo tem "v3" ou "v2" no nome? Há arquivos coexistindo (`rc_overlay_prompt.py` e `rc_overlay_prompt_v3.py`)? Se sim, qual é o importado pelos callsites?
- **Docstring**: reproduzir (ou parafrasear curto) para estabelecer contrato
- **Seções internas do prompt** (`<role>`, `<context>`, `<task>`, `<constraints>`, `<format>`, etc. — se usam XML-like tags do estilo Anthropic): listar
- **Schema de output declarado**: extrair do prompt o JSON schema esperado do LLM (parafraseando se muito extenso)

Listar também qualquer **helper/utility** relacionado ao prompt no mesmo arquivo ou em arquivos adjacentes (ex: `_estimar_legendas`, `_calcular_duracao`, `_extract_context`, etc.) — essas funções costumam ser consumidas pelo prompt e pelos pós-processadores.

### 5.5 Validadores de schema JSON

- Existem validadores de schema aplicados ao output do LLM?
- Se sim: biblioteca usada (`pydantic`, `jsonschema`, `marshmallow`, validação manual com dict checks)
- Para cada etapa: o validador existe? Onde? Lista de campos obrigatórios e opcionais?
- Como é tratada a falha de validação? (erro 400, retry do LLM, fallback?)
- Há diferença entre "shape validation" (campos existem) e "semantic validation" (valores fazem sentido)?
- Algum validador bloqueia publicação se certos invariantes não baterem (ex: `analise_diversidade.todos_diferentes == false`)?

### 5.6 Pós-processamento

A saída do LLM raramente é usada bruta. Tipicamente há camadas de transformação entre LLM e artefato final. Mapear:

- Existe função `_sanitize_rc` ou similar? Em qual arquivo? O que remove/reescreve? (travessões, metadados vazados, emojis proibidos, etc.)
- Existe função `process_overlay_rc` ou similar? O que faz? Provável escopo: calcular timestamps deterministicamente a partir do JSON do LLM (a função Python, não o LLM, calcula os tempos de cada legenda)
- Há pós-processadores específicos por etapa? Listar todos.
- Ordem de aplicação dos pós-processadores (pipeline interno)?
- Algum pós-processador depende de **campos específicos** do JSON de saída? (Se sim, adicionar um campo novo sem avisar o pós-processador é risco de regressão)

### 5.7 Frontend/renderização da descrição

A Etapa 4 (`rc-post`) produz um JSON com múltiplos campos (header, 3 parágrafos, CTAs, hashtags). Esse JSON é transformado numa **string única** que é colada no Instagram.

A auditoria **não** alterou a arquitetura visual da descrição — header permanece no topo, 3 parágrafos, CTAs, 4 hashtags no fim. A única mudança estrutural na Etapa 4 é a adição de **um campo novo** (`save_cta`) que deve aparecer entre `paragrafo3` e `follow_cta` na renderização.

Ainda assim, é essencial mapear a lógica atual de renderização para saber **onde** inserir o novo campo sem quebrar a estrutura existente. Pontos a mapear:

- Onde está a lógica que transforma o JSON da Etapa 4 na string final do Instagram?
- É backend (Python serializando string) ou frontend (JS/TS montando string)?
- Se backend: qual função/método? Qual arquivo?
- Se frontend: qual componente/template? Qual arquivo?
- Qual é a **ordem atual** de renderização (listar os campos na ordem em que entram na string)?
- Qual é o **separador** entre seções (blank line única? duas blank lines? `•`? outro caractere)?
- Como blank lines são geradas? (`\n\n` literal? renderização de array com join? loop com template)
- Como emojis são tratados? (Unicode direto? shortcodes? escape)
- Posts antigos (gerados antes desta migração) têm JSON sem `save_cta`. A renderização atual tem fallback para campos ausentes, ou quebra?
- A string final é salva em banco (`post_text` ou similar) ou sempre regenerada?
- Há preview da string final antes da publicação? Onde?
- Há algum caractere invisível, espaço em excesso, trimming automático que possa alterar a string final?

### 5.8 Renderização do overlay no vídeo

A Etapa 3 (`rc-overlay`) produz JSON com as legendas (texto + tipo + ordem). Os **timestamps** são calculados pelo código (não pelo LLM). O artefato final é texto burn-in no vídeo ou um arquivo SRT/ASS — investigar qual.

- Formato final das legendas do overlay: SRT, ASS, burn-in direto no vídeo, overlay HTML/CSS, JSON processado pelo app que publica?
- Onde está a lógica de cálculo de timestamps a partir do JSON da Etapa 3?
- Algoritmo de cálculo: proporcional ao número de caracteres? tempo fixo por legenda? distribuição conforme faixa de duração (regra v3.1 de 4-6s/legenda)?
- Biblioteca/ferramenta usada para burn-in (se burn-in): FFmpeg? Remotion? OpenCV? outra?
- Fonte, cor, tamanho, posição: hardcoded? configuráveis por vídeo? por operador?
- Há preview do overlay antes da publicação?

### 5.9 Persistência e banco de dados

- SGBD: PostgreSQL, MySQL, SQLite, outro?
- ORM ou SQL cru (Django ORM, SQLAlchemy, Tortoise, Piccolo, `asyncpg`/`psycopg` cru)?
- Tabelas relevantes ao pipeline RC: listar com estrutura resumida (nome, colunas principais, tipos)
- Para cada etapa do pipeline, a saída JSON é armazenada como:
  - Coluna blob/jsonb única com o JSON inteiro?
  - Múltiplas colunas estruturadas (uma por campo)?
  - Divisão mista (alguns campos normalizados, resto em blob)?
- Há tabelas adjacentes (logs, histórico de versões, auditoria)?
- Migrations: existe sistema de migrations? (Django migrations, Alembic, yoyo, manual)
- Como são aplicadas migrations em produção?
- Se a sessão de execução precisar adicionar colunas novas (ex: `hook_seo` separado do `header`), qual é o processo correto no projeto?

### 5.10 Internacionalização

- A Etapa 6 (tradução) é invocada em qual momento? (Junto com publicação principal? Separado? Opcional?)
- Output da Etapa 6: formato atual (JSON único com 7 idiomas? ZIP de arquivos? 7 JSONs separados? outro?)
- Frontend/consumidor dos 7 idiomas: mostra todos? usuário escolhe idioma de publicação? 7 posts separados no Instagram?
- CTAs por idioma: armazenados como constantes (no código, em JSON de config, em banco) ou gerados pelo LLM em cada request?
- Se há tabela de CTAs hardcoded: path e conteúdo atual

### 5.11 Logs, observabilidade, tratamento de erros

- Biblioteca de logging: stdlib `logging`, `structlog`, `loguru`, outra?
- Nível configurado para produção
- Destino dos logs: stdout, arquivo, serviço (Sentry, Datadog, CloudWatch, Logtail)
- Tratamento estruturado de erros do pipeline: existe um tipo/classe de exceção específico por etapa?
- Erros do LLM (provider down, rate limit, JSON inválido): como são tratados? Há fallback? Retry visível ao usuário?
- Observabilidade: tracing (OpenTelemetry)? métricas (Prometheus, DataDog)?
- Analytics de vídeos publicados (performance pós-publicação): existe sistema de coleta?

### 5.12 Testes existentes

- Framework: `pytest`, `unittest`, `nose`?
- Pasta de testes: path, estrutura
- Coverage atual (se há script/config para rodar e medir)
- Tipos de teste presentes: unit, integration, E2E?
- Tests existentes que cobrem o pipeline RC: listar por etapa
- Há fixtures de metadata, pesquisa, overlay, etc. (material de teste reutilizável)?
- Há mock do provedor LLM nos testes? (ou testes rodam contra LLM real?)
- CI roda testes automaticamente? Em qual plataforma?

### 5.13 Deploy, branches e ambientes

- Git strategy: gitflow, trunk-based, outro?
- Branches principais (`main`, `master`, `develop`, `production`)
- Como código entra em produção (merge na main dispara deploy? tag cria release? manual?)
- Plataforma de deploy: Heroku, Render, Railway, AWS (ECS/Lambda/EC2), GCP, Vercel, Fly.io, VPS cru?
- Existe ambiente de staging?
- É possível testar patches em staging antes de prod?
- Rollback: processo manual, automático, impossível?

### 5.14 Secrets e configuração

- Onde secrets são armazenados (env vars, AWS Secrets Manager, Vault, arquivo `.env`, outro)
- Configs (não-secretas) — arquivo único, múltiplos, env vars, banco
- Chaves de API dos provedores LLM: mecanismo de rotação
- Algum secret referenciado no código mas não óbvio de onde vem?

### 5.15 Dependências e versões

- Gerenciador de dependências: `pip + requirements.txt`, `pip-tools`, `poetry`, `uv`, `pipenv`, outro?
- Arquivo de dependências: path e conteúdo resumido (listar bibliotecas principais)
- Versões travadas ou ranges?
- Versões do SDK do provedor LLM (relevante — APIs mudam entre versões)
- Alguma biblioteca já desatualizada que possa bloquear mudanças futuras?

---

## 6. Princípios metodológicos da investigação

**Cite, não resuma.** Toda afirmação no relatório acompanhada de path + linha. Exemplo correto: "`services/rc_prompts.py:47-89` define `build_rc_overlay_prompt(metadata, research_data, selected_hook, ...)`". Exemplo incorreto: "a função de overlay fica em services".

**Sem inferência por analogia.** Se o repo usa Django, não assuma que segue convenção Django padrão — leia o código. Frameworks maduros têm escape hatches e customizações.

**Separe observação de interpretação.** No relatório, traga primeiro o fato observado, depois (em parágrafo separado) a interpretação se relevante.

**Verifique duplicatas.** Antes de concluir que uma função está em um único arquivo, execute `grep -rn "def build_rc_overlay_prompt" .` (ou equivalente) para confirmar. Funções duplicadas são fonte comum de bugs de implementação.

**Teste invariantes com dry-run read-only.** Se for útil invocar uma função para entender seu output, fazer isso em um REPL/script sem efeitos colaterais (sem chamar LLM real, sem tocar em banco, sem rede). Se a função não permite dry-run sem efeito, registrar isso no relatório.

**Declare o que não foi investigado.** Se uma dimensão da seção 5 não pôde ser coberta (falta de acesso, escopo do repo maior que o tempo disponível, etc.), declare isso explicitamente — não omita.

**Validação numérica.** Qualquer contagem que você reportar (número de ocorrências, linhas, funções, etc.) passa por execução de comando (`wc -l`, `grep -c`, etc.) antes de ir ao relatório. Números de cabeça são fonte recorrente de erro.

---

## 7. Formato do relatório de entrega

Produzir arquivo `RELATORIO_INVESTIGACAO.md` na raiz do repositório ou em `docs/rc_v3_migration/` (ver seção 10). Estrutura:

```
# Relatório de Investigação — RC Pipeline (pré-migração v3/v3.1)

## 0. Sumário executivo
- 1 parágrafo sobre o estado geral do código RC
- 3-5 bullets com os achados mais importantes para quem vai patchar depois

## 1. Arquitetura de alto nível
(responder seção 5.1 com paths e evidência)

## 2. Fluxo de dados do pipeline
(responder seção 5.2)

## 3. Integração com LLM
(responder seção 5.3)

## 4. Prompts do pipeline
### 4.1 rc-research
### 4.2 rc-hooks
### 4.3 rc-overlay
### 4.4 rc-post
### 4.5 rc-automation
### 4.6 rc-translation
(para cada: path, linhas, SHA256, assinatura, docstring resumida, schema esperado, helpers no mesmo arquivo)

## 5. Validadores de schema
## 6. Pós-processamento
## 7. Frontend da descrição
## 8. Renderização do overlay
## 9. Persistência e banco
## 10. Internacionalização
## 11. Logs, observabilidade, erros
## 12. Testes existentes
## 13. Deploy e ambientes
## 14. Secrets e configuração
## 15. Dependências

## 16. Diff simbólico — estado atual vs anexos da auditoria
Para cada um dos 3 prompts anexados (translation, automation, overlay v3.1):
- O arquivo correspondente existe no repo? Qual path?
- SHA256 do arquivo do repo vs SHA256 do anexo
- Linhas adicionadas/removidas se tentasse sobrescrever (usar `diff -u repo/arquivo anexo/arquivo | wc -l`)
- Campos do schema JSON do anexo que NÃO existem no prompt do repo (inferir do diff)

## 17. Contratos implícitos identificados
Liste contratos que o sistema atual assume mas que **não estão documentados**.
Exemplos do tipo de coisa a capturar:
- "O frontend da descrição assume que `header` é campo único de 2-3 linhas; se for dividido em `hook_seo` + `header`, o componente X em Y precisa mudar"
- "O pós-processador sanitize assume que campo `legendas[].texto` não contém `\\n`; o schema v3.1 permite `\\n` para quebra de linha"
- etc.

## 18. Ambiguidades e lacunas
O que não foi possível mapear e por quê.

## 19. Riscos identificados para o patch futuro
Coisas que podem dar errado na sessão de execução (PROMPT 2) se não forem endereçadas.
Priorizar por severidade: crítico / alto / médio / baixo.

## 20. Proposta de ordem de patches
Baseada nas dependências reais descobertas, em que ordem os patches devem ser aplicados na sessão de execução.
Exemplo de formato:
1. [etapa/arquivo] — por que primeiro
2. [etapa/arquivo] — por que depois
...
```

O relatório é o **único output** desta sessão. Nenhum patch, nenhum rascunho de código.

---

## 8. Entregáveis desta sessão

1. `RELATORIO_INVESTIGACAO.md` — relatório completo conforme seção 7
2. `mapa_paths.txt` — lista de todos os arquivos e diretórios relevantes ao pipeline RC, um por linha, com 1 frase de descrição
3. (opcional) snippets de código referenciados no relatório salvos em `evidencias/` — útil se algum snippet for grande demais para o relatório principal

Nenhum commit no repositório. Nenhum branch novo. O relatório pode ser criado em `docs/rc_v3_migration/` ou equivalente, mas sem integrar no fluxo git até aprovação.

---

## 9. O que vem depois (contexto, não instrução)

Depois de você entregar o relatório e ele ser aprovado, uma segunda sessão (PROMPT 2) cuidará da execução dos patches. Nela você receberá:

- Os 3 prompts v3/v3.1 patched para substituir no código
- Especificação de quais consumidores dos JSONs precisam ser atualizados
- Especificação da mudança pontual no frontend da descrição (adição do campo `save_cta` entre `paragrafo3` e `follow_cta` — a arquitetura visual da descrição permanece inalterada)
- Smoke tests por etapa
- Teste de regressão E2E
- Critérios de aceitação

Você **não recebe esses detalhes agora** porque conhecê-los durante a investigação pode enviesar seu olhar — você buscaria só o que confirma a proposta em vez de mapear o sistema como ele é. Sua investigação precisa ser neutra sobre o que mudará depois.

---

## 10. Anexos presentes neste pacote

O operador copiará para um diretório do repositório (sugestão: `docs/rc_v3_migration/`) os seguintes arquivos antes de abrir esta sessão:

- `PROMPT_1_INVESTIGACAO.md` — este documento
- `rc_translation_prompt_v3.py` — versão patched que será aplicada na fase de execução (referência para seção 16 do relatório)
- `rc_automation_prompt_v3.py` — idem
- `rc_overlay_prompt_v3_1.py` — idem
- `rc-overlay_SKILL.md`, `rc-post_SKILL.md`, `rc-translation_SKILL.md`, `rc-research_SKILL.md`, `rc-hooks_SKILL.md`, `rc-automation_SKILL.md` — referência cruzada do comportamento esperado (não substituem nada no site; são usadas pelo app Claude separado)
- `RELATORIO_LOTE_D.md` — contexto dos 3 patches v3/v3.1
- `RELATORIO_LOTES_A_B_C_F.md` — contexto das 6 SKILLs reescritas

**Durante a investigação**, você pode (e deve) abrir os anexos para:

- Entender o formato esperado de saída dos prompts (seção 16 do relatório — diff simbólico)
- Identificar campos JSON novos que seu código atual provavelmente não conhece
- Entender o vocabulário da auditoria (nomes de fichas, decisões editoriais)

**Você não aplica os anexos nesta sessão.** Eles são referência, não input de execução.

---

## 11. Primeiro output esperado de você

Nesta ordem:

1. **Confirmação de leitura** (1 parágrafo, 4-6 linhas): resuma em suas palavras o papel, os limites e o entregável. Isto serve para alinharmos antes de você gastar tokens explorando.
2. **Plano de investigação** (lista de 5-10 itens): qual a primeira passada que você vai dar? Qual ordem das 15 dimensões da seção 5 faz sentido para este repo específico (que você vai descobrir)? Quais comandos read-only (bash, grep, find) você planeja executar primeiro?
3. **Pausa**. Aguarde confirmação do operador antes de começar a leitura exaustiva.

Depois da confirmação, siga o plano. Não pule a etapa 1 (confirmação de leitura) por pressa — ela captura mal-entendidos antes deles se multiplicarem.

---

## 12. Regra final

Em caso de dúvida se algo cabe nesta sessão ou na próxima (execução), a resposta padrão é: **cabe na próxima**. Esta sessão é estritamente investigação. Mesmo que você identifique um bug óbvio com fix óbvio, **registre no relatório** e deixe o fix para a sessão de execução. Isso preserva a separação de preocupações que torna o processo robusto.
