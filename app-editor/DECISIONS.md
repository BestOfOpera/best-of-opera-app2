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
