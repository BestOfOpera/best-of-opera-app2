FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fontconfig \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir yt-dlp

WORKDIR /app
COPY app-editor/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app-editor/backend/app/ ./app/
COPY shared/ ./shared/
COPY app-editor/backend/fonts/ /usr/local/share/fonts/custom/

RUN fc-cache -fv && mkdir -p /storage/videos /storage/renders

EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
