# Backend Stage
FROM python:3.12.6-slim AS backend

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y curl apt-transport-https lsb-release gnupg && \
    curl -sL https://aka.ms/InstallAzureCLIDeb | bash && \
    rm -rf /var/lib/apt/lists/*

# Copy only the requirements file for caching
COPY requirements.txt .

# Upgrade pip and install dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend files
COPY .env /app/.env
COPY backend /app/backend

# Frontend Stage
FROM node:18 AS frontend

WORKDIR /app

# Copy only package.json for caching
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install

# Copy frontend source code
COPY frontend /app

# Build the frontend
RUN npm run build

# Production Image
FROM python:3.12.6-slim

WORKDIR /app

# Copy backend application code from the backend stage
COPY --from=backend /app /app

# Copy Python installed packages from backend stage
COPY --from=backend /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=backend /usr/local/bin /usr/local/bin

# Copy built frontend from the frontend stage
COPY --from=frontend /app/dist /app/backend/static

# Expose backend port
EXPOSE 8000

ENV FASTAPI_APP=/app/backend/main.py
ENV FASTAPI_ENV=production

# Command to run the FastAPI app
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
