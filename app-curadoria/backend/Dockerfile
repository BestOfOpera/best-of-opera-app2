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

# bgutil script-deno — gera PO Tokens localmente via Deno (sem servidor HTTP)
# IMPORTANTE: `deno install` resolve deps; `deno task build` compila build/generate_once.js
RUN git clone --depth 1 https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git /app/bgutil-pot \
    && cd /app/bgutil-pot/server \
    && deno install --allow-scripts=npm:canvas --frozen \
    && deno task build \
    && ls -la /app/bgutil-pot/server/ \
    && ls -la /app/bgutil-pot/server/build/ \
    && which deno \
    && echo "PATH=$PATH"

COPY app-curadoria/backend/ .
COPY shared/ ./shared/

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
