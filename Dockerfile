# Backend Stage
FROM python:3.12-slim AS backend

WORKDIR /app

# Copy static files first for caching
COPY requirements.txt .
COPY .env /app/.env

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY RAG /app/RAG

# Expose the backend port
EXPOSE 8000

ENV FASTAPI_APP=/app/RAG/main.py
ENV FASTAPI_ENV=production

# Frontend Stage
FROM node:18 AS frontend

WORKDIR /app

# Copy static files first for caching
COPY update_article/package.json update_article/package-lock.json ./
RUN npm install

# Copy frontend source code
COPY update_article /app

# Build the frontend
RUN npm run build

# Production Image
FROM python:3.12-slim

WORKDIR /app

# Copy backend from the backend stage
COPY --from=backend /app /app

# Copy built frontend from the frontend stage
COPY --from=frontend /app/dist /app/RAG/static

# Expose backend port
EXPOSE 8000

ENV FASTAPI_APP=/app/RAG/main.py
ENV FASTAPI_ENV=production

# Command to run the FastAPI app
CMD ["python", "/app/RAG/main.py"]
