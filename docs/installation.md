# Installation Guide

## System Requirements

- Python 3.8 or higher
- Git (for development installation)
- pipx (recommended for installation)

## Installation Methods

### 1. Install with pipx (Recommended)

```bash
# Install pipx if not already installed
pip install --user pipx
pipx ensurepath

# Install LLM Proxifier
pipx install llm-proxifier

# Verify installation
llm-proxifier --version
```

### 2. Install with pip

```bash
pip install llm-proxifier
```

### 3. Development Installation

```bash
# Clone the repository
git clone https://github.com/fluffypony/llm-proxifier.git
cd llm-proxifier

# Run development setup script
./scripts/dev_install.sh
```

## First-Time Setup

### 1. Create Configuration Directory

```bash
mkdir -p config
```

### 2. Create Models Configuration

Create `config/models.yaml`:

```yaml
models:
  llama2-7b:
    port: 8001
    model_path: "./models/llama-2-7b-chat.Q4_K_M.gguf"
    context_length: 4096
    gpu_layers: 35
    chat_format: "llama-2"
    auto_start: true
    preload: false
    priority: 8
    resource_group: "small"
    
  codellama-13b:
    port: 8002
    model_path: "./models/codellama-13b-instruct.Q4_K_M.gguf"
    context_length: 16384
    gpu_layers: 40
    chat_format: "codellama"
    auto_start: false
    preload: true
    priority: 5
    resource_group: "medium"
```

### 3. Create Authentication Configuration (Optional)

Create `config/auth.yaml`:

```yaml
authentication:
  enabled: true
  dashboard_auth_required: true
  public_endpoints:
    - "/health"
    - "/metrics"
  api_keys:
    - key: "your-api-key-here"
      name: "default"
      permissions: ["*"]
    - key: "readonly-key"
      name: "readonly"
      permissions: ["/v1/models", "/health", "/metrics"]
  rate_limits:
    default: 100
```

### 4. Download Models

Download your GGUF model files to the `./models/` directory or update the `model_path` in your configuration to point to existing model files.

## Usage

### Start the Server

```bash
# Basic start
llm-proxifier start

# Custom configuration
llm-proxifier start --config ./my-config/models.yaml --port 9000

# Development mode (no auth)
llm-proxifier start --disable-auth --log-level DEBUG
```

### Check Status

```bash
llm-proxifier status
```

### List Models

```bash
llm-proxifier models
```

### Open Dashboard

```bash
llm-proxifier dashboard
```

## Environment Variables

You can also configure LLM Proxifier using environment variables. Create a `.env` file or export these variables:

```bash
# Server Configuration
PROXY_HOST=0.0.0.0
PROXY_PORT=8000
LOG_LEVEL=INFO

# Dashboard Configuration  
DASHBOARD_PORT=3000
DASHBOARD_ENABLED=true

# Authentication Configuration
AUTH_ENABLED=true
AUTH_CONFIG_PATH=./config/auth.yaml

# Model Configuration
CONFIG_PATH=./config/models.yaml
TIMEOUT_MINUTES=2
MAX_CONCURRENT_MODELS=4
HEALTH_CHECK_INTERVAL=30
```

## Troubleshooting

### Common Issues

#### 1. Port Already in Use

**Error**: `Port {port} is already in use`

**Solution**: 
- Check if another service is using the port: `lsof -i :{port}`
- Change the port in your configuration
- Stop the conflicting service

#### 2. Model File Not Found

**Error**: `Model path {path} does not exist`

**Solution**:
- Verify the model file exists at the specified path
- Update the `model_path` in your configuration
- Download the required model file

#### 3. Memory Issues

**Error**: Model fails to start or crashes

**Solution**:
- Reduce `gpu_layers` in configuration
- Reduce `max_concurrent_models`
- Ensure sufficient RAM/VRAM available
- Use smaller quantized models (Q4_K_M instead of Q8_0)

#### 4. Permission Denied

**Error**: Permission denied when starting models

**Solution**:
- Check file permissions on model files
- Ensure LLM Proxifier has read access to model directory
- Run with appropriate user permissions

### Getting Help

1. Check the logs for detailed error messages
2. Validate your configuration: `llm-proxifier config validate`
3. Test with minimal configuration
4. Check the [GitHub Issues](https://github.com/fluffypony/llm-proxifier/issues)

## Uninstalling

### pipx Installation

```bash
pipx uninstall llm-proxifier
```

### pip Installation

```bash
pip uninstall llm-proxifier
```

### Development Installation

```bash
# Remove from pipx if installed in development mode
pipx uninstall llm-proxifier

# Remove virtual environment
rm -rf .venv

# Remove build artifacts
rm -rf build/ dist/ *.egg-info/
```
