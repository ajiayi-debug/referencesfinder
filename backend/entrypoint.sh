#!/usr/bin/env sh
set -e

echo "Logging into Azure CLI using service principal..."
az login --service-principal \
  -u "$AZURE_CLIENT_ID" \
  -p "$AZURE_CLIENT_SECRET" \
  --tenant "$AZURE_TENANT_ID"

echo "Starting FastAPI application..."
exec "$@"
