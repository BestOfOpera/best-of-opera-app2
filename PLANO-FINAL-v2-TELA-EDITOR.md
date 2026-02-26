# PLANO FINAL v2 — Tela Final do App-Editor

> Consolidação Claude + Gemini. Documento definitivo para execução.
> Gerado em 2026-02-25. Substitui versão anterior.
> Cada ação = uma sessão isolada do Claude Code. Executar na ordem.

---

## RESUMO EXECUTIVO

12 problemas mapeados. 12 ações ordenadas por dependência.

- **AÇÃO 0:** Desbloquear o projeto AGORA (curl manual, 2 minutos)
- **Ações 1-4:** Backend crítico (sem isso nada funciona)
- **Ações 5-7:** Frontend funcional (UI que mostra e baixa)
- **Ação 8:** Rotas de fuga / recovery na UI
- **Ações 9-10:** Prevenção e resiliência
- **Ação 11:** Limpeza + remoção de endpoint perigoso
- **VALIDAÇÃO FINAL:** Teste end-to-end completo

### Estratégia de deploy

**Cada ação backend (1-4, 9-11) faz deploy individual.** O motivo é
que cada uma corrige um bug independente e precisa ser testável
isoladamente. Se uma ação quebrar algo, o rollback é de um commit só.

**As ações de frontend (5-8) fazem deploy em bloco ao final.** O
frontend depende de todas as correções de backend estarem no ar.
Fazer deploy do frontend antes do backend causaria chamadas a
endpoints que ainda não funcionam corretamente.

**Ordem de deploy:**
```
1. Backend: Ação 1 → deploy → testar
2. Backend: Ação 2 → deploy → testar
3. Backend: Ação 3 → deploy → testar
4. Backend: Ação 4 → deploy → testar
5. Frontend: Ações 5 + 6 + 7 + 8 → deploy único → testar
6. Backend: Ação 9 → deploy → testar
7. Backend: Ação 10 → deploy → testar
8. Backend: Ação 11 → deploy → testar
9. Validação final (Ação 12)
```

As ações 9-11 podem ser deployadas antes ou depois do frontend —
são independentes. Coloquei depois porque o frontend é prioridade
para destravar o fluxo.

---

## AÇÃO 0 — DESBLOQUEAR O PROJETO AGORA (manual, sem código)

**Situação atual:** O projeto está parado com status `preview_pronto`.
O botão "Renderizar Todos" não existe no frontend, então não há como
avançar pela UI. Mas o endpoint do backend JÁ aceita esse status.

**Solução imediata (2 minutos):**

```bash
# 1. Descubra o ID da edição parada
curl https://SEU-DOMINIO-RAILWAY/api/v1/editor/edicoes

# 2. Procure na resposta a edição com status "preview_pronto"
# Anote o ID (ex: 42)

# 3. Dispare o render de todos os idiomas direto pela API
curl -X POST https://SEU-DOMINIO-RAILWAY/api/v1/editor/edicoes/42/renderizar

# 4. Acompanhe o progresso
curl https://SEU-DOMINIO-RAILWAY/api/v1/editor/fila/status

# 5. Quando status mudar para "concluido", liste os renders
curl https://SEU-DOMINIO-RAILWAY/api/v1/editor/edicoes/42/renders
```

**Por que funciona:** O endpoint `POST /renderizar` aceita status
`{"montagem", "preview_pronto", "erro"}`. O preview_pronto está na
lista. O backend enfileira a _render_task normalmente.

**Risco:** Se o _render_task não calcula idiomas faltantes (P9),
ele pode re-renderizar o PT. Isso desperdiça tempo mas não quebra
nada — o vídeo PT seria sobrescrito no R2 com o mesmo conteúdo.

**IMPORTANTE:** Esta é uma solução paliativa. As Ações 1-8 são
necessárias para que o fluxo funcione pela UI sem intervenção manual.

---

## AÇÃO 1 — Verificar e corrigir `aprovar-preview`
**Prioridade:** CRÍTICA — provável causa raiz do travamento
**Tipo:** Backend (pipeline.py)
**Deploy:** SIM, imediato após implementação

**O que verificar:**
O endpoint `POST /edicoes/{id}/aprovar-preview` pode estar mudando
o status para "renderizando" sem colocar a `_render_task` na fila
do worker. Se for o caso, o status fica preso para sempre.

**Prompt para o Claude Code:**
```
Leia PLANO-FINAL-v2-TELA-EDITOR.md na raiz do repo para contexto.
Depois leia app-editor/backend/app/routes/pipeline.py.

Encontre o endpoint POST /edicoes/{edicao_id}/aprovar-preview.

Preciso confirmar TRÊS coisas:
1. Ele faz check-and-set atômico (UPDATE WHERE status='preview_pronto')?
2. Ele coloca a _render_task na task_queue do worker?
3. Se enfileira, ele passa idiomas_renderizar excluindo o idioma do
   preview (PT já foi renderizado)?

Se NÃO enfileira a task na fila: corrija para que, após a transição
atômica do status, enfileire _render_task na task_queue.

O idioma do preview que deve ser EXCLUÍDO da renderização é "pt"
quando edicao.idioma != "pt", senão é edicao.idioma.

Os 7 idiomas alvo são: en, pt, es, de, fr, it, pl
Logo, se o preview é PT, renderizar: en, es, de, fr, it, pl (6 idiomas)

Padrões obrigatórios:
- Imports dentro do try-except
- except BaseException (não só Exception)
- Sessões curtas de banco (fechar antes de I/O)
- Check-and-set atômico com UPDATE WHERE

Não mude nada no frontend. Não mude nenhum outro endpoint.
Faça commit com mensagem em português e deploy.
```

**Teste após deploy:**
```bash
# Com uma edição em status "preview_pronto":
curl -X POST .../edicoes/{id}/aprovar-preview
# Verificar nos logs Railway: "[worker] Iniciando task edicao_id=..."
# Verificar: curl .../fila/status → ocupado=true, etapa=renderizando
```

**Critério de aceite:**
- Endpoint faz UPDATE WHERE status='preview_pronto'
- Endpoint enfileira _render_task na task_queue
- idiomas_renderizar exclui o idioma do preview
- Worker inicia a task (visível nos logs)

---

## AÇÃO 2 — `_render_task` calcula faltantes + verificação R2
**Prioridade:** CRÍTICA — recovery + salvamento correto
**Tipo:** Backend (pipeline.py)
**Deploy:** SIM, imediato após implementação

**Prompt para o Claude Code:**
```
Leia PLANO-FINAL-v2-TELA-EDITOR.md na raiz do repo para contexto.
Depois leia app-editor/backend/app/routes/pipeline.py.

Encontre a função _render_task(edicao_id, idiomas_renderizar=None,
is_preview=False).

PARTE A — CÁLCULO DE FALTANTES:
Quando idiomas_renderizar=None (caso do requeue_stale_tasks após
restart), a task DEVE calcular automaticamente:
1. Abrir sessão curta no banco
2. Ler renders já concluídos (tabela Render, status="concluido",
   para este edicao_id)
3. Calcular: faltantes = {"en","pt","es","de","fr","it","pl"} - já_concluídos
4. Se faltantes vazio → setar status "concluido" e sair
5. Se não → renderizar só os faltantes

Se a task NÃO faz isso, corrija.

PARTE B — ESTRUTURA R2 (SALVAMENTO CORRETO):
Verificar que o upload pro R2 segue esta estrutura EXATA:

  Chave R2: {r2_base}/{idioma}/video_{idioma}.mp4

  Onde r2_base é formado como: editor/{artista} - {musica}
  (ou o valor que está salvo em edicao.r2_base)

  Exemplo para "Pavarotti - Nessun Dorma":
    editor/Pavarotti - Nessun Dorma/en/video_en.mp4
    editor/Pavarotti - Nessun Dorma/pt/video_pt.mp4
    editor/Pavarotti - Nessun Dorma/es/video_es.mp4
    editor/Pavarotti - Nessun Dorma/de/video_de.mp4
    editor/Pavarotti - Nessun Dorma/fr/video_fr.mp4
    editor/Pavarotti - Nessun Dorma/it/video_it.mp4
    editor/Pavarotti - Nessun Dorma/pl/video_pl.mp4

Se a estrutura R2 estiver diferente disso, corrija.
Se r2_base não está sendo setado na edição, identifique onde deveria
ser setado (provavelmente no passo de download ou importação) e
corrija.

PARTE C — TIMEOUT FFMPEG:
Confirme que asyncio.wait_for(timeout=600) + processo.kill() está
presente em TODOS os caminhos de chamada do FFmpeg, incluindo
is_preview=True.

Padrões obrigatórios:
- Sessões curtas de banco (fechar antes de chamar FFmpeg)
- Imports dentro do try-except
- except BaseException
- Heartbeat antes de cada render

Não mude nada no frontend. Não mude nenhum outro endpoint.
Faça commit com mensagem em português e deploy.
```

**Teste após deploy:**
```bash
# Forçar restart do container (deploy vazio ou restart no Railway)
# Verificar nos logs: "requeue: edicao_id=X reagendada"
# Se havia renders parciais, verificar que só os faltantes são refeitos
# Verificar no R2 que os paths seguem a estrutura correta
```

**Critério de aceite:**
- Com idiomas_renderizar=None, task calcula faltantes automaticamente
- Se todos já renderizados, seta "concluido" sem refazer
- Estrutura R2 segue {r2_base}/{idioma}/video_{idioma}.mp4
- r2_base está corretamente preenchido na edição
- Timeout FFmpeg presente em todos os caminhos

---

## AÇÃO 3 — Preview PT salvo no R2
**Prioridade:** ALTA
**Tipo:** Backend (pipeline.py)
**Deploy:** SIM, imediato após implementação

**Prompt para o Claude Code:**
```
Leia PLANO-FINAL-v2-TELA-EDITOR.md na raiz do repo para contexto.
Depois leia app-editor/backend/app/routes/pipeline.py.

Na função _render_task, quando is_preview=True:
1. O vídeo renderizado é uploaded para o R2?
2. O registro Render é salvo no banco com o path R2 correto?
3. O arquivo local é deletado após upload?

O vídeo do preview (PT) PRECISA ir pro R2 na mesma estrutura:
{r2_base}/pt/video_pt.mp4

E o registro Render PRECISA existir no banco com:
- edicao_id = ID da edição
- idioma = "pt" (ou o idioma do preview)
- status = "concluido"
- arquivo = path R2 completo

Se o upload pro R2 NÃO acontece quando is_preview=True, corrija
para seguir EXATAMENTE o mesmo fluxo do render normal:
FFmpeg → upload R2 → salvar Render no banco → deletar local.

IMPORTANTE: Se o registro Render do preview já existir no banco
quando o render final rodar (Ação 2, cálculo de faltantes), o
PT será corretamente pulado. Isso é a idempotência funcionando.

Deploy no Railway com disco efêmero. Sem R2, o vídeo se perde
no restart.

Não mude nada no frontend. Não mude outros fluxos.
Faça commit com mensagem em português e deploy.
```

**Teste após deploy:**
```bash
# Renderizar preview de uma edição
curl -X POST .../edicoes/{id}/renderizar-preview
# Aguardar conclusão
# Verificar:
curl .../edicoes/{id}/renders
# Deve ter 1 render (PT) com status "concluido" e arquivo com path R2
# Verificar no dashboard R2: arquivo existe em {r2_base}/pt/video_pt.mp4
```

---

## AÇÃO 4 — Cleanup sequencial por idioma
**Prioridade:** ALTA
**Tipo:** Backend (pipeline.py)
**Deploy:** SIM, imediato após implementação

**Prompt para o Claude Code:**
```
Leia PLANO-FINAL-v2-TELA-EDITOR.md na raiz do repo para contexto.
Depois leia app-editor/backend/app/routes/pipeline.py, função _render_task.

Dentro do loop que renderiza cada idioma, confirme que a ordem é:
1. Heartbeat no banco (sessão curta)
2. Gerar arquivo ASS (legendas) — temporário
3. FFmpeg renderiza vídeo → arquivo local temporário
4. Upload do arquivo de vídeo para R2
5. Deletar arquivo de VÍDEO local (os.remove ou Path.unlink)
6. Deletar arquivo ASS temporário
7. Salvar registro Render no banco (sessão curta)
8. SÓ ENTÃO passar para o próximo idioma

Regra: NUNCA devem existir 2 vídeos renderizados no disco ao mesmo
tempo. Disco Railway ~1-2GB livre. Cada vídeo 50-100MB.

Se o cleanup NÃO acontece antes do próximo idioma, corrija a ordem.
Garanta que TODOS os arquivos temporários (vídeo + ASS) são limpos.

TAMBÉM: adicionar try/except nos os.remove para que falha de
limpeza não interrompa o processamento dos próximos idiomas.
Logar warning se não conseguir deletar.

Não mude nada no frontend.
Faça commit com mensagem em português e deploy.
```

**Teste após deploy:**
```bash
# Monitorar logs durante render de múltiplos idiomas
# Verificar que cada idioma logga: "upload R2 ok" → "arquivo local deletado"
# Verificar que disco não acumula arquivos
```

---

## AÇÃO 5 — Frontend: botão "Aprovar e Renderizar" + polling de renders
**Prioridade:** ALTA
**Tipo:** Frontend (conclusion.tsx + editor.ts)
**Deploy:** NÃO — aguardar Ações 6, 7 e 8 para deploy único do frontend

**Prompt para o Claude Code:**
```
Leia PLANO-FINAL-v2-TELA-EDITOR.md na raiz do repo para contexto.
Depois leia:
- app-portal/components/editor/conclusion.tsx
- app-portal/lib/api/editor.ts
- app-portal/lib/hooks/use-polling.ts

PARTE 1 — BOTÃO "APROVAR E RENDERIZAR TODOS":
- Visível quando status == "preview_pronto"
- Ao clicar, chama editorApi.aprovarPreview(edicaoId)
  (NÃO editorApi.renderizar — o backend já enfileira após aprovar)
- Após clicar, desabilita o botão e mostra loading "Renderizando..."
- Se API retornar 409, mostrar toast/mensagem amigável de conflito
- Se API retornar outro erro, mostrar erro_msg

PARTE 2 — POLLING DE RENDERS:
- Quando status == "renderizando", ALÉM do polling normal da edição,
  fazer polling em editorApi.listarRenders(edicaoId) no mesmo intervalo
- Usar a lista de renders para mostrar status por idioma na tabela:
  - Render com status "concluido" → ícone verde ✓ + botão "Baixar"
  - Render com status "erro" → ícone vermelho ✗ + mensagem do erro
  - Idioma sem render ainda → "Pendente" em cinza
- O polling de renders PARA quando status da edição muda para
  "concluido" ou "erro"
- Se lista de renders vazia (nenhum concluiu ainda) → todos "Pendente"

Os 7 idiomas são: en, pt, es, de, fr, it, pl
Usar as bandeiras que já existem no componente.

NÃO faça deploy ainda — aguarde as Ações 6, 7 e 8.
NÃO mude nada no backend. NÃO mude o useAdaptivePolling existente.
Faça commit com mensagem em português (sem deploy).
```

---

## AÇÃO 6 — Frontend: downloads individuais + substituir player
**Prioridade:** MÉDIA
**Tipo:** Frontend (conclusion.tsx)
**Deploy:** NÃO — aguardar Ações 7 e 8 para deploy único

**Prompt para o Claude Code:**
```
Leia PLANO-FINAL-v2-TELA-EDITOR.md na raiz do repo para contexto.
Depois leia app-portal/components/editor/conclusion.tsx e
app-portal/lib/api/editor.ts.

PARTE 1 — DOWNLOADS POR IDIOMA:
Para cada render com status "concluido" na lista de idiomas,
mostrar botão "Baixar" que abre em nova aba:
editorApi.downloadRenderUrl(edicaoId, renderId)

Usar: <a href={url} target="_blank" rel="noopener">Baixar</a>

PARTE 2 — SUBSTITUIR PLAYER EMBARCADO:
Remover QUALQUER componente de player de vídeo embarcado
(<video>, <iframe>, ou similar) usado para o preview.
Substituir por botão "Baixar Preview" que faz download do
render PT (mesmo mecanismo do item 1).

NÃO faça deploy ainda — aguarde as Ações 7 e 8.
NÃO mude nada no backend. NÃO mude lógica de polling.
Faça commit com mensagem em português (sem deploy).
```

---

## AÇÃO 7 — Frontend: "Baixar Todos"
**Prioridade:** BAIXA
**Tipo:** Frontend (conclusion.tsx)
**Deploy:** NÃO — aguardar Ação 8 para deploy único

**Prompt para o Claude Code:**
```
Leia PLANO-FINAL-v2-TELA-EDITOR.md na raiz do repo para contexto.
Depois leia app-portal/components/editor/conclusion.tsx e
app-portal/lib/api/editor.ts.

Quando TODOS os 7 renders estiverem com status "concluido":
- Mostrar botão "Baixar Todos" (destaque visual, botão primário)
- Ao clicar, tentar chamar editorApi.pacoteUrl(edicaoId) para ZIP
- Se funcionar, abrir URL do ZIP em nova aba
- Se der erro (endpoint não existe ou falha), FALLBACK:
  abrir as 7 URLs uma a uma com 500ms de delay:

  renders.forEach((render, i) => {
    setTimeout(() => window.open(downloadUrl(render), '_blank'), i * 500)
  })

NÃO faça deploy ainda — aguarde a Ação 8.
NÃO mude nada no backend.
Faça commit com mensagem em português (sem deploy).
```

---

## AÇÃO 8 — Frontend: rotas de fuga e recovery na UI
**Prioridade:** ALTA — evita o problema recorrente de "travar e ter que resetar"
**Tipo:** Frontend (conclusion.tsx)
**Deploy:** SIM — agora sim, deploy do frontend com Ações 5+6+7+8 juntas

**Contexto:** Hoje, quando algo dá errado na tela final, o operador
não tem opção na UI. Precisa ir no banco ou pedir pro desenvolvedor.
Esta ação adiciona TODAS as rotas de fuga necessárias para que o
operador resolva sozinho.

**Prompt para o Claude Code:**
```
Leia PLANO-FINAL-v2-TELA-EDITOR.md na raiz do repo para contexto.
Depois leia app-portal/components/editor/conclusion.tsx e
app-portal/lib/api/editor.ts.

Adicionar os seguintes mecanismos de recovery na tela de conclusão:

1. BOTÃO "DESBLOQUEAR" (recovery principal):
   - Visível quando status == "erro"
   - TAMBÉM visível quando status está em "traducao", "renderizando"
     ou "preview" E o task_heartbeat é mais antigo que 5 minutos
     (comparar com Date.now())
   - Ao clicar, chama editorApi.desbloquear(edicaoId)
   - Após resposta, recarrega dados da edição (polling imediato)
   - Texto do botão: "Desbloquear Edição"
   - Estilo: botão outline/secundário com ícone de cadeado

2. BOTÃO "REFAZER TRADUÇÃO":
   - Visível quando status == "montagem" ou "erro"
   - Ao clicar, chama editorApi.traduzirLyrics(edicaoId)
   - Isso permite refazer traduções sem ter que resetar tudo

3. BOTÃO "REFAZER PREVIEW":
   - Visível quando status == "preview_pronto" ou "erro"
   - Ao clicar, primeiro chama editorApi.desbloquear(edicaoId)
     para voltar ao status correto, depois
     editorApi.renderizarPreview(edicaoId)
   - Permite re-gerar o preview se ficou ruim na revisão

4. MENSAGEM DE ERRO CONTEXTUAL:
   - Quando status == "erro", mostrar edicao.erro_msg em um banner
     vermelho/rosa claro
   - Abaixo do erro, mostrar os botões de recovery relevantes:
     - Se erro_msg contém "tradução" ou "traducao" → "Refazer Tradução"
     - Se erro_msg contém "render" ou "FFmpeg" → "Desbloquear"
     - Sempre mostrar "Desbloquear" como opção

5. INDICADOR DE HEARTBEAT STALE:
   - Se status é ativo (traducao/renderizando/preview) E
     task_heartbeat é mais antigo que 5 minutos:
   - Mostrar banner amarelo: "O processamento parece travado.
     Último sinal há X minutos."
   - Mostrar botão "Desbloquear Edição"

6. VOLTAR PARA ETAPAS ANTERIORES:
   - Quando status == "erro" ou "montagem", mostrar link discreto
     "← Voltar para Alinhamento" que navega para o passo 4
   - Isso permite que o operador corrija o alinhamento se o
     problema estiver nos dados de entrada, sem resetar tudo

LAYOUT: Os botões de recovery ficam em uma seção separada abaixo
dos botões principais, com título "Opções de recovery" ou
"Resolver problemas". Não devem competir visualmente com o
fluxo principal (Traduzir → Preview → Aprovar → Baixar).

AGORA SIM: faça commit com mensagem em português e DEPLOY.
Este deploy inclui as Ações 5, 6, 7 e 8 do frontend.
```

**Critério de aceite:**
- Em status "erro": banner com mensagem + botões de recovery visíveis
- Em status ativo com heartbeat >5min: banner amarelo + Desbloquear
- Botão "Desbloquear" funciona e recarrega a tela
- Botão "Refazer Tradução" funciona a partir de montagem/erro
- Botão "Refazer Preview" funciona a partir de preview_pronto/erro
- Link "Voltar para Alinhamento" funciona

---

## AÇÃO 9 — Defesa contra disco cheio (sugestão Gemini)
**Prioridade:** MÉDIA — prevenção
**Tipo:** Backend (pipeline.py)
**Deploy:** SIM, imediato

**Prompt para o Claude Code:**
```
Leia PLANO-FINAL-v2-TELA-EDITOR.md na raiz do repo para contexto.
Depois leia app-editor/backend/app/routes/pipeline.py, função _render_task.

Adicionar verificação de espaço em disco ANTES de cada FFmpeg,
dentro do loop de idiomas:

import shutil
uso = shutil.disk_usage("/")
livre_mb = uso.free / (1024 * 1024)
if livre_mb < 200:
    # Tentar limpar lixo antes de desistir
    import glob
    for f in glob.glob("/tmp/*.mp4") + glob.glob("/tmp/*.ass"):
        try:
            os.remove(f)
        except:
            pass
    uso = shutil.disk_usage("/")
    livre_mb = uso.free / (1024 * 1024)
    if livre_mb < 200:
        raise RuntimeError(f"Espaço em disco insuficiente: {livre_mb:.0f}MB livre")

Threshold: 200MB. Se não tiver espaço, task vai pra "erro" com
mensagem clara em vez de falhar misteriosamente.

TAMBÉM: adicionar limpeza preventiva de /tmp no INÍCIO da
_render_task (antes do loop), removendo *.mp4 e *.ass residuais
de execuções anteriores que crasharam.

Não mude nada no frontend.
Faça commit com mensagem em português e deploy.
```

---

## AÇÃO 10 — Dead-letter: evitar crash-loop (sugestão Gemini)
**Prioridade:** MÉDIA — prevenção
**Tipo:** Backend (models + worker + pipeline)
**Deploy:** SIM, imediato

**Prompt para o Claude Code:**
```
Leia PLANO-FINAL-v2-TELA-EDITOR.md na raiz do repo para contexto.

Implementar dead-letter simples para evitar que uma edição que
sempre falha entre em loop infinito de tentativas a cada restart:

1. MIGRATION — Em app/main.py, _run_migrations(), adicionar:
   ("tentativas_requeue", "INTEGER DEFAULT 0")

2. MODELO — Em app/models/edicao.py, adicionar:
   tentativas_requeue = Column(Integer, default=0)

3. REQUEUE — Em app/worker.py, requeue_stale_tasks():
   - Antes de reenfileirar, checar: se edicao.tentativas_requeue >= 3,
     NÃO reenfileirar. Setar status="erro" com erro_msg=
     "Falha após 3 tentativas de recovery automático. Use
     Desbloquear para retry manual."
     Logar logger.warning com a info.
   - Se reenfileirar, incrementar tentativas_requeue += 1 e commit.

4. RESET DO CONTADOR — Quando task conclui com sucesso:
   - Em _render_task, ao setar "concluido" ou "preview_pronto":
     edicao.tentativas_requeue = 0
   - Em _traducao_task, ao setar "montagem":
     edicao.tentativas_requeue = 0
   - No endpoint /desbloquear: resetar tentativas_requeue = 0
     (permite retry manual limpo após dead-letter)

5. SCHEMA — Adicionar tentativas_requeue ao EdicaoOut em schemas.py.

Não mude nada no frontend.
Faça commit com mensagem em português e deploy.
```

---

## AÇÃO 11 — Limpeza: remover endpoint perigoso
**Prioridade:** BAIXA (segurança)
**Tipo:** Backend
**Deploy:** SIM, imediato

**Prompt para o Claude Code:**
```
Em app-editor/backend/app/routes/ (pipeline.py ou edicoes.py):
encontre e remova o endpoint POST /admin/reset-total.
Este é um endpoint temporário de testes que zera TODOS os dados
do editor. Não deve existir em produção.

Remova o endpoint, a função handler, e qualquer import associado.

Não mude nenhuma lógica de negócio.
Faça commit com mensagem em português e deploy.
```

---

## VALIDAÇÃO FINAL — Teste end-to-end completo

**Executar após TODAS as ações deployadas.**
**Manter logs do Railway abertos em aba separada durante todo o teste.**

```
═══════════════════════════════════════════════════════
 TESTE 1 — FLUXO COMPLETO (música NÃO em português)
═══════════════════════════════════════════════════════

1. Importar ou criar edição nova (música em italiano, por exemplo)

2. Processar passos 1-5 normalmente:
   download → letra → transcrição → alinhamento → corte

3. Na tela final, clicar "Traduzir"
   ✅ Progresso mostra "Traduzindo: 1/7, 2/7... 7/7"
   ✅ Status muda para "montagem" ao terminar
   ✅ Logs: nenhum erro, heartbeat atualizado a cada idioma

4. Clicar "Renderizar Preview"
   ✅ Progresso mostra "Renderizando preview PT..."
   ✅ Status muda para "preview_pronto"
   ✅ Botão "Baixar Preview" aparece (NÃO player embarcado)
   ✅ R2: existe {r2_base}/pt/video_pt.mp4
   ✅ Banco: registro Render com idioma=pt, status=concluido

5. Baixar preview PT e verificar no VLC/QuickTime:
   ✅ Overlay (texto editorial) no TOPO do frame 9:16
   ✅ Lyrics (transcrição original) na BASE
   ✅ Tradução PT ACIMA dos lyrics
   ✅ Nenhuma legenda sobre o vídeo 16:9 centralizado
   Se posição errada → ajustar marginv em legendas.py

6. Clicar "Aprovar e Renderizar Todos"
   ✅ Status muda para "renderizando"
   ✅ Progresso mostra idiomas sendo renderizados
   ✅ Lista de idiomas atualiza: ✓ verde conforme cada um conclui
   ✅ Botão "Baixar" aparece por idioma conforme conclui
   ✅ PT já aparece como concluído desde o início (era o preview)
   ✅ Logs: cleanup de arquivo local após cada upload R2
   ✅ Logs: nunca 2 vídeos no disco ao mesmo tempo

7. Quando todos concluídos (status = "concluido"):
   ✅ Todos os 7 botões "Baixar" funcionam
   ✅ Botão "Baixar Todos" aparece
   ✅ Baixar vídeo EN → verificar legendas em inglês
   ✅ Baixar vídeo DE → verificar legendas em alemão

8. Verificar R2 — estrutura correta:
   ✅ {r2_base}/en/video_en.mp4
   ✅ {r2_base}/pt/video_pt.mp4
   ✅ {r2_base}/es/video_es.mp4
   ✅ {r2_base}/de/video_de.mp4
   ✅ {r2_base}/fr/video_fr.mp4
   ✅ {r2_base}/it/video_it.mp4
   ✅ {r2_base}/pl/video_pl.mp4

═══════════════════════════════════════════════════════
 TESTE 2 — RECOVERY E ROTAS DE FUGA
═══════════════════════════════════════════════════════

9. TESTE HEARTBEAT STALE:
   - Iniciar render e esperar 6 minutos sem progresso (simular travando)
   ✅ Banner amarelo aparece: "processamento parece travado"
   ✅ Botão "Desbloquear" aparece
   ✅ Clicar Desbloquear → status volta para estado inferido correto

10. TESTE DESBLOQUEAR DE ERRO:
    - Se alguma edição estiver em "erro":
    ✅ Banner vermelho mostra a mensagem de erro
    ✅ Botões de recovery visíveis (Desbloquear, Refazer Tradução, etc.)
    ✅ Clicar Desbloquear → status volta ao ponto correto
    ✅ Clicar Refazer Tradução → tradução reinicia

11. TESTE REFAZER PREVIEW:
    - Com edição em "preview_pronto":
    ✅ Botão "Refazer Preview" visível
    ✅ Clicar → preview é re-renderizado
    ✅ Novo preview sobe pro R2

12. TESTE RECOVERY PÓS-RESTART:
    - Durante render dos 6 idiomas, forçar restart do container
    ✅ Logs pós-restart: "requeue: edicao_id=X reagendada"
    ✅ tentativas_requeue incrementou
    ✅ Render continua do idioma onde parou (não refaz concluídos)
    ✅ Frontend reconecta e mostra progresso

13. TESTE DEAD-LETTER:
    - Se possível, causar 3 restarts com mesma edição ativa
    ✅ Na 4ª vez: edição vai pra "erro" com mensagem dead-letter
    ✅ /desbloquear reseta contador e permite retry limpo
    ✅ tentativas_requeue volta a 0

═══════════════════════════════════════════════════════
 TESTE 3 — EDGE CASES
═══════════════════════════════════════════════════════

14. DOUBLE-CLICK:
    - Clicar "Traduzir" duas vezes rápido
    ✅ Segundo clique retorna 409, não duplica task

15. SISTEMA OCUPADO:
    - Iniciar tradução na edição A
    - Abrir edição B e tentar traduzir
    ✅ Banner âmbar: "Sistema ocupado com outra edição"
    ✅ Task B entra na fila e espera

16. EDIÇÃO INSTRUMENTAL:
    - Processar uma edição com eh_instrumental=True
    ✅ Tradução é pulada (sem letra)
    ✅ Preview renderiza sem legendas de lyrics
```

---

## MAPA DE DEPENDÊNCIAS E DEPLOYS

```
                     BACKEND (deploy individual)
                     ═══════════════════════════
AÇÃO 0 (curl manual) ─── imediato, sem código

AÇÃO 1 (aprovar-preview) ──→ deploy → testar
          │
AÇÃO 2 (faltantes + R2) ──→ deploy → testar
          │
AÇÃO 3 (preview R2) ──────→ deploy → testar
          │
AÇÃO 4 (cleanup) ─────────→ deploy → testar
          │
          ▼
                     FRONTEND (deploy único)
                     ═══════════════════════
          ├── AÇÃO 5 (botão + polling) ── commit
          ├── AÇÃO 6 (downloads) ──────── commit
          ├── AÇÃO 7 (baixar todos) ───── commit
          └── AÇÃO 8 (rotas de fuga) ──── commit + DEPLOY
                     │
                     ▼
                     PREVENÇÃO (deploy individual)
                     ════════════════════════════
          AÇÃO 9  (disco cheio) ──→ deploy
          AÇÃO 10 (dead-letter) ──→ deploy
          AÇÃO 11 (limpeza) ──────→ deploy
                     │
                     ▼
               VALIDAÇÃO FINAL (teste manual)
```

---

## BUGS JÁ CORRIGIDOS (NÃO REPETIR)

1. ✅ Import fora do try-except nas tasks
2. ✅ Worker não setava status="erro" em falha
3. ✅ CancelledError não capturado (except Exception)
4. ✅ requeue_stale_tasks checava heartbeat no startup
5. ✅ progresso_detalhe e task_heartbeat não expostos na API
6. ✅ Idioma hardcoded como "it"
7. ✅ Preview renderizava no idioma da música (não PT)
8. ✅ Legenda fantasma no segundo 0
9. ✅ Timeout de tradução curto (30s → 180s)

---

## SUGESTÃO DESCARTADA

**"Timeout no FFmpeg" (Gemini)** — Já existe no sistema:
asyncio.wait_for(timeout=600) + processo.kill(). A Ação 2
confirma que está presente em todos os caminhos.
