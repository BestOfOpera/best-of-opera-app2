FROM python:3.11-slim

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
RUN pip install yt-dlp

WORKDIR /app
COPY app-editor/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app-editor/backend/app/ ./app/
COPY shared/ ./shared/

RUN mkdir -p /storage/videos /storage/renders

EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
