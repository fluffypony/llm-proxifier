#!/bin/bash

# Get version script for LLM Proxifier
# Supports both tagged and development builds

set -e

# Function to get version from git
get_git_version() {
    # Check if we're in a git repository
    if ! git rev-parse --git-dir >/dev/null 2>&1; then
        echo "1.8.0-dev"
        return
    fi
    
    # Get the current tag or commit
    if ! VERSION=$(git describe --tags --dirty --always 2>/dev/null); then
        echo "1.8.0-dev"
        return
    fi
    
    # Remove 'v' prefix if present
    VERSION=${VERSION#v}
    
    # Handle dirty working directory
    if [[ $VERSION == *-dirty ]]; then
        VERSION="${VERSION%-dirty}-dev-dirty"
    elif [[ $VERSION == *-g* ]]; then
        # Format: tag-commits-ghash
        IFS='-' read -ra PARTS <<< "$VERSION"
        if [ ${#PARTS[@]} -ge 3 ]; then
            TAG=${PARTS[0]}
            COMMITS=${PARTS[1]}
            GHASH=${PARTS[2]}
            VERSION="${TAG}-dev+${COMMITS}.${GHASH}"
        fi
    fi
    
    echo "$VERSION"
}

# Main execution
if [ "$1" = "--short" ]; then
    # Just output version without extra info
    get_git_version
else
    VERSION=$(get_git_version)
    echo "Version: $VERSION"
    
    # Additional build info
    if git rev-parse --git-dir >/dev/null 2>&1; then
        COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
        DATE=$(git log -1 --format="%ci" 2>/dev/null || echo "unknown")
        
        echo "Commit: $COMMIT"
        echo "Date: $DATE"
        
        if ! git diff --quiet 2>/dev/null; then
            echo "Status: dirty"
        else
            echo "Status: clean"
        fi
    fi
fi
