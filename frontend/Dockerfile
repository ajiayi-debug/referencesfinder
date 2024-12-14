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

