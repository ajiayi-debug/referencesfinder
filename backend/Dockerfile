FROM python:3.12.6-slim

WORKDIR /app

# Install Azure CLI (if needed)
RUN apt-get update && apt-get install -y curl apt-transport-https lsb-release gnupg && \
    curl -sL https://aka.ms/InstallAzureCLIDeb | bash && \
    rm -rf /var/lib/apt/lists/*

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

# Expose backend port
EXPOSE 8000

# Set environment if needed
ENV FASTAPI_APP=/app/main.py
ENV FASTAPI_ENV=production

# Run the entrypoint, then uvicorn
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
