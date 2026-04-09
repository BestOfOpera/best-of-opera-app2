FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fontconfig curl \
    && ffmpeg -version | head -1 \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir yt-dlp bgutil-ytdlp-pot-provider \
    && yt-dlp -U

WORKDIR /app
COPY app-editor/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app-editor/backend/app/ ./app/
COPY shared/ ./shared/
COPY app-editor/backend/fonts/ /usr/local/share/fonts/custom/

RUN fc-cache -fv && mkdir -p /storage/videos /storage/renders

EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
