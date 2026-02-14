# BRIEFING CLAUDE CODE — APP EDITOR (APP3)
## Documento de Autonomia Total para Desenvolvimento

**Data:** 13 de Fevereiro de 2026
**Objetivo:** Claude Code deve construir, testar e deployar o APP Editor com autonomia total
**Expectativa:** Acordar amanhã com o app funcionando

---

## CONTEXTO DO PROJETO

### Ecossistema Best of Opera — 3 APPs

Operamos dois perfis de música clássica em redes sociais (Instagram, TikTok, YouTube, Facebook).
Produzimos 50-100 vídeos/mês em 7 idiomas. O ecossistema tem 3 APPs:

```
APP1 CURADORIA (pronto, em produção)
  → Busca e pontua vídeos de ópera no YouTube
  → Stack: FastAPI + PostgreSQL + Railway
  → Repo: [será fornecido]
  → URL: [será fornecido]

APP2 REDATOR (pronto, em produção)  
  → Gera overlay, post e SEO em 7 idiomas
  → Stack: FastAPI + PostgreSQL + Railway
  → Repo: [será fornecido]
  → URL: [será fornecido]

APP3 EDITOR (A CONSTRUIR — este briefing)
  → Download, corte, lyrics, renderização em 7 idiomas
  → Stack: FastAPI + React + PostgreSQL + FFmpeg + Railway
```

### Princípio de Integração Futura

Os 3 APPs hoje funcionam separados mas COMPARTILHAM o mesmo PostgreSQL no Railway.
A integração futura será via banco de dados compartilhado.
Ao construir o Editor, usar a mesma instância PostgreSQL dos outros APPs.
Planejar tabelas com prefixos claros e foreign keys preparadas.

---

## CREDENCIAIS NECESSÁRIAS

**O desenvolvedor (Bolivar) precisa fornecer ANTES de iniciar:**

```
┌─────────────────────────────────────────────────────────────────┐
│  CHECKLIST DE CREDENCIAIS                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. RAILWAY                                                      │
│     □ Railway API Token                                          │
│       → Settings > Tokens > Create Token                         │
│       → Permissão: Full Access                                   │
│       → Formato: rly_xxxxxxxxxxxxxxxxxxxxxxxx                    │
│                                                                  │
│     □ ID do Projeto Railway existente                            │
│       → O projeto onde Curadoria e Redator já rodam              │
│       → Dashboard > Project Settings > Project ID                │
│       → Formato: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx            │
│                                                                  │
│     □ Connection string do PostgreSQL                            │
│       → O mesmo banco usado pela Curadoria e Redator             │
│       → Railway > PostgreSQL service > Connect > DATABASE_URL    │
│       → Formato: postgresql://postgres:xxx@xxx.railway.app:5432/railway │
│                                                                  │
│  2. GEMINI API                                                   │
│     □ API Key do Google AI Studio                                │
│       → https://aistudio.google.com/apikey                       │
│       → Formato: AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX       │
│       → Precisa ter acesso ao Gemini 2.5 Pro                     │
│                                                                  │
│  3. GITHUB                                                       │
│     □ URL do repositório (novo ou existente)                     │
│       → Se novo: Claude Code cria                                │
│       → Se existente: fornecer URL + branch                     │
│     □ GitHub Token (se repo privado)                             │
│       → Settings > Developer Settings > Personal Access Tokens   │
│       → Permissões: repo (full)                                  │
│       → Formato: ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx        │
│                                                                  │
│  4. INFORMAÇÕES DOS APPS EXISTENTES                              │
│     □ Nome do service da Curadoria no Railway                    │
│     □ Nome do service do Redator no Railway                      │
│     □ Tabelas existentes no PostgreSQL                           │
│       → Claude Code vai inspecionar automaticamente              │
│       → Mas se tiver um dump do schema, fornecer                │
│                                                                  │
│  5. OPCIONAL (pode ser configurado depois)                       │
│     □ Domínio customizado (se quiser)                            │
│     □ YouTube API Key (yt-dlp funciona sem, mas com limites)     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## CONFIGURAÇÃO DO CLAUDE CODE

### Permissões e Autonomia

Colar no início da sessão do Claude Code:

```
MODO DE OPERAÇÃO: Autonomia total.

Regras:
1. NÃO peça confirmação pra executar comandos. Execute diretamente.
2. NÃO peça confirmação pra criar/editar arquivos. Faça diretamente.
3. NÃO peça confirmação pra instalar dependências. Instale diretamente.
4. NÃO peça confirmação pra fazer deploy. Faça diretamente.
5. Se encontrar um erro, tente resolver sozinho até 3 vezes antes de perguntar.
6. Documente decisões técnicas em DECISIONS.md no repo.
7. Faça commits frequentes com mensagens descritivas em português.
8. Teste cada componente antes de seguir pro próximo.
9. Se precisar escolher entre opções técnicas, escolha a mais simples que funcione.
10. Mantenha um log de progresso em PROGRESS.md atualizado a cada etapa.
```

### Configuração do CLAUDE.md (arquivo de projeto)

Criar na raiz do repositório:

```markdown
# APP EDITOR — Best of Opera

## Projeto
App de edição automatizada de vídeos de ópera para redes sociais.
Parte de um ecossistema de 3 apps: Curadoria → Redator → Editor.

## Stack
- Backend: FastAPI (Python 3.11+)
- Frontend: React + Vite + Tailwind
- Banco: PostgreSQL (compartilhado com outros apps)
- Processamento: FFmpeg, pysubs2, yt-dlp
- AI: Gemini 2.5 Pro API
- Hosting: Railway
- Idioma da interface: Português (PT-BR)

## Padrões
- Código: Python com type hints, docstrings em português
- API: RESTful, prefixo /api/v1/editor
- Banco: Tabelas com prefixo editor_ (ex: editor_edicoes)
- Commits: Em português, formato "feat: descrição" / "fix: descrição"
- Testes: pytest para backend, componentes críticos

## Estrutura do Projeto
```
app-editor/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── routes/
│   │   ├── services/
│   │   │   ├── youtube.py      (download via yt-dlp — fallback se APP1 não tem)
│   │   │   ├── ffmpeg.py       (extração áudio, corte na janela, renderização)
│   │   │   ├── gemini.py       (transcrição guiada completa, tradução, busca letra)
│   │   │   ├── alinhamento.py  (fuzzy matching lyrics × timestamps)
│   │   │   ├── regua.py        (aplica overlay como régua: recorta vídeo+lyrics+tradução)
│   │   │   └── legendas.py     (geração ASS/SRT multi-track)
│   │   └── utils/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── FilaEdicao.jsx
│   │   │   ├── ValidarLetra.jsx
│   │   │   ├── ValidarAlinhamento.jsx  (mostra quais segmentos estão dentro/fora do corte)
│   │   │   └── Conclusao.jsx
│   │   ├── components/
│   │   └── App.jsx
│   ├── package.json
│   └── Dockerfile
├── CLAUDE.md
├── DECISIONS.md
├── PROGRESS.md
└── railway.json
```

## CONCEITO CENTRAL: OVERLAY COMO RÉGUA
O overlay SRT do Redator tem timestamps relativos ao vídeo ORIGINAL.
Esses timestamps DEFINEM a janela de corte de tudo.
A transcrição é feita no áudio COMPLETO (mais preciso).
Depois o sistema recorta vídeo + lyrics na janela do overlay.

## OS 9 PASSOS DO APP EDITOR
```
PASSO 1:  Receber dados + garantir vídeo disponível
PASSO 2:  Aquisição da letra original (se vocal)
PASSO 3:  Transcrição guiada no áudio COMPLETO (se vocal)
PASSO 4:  Alinhamento automático + validação do operador (se vocal)
PASSO 5:  Aplicar régua do overlay (corte automático de tudo)
PASSO 6:  Tradução da letra cantada ×7 idiomas (se vocal)
PASSO 7:  Montagem legendas ASS (3 tracks × 7 idiomas)
PASSO 8:  Renderização batch (7 vídeos 9:16 + 1 cru)
PASSO 9:  Pacote de entrega
```

## Comandos Úteis
- Backend: `cd backend && uvicorn app.main:app --reload`
- Frontend: `cd frontend && npm run dev`
- Testes: `cd backend && pytest`
- DB migrations: via SQLAlchemy + Alembic
```

---

## ESPECIFICAÇÃO TÉCNICA COMPLETA

### CONCEITO CENTRAL: OVERLAY COMO RÉGUA

O overlay SRT do Redator tem timestamps relativos ao vídeo ORIGINAL do YouTube.
Ex: overlay começa em 01:23,000 e termina em 03:13,000.
Isso DEFINE automaticamente a janela de corte de TUDO: vídeo, lyrics, tradução.
O operador NÃO define corte manualmente — o Redator já fez essa decisão.

A transcrição é feita no áudio COMPLETO (não no trecho cortado) pra mais precisão.
Depois o sistema recorta apenas a janela definida pelo overlay.

### 1. Banco de Dados

Usar o PostgreSQL EXISTENTE no Railway (mesmo dos outros apps).
Prefixar todas as tabelas com `editor_` pra evitar conflitos.

```sql
-- ============================================
-- TABELAS DO APP EDITOR (V4)
-- ============================================

-- Edição principal (1 registro por vídeo em edição)
CREATE TABLE editor_edicoes (
    id SERIAL PRIMARY KEY,
    
    -- Referência ao Curadoria (integração futura via FK)
    curadoria_video_id INTEGER,
    youtube_url VARCHAR(500) NOT NULL,
    youtube_video_id VARCHAR(20) NOT NULL,
    
    -- Metadados do vídeo (copiados do Curadoria)
    artista VARCHAR(300) NOT NULL,
    musica VARCHAR(300) NOT NULL,
    compositor VARCHAR(300),
    opera VARCHAR(300),
    categoria VARCHAR(50),
    idioma VARCHAR(10) NOT NULL,
    eh_instrumental BOOLEAN DEFAULT FALSE,
    duracao_total_sec FLOAT,
    
    -- Status e progresso
    status VARCHAR(30) DEFAULT 'aguardando',
    -- 'aguardando', 'baixando', 'letra', 'transcricao',
    -- 'alinhamento', 'corte', 'traducao', 'montagem', 'renderizando',
    -- 'concluido', 'erro'
    passo_atual INTEGER DEFAULT 1,
    erro_msg TEXT,
    
    -- Janela de corte (DEFINIDA PELO OVERLAY — automático)
    janela_inicio_sec FLOAT,       -- Extraído do primeiro timestamp do overlay
    janela_fim_sec FLOAT,          -- Extraído do último timestamp do overlay
    duracao_corte_sec FLOAT,
    
    -- Arquivos (paths no storage)
    arquivo_video_completo VARCHAR(500),  -- Vídeo original (do APP1 ou download)
    arquivo_video_cortado VARCHAR(500),   -- Vídeo cortado na janela do overlay
    arquivo_audio_completo VARCHAR(500),  -- Áudio do vídeo completo (pra transcrição)
    arquivo_video_cru VARCHAR(500),       -- Cópia sem legendas pra YouTube futuro
    
    -- Alinhamento
    rota_alinhamento VARCHAR(5),
    confianca_alinhamento FLOAT,
    
    -- Tracking
    editado_por VARCHAR(100),
    tempo_edicao_seg INTEGER,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Banco de letras (crescimento orgânico, compartilhável entre apps)
CREATE TABLE editor_letras (
    id SERIAL PRIMARY KEY,
    musica VARCHAR(300) NOT NULL,
    compositor VARCHAR(300),
    opera VARCHAR(300),
    idioma VARCHAR(10) NOT NULL,
    letra TEXT NOT NULL,
    fonte VARCHAR(50),
    validado_por VARCHAR(100),
    validado_em TIMESTAMP,
    vezes_utilizada INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(musica, compositor, idioma)
);

-- Overlay (recebido do Redator — timestamps relativos ao vídeo original)
CREATE TABLE editor_overlays (
    id SERIAL PRIMARY KEY,
    edicao_id INTEGER REFERENCES editor_edicoes(id) ON DELETE CASCADE,
    idioma VARCHAR(10) NOT NULL,
    segmentos_original JSONB NOT NULL,     -- Timestamps relativos ao vídeo original
    segmentos_reindexado JSONB,            -- Timestamps reindexados (base 0:00) após corte
    created_at TIMESTAMP DEFAULT NOW()
);

-- Posts (recebidos do Redator)
CREATE TABLE editor_posts (
    id SERIAL PRIMARY KEY,
    edicao_id INTEGER REFERENCES editor_edicoes(id) ON DELETE CASCADE,
    idioma VARCHAR(10) NOT NULL,
    texto TEXT NOT NULL,
    hashtags TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

-- SEO YouTube (recebido do Redator)
CREATE TABLE editor_seo (
    id SERIAL PRIMARY KEY,
    edicao_id INTEGER REFERENCES editor_edicoes(id) ON DELETE CASCADE,
    idioma VARCHAR(10) NOT NULL,
    titulo VARCHAR(300),
    descricao TEXT,
    tags TEXT[],
    category_id INTEGER DEFAULT 10,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Alinhamento lyrics (transcrição completa + cortado na janela)
CREATE TABLE editor_alinhamentos (
    id SERIAL PRIMARY KEY,
    edicao_id INTEGER REFERENCES editor_edicoes(id) ON DELETE CASCADE,
    letra_id INTEGER REFERENCES editor_letras(id),
    segmentos_completo JSONB NOT NULL,     -- Transcrição/alinhamento do áudio COMPLETO
    segmentos_cortado JSONB,               -- Apenas segmentos na janela, reindexados
    confianca_media FLOAT,
    rota VARCHAR(5),
    validado BOOLEAN DEFAULT FALSE,
    validado_por VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Traduções da letra cantada
CREATE TABLE editor_traducoes_letra (
    id SERIAL PRIMARY KEY,
    edicao_id INTEGER REFERENCES editor_edicoes(id) ON DELETE CASCADE,
    idioma VARCHAR(10) NOT NULL,
    segmentos JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Renders finais
CREATE TABLE editor_renders (
    id SERIAL PRIMARY KEY,
    edicao_id INTEGER REFERENCES editor_edicoes(id) ON DELETE CASCADE,
    idioma VARCHAR(10) NOT NULL,
    tipo VARCHAR(20) NOT NULL,
    arquivo VARCHAR(500),
    tamanho_bytes BIGINT,
    status VARCHAR(20) DEFAULT 'pendente',
    erro_msg TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_editor_edicoes_status ON editor_edicoes(status);
CREATE INDEX idx_editor_letras_musica ON editor_letras(musica);
CREATE INDEX idx_editor_letras_compositor ON editor_letras(compositor);
CREATE INDEX idx_editor_renders_edicao ON editor_renders(edicao_id);
```

### 2. Backend — Rotas da API

```
PREFIXO: /api/v1/editor

# Fila de edição
GET    /edicoes                           Lista edições (filtros: status, categoria)
POST   /edicoes                           Criar edição (metadados + overlay + post + SEO)
GET    /edicoes/{id}                      Detalhes de uma edição
PATCH  /edicoes/{id}                      Atualizar edição
DELETE /edicoes/{id}                      Remover edição

# Vídeo (Passo 1 — busca do APP1 ou download fallback)
POST   /edicoes/{id}/garantir-video       Verifica se APP1 tem o vídeo, senão baixa via yt-dlp
GET    /edicoes/{id}/video/status         Status do download (se necessário)

# Letra (Passo 2)
GET    /letras                            Lista banco de letras
GET    /letras/buscar                     Busca por música/compositor
POST   /edicoes/{id}/letra                Associar/buscar letra (banco → YouTube → Gemini)
PUT    /edicoes/{id}/letra                Editar/aprovar letra

# Transcrição completa (Passo 3 — áudio COMPLETO)
POST   /edicoes/{id}/transcricao          Extrai áudio completo + envia pro Gemini
GET    /edicoes/{id}/transcricao          Resultado da transcrição

# Alinhamento (Passo 4)
GET    /edicoes/{id}/alinhamento          Resultado com flags + janela do overlay marcada
PUT    /edicoes/{id}/alinhamento          Operador valida/corrige
POST   /edicoes/{id}/alinhamento/sync     Click-to-sync manual (Rota C)

# Régua do overlay / Corte automático (Passo 5)
POST   /edicoes/{id}/aplicar-corte        Aplica régua: corta vídeo + recorta lyrics + reindexa
GET    /edicoes/{id}/corte                Info da janela (inicio, fim, duração)

# Tradução lyrics (Passo 6)
POST   /edicoes/{id}/traducao-lyrics      Inicia tradução dos lyrics cortados ×7 idiomas
GET    /edicoes/{id}/traducao-lyrics      Resultado das traduções

# Montagem + Renderização (Passos 7-8)
POST   /edicoes/{id}/renderizar           Monta ASS (3 tracks × 7) + renderiza FFmpeg batch
GET    /edicoes/{id}/renderizar/status    Status por idioma
GET    /edicoes/{id}/renders              Lista renders completos

# Pacote (Passo 9)
GET    /edicoes/{id}/pacote               Metadados do pacote completo
GET    /edicoes/{id}/pacote/download      Download ZIP

# Preview / Streaming
GET    /edicoes/{id}/video/stream         Stream vídeo original
GET    /edicoes/{id}/video/cortado/stream Stream vídeo cortado
GET    /edicoes/{id}/preview/{idioma}     Stream vídeo renderizado

# Configurações
GET    /config/estilos                    Estilos de legenda padrão
PUT    /config/estilos                    Atualizar estilos

# Health
GET    /health                            Health check
```

### 3. Backend — Services

#### 3.1 youtube.py (Download)

```python
"""
Serviço de download de vídeos do YouTube via yt-dlp.
"""
import subprocess
import json
from pathlib import Path

async def download_video(youtube_url: str, video_id: int, storage_path: str) -> dict:
    """
    Baixa vídeo do YouTube em 1080p.
    Retorna paths dos arquivos e metadados.
    """
    output_dir = Path(storage_path) / str(video_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "--merge-output-format", "mp4",
        "-o", str(output_dir / "original.mp4"),
        "--write-thumbnail",
        "--write-info-json",
        "--sub-langs", "all",
        "--write-subs",
        "--no-warnings",
        "--no-progress",
        youtube_url
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        raise Exception(f"yt-dlp falhou: {stderr.decode()}")
    
    # Ler metadados
    info_file = output_dir / "original.info.json"
    info = json.loads(info_file.read_text()) if info_file.exists() else {}
    
    # Verificar legendas manuais
    legendas_manuais = list(output_dir.glob("original.*.vtt"))
    
    return {
        "arquivo_original": str(output_dir / "original.mp4"),
        "duracao_total": info.get("duration", 0),
        "resolucao": f"{info.get('width', '?')}x{info.get('height', '?')}",
        "legendas_manuais": [str(f) for f in legendas_manuais],
        "thumbnail": str(output_dir / "original.webp"),  # ou .jpg
    }
```

#### 3.2 ffmpeg.py (Extração, Corte e Renderização)

```python
"""
Serviço de processamento de vídeo via FFmpeg.
- Extração de áudio do vídeo completo (pra transcrição)
- Corte na janela do overlay (Passo 5)
- Renderização batch (Passo 8)
"""
import asyncio
from pathlib import Path

async def extrair_audio_completo(video_path: str, video_id: int, 
                                  storage_path: str) -> str:
    """
    Extrai áudio do vídeo COMPLETO pra enviar pro Gemini.
    """
    output_dir = Path(storage_path) / str(video_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    audio = output_dir / "audio_completo.ogg"
    
    await run_ffmpeg(
        f'ffmpeg -y -i "{video_path}" '
        f'-vn -acodec libopus -b:a 128k "{audio}"'
    )
    return str(audio)


async def cortar_na_janela_overlay(video_path: str, janela_inicio_sec: float,
                                    janela_fim_sec: float, video_id: int,
                                    storage_path: str) -> dict:
    """
    Corta o vídeo na janela definida pelo overlay SRT.
    Gera vídeo cortado + cópia cru.
    """
    output_dir = Path(storage_path) / str(video_id)
    cortado = output_dir / "video_cortado.mp4"
    cru = output_dir / "video_cru.mp4"
    
    # Cortar na janela do overlay
    await run_ffmpeg(
        f'ffmpeg -y -i "{video_path}" '
        f'-ss {janela_inicio_sec} -to {janela_fim_sec} '
        f'-c copy "{cortado}"'
    )
    
    # Cópia cru (sem legendas, pra YouTube futuro)
    import shutil
    shutil.copy(str(cortado), str(cru))
    
    return {
        "arquivo_cortado": str(cortado),
        "arquivo_cru": str(cru),
        "duracao_corte": janela_fim_sec - janela_inicio_sec
    }


async def renderizar_video(video_cortado: str, ass_file: str,
                           output_path: str) -> dict:
    """
    Renderiza vídeo com legendas ASS em formato 9:16.
    """
    await run_ffmpeg(
        f'ffmpeg -y -i "{video_cortado}" '
        f'-vf "scale=1080:1920:force_original_aspect_ratio=decrease,'
        f'pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,'
        f'ass={ass_file}" '
        f'-c:v libx264 -preset medium -crf 23 '
        f'-c:a aac -b:a 128k '
        f'"{output_path}"'
    )
    
    size = Path(output_path).stat().st_size
    return {"arquivo": output_path, "tamanho_bytes": size}


async def renderizar_batch(video_cortado: str, legendas_por_idioma: dict,
                           video_id: int, storage_path: str) -> dict:
    """
    Renderiza 7 versões legendadas (uma por idioma).
    """
    resultados = {}
    
    for idioma, ass_file in legendas_por_idioma.items():
        output_dir = Path(storage_path) / str(video_id) / "renders" / idioma
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / f"video_{idioma}.mp4"
        
        resultado = await renderizar_video(video_cortado, ass_file, str(output))
        resultados[idioma] = resultado
    
    return resultados


async def run_ffmpeg(cmd: str):
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise Exception(f"FFmpeg falhou: {stderr.decode()}")
    return stdout.decode()
```

#### 3.3 gemini.py (Transcrição no Áudio Completo + Tradução)

```python
"""
Serviço de integração com Gemini 2.5 Pro.
Transcrição guiada no áudio COMPLETO e tradução de lyrics.
"""
import google.generativeai as genai

def configurar_gemini(api_key: str):
    genai.configure(api_key=api_key)

async def transcrever_guiado_completo(audio_completo_path: str, letra_original: str, 
                                       idioma: str, metadados: dict) -> list:
    """
    Envia o áudio COMPLETO + letra + idioma pro Gemini.
    Retorna timestamps relativos ao início do vídeo original.
    Transcrição no áudio completo = mais contexto = mais precisão.
    """
    model = genai.GenerativeModel('gemini-2.5-pro')
    
    audio_file = genai.upload_file(audio_completo_path)
    
    prompt = f"""
Você é um assistente de legendagem de vídeos de ópera.

CONTEXTO:
- Artista: {metadados.get("artista", "Desconhecido")}
- Música: {metadados.get("musica", "Desconhecida")}
- Idioma: {idioma}
- Compositor: {metadados.get("compositor", "N/A")}

LETRA ORIGINAL (texto correto e oficial):
---
{letra_original}
---

TAREFA:
Ouça o áudio COMPLETO e marque os TIMESTAMPS de cada verso da letra.

REGRAS:
1. Use EXATAMENTE o texto da letra original fornecida
2. NÃO modifique nenhuma palavra
3. Marque QUANDO cada frase começa e termina no áudio
4. Timestamps relativos ao INÍCIO do áudio (00:00:00 = início do vídeo)
5. Ignore trechos instrumentais, aplausos e silêncios
6. Se uma frase NÃO APARECE no áudio, OMITA-a
7. Se há repetições não escritas na letra, adicione com [REPETIÇÃO]
8. Se não tem certeza do alinhamento, adicione [?]
9. Marque [TEXTO NÃO IDENTIFICADO] se ouvir algo fora da letra

FORMATO JSON:
[
  {{"index": 1, "start": "00:01:25,300", "end": "00:01:29,800", "text": "Nessun dorma! Nessun dorma!"}},
  {{"index": 2, "start": "00:01:30,200", "end": "00:01:35,400", "text": "Tu pure, o Principessa,"}}
]

Retorne APENAS o JSON, sem markdown, sem explicação.
"""
    
    response = model.generate_content([audio_file, prompt])
    return parse_json_response(response.text)


async def traduzir_letra(segmentos_alinhados: list, idioma_original: str,
                          idioma_alvo: str, metadados: dict) -> list:
    """
    Traduz a letra cantada de um idioma pra outro.
    Mantém a mesma segmentação (timestamps).
    """
    model = genai.GenerativeModel('gemini-2.5-pro')
    
    letra_formatada = "\n".join(
        f"{s['index']}. {s['texto_final']}" for s in segmentos_alinhados
    )
    
    nomes_idiomas = {
        "en": "inglês", "pt": "português", "es": "espanhol",
        "de": "alemão", "fr": "francês", "it": "italiano", "pl": "polonês"
    }
    
    prompt = f"""
Traduza a seguinte letra de ópera para {nomes_idiomas[idioma_alvo]}.

Música: {metadados.get("musica", "")}
Compositor: {metadados.get("compositor", "")}
Idioma original: {idioma_original}

Letra:
---
{letra_formatada}
---

Regras:
1. Tradução LITERÁRIA (não literal)
2. Para árias famosas, use traduções consagradas
3. MANTENHA A MESMA NUMERAÇÃO (mesmos índices = mesmos timestamps)
4. Cada segmento traduzido deve ter comprimento similar ao original

Retorne APENAS JSON:
[
  {{"index": 1, "original": "...", "traducao": "..."}},
  ...
]
"""
    
    response = model.generate_content(prompt)
    return parse_json_response(response.text)


async def buscar_letra(metadados: dict) -> str:
    """
    Pede ao Gemini pra fornecer a letra de uma ária/música.
    """
    model = genai.GenerativeModel('gemini-2.5-pro')
    
    prompt = f"""
Forneça a letra COMPLETA e ORIGINAL da seguinte música/ária:

Artista/Personagem: {metadados.get("artista", "N/A")}
Música/Ária: {metadados["musica"]}
Ópera: {metadados.get("opera", "N/A")}
Compositor: {metadados.get("compositor", "N/A")}
Idioma original: {metadados["idioma"]}

Regras:
1. Retorne APENAS a letra no idioma original
2. Mantenha a grafia exata (acentos, caracteres especiais)
3. Separe os versos em linhas
4. Se houver múltiplos personagens, identifique cada um com [NOME]
5. Se não tiver certeza, comece com INCERTO:
6. NÃO invente texto

Retorne APENAS a letra, sem explicação ou markdown.
"""
    
    response = model.generate_content(prompt)
    return response.text.strip()


def parse_json_response(text: str) -> list:
    """Parse JSON do Gemini, removendo markdown se presente."""
    import json, re
    text = text.strip()
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return json.loads(text)
```

#### 3.4 alinhamento.py (Fuzzy Matching)

```python
"""
Serviço de alinhamento de letra original com timestamps do Gemini.
Usa fuzzy matching pra garantir que o texto final é da letra oficial.
"""
from difflib import SequenceMatcher
import re

def alinhar_letra_com_timestamps(letra_original: str, srt_gemini: list) -> dict:
    """
    Merge da letra original (texto soberano) com timestamps do Gemini.
    Retorna segmentos com flags de confiança.
    """
    versos = [v.strip() for v in letra_original.split('\n') if v.strip()]
    # Remover marcações de personagem pra matching (mas manter no texto final)
    versos_limpos = [re.sub(r'^\[.*?\]\s*', '', v) for v in versos]
    
    resultado = []
    
    for segmento in srt_gemini:
        texto_gemini = segmento.get("text", "")
        
        # Flags especiais
        if "[TEXTO NÃO IDENTIFICADO" in texto_gemini:
            resultado.append({
                **segmento,
                "texto_final": texto_gemini,
                "flag": "ROXO",
                "confianca": 0.0
            })
            continue
        
        eh_repeticao = "[REPETIÇÃO]" in texto_gemini
        if eh_repeticao:
            texto_gemini = texto_gemini.replace("[REPETIÇÃO]", "").strip()
        
        # Encontrar melhor match na letra original
        match, score, indice = encontrar_melhor_match(texto_gemini, versos_limpos)
        texto_original = versos[indice] if indice is not None else texto_gemini
        
        if score >= 0.85:
            resultado.append({
                **segmento,
                "texto_final": texto_original,
                "flag": "VERDE",
                "confianca": score,
                "eh_repeticao": eh_repeticao
            })
        elif score >= 0.50:
            resultado.append({
                **segmento,
                "texto_final": texto_original,
                "texto_gemini": segmento.get("text", ""),
                "flag": "AMARELO",
                "confianca": score,
                "eh_repeticao": eh_repeticao
            })
        else:
            resultado.append({
                **segmento,
                "texto_final": segmento.get("text", ""),
                "candidato_letra": texto_original,
                "flag": "VERMELHO",
                "confianca": score,
                "eh_repeticao": eh_repeticao
            })
    
    # Calcular métricas
    confiancas = [s["confianca"] for s in resultado if s["flag"] != "ROXO"]
    media = sum(confiancas) / len(confiancas) if confiancas else 0
    vermelhos = sum(1 for s in resultado if s["flag"] == "VERMELHO")
    total = len(resultado)
    
    if media >= 0.85 and vermelhos == 0:
        rota = "A"
    elif media >= 0.60 and (vermelhos / total < 0.3 if total > 0 else True):
        rota = "B"
    else:
        rota = "C"
    
    return {
        "segmentos": resultado,
        "confianca_media": round(media, 3),
        "total_verde": sum(1 for s in resultado if s["flag"] == "VERDE"),
        "total_amarelo": sum(1 for s in resultado if s["flag"] == "AMARELO"),
        "total_vermelho": vermelhos,
        "total_roxo": sum(1 for s in resultado if s["flag"] == "ROXO"),
        "rota": rota
    }


def encontrar_melhor_match(texto: str, versos: list) -> tuple:
    """Encontra o verso mais similar via fuzzy matching."""
    texto_norm = normalizar(texto)
    melhor_score = 0
    melhor_verso = ""
    melhor_indice = None
    
    for i, verso in enumerate(versos):
        verso_norm = normalizar(verso)
        score = SequenceMatcher(None, texto_norm, verso_norm).ratio()
        
        # Bonus se contido
        if verso_norm in texto_norm or texto_norm in verso_norm:
            score = max(score, 0.85)
        
        if score > melhor_score:
            melhor_score = score
            melhor_verso = verso
            melhor_indice = i
    
    # Tentar combinações de versos consecutivos
    for i in range(len(versos) - 1):
        combinado = versos[i] + " " + versos[i + 1]
        combinado_norm = normalizar(combinado)
        score = SequenceMatcher(None, texto_norm, combinado_norm).ratio()
        if score > melhor_score:
            melhor_score = score
            melhor_verso = combinado
            melhor_indice = i
    
    return melhor_verso, melhor_score, melhor_indice


def normalizar(texto: str) -> str:
    texto = texto.lower()
    texto = re.sub(r'\[.*?\]', '', texto)
    texto = re.sub(r'[^\w\s]', '', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto


def validar_automatico(resultado: dict, metadados: dict) -> list:
    """Checks automáticos antes de mostrar pro operador."""
    alertas = []
    segmentos = resultado["segmentos"]
    
    # Timestamps sobrepostos
    for i in range(1, len(segmentos)):
        if parse_timestamp(segmentos[i]["start"]) < parse_timestamp(segmentos[i-1]["end"]):
            alertas.append({
                "tipo": "TIMESTAMPS_SOBREPOSTOS",
                "severidade": "MEDIA",
                "msg": f"Segmentos {i} e {i+1} sobrepostos"
            })
    
    # Gaps grandes (>15s)
    for i in range(1, len(segmentos)):
        gap = parse_timestamp(segmentos[i]["start"]) - parse_timestamp(segmentos[i-1]["end"])
        if gap > 15000:
            alertas.append({
                "tipo": "GAP_GRANDE",
                "severidade": "BAIXA",
                "msg": f"Gap de {gap/1000:.0f}s entre segmentos {i} e {i+1}"
            })
    
    # Segmentos longos (>10s)
    for seg in segmentos:
        duracao = parse_timestamp(seg["end"]) - parse_timestamp(seg["start"])
        if duracao > 10000:
            alertas.append({
                "tipo": "SEGMENTO_LONGO",
                "severidade": "BAIXA",
                "msg": f"Segmento com {duracao/1000:.0f}s — considerar dividir"
            })
    
    return alertas
```

#### 3.5 legendas.py (Geração ASS)

```python
"""
Serviço de geração de arquivos ASS com 3 tracks de legenda.
"""
import pysubs2

# Configurações padrão (editáveis via /config/estilos)
ESTILOS_PADRAO = {
    "overlay": {
        "fontname": "Montserrat",
        "fontsize": 42,
        "primarycolor": "#FFFFFF",
        "outlinecolor": "#000000",
        "outline": 2,
        "shadow": 1,
        "alignment": 8,  # topo centro
        "marginv": 80,
        "bold": True,
        "italic": False,
    },
    "lyrics": {
        "fontname": "Georgia",
        "fontsize": 36,
        "primarycolor": "#FFFF64",  # amarelo claro
        "outlinecolor": "#000000",
        "outline": 2,
        "alignment": 2,  # embaixo centro
        "marginv": 130,
        "bold": False,
        "italic": True,
    },
    "traducao": {
        "fontname": "Georgia",
        "fontsize": 30,
        "primarycolor": "#DCDCDC",  # cinza claro
        "outlinecolor": "#000000",
        "outline": 1.5,
        "alignment": 2,  # embaixo centro
        "marginv": 60,
        "bold": False,
        "italic": False,
    }
}

def gerar_ass(overlay: list, lyrics: list, traducao: list | None,
              idioma_versao: str, idioma_musica: str,
              estilos: dict = None) -> pysubs2.SSAFile:
    """
    Gera arquivo ASS com até 3 tracks.
    
    overlay:   do REDATOR (já no idioma da versão)
    lyrics:    do EDITOR (idioma original, fixo)
    traducao:  do EDITOR (traduzida pro idioma da versão) ou None
    """
    estilos = estilos or ESTILOS_PADRAO
    subs = pysubs2.SSAFile()
    subs.info["PlayResX"] = "1080"
    subs.info["PlayResY"] = "1920"
    
    # Criar estilos
    for nome, config in estilos.items():
        style = pysubs2.SSAStyle()
        style.fontname = config["fontname"]
        style.fontsize = config["fontsize"]
        style.primarycolor = hex_to_ssa_color(config["primarycolor"])
        style.outlinecolor = hex_to_ssa_color(config["outlinecolor"])
        style.outline = config.get("outline", 2)
        style.shadow = config.get("shadow", 0)
        style.alignment = config["alignment"]
        style.marginv = config["marginv"]
        style.bold = config.get("bold", False)
        style.italic = config.get("italic", False)
        subs.styles[nome.capitalize()] = style
    
    # Track 1: Overlay
    for seg in overlay:
        event = pysubs2.SSAEvent()
        event.start = seg_to_ms(seg["start_sec"] if "start_sec" in seg else seg["start"])
        event.end = seg_to_ms(seg.get("end_sec", seg.get("start_sec", 0) + seg.get("duration_sec", 4)))
        event.text = seg["text"]
        event.style = "Overlay"
        subs.events.append(event)
    
    # Track 2: Lyrics (fixo em todas as versões)
    for seg in lyrics:
        event = pysubs2.SSAEvent()
        event.start = parse_srt_timestamp(seg["start"])
        event.end = parse_srt_timestamp(seg["end"])
        event.text = seg["texto_final"]
        event.style = "Lyrics"
        subs.events.append(event)
    
    # Track 3: Tradução (só se idioma da versão ≠ idioma da música)
    if idioma_versao != idioma_musica and traducao:
        for seg in traducao:
            event = pysubs2.SSAEvent()
            event.start = parse_srt_timestamp(seg["start"])
            event.end = parse_srt_timestamp(seg["end"])
            event.text = seg["traducao"]
            event.style = "Traducao"
            subs.events.append(event)
    
    return subs
```

#### 3.6 regua.py (Overlay como Régua — Corte Automático)

```python
"""
Serviço que aplica o overlay SRT como "régua" pra definir a janela de corte.
Recorta vídeo, lyrics e tradução na mesma janela. Reindexa timestamps pra base 0:00.
"""

def extrair_janela_do_overlay(overlay_srt: list) -> dict:
    """Lê overlay SRT e extrai início/fim da janela de corte."""
    inicio = timestamp_to_seconds(overlay_srt[0]["start"])
    fim = timestamp_to_seconds(overlay_srt[-1]["end"])
    return {"janela_inicio_sec": inicio, "janela_fim_sec": fim, "duracao_corte_sec": fim - inicio}

def reindexar_timestamps(segmentos: list, janela_inicio_sec: float) -> list:
    """Subtrai janela_inicio de todos os timestamps (rebasa pra 0:00)."""
    resultado = []
    for seg in segmentos:
        inicio = timestamp_to_seconds(seg["start"]) - janela_inicio_sec
        fim = timestamp_to_seconds(seg["end"]) - janela_inicio_sec
        resultado.append({
            **seg,
            "start": seconds_to_timestamp(max(0, inicio)),
            "end": seconds_to_timestamp(max(0, fim)),
        })
    return resultado

def recortar_lyrics_na_janela(lyrics_completo: list, janela_inicio_sec: float,
                               janela_fim_sec: float) -> list:
    """Filtra lyrics dentro da janela + reindexa."""
    dentro = []
    for seg in lyrics_completo:
        seg_inicio = timestamp_to_seconds(seg["start"])
        seg_fim = timestamp_to_seconds(seg["end"])
        if seg_fim > janela_inicio_sec and seg_inicio < janela_fim_sec:
            novo_inicio = max(seg_inicio, janela_inicio_sec) - janela_inicio_sec
            novo_fim = min(seg_fim, janela_fim_sec) - janela_inicio_sec
            dentro.append({
                **seg,
                "start": seconds_to_timestamp(novo_inicio),
                "end": seconds_to_timestamp(novo_fim),
            })
    return dentro

def aplicar_regua(overlay_srt_idiomas: dict, lyrics_alinhados: list) -> dict:
    """
    Aplica overlay como régua. Retorna tudo reindexado e pronto pra montagem.
    overlay_srt_idiomas: {"en": [...], "pt": [...]} do Redator
    lyrics_alinhados: [...] do alinhamento (Passo 4)
    """
    primeiro_idioma = list(overlay_srt_idiomas.keys())[0]
    janela = extrair_janela_do_overlay(overlay_srt_idiomas[primeiro_idioma])
    
    overlays_reindexados = {
        idioma: reindexar_timestamps(segs, janela["janela_inicio_sec"])
        for idioma, segs in overlay_srt_idiomas.items()
    }
    lyrics_cortados = recortar_lyrics_na_janela(
        lyrics_alinhados, janela["janela_inicio_sec"], janela["janela_fim_sec"]
    )
    return {**janela, "overlays_reindexados": overlays_reindexados, "lyrics_cortados": lyrics_cortados}

def timestamp_to_seconds(ts: str) -> float:
    parts = ts.replace(',', '.').split(':')
    return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])

def seconds_to_timestamp(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    ms = int((s % 1) * 1000)
    return f"{h:02d}:{m:02d}:{int(s):02d},{ms:03d}"
```

### 4. Frontend — Páginas Principais

**4 páginas React, interface em português:**

#### 4.1 FilaEdicao.jsx
- Lista de vídeos pendentes/em andamento/concluídos
- Mostra corte automático calculado do overlay (ex: "1:23 → 3:13 (1:50)")
- Cards com metadados, status, score
- Botão "Editar" abre o fluxo
- Botão "Novo" pra adicionar vídeo manualmente

#### 4.2 ValidarLetra.jsx
- Exibe a letra encontrada (fonte: banco, YouTube, ou Gemini)
- Textarea editável
- Botões: Aprovar / Editar / Colar outra / Rebuscar
- Se instrumental: tela é pulada automaticamente

#### 4.3 ValidarAlinhamento.jsx
- Player de vídeo com legendas sobrepostas (preview)
- Lista de segmentos com flags coloridas (🟢🟡🔴🟣)
- **Separação visual: segmentos DENTRO vs FORA da janela do overlay**
  - Seção "Dentro do corte" (destaque) — estes vão pro vídeo final
  - Seção "Fora do corte" (esmaecida) — contexto, não vão pro vídeo
- Indicador da janela: "📐 Corte: 01:23 → 03:13 (1:50)"
- Score de confiança geral e por segmento
- Rota indicada (A/B/C)
- Rota A: botão "Aprovar Tudo"
- Rota B: segmentos amarelos/vermelhos editáveis inline
- Rota C: modo click-to-sync (ENTER marca timestamp de cada verso)
- Alertas automáticos (gaps, sobreposições, etc)

#### 4.4 Conclusao.jsx
- Resumo da edição (tempo, rota, confiança, janela de corte)
- Preview rápido por idioma (bandeiras clicáveis)
- Botão "Baixar Pacote" (ZIP)
- Botão "Próximo Vídeo" → volta pra fila
- Estatísticas acumuladas (vídeos editados hoje, tempo médio)

### 5. Estilo Visual

```
Cores:
- Background: #FFFFF5 (creme/off-white)
- Accent primário: #7C3AED (roxo — cor da marca)
- Accent secundário: #A78BFA (roxo claro)
- Texto: #1E1E1E
- Success: #22C55E (verde)
- Warning: #F59E0B (amarelo)
- Error: #EF4444 (vermelho)
- Info: #8B5CF6 (roxo/info)

Fontes:
- Interface: Inter ou system-ui
- Código/legendas: JetBrains Mono

Componentes:
- Cards com sombra suave, border-radius 12px
- Botões primários em roxo, secundários outline
- Sidebar fixa à esquerda com navegação
```

### 6. Docker + Railway Deploy

#### Dockerfile Backend
```dockerfile
FROM python:3.11-slim

# FFmpeg e yt-dlp
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install yt-dlp

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ ./app/

# Storage volume
RUN mkdir -p /storage/videos /storage/renders

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Dockerfile Frontend
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

#### railway.json
```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE"
  },
  "deploy": {
    "numReplicas": 1,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

### 7. Dependências

#### requirements.txt
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
asyncpg==0.29.0
alembic==1.13.1
pydantic==2.5.3
python-multipart==0.0.6
google-generativeai==0.8.0
pysubs2==1.7.2
aiofiles==23.2.1
httpx==0.26.0
python-dotenv==1.0.0
pytest==8.0.0
```

#### package.json (frontend — deps principais)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.22.0",
    "axios": "^1.6.7",
    "@tanstack/react-query": "^5.17.0",
    "lucide-react": "^0.323.0"
  },
  "devDependencies": {
    "vite": "^5.1.0",
    "@vitejs/plugin-react": "^4.2.1",
    "tailwindcss": "^3.4.1",
    "autoprefixer": "^10.4.17",
    "postcss": "^8.4.33"
  }
}
```

---

## PLANO DE EXECUÇÃO (Ordem de Construção)

```
FASE 1: Infraestrutura (30-45 min)
├── Criar repo GitHub
├── Configurar estrutura de pastas
├── Configurar PostgreSQL (conectar ao existente)
├── Criar tabelas com Alembic
├── Setup FastAPI com health check
├── Setup React com Vite + Tailwind
├── Testar: backend responde /health, frontend renderiza

FASE 2: Backend Core (1-2h)
├── Models SQLAlchemy
├── CRUD routes (edicoes, letras)
├── Service: youtube.py (download fallback via yt-dlp)
├── Service: ffmpeg.py (extração áudio completo + corte na janela + render)
├── Service: gemini.py (transcrição guiada no áudio completo + tradução)
├── Service: alinhamento.py (fuzzy matching lyrics × timestamps)
├── Service: regua.py (overlay como régua — recorta tudo na janela)
├── Service: legendas.py (geração ASS multi-track)
├── Testar: cada service isoladamente

FASE 3: Frontend Core (1-2h)
├── Layout base (sidebar + main content, tudo em português)
├── FilaEdicao (lista + criação manual + corte automático visível)
├── ValidarLetra (texto + ações)
├── ValidarAlinhamento (flags + segmentos dentro/fora da janela + preview)
├── Conclusao (resumo + download pacote)
├── Testar: navegação completa

FASE 4: Integração (1h)
├── Conectar frontend → backend (API calls)
├── Fluxo completo ponta a ponta (9 passos)
├── Background tasks (download, transcrição, corte, render)
├── Fluxo instrumental (pula passos 2-4, 6)
├── Testar: fluxo de 1 vídeo do início ao fim

FASE 5: Deploy Railway (30-45 min)
├── Build Docker backend (com FFmpeg + yt-dlp)
├── Build Docker frontend
├── Deploy no Railway (mesmo projeto dos outros apps)
├── Variáveis de ambiente
├── Volume pra storage de vídeos
├── Testar: acessar via URL pública

FASE 6: Polimento (30 min)
├── Loading states e progress bars
├── Error handling robusto
├── Responsividade básica
├── PROGRESS.md e DECISIONS.md atualizados

TEMPO TOTAL ESTIMADO: 5-7 horas
```

---

## VARIÁVEIS DE AMBIENTE

```env
# PostgreSQL (mesmo do Curadoria/Redator)
DATABASE_URL=postgresql://postgres:xxx@xxx.railway.app:5432/railway

# Gemini
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXX

# Storage
STORAGE_PATH=/storage
MAX_VIDEO_SIZE_MB=500

# App
APP_NAME=Best of Opera Editor
APP_ENV=production
SECRET_KEY=gerar-uma-chave-aleatoria
CORS_ORIGINS=["https://editor-frontend.up.railway.app"]

# Opcional
YOUTUBE_API_KEY=  # yt-dlp funciona sem, mas com limites
```

---

## TESTES MÍNIMOS OBRIGATÓRIOS

Antes de considerar "pronto", Claude Code deve verificar:

```
□ Backend responde em /health
□ Tabelas criadas no PostgreSQL (com prefixo editor_)
□ CRUD de edições funciona (criar, listar, atualizar)
□ Download de vídeo via yt-dlp funciona (fallback)
□ Extração de áudio completo funciona
□ Gemini retorna timestamps (pode testar com mock se API key não disponível)
□ Alinhamento fuzzy matching funciona (testar com strings conhecidas)
□ Régua do overlay recorta corretamente (testar com timestamps conhecidos)
□ Reindexação de timestamps funciona (subtrair janela_inicio)
□ Geração de ASS funciona (pysubs2, 3 tracks)
□ FFmpeg renderiza vídeo 9:16 com legendas
□ Frontend carrega e navega entre páginas
□ Fluxo de criação de edição → validação → render funciona end-to-end
□ Deploy no Railway acessível via URL
```

---

## NOTAS IMPORTANTES

1. **Overlay é a régua:** O conceito central é que o overlay SRT do Redator define a janela de corte. Seus timestamps são relativos ao vídeo original. O Editor NÃO tem etapa de corte manual — tudo é automático a partir do overlay.

2. **Transcrição no áudio completo:** O Gemini recebe o áudio do vídeo inteiro (não cortado). Isso dá mais contexto e precisão. Depois, o sistema recorta só os segmentos dentro da janela do overlay.

3. **Vídeo vem do APP1:** O arquivo de vídeo já baixado pelo Curadoria deve ser reutilizado. O Editor só baixa via yt-dlp se o arquivo não existir (fallback).

4. **Integração via banco:** Os 3 APPs compartilham o mesmo PostgreSQL no Railway. Não construir APIs entre apps agora. Tabelas com prefixo `editor_` pra evitar conflitos. No futuro, o Editor lê direto das tabelas do Curadoria/Redator.

5. **Input manual na V1:** Como os apps ainda não estão integrados via banco, o Editor na V1 terá um formulário manual pra inserir metadados e colar os overlays/posts/SEO do Redator. Na V2 (integração), isso fica automático.

6. **Storage de vídeos:** Railway volumes são efêmeros em redeploys. Pra V1 funciona (vídeos são temporários, pacote final é baixado). Futuro: Cloudflare R2 ou S3.

7. **FFmpeg no Railway:** Instala via apt-get no Docker. Renderização de 7 vídeos ~2min leva ~5-8 min. Se Railway free tier limitar CPU, usar preset ultrafast e CRF mais alto.

8. **yt-dlp:** Funciona sem API key do YouTube mas pode ter rate limiting. Se der problemas, adicionar cookies.
