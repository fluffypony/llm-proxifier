#!/bin/bash

# Docker build script for LLM Proxifier
set -e

VERSION=${1:-latest}
IMAGE_NAME="llm-proxifier"
REGISTRY=${REGISTRY:-""}

echo "Building Docker image: ${IMAGE_NAME}:${VERSION}"

# Build the image
docker build -t ${IMAGE_NAME}:${VERSION} .

# Also tag as latest if version is not latest
if [ "$VERSION" != "latest" ]; then
    docker tag ${IMAGE_NAME}:${VERSION} ${IMAGE_NAME}:latest
fi

# If registry is set, tag for registry
if [ -n "$REGISTRY" ]; then
    docker tag ${IMAGE_NAME}:${VERSION} ${REGISTRY}/${IMAGE_NAME}:${VERSION}
    docker tag ${IMAGE_NAME}:${VERSION} ${REGISTRY}/${IMAGE_NAME}:latest
    echo "Tagged for registry: ${REGISTRY}/${IMAGE_NAME}:${VERSION}"
fi

echo "Build completed successfully!"
echo "Image: ${IMAGE_NAME}:${VERSION}"

# Show image size
docker images ${IMAGE_NAME}:${VERSION}
