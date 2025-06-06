#!/bin/bash

# Build script for LLM Proxifier
set -e

echo "Building LLM Proxifier..."

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info/

# Get version information
VERSION=$(./scripts/get_version.sh --short)
echo "Building version: $VERSION"

# Create build directory
mkdir -p build

# Run version detection and save build info
echo "Generating build information..."
./scripts/get_version.sh > build/version.txt

# Check if virtual environment exists
if [[ -d ".venv" ]]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
elif [[ -d "venv" ]]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Install build dependencies
echo "Installing build dependencies..."
pip install --upgrade pip setuptools wheel build

# Build source distribution
echo "Building source distribution..."
python -m build --sdist

# Build wheel distribution
echo "Building wheel distribution..."
python -m build --wheel

# Validate package contents
echo "Validating package contents..."
python -m pip install --upgrade twine
python -m twine check dist/*

echo "Build complete!"
echo "Artifacts:"
ls -la dist/

echo ""
echo "Version info:"
cat build/version.txt

echo ""
echo "To install locally:"
echo "pip install dist/llm_proxifier-${VERSION}-py3-none-any.whl"

echo ""
echo "To upload to PyPI:"
echo "twine upload dist/*"
