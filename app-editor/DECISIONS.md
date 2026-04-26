# Decisões Técnicas — APP Editor

## 1. SQLite para dev local, PostgreSQL para produção
- Usamos JSON em vez de JSONB/ARRAY nos models para compatibilidade
- Em produção, o SQLAlchemy funciona identicamente com PostgreSQL
- O banco é criado automaticamente via `Base.metadata.create_all()`

## 2. Backend e Frontend separados
- Backend: FastAPI na porta 8001 (local) / 8000 (produção)
- Frontend: Vite React na porta 5174 (local) / Nginx (produção)
- Proxy de API configurado no vite.config.js para dev

## 3. Tailwind CSS v3 (CJS configs)
- tailwind.config.cjs e postcss.config.cjs em formato CommonJS
- Necessário por compatibilidade com o Node.js instalado

## 4. Background tasks do FastAPI
- Download, transcrição, tradução e renderização rodam em background
- O frontend faz polling a cada 5s durante processos longos

## 5. Gemini API para transcrição e tradução
- google-generativeai SDK
- Lazy init do client para não falhar sem API key em dev

## 6. Anti-duplicata na importação do Redator
- **Camada 1 (API):** Endpoint `POST /redator/importar/{project_id}` verifica se `redator_project_id` já existe em `editor_edicoes` antes de criar. Retorna 409 com ID da edição existente.
- **Camada 2 (DB):** Migration cria `UNIQUE INDEX` parcial em `redator_project_id` (onde NOT NULL). Verifica duplicatas antes de criar — se existirem, loga warning e NÃO cria o index.
- **Camada 3 (Listagem):** `GET /redator/projetos` retorna `editor_status` ("em_andamento"/"concluido"/null) e `editor_edicao_id` cruzando com `editor_edicoes`.
- **Frontend:** Badges visuais (verde/amarelo/cinza) por status, botão desabilitado para projetos já importados, modal de aviso ao tentar duplicar com link para edição existente.
- **Motivação:** Caso real — "Stand by Me" importado como edição 39 e 40, causando confusão e worker bloqueado.

## 7. Fix posicionamento de legendas (tradução × lyrics)

**Problema:** Em vídeos com tradução longa (ex: alemão), as legendas de tradução (branco) e lyrics (amarelo) trocavam de posição visual — tradução crescia "para cima" e invadia o espaço do lyrics.

**Causa raiz (2 problemas):**
1. Ordem invertida: lyrics (marginv=580) estava mais próximo do vídeo que tradução (marginv=520)
2. Sem word-wrap: textos longos geravam múltiplas linhas que se sobrepunham

**Solução implementada (2 frentes):**

### Frente A — Word-wrap (`_formatar_texto_legenda`)
- Nova função em `legendas.py`: `_formatar_texto_legenda(texto, max_chars=40, max_linhas=2)`
- Quebra texto com `\N` (line break ASS) respeitando limites de palavras
- Aplicada em TODOS os eventos: overlay (max_chars=35), lyrics e tradução (max_chars=40)

### Frente B — Posicionamento fixo (marginv swap + gap)
- **Tradução (branco):** marginv=570 (era 520) → primeiro abaixo do vídeo, y≈1350
- **Lyrics (amarelo):** marginv=410 (era 580) → segundo, mais embaixo, y≈1510
- Gap entre eles: 160px (era 60px) — espaço suficiente para 2 linhas em cada track

### Layout final (de cima para baixo no frame 9:16)
```
Barra preta superior
Overlay (branco, marginv=490, alignment=8)
Vídeo 16:9 (y=656 a y=1264)
Tradução (branco, marginv=570, alignment=2) ← primeiro
Lyrics (amarelo, marginv=410, alignment=2) ← segundo
Barra preta inferior
```

### Teste visual (FFmpeg)
- Testado com 3 cenários: texto curto (1 linha), médio (2 linhas), longo (2 linhas em ambos)
- Tradução DE com 71 chars: "Also Liebling, Liebling, steh mir bei, oh steh mir bei, oh steh mir bei"
- Confirmado: sem sobreposição, sem invasão do vídeo, ordem correta

## 8. Badge unificado na tela de importação (editor_status)

**Problema:** Na listagem de projetos do Redator, o badge "Pronto" (status export_ready do Redator) era ambíguo — parecia "pronto para importar" mas significava "concluído no Redator". Projetos já editados no Editor não tinham marcação clara, e o operador não sabia quais já foram importados/concluídos.

**Solução:** Badge unificado que prioriza o status no Editor sobre o status no Redator:

| editor_status | Badge | Cor | Botão |
|---|---|---|---|
| null + export_ready | "Disponível para edição" | Verde | Importar |
| null + outro status | Label original do Redator | Padrão | Importar |
| "em_andamento" | "Em edição #XX" (link) | Âmbar | "Ir para edição #XX" |
| "concluido" | "Concluído ✓" | Cinza | Desabilitado |

- Projetos concluídos ficam com opacidade reduzida (50%)
- Projetos em andamento ficam levemente esmaecidos (80%)
- Link do badge "Em edição" e botão apontam para `/editor/edicao/{id}/conclusao`
- Backend já retornava `editor_status` e `editor_edicao_id` (Decisão 6, Camada 3)

## 9. Fix marginv lyrics/traducao — legendas na barra preta inferior, simétricas ao overlay

**Problema anterior (commit errado):** Decisão 9 anterior usava marginv=680/620, que colocava
as legendas DENTRO do vídeo (y_base=1240/1300, ambos acima de y=1264 que é a base do vídeo).
O objetivo era descer as legendas para a barra preta, mas o commit fez o oposto — subiu.

**Geometria confirmada:**
```
Frame:           1080 × 1920 (9:16)
Vídeo 16:9:      1080 × 608
Topo vídeo:      y = 656
Base vídeo:      y = 1264
Barra preta inf: y = 1264..1920 (656px de espaço)
```

**Constraints de layout:**
- Todas as 3 tracks têm max 2 linhas (overlay via `quebrar_texto_overlay`, lyrics/traducao via `_formatar_texto_legenda(max_linhas=2)`)
- fontsize=35 + outline=2 → altura por linha ≈ 42px, 2 linhas = 84px
- alignment=2 (bottom-center): `y_base = 1920 - marginv`, texto cresce para cima

**Referência de simetria — overlay (topo):**
- overlay: alignment=8, marginv=530 (era 490, corrigido separadamente)
- Com 2 linhas (~94px): base do overlay em y≈584
- Gap entre base do overlay e topo do vídeo (656): ~72px

**Solução — simetria exata com overlay:**

| Track | marginv | y_base | 2 linhas topo | Gap ao vídeo (1264) | Gap entre tracks |
|-------|---------|--------|---------------|---------------------|------------------|
| lyrics (amarelo) | **500** | 1420 | 1336 | **72px** ← simétrico ao overlay | — |
| traducao (branco) | **380** | 1540 | 1456 | — | 36px abaixo do lyrics |

**Verificação:**
- lyrics 2 linhas: topo em 1336, gap ao vídeo = 1336-1264 = 72px ✓ (= overlay gap)
- lyrics 1 linha: topo em 1378, gap = 114px ✓
- traducao 2 linhas: topo em 1456, gap ao lyrics base (1420) = 36px ✓
- traducao fundo: 1920-1540 = 380px de folga ✓
- **Overlay não alterado** (marginv=530, alignment=8, topo)

## 10. Fonte menor (30) e margens mais justas para lyrics/traducao

**Motivação:** fontsize=35 ocupava espaço demais na barra preta inferior. Reduzir para 30 permite aproximar as legendas da base do vídeo, melhorando a legibilidade e o aproveitamento visual.

**Alterações em ESTILOS_PADRAO:**

| Track | fontsize | marginv | y_base | 2 linhas topo | Gap ao vídeo (1264) |
|-------|----------|---------|--------|---------------|---------------------|
| lyrics (amarelo) | 35→**30** | 500→**554** | 1366 | 1294 | **30px** |
| traducao (branco) | 35→**30** | 380→**452** | 1468 | 1396 | 30px ao lyrics base |

**Geometria (fontsize=30 + outline=2):**
- Altura por linha ≈ 36px (era 42px com fontsize=35)
- 2 linhas = 72px por track (era 84px)
- Gap entre lyrics base (1366) e traducao topo com 2 linhas (1396) = 30px
- Gap entre lyrics topo com 2 linhas (1294) e base do vídeo (1264) = 30px

**Overlay NÃO alterado** (fontsize=47, marginv=530).

## 11. Overlay congelado na importação (2026-03-03)

**Problema:** O vídeo renderizado exibia texto de overlay diferente do aprovado pelo operador.

**Causa raiz (3 bugs combinados):**
1. **Bug de `None` vs `[]`**: Na `_render_task`, a expressão
   `overlay.segmentos_reindexado if overlay else []` avaliava para `None`
   quando o overlay existia mas `segmentos_reindexado` era NULL (antes de
   `aplicar_corte` rodar ou se este falhasse). Isso causava crash ou overlay
   vazio no render.
2. **Sem fallback**: Se `segmentos_reindexado` não estava populado, não havia
   fallback para `segmentos_original` (o campo congelado na importação).
3. **Sem rastreabilidade**: Nenhum log registrava qual texto de overlay era
   usado em cada render, impossibilitando diagnóstico.

**Correção aplicada:**
- `_render_task` agora usa `segmentos_reindexado` com fallback para
  `segmentos_original`. Se ambos forem NULL, falha com erro claro:
  "Overlay não encontrado — reimporte o projeto".
- Log explícito no início de cada render por idioma com o texto exato do overlay.
- Log na importação (`importar.py`) registrando o texto congelado.
- Log de alerta em `aplicar_corte` se `normalizar_segmentos` alterar texto.
- `redator_project_id` agora é salvo na importação para rastreabilidade.

**Princípio:** O overlay é IMUTÁVEL após importação. O Editor nunca re-busca
overlay do Redator durante render — lê exclusivamente do banco local
(`editor_overlays.segmentos_original` / `segmentos_reindexado`).

## 12. Toggle "Sem legendas de transcrição" (sem_lyrics) (2026-03-03)

**Motivação:** Músicas instrumentais ou com texto mínimo repetitivo (ex: "Ave Maria")
não precisam de legendas de letra (amarelo) nem tradução (branco) — apenas o overlay
editorial no topo.

**Implementação (4 partes):**

### Banco de dados
- Novo campo `sem_lyrics` (Boolean, default=False) em `editor_edicoes`
- Migration automática em `_run_migrations()`: `ALTER TABLE ... ADD COLUMN sem_lyrics BOOLEAN DEFAULT FALSE`
- Exposto em `EdicaoOut` e `EdicaoUpdate` (schemas Pydantic)

### Serviço de legendas
- `gerar_ass()` recebe parâmetro `sem_lyrics: bool = False`
- Quando True: gera apenas a track de overlay (topo), retorna antes de criar tracks de lyrics/tradução
- Quando False: comportamento inalterado (3 tracks)

### Task de render
- `_render_task` lê `edicao.sem_lyrics` no Passo A (sessão curta)
- Passa para `gerar_ass(sem_lyrics=sem_lyrics_val)`

### Frontend (Portal)
- Toggle "Sem legendas de transcrição" na página de conclusão, persistido via PATCH
- Estado carregado do campo `sem_lyrics` da edição
- Tooltip: "Ative para músicas instrumentais ou com texto mínimo repetitivo"

**Distinção de `sem_legendas` (existente):**
- `sem_lyrics=True`: mantém overlay, omite lyrics+tradução (ASS com 1 track)
- `sem_legendas=True`: remove TODAS as legendas (sem ASS, apenas scale+pad)

## 13. Fix collision detection libass + calibração final do posicionamento RC (2026-04-26)

**Problema:** Após as migrations v12 (`gap_from_image: 4→0`, `inter_line_gap: 2→-10`) e v13 (`inter_line_gap: -10→-25`), o gap visual entre lyrics e tradução continuava grande (~40px medidos) — e qualquer valor mais agressivo de `inter_line_gap` simplesmente não produzia efeito. Adicionalmente, o gap entre a base do vídeo e o topo do lyrics permanecia visível (~28px), apesar de `gap_from_image=0`.

**Causa raiz #1 — collision detection do libass (bug oculto):** em `legendas.py`, os SSAEvent de Lyrics e Tradução eram criados sem setar `event.layer`, ambos caindo em Layer 0 (default do pysubs2). Quando duas legendas em mesma layer ficam próximas, o libass aplica **collision avoidance automático** e força ~40px de gap mínimo, ignorando o `marginv` calculado.

Validação empírica (FFmpeg + libass real + Poppins Bold Italic 58):

| `traducao_marginv` | Mesma layer (atual) | Layers separadas |
|---|---|---|
| 1280 | y=1357 (clipado) | y=1303 (responde) |
| 1314 | y=1357 (clipado) | y=1326 (responde) |
| 1329 | y=1357 (clipado) | y=1341 (responde) |
| 1370 | y=1382 (responde) | y=1382 (responde) |

Conclusão: na configuração atual (`lyrics_marginv≈581`), qualquer `traducao_marginv < 1370` é clipado para y=1357, tornando v12/v13 no-ops visuais.

**Causa raiz #2 — superestimação de text_height:** a fórmula `text_height = int(fontsize_lyrics * 1.3) = 75` (com fontsize=58) é maior que a altura visual real do glyph Poppins renderizado (~50px). Sobra um buffer de ~28px entre a base do vídeo e o topo visual do lyrics, mesmo com `gap_from_image=0`.

**Solução em três frentes:**

### Frente A — Fix de layer (`legendas.py`)
Setar `event_trad.layer = 1` no SSAEvent da tradução. Lyrics permanece em Layer 0 (default). Layers diferentes desativam o collision detection. Single-line change.

### Frente B — Migration v14: `gap_from_image: 0 → -20`
Compensa o buffer de ~28px da text_height superestimada. Cada −1 em `gap_from_image` reduz 1px no gap visual vídeo→amarelo. Resultado: gap cai de 28px para 8px.

### Frente C — Migration v15: `inter_line_gap: -25 → -22`
Recalibração feita DEPOIS do fix de layer (com a layer corrigida, valores respondem linearmente). Resultado: gap amarelo→branco de 12px.

### Configuração unificada de estilo (já no banco desde v6/v7, confirmada)
Lyrics e Tradução têm atributos visuais idênticos. Diferem apenas em `primarycolor` (amarelo `#FFFF00` × branco `#FFFFFF`) e `alignment` (2 × 8). O `alignment` é diferente por necessidade matemática — lyrics ancora pelo bottom (referência base), tradução pelo top (posiciona-se em relação ao lyrics via `traducao_marginv = frame_h − lyrics_marginv + inter_line_gap`).

| Atributo | Lyrics | Tradução |
|---|---|---|
| fontname | Poppins | Poppins |
| fontsize | 58 | 58 |
| outline / outlinecolor | 3 / `#000000` | 3 / `#000000` |
| bold / italic | True / True | True / True |
| primarycolor | `#FFFF00` | `#FFFFFF` |
| alignment | 2 (bottom-center) | 8 (top-center) |
| layer (no event) | 0 (default) | **1** (fix Frente A) |

### Posicionamento final medido (vídeo 16:9 → image_top_px=656, frame 1080×1920)

```
gap_from_image  = -20    (v14)
inter_line_gap  = -22    (v15)

text_height       = 75
lyrics_marginv    = 656 - (-20) - 75 = 601
traducao_marginv  = 1920 - 601 + (-22) = 1297
```

| Métrica | Valor medido |
|---|---|
| Gap vídeo (y=1264) → topo do amarelo | **8 px** |
| Gap baseline do amarelo → topo do branco | **12 px** |
| Altura visual do amarelo | ~26 px |
| Altura visual do branco | ~25 px |

### Limitação conhecida (pré-existente, não introduzida por esta mudança)
Com lyrics em **2 linhas** (`\N`), o texto cresce para cima por causa de alignment=2 e invade o vídeo em ~30px. Isto já acontecia antes das mudanças desta decisão — para o caso típico do RC (lyrics curtos, 1 linha), a configuração funciona cleanly. Tratar em iteração futura adicionando lógica de "se 2 linhas, comprimir text_height" na fórmula.
