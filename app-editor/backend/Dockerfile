FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fontconfig curl git unzip \
    && ffmpeg -version | head -1 \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir yt-dlp bgutil-ytdlp-pot-provider \
    && yt-dlp -U

# Deno — runtime JS executado pelo provider bgutil-script para gerar PO Tokens.
RUN curl -fsSL https://github.com/denoland/deno/releases/latest/download/deno-x86_64-unknown-linux-gnu.zip -o /tmp/deno.zip \
    && unzip /tmp/deno.zip -d /usr/local/bin/ \
    && chmod +x /usr/local/bin/deno \
    && rm /tmp/deno.zip \
    && deno --version
ENV PATH="/usr/local/bin:${PATH}"

# bgutil-pot — server code (generate_once.ts) que o plugin chama via Deno.
# O pacote PyPI bgutil-ytdlp-pot-provider já está instalado acima; aqui só
# clonamos o lado server e instalamos as deps Deno. Path bate com o
# server_home passado via --extractor-args em pipeline.py e services/youtube.py.
RUN git clone --depth 1 https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git /app/bgutil-pot \
    && cd /app/bgutil-pot/server \
    && deno install --allow-scripts=npm:canvas --frozen \
    && ls /app/bgutil-pot/server/src/ || true

WORKDIR /app
COPY app-editor/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app-editor/backend/app/ ./app/
COPY shared/ ./shared/
COPY app-editor/backend/fonts/ /usr/local/share/fonts/custom/

RUN fc-cache -fv && mkdir -p /storage/videos /storage/renders

EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
