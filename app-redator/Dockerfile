FROM node:18-slim AS frontend-build
WORKDIR /build
COPY app-redator/frontend/package.json app-redator/frontend/package-lock.json ./
RUN npm ci
COPY app-redator/frontend/ .
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

COPY app-redator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app-redator/backend/ ./backend/
COPY shared/ ./shared/
COPY --from=frontend-build /build/dist ./frontend/dist

EXPOSE 8000
CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
