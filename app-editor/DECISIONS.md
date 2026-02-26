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
