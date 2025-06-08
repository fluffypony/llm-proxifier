"""Version information for llm-proxifier."""

import os
import subprocess
from typing import Optional

try:
    import tomllib
except ImportError:
    import tomli as tomllib


def get_version() -> str:
    """Get version string from pyproject.toml or git tags."""
    # First try to read from pyproject.toml
    try:
        # Get the path to pyproject.toml (go up from src/llm_proxifier to project root)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        toml_path = os.path.join(project_root, "pyproject.toml")
        
        if os.path.exists(toml_path):
            with open(toml_path, "rb") as f:
                pyproject = tomllib.load(f)
                version = pyproject.get("project", {}).get("version")
                if version:
                    return version
    except Exception:
        pass
    
    # Fallback to git version
    git_version = _get_git_version()
    if git_version:
        return git_version
    
    # Final fallback
    return "0.1.0"


def _get_git_version() -> Optional[str]:
    """Get version from git describe."""
    try:
        # Check if we're in a git repository
        git_dir = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )

        if git_dir.returncode != 0:
            return None

        # Get the current tag or commit
        result = subprocess.run(
            ["git", "describe", "--tags", "--dirty", "--always"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )

        if result.returncode == 0:
            version = result.stdout.strip()

            # Parse version format
            if version.startswith('v'):
                version = version[1:]  # Remove 'v' prefix

            # If it's just a commit hash (no tags), use fallback
            if len(version) == 7 or (len(version) > 7 and all(c in '0123456789abcdef' for c in version)):
                return None  # Fall back to static version

            # Handle dirty working directory
            if version.endswith('-dirty'):
                # If it's a tag with dirty suffix, clean it up properly
                clean_version = version[:-6]
                if clean_version and not all(c in '0123456789abcdef' for c in clean_version):
                    return clean_version + ".dev0"
                else:
                    return None  # Fall back to static version
            elif '-g' in version:
                # Format: tag-commits-ghash
                parts = version.split('-')
                if len(parts) >= 3:
                    tag, commits = parts[0], parts[1]
                    return f"{tag}.dev{commits}"

            return version

    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return None


def get_build_info() -> dict:
    """Get build information."""
    version = get_version()

    try:
        # Get git commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        commit_hash = result.stdout.strip() if result.returncode == 0 else "unknown"

        # Get git commit date
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ci"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        commit_date = result.stdout.strip() if result.returncode == 0 else "unknown"

        # Check if working directory is dirty
        result = subprocess.run(
            ["git", "diff", "--quiet"],
            capture_output=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        is_dirty = result.returncode != 0

    except (subprocess.CalledProcessError, FileNotFoundError):
        commit_hash = "unknown"
        commit_date = "unknown"
        is_dirty = False

    return {
        "version": version,
        "commit_hash": commit_hash,
        "commit_date": commit_date,
        "dirty": is_dirty
    }


# Main version export
__version__ = get_version()
