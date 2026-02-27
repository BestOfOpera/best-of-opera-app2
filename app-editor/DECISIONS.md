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
