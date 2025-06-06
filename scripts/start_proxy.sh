#!/bin/bash

# Start script for LLM Proxifier
# Usage: ./scripts/start_proxy.sh [options]

set -e

# Default values
PROXY_HOST="${PROXY_HOST:-0.0.0.0}"
PROXY_PORT="${PROXY_PORT:-8000}"
CONFIG_PATH="${CONFIG_PATH:-./config/models.yaml}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--host)
            PROXY_HOST="$2"
            shift 2
            ;;
        -p|--port)
            PROXY_PORT="$2"
            shift 2
            ;;
        -c|--config)
            CONFIG_PATH="$2"
            shift 2
            ;;
        -l|--log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  -h, --host HOST        Host to bind to (default: 0.0.0.0)"
            echo "  -p, --port PORT        Port to bind to (default: 8000)"
            echo "  -c, --config PATH      Path to models config (default: ./config/models.yaml)"
            echo "  -l, --log-level LEVEL  Log level (default: INFO)"
            echo "  --help                 Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if config file exists
if [[ ! -f "$CONFIG_PATH" ]]; then
    echo "Error: Configuration file not found: $CONFIG_PATH"
    exit 1
fi

# Check if virtual environment exists and activate it
if [[ -d "venv" ]]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
elif [[ -d ".venv" ]]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Check if required packages are installed
if ! python -c "import fastapi, uvicorn" 2>/dev/null; then
    echo "Installing required packages..."
    pip install -r requirements.txt
fi

# Export environment variables
export PROXY_HOST="$PROXY_HOST"
export PROXY_PORT="$PROXY_PORT"
export CONFIG_PATH="$CONFIG_PATH"
export LOG_LEVEL="$LOG_LEVEL"

echo "Starting LLM Proxifier..."
echo "Host: $PROXY_HOST"
echo "Port: $PROXY_PORT"
echo "Config: $CONFIG_PATH"
echo "Log Level: $LOG_LEVEL"
echo ""

# Start the server
uvicorn src.main:app \
    --host "$PROXY_HOST" \
    --port "$PROXY_PORT" \
    --log-level "$(echo $LOG_LEVEL | tr '[:upper:]' '[:lower:]')" \
    --access-log
