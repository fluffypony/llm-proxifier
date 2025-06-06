#!/bin/bash

# Docker start script for LLM Proxifier
set -e

# Default values
MODELS_DIR=${MODELS_DIR:-"./models"}
CONFIG_DIR=${CONFIG_DIR:-"./config"}
PROXY_PORT=${PROXY_PORT:-8000}
DASHBOARD_PORT=${DASHBOARD_PORT:-3000}
CONTAINER_NAME=${CONTAINER_NAME:-"llm-proxifier"}
AUTH_CONFIG_PATH=${AUTH_CONFIG_PATH:-"./config/auth.yaml"}
DASHBOARD_ENABLED=${DASHBOARD_ENABLED:-"true"}
AUTH_ENABLED=${AUTH_ENABLED:-"true"}

echo "Starting LLM Proxifier container..."
echo "Models directory: $MODELS_DIR"
echo "Config directory: $CONFIG_DIR"
echo "Proxy port: $PROXY_PORT"
echo "Dashboard port: $DASHBOARD_PORT"
echo "Auth config path: $AUTH_CONFIG_PATH"
echo "Dashboard enabled: $DASHBOARD_ENABLED"
echo "Auth enabled: $AUTH_ENABLED"

# Check if directories exist
if [ ! -d "$MODELS_DIR" ]; then
    echo "Warning: Models directory $MODELS_DIR does not exist"
fi

if [ ! -d "$CONFIG_DIR" ]; then
    echo "Error: Config directory $CONFIG_DIR does not exist"
    exit 1
fi

# Stop existing container if running
if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
    echo "Stopping existing container..."
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
fi

# Start the container
docker run -d \
    --name $CONTAINER_NAME \
    -p $PROXY_PORT:8000 \
    -p $DASHBOARD_PORT:3000 \
    -v "$MODELS_DIR:/app/models:ro" \
    -v "$CONFIG_DIR:/app/config:ro" \
    -e PROXY_PORT=8000 \
    -e DASHBOARD_PORT=3000 \
    -e AUTH_CONFIG_PATH="$AUTH_CONFIG_PATH" \
    -e DASHBOARD_ENABLED="$DASHBOARD_ENABLED" \
    -e AUTH_ENABLED="$AUTH_ENABLED" \
    --restart unless-stopped \
    llm-proxifier:latest

echo "Container started successfully!"
echo "Proxy server: http://localhost:$PROXY_PORT"
echo "Dashboard: http://localhost:$DASHBOARD_PORT"
echo "Health check: http://localhost:$PROXY_PORT/health"

# Show container status
docker ps -f name=$CONTAINER_NAME
