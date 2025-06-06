#!/bin/bash

# Stop script for LLM Proxifier
# Usage: ./scripts/stop_proxy.sh

set -e

PROXY_PORT="${PROXY_PORT:-8000}"

echo "Stopping LLM Proxifier..."

# Find and kill the process
PID=$(lsof -ti:$PROXY_PORT 2>/dev/null || true)

if [[ -n "$PID" ]]; then
    echo "Found process on port $PROXY_PORT (PID: $PID)"
    echo "Sending SIGTERM..."
    kill -TERM "$PID"
    
    # Wait for graceful shutdown
    for i in {1..10}; do
        if ! kill -0 "$PID" 2>/dev/null; then
            echo "Process stopped gracefully"
            exit 0
        fi
        echo "Waiting for graceful shutdown... ($i/10)"
        sleep 1
    done
    
    # Force kill if still running
    if kill -0 "$PID" 2>/dev/null; then
        echo "Forcing process termination..."
        kill -KILL "$PID"
        echo "Process killed"
    fi
else
    echo "No process found on port $PROXY_PORT"
fi

echo "LLM Proxifier stopped"
