FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl unzip git && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y --no-install-recommends ffmpeg nodejs && \
    rm -rf /var/lib/apt/lists/* && \
    node --version && which node

# Deno — runtime JS padrão do yt-dlp para resolver YouTube challenges
RUN curl -fsSL https://github.com/denoland/deno/releases/latest/download/deno-x86_64-unknown-linux-gnu.zip -o /tmp/deno.zip \
    && unzip /tmp/deno.zip -d /usr/local/bin/ \
    && chmod +x /usr/local/bin/deno \
    && rm /tmp/deno.zip \
    && deno --version

# PATH explícito — garantia para subprocesses Python (deno, node)
ENV PATH="/usr/local/bin:${PATH}"

COPY app-curadoria/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -U yt-dlp

# bgutil script-deno — SÓ o server code (Deno) para gerar PO Tokens.
# yt-dlp >=2026.03.17 já traz os providers BgUtilHTTP/BgUtilScriptNode
# embutidos; instalar o pacote PyPI bgutil-ytdlp-pot-provider gera
# "AssertionError: PoTokenProvider ... already registered" e derruba todos
# os providers. Os providers nativos leem server_home via extractor_args.
RUN git clone --depth 1 https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git /app/bgutil-pot \
    && cd /app/bgutil-pot/server \
    && deno install --allow-scripts=npm:canvas --frozen \
    && ls /app/bgutil-pot/server/src/ || true

# Sanity test: imprime as 5 primeiras linhas do deno run generate_once.ts.
# Expõe erros de módulo/import nos logs de build sem quebrar o deploy.
RUN cd /app/bgutil-pot/server && deno run --allow-all src/generate_once.ts 2>&1 | head -5 || echo "BGUTIL TEST: script falhou mas build continua"

COPY app-curadoria/backend/ .
COPY shared/ ./shared/

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
