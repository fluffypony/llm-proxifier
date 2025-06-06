#!/bin/bash

# Development installation script for LLM Proxifier
set -e

echo "Setting up LLM Proxifier for development..."

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Check if pipx is available
if ! command -v pipx >/dev/null 2>&1; then
    echo "Error: pipx is not installed. Please install pipx first:"
    echo "  pip install --user pipx"
    echo "  pipx ensurepath"
    exit 1
fi

# Install in editable mode with pipx
echo "Installing LLM Proxifier in editable mode with pipx..."
pipx install -e . --force

# Install development dependencies
echo "Installing development dependencies..."
if [[ -d ".venv" ]]; then
    echo "Activating existing virtual environment..."
    source .venv/bin/activate
else
    echo "Creating virtual environment..."
    python -m venv .venv
    source .venv/bin/activate
fi

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -e ".[dev]"

# Install pre-commit hooks if available
if [ -f ".pre-commit-config.yaml" ]; then
    echo "Installing pre-commit hooks..."
    pre-commit install
fi

echo ""
echo "Development setup complete!"
echo ""
echo "Available commands:"
echo "  llm-proxifier --help    # Show CLI help"
echo "  llm-proxifier start     # Start the server"
echo "  llm-proxifier status    # Check server status"
echo ""
echo "Development commands:"
echo "  pytest                  # Run tests"
echo "  black src/              # Format code"
echo "  ruff check src/         # Lint code"
echo "  mypy src/               # Type check"
echo ""
echo "Virtual environment activated at: .venv"
echo "To deactivate: deactivate"
