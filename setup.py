"""Setup script for llm-proxifier."""

from setuptools import setup, find_packages
import sys
import os

# Add src to path to import version
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from _version import get_version
    version = get_version()
except ImportError:
    # Fallback if _version module is not available
    version = "1.8.0-dev"

setup(
    name="llm-proxifier",
    version=version,
    description="A lightweight, intelligent proxy server that manages multiple LLaMA models on-demand",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="LLM Proxifier Contributors",
    url="https://github.com/fluffypony/llm-proxifier",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    package_data={
        "": ["py.typed"],
    },
    python_requires=">=3.8",
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "pyyaml>=6.0",
        "httpx>=0.25.0",
        "psutil>=5.9.0",
        "click>=8.0.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
        ],
        "docs": [
            "mkdocs>=1.5.0",
            "mkdocs-material>=9.0.0",
            "mkdocstrings[python]>=0.23.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "llm-proxifier=src.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    keywords="llm proxy llama ai model-management",
    license="MIT",
    project_urls={
        "Homepage": "https://github.com/fluffypony/llm-proxifier",
        "Repository": "https://github.com/fluffypony/llm-proxifier",
        "Issues": "https://github.com/fluffypony/llm-proxifier/issues",
        "Documentation": "https://github.com/fluffypony/llm-proxifier/blob/main/README.md",
    },
)
