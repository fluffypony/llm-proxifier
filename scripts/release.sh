#!/bin/bash

# Release script for LLM Proxifier
set -e

# Configuration
REPO_URL="https://github.com/fluffypony/llm-proxifier"

# Functions
usage() {
    echo "Usage: $0 <version>"
    echo "Example: $0 1.8.0"
    exit 1
}

# Check arguments
if [ $# -ne 1 ]; then
    usage
fi

VERSION="$1"

# Validate version format (simple check)
if ! [[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Version must be in format X.Y.Z (e.g., 1.8.0)"
    exit 1
fi

echo "Preparing release for version $VERSION..."

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Check if we're in a git repository
if ! git rev-parse --git-dir >/dev/null 2>&1; then
    echo "Error: Not in a git repository"
    exit 1
fi

# Check if working directory is clean
if ! git diff --quiet; then
    echo "Error: Working directory is not clean. Commit or stash changes first."
    exit 1
fi

# Check if on main branch
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" != "main" ] && [ "$BRANCH" != "master" ]; then
    echo "Warning: Not on main/master branch (currently on $BRANCH)"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if tag already exists
if git tag | grep -q "^v$VERSION$"; then
    echo "Error: Tag v$VERSION already exists"
    exit 1
fi

# Update version in files if needed
echo "Updating version references..."

# Run tests if they exist
if [ -f "pytest.ini" ] || [ -f "pyproject.toml" ]; then
    echo "Running tests..."
    if command -v pytest >/dev/null 2>&1; then
        pytest
    else
        echo "Warning: pytest not found, skipping tests"
    fi
fi

# Build the package
echo "Building package..."
./scripts/build.sh

# Create and push the tag
echo "Creating git tag v$VERSION..."
git tag -a "v$VERSION" -m "Release version $VERSION"

echo "Pushing tag to origin..."
git push origin "v$VERSION"

# Create GitHub release (if gh CLI is available)
if command -v gh >/dev/null 2>&1; then
    echo "Creating GitHub release..."
    gh release create "v$VERSION" \
        --title "Release $VERSION" \
        --notes "Release version $VERSION" \
        dist/*
else
    echo "GitHub CLI (gh) not found. Please create release manually at:"
    echo "$REPO_URL/releases/new?tag=v$VERSION"
fi

# Upload to PyPI (optional)
echo ""
echo "Release $VERSION created successfully!"
echo ""
echo "Next steps:"
echo "1. Upload to PyPI: twine upload dist/*"
echo "2. Update documentation if needed"
echo "3. Announce the release"

echo ""
echo "Files ready for PyPI upload:"
ls -la dist/
