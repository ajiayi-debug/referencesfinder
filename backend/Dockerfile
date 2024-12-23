<<<<<<< HEAD
FROM python:3.12.6-slim

WORKDIR /app

# Install Azure CLI (if needed)
=======
# Backend Stage
FROM python:3.12.6-slim AS backend

WORKDIR /app

# Install system dependencies
>>>>>>> 385a3648c0d70765a1fea7959b5fc26ee04325fc
RUN apt-get update && apt-get install -y curl apt-transport-https lsb-release gnupg && \
    curl -sL https://aka.ms/InstallAzureCLIDeb | bash && \
    rm -rf /var/lib/apt/lists/*

<<<<<<< HEAD
# Copy requirements and install
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python code (main.py and token_manager.py) to /app
COPY backend/main.py /app/
COPY backend/token_manager.py /app/

# Copy entrypoint script
COPY backend/entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh
=======
# Copy only the requirements file for caching
COPY requirements.txt ./

# Upgrade pip and install dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend files
COPY .env /app/.env
COPY backend /app/backend
>>>>>>> 385a3648c0d70765a1fea7959b5fc26ee04325fc

# Expose backend port
EXPOSE 8000

<<<<<<< HEAD
# Set environment if needed
ENV FASTAPI_APP=/app/main.py
ENV FASTAPI_ENV=production

# Run the entrypoint, then uvicorn
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
=======
ENV FASTAPI_APP=/app/backend/main.py
ENV FASTAPI_ENV=production

# Command to run the FastAPI app
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
>>>>>>> 385a3648c0d70765a1fea7959b5fc26ee04325fc
