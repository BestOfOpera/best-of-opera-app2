# SPEC-005d — Ativar PO Token no yt-dlp (curadoria)

**Status:** EM EXECUÇÃO
**PRD de origem:** `docs/PRD-005-diagnostico-erros-plataforma.md` (problema #4)
**Data:** 23/03/2026

---

## Contexto

O YouTube exige PO Token (Proof of Origin Token) desde meados de 2024. Sem ele,
o yt-dlp é identificado como bot e bloqueado mesmo com cookies válidos.

O container já tem Deno instalado para este fim (Dockerfile linha 8), mas o plugin
`bgutil-ytdlp-pot-provider` nunca foi adicionado nem o yt-dlp foi configurado para usá-lo.
Alguém iniciou a preparação mas não concluiu.

**Arquivos a modificar:** 2
- `app-curadoria/backend/requirements.txt`
- `app-curadoria/backend/services/download.py`

---

## Tarefa 1 — Adicionar plugin ao requirements.txt

**Arquivo:** `app-curadoria/backend/requirements.txt`

**Adicionar linha:**
```
bgutil-ytdlp-pot-provider
```

O plugin auto-registra com o yt-dlp ao ser instalado — nenhum import explícito necessário.

**Critério de feito:** linha presente no arquivo.

---

## Tarefa 2 — Configurar yt-dlp para usar o plugin

**Arquivo:** `app-curadoria/backend/services/download.py`

**Localizar** `_get_ydl_opts()` (~linha 70). Dentro do dict `opts`, após a chave `http_headers`, adicionar:

```python
'extractor_args': {
    'youtube': {
        'pot_from_server': ['bgutil'],
    }
},
```

**Critério de feito:** chave `extractor_args` presente no dict retornado por `_get_ydl_opts()`.

---

## Risco conhecido

O `bgutil-ytdlp-pot-provider` foi projetado primariamente para Node.js. O container
tem Deno. Versões recentes do plugin suportam Deno, mas só é possível confirmar após
deploy e teste com vídeo real.

**Plano B se Deno não funcionar:** substituir as linhas do Dockerfile:
```dockerfile
# Install Deno (JS runtime required by yt-dlp for PO token generation)
RUN curl -fsSL https://deno.land/install.sh | sh
ENV DENO_DIR=/root/.deno
ENV PATH="/root/.deno/bin:${PATH}"
```
por:
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm && rm -rf /var/lib/apt/lists/*
```
Sem alteração no requirements.txt nem no download.py — apenas o runtime muda.

---

## Verificação pós-deploy

1. Acessar curadoria → buscar qualquer vídeo → clicar "Preparar vídeo"
2. Acompanhar logs do Railway (`curadoria-backend`) — deve aparecer `[yt-dlp]` sem erro de bot detection
3. Vídeo deve chegar no R2 sem upload manual
4. Se aparecer erro relacionado a Deno/Node → aplicar Plano B e fazer novo deploy
