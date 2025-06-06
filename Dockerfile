FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash llm-proxy

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY --chown=llm-proxy:llm-proxy . .

# Create necessary directories
RUN mkdir -p /app/models /app/config /app/templates /app/static

# Switch to app user
USER llm-proxy

# Set environment variables
ENV PYTHONPATH=/app
ENV PROXY_HOST=0.0.0.0
ENV PROXY_PORT=8000
ENV DASHBOARD_PORT=3000

# Expose ports
EXPOSE 8000 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
