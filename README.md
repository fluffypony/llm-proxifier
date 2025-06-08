# LLM Proxifier

A lightweight, intelligent proxy server that manages multiple LLaMA models on-demand, providing OpenAI-compatible API endpoints with automatic lifecycle management.

## 🚀 Features

### Core Functionality
- **OpenAI-Compatible API**: Drop-in replacement for OpenAI endpoints (`/v1/chat/completions`, `/v1/completions`)
- **On-Demand Model Loading**: Models start automatically when requested and stop after inactivity
- **Multi-Model Support**: Run multiple models simultaneously with configurable limits
- **Streaming Support**: Full server-sent events (SSE) streaming support

### Advanced Model Management
- **Priority-Based Loading**: Configure model startup order with priority levels (1-10)
- **Resource Groups**: Organize models for bulk operations and management
- **Auto-Start & Preload**: Automatically start critical models on server startup
- **Hot Model Swapping**: Update model configurations without server restart
- **Request Queuing**: Intelligent request queuing during model transitions

### Administration & Monitoring
- **Advanced Dashboard**: Web-based interface with real-time monitoring
- **Queue Status Monitoring**: Real-time queue depth and request tracking
- **Configuration Management**: Hot-reload configurations with backup/restore
- **Health Monitoring**: Built-in health checks and comprehensive metrics
- **Resource Monitoring**: Memory and CPU usage tracking per model
- **Bulk Operations**: Start/stop multiple models or entire resource groups

### Security & Authentication
- **API Key Authentication**: Configurable API key management with permissions
- **Rate Limiting**: Per-key rate limiting with configurable thresholds
- **Dashboard Authentication**: Optional authentication for admin interface
- **Public Endpoints**: Configure endpoints that don't require authentication

## 📋 Requirements

- Python 3.8+
- `llama-server` (from llama.cpp) in your PATH
- Model files in GGUF format

## 🛠️ Quick Start

### Install from PyPI (Recommended)

```bash
# Install the package
pip install llm-proxifier

# Create a config directory
mkdir -p config

# Create your models configuration
cat > config/models.yaml << 'EOF'
models:
  llama-7b:
    port: 11001
    model_path: "./models/your-model.gguf"
    context_length: 4096
    gpu_layers: -1
    chat_format: llama-2
EOF

# Start the proxy server
llm-proxifier start
```

### Install from Source

#### Linux/macOS

```bash
# Clone the repository
git clone https://github.com/fluffypony/llm-proxifier.git
cd llm-proxifier

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure your models (edit config/models.yaml)
# Make sure your model paths are correct!

# Start the proxy server
./scripts/start_proxy.sh
```

#### Windows

```powershell
# Clone the repository
git clone https://github.com/fluffypony/llm-proxifier.git
cd llm-proxifier

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure your models (edit config/models.yaml)
# Make sure your model paths are correct!

# Start the proxy server
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Docker

```bash
# Build the Docker image
docker build -t llm-proxifier .

# Run with volume mounts for models and config
docker run -d \
  --name llm-proxifier \
  -p 8000:8000 \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/config:/app/config \
  -e LLM_PROXY_HOST=0.0.0.0 \
  -e LLM_PROXY_PORT=8000 \
  -e LLM_PROXY_MAX_CONCURRENT=4 \
  llm-proxifier

# For GPU support (requires NVIDIA Docker runtime)
docker run -d \
  --name llm-proxifier-gpu \
  --gpus all \
  -p 8000:8000 \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/config:/app/config \
  llm-proxifier
```

### Alternative Installation Methods

#### pipx Installation (System-wide)

```bash
# Install globally with pipx
pipx install llm-proxifier

# Run with custom config
llm-proxifier start --config /path/to/your/config/models.yaml --port 8000
```

## ⚙️ Configuration

### Advanced Model Configuration

LLM Proxifier now supports advanced model management features:

```yaml
models:
  # High-priority model that starts automatically
  qwen-32b:
    port: 11001
    model_path: "./models/qwen-32b/qwen2.5-coder-32b-instruct-q4_k_m.gguf"
    priority: 9                    # Higher priority loads first (1-10)
    resource_group: "coding"       # Group models for bulk operations
    auto_start: true              # Start automatically on server startup
    preload: false                # Keep running permanently (use sparingly)
    context_length: 32768
    gpu_layers: -1
    chat_format: chatml

  # Production model that's always ready
  llama-70b:
    port: 11004
    model_path: "./models/llama-70b/Meta-Llama-3-70B-Instruct-Q4_K_M.gguf"
    priority: 10                  # Highest priority
    resource_group: "production"
    auto_start: true
    preload: true                 # Always keep running
    context_length: 8192
    gpu_layers: -1
    chat_format: llama-2

  # Development model with lower priority
  llama-7b:
    port: 11005
    model_path: "./models/llama-7b/llama-2-7b-chat.gguf"
    priority: 3                   # Lower priority
    resource_group: "development"
    auto_start: false             # Start only when requested
    preload: false
    context_length: 4096
    gpu_layers: 20
```

### Basic Configuration

Edit `config/models.yaml` to configure your models:

```yaml
models:
  qwen-32b:
    port: 11001
    model_path: "./models/qwen-32b/qwen2.5-coder-32b-instruct-q4_k_m.gguf"
    context_length: 32768
    gpu_layers: -1
    chat_format: chatml
    additional_args:
      - "--mlock"
      - "--n_batch=512"

  llama-70b:
    port: 11004
    model_path: "./models/llama-70b/Meta-Llama-3-70B-Instruct-Q4_K_M.gguf"
    context_length: 8192
    gpu_layers: -1
    chat_format: llama-2
    additional_args:
      - "--mlock"
      - "--threads=16"
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PROXY_HOST` | `0.0.0.0` | Host to bind proxy server |
| `PROXY_PORT` | `8000` | Port for proxy server |
| `TIMEOUT_MINUTES` | `5` | Model inactivity timeout |
| `MAX_CONCURRENT_MODELS` | `4` | Maximum simultaneous models |
| `CONFIG_PATH` | `./config/models.yaml` | Path to model configuration |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

## 💻 Command Line Interface

### Basic Commands

```bash
# Start the server (default: on-demand mode)
llm-proxifier start

# Start with legacy auto-start behavior  
llm-proxifier start --no-on-demand

# Start on custom port with dashboard
llm-proxifier start --port 8080 --dashboard-port 3001

# Check server status
llm-proxifier status

# List available models
llm-proxifier models

# Open dashboard in browser
llm-proxifier dashboard

# Validate configuration
llm-proxifier config validate

# Show configuration details
llm-proxifier config show

# Show version information
llm-proxifier version
```

### Start Command Options

```bash
llm-proxifier start [OPTIONS]

Options:
  --host HOST                     Host to bind to (default: from config)
  --port PORT                     Port to bind to (default: from config)  
  --dashboard-port PORT           Dashboard port (default: from config)
  --disable-auth                  Disable authentication
  --disable-dashboard             Disable web dashboard
  --on-demand-only               Enable on-demand loading (default)
  --no-on-demand                 Use legacy auto-start behavior
  --log-level LEVEL              Set log level (DEBUG, INFO, WARNING, ERROR)
  --config PATH                  Path to models config file
  --auth-config PATH             Path to auth config file
```

### Global Options

```bash
  --version                      Show version and exit
  --config PATH                  Path to models config file
  --auth-config PATH             Path to auth config file  
  --host HOST                    Host to connect to
  --port PORT                    Port to connect to
  --log-level LEVEL              Set log level
```

## 🔌 API Usage

### Chat Completions

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-32b",
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "stream": false
  }'
```

### Streaming

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-32b",
    "messages": [
      {"role": "user", "content": "Write a Python function to calculate fibonacci"}
    ],
    "stream": true
  }'
```

### List Models

```bash
curl http://localhost:8000/v1/models
```

### Health Check

```bash
curl http://localhost:8000/health
```

### Dashboard Health Check

The dashboard includes an enhanced health endpoint for connection monitoring:

```bash
curl http://localhost:8000/dashboard/api/health
```

Response format:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "queue_manager_available": true,
  "queue_manager_responsive": true,
  "model_count": 3,
  "version": "1.0.0"
}
```

### Metrics

```bash
curl http://localhost:8000/metrics
```

## 🎮 Admin Endpoints

### Model Management

```bash
# Start a model manually
curl -X POST http://localhost:8000/admin/models/qwen-32b/start

# Stop a model
curl -X POST http://localhost:8000/admin/models/qwen-32b/stop

# Get model status
curl http://localhost:8000/admin/models/qwen-32b/status

# Get all models status
curl http://localhost:8000/admin/models/status

# Hot reload a model configuration
curl -X POST http://localhost:8000/admin/models/qwen-32b/reload
```

### Bulk Operations

```bash
# Start all models
curl -X POST http://localhost:8000/admin/models/start-all

# Stop all models (except preloaded)
curl -X POST http://localhost:8000/admin/models/stop-all

# Restart all running models
curl -X POST http://localhost:8000/admin/models/restart-all
```

### Resource Group Management

```bash
# Get resource group status
curl http://localhost:8000/admin/groups/status

# Start all models in a resource group
curl -X POST http://localhost:8000/admin/groups/production/start

# Stop all models in a resource group
curl -X POST http://localhost:8000/admin/groups/development/stop
```

### Queue Management

```bash
# Get queue status for all models
curl http://localhost:8000/admin/queue/status

# Get queue status for specific model
curl http://localhost:8000/admin/queue/qwen-32b/status

# Clear queue for specific model
curl -X POST http://localhost:8000/admin/queue/qwen-32b/clear
```

### Configuration Management

```bash
# Get models configuration schema
curl http://localhost:8000/admin/config/models/schema

# List configuration backups
curl http://localhost:8000/admin/config/models/backups

# Create configuration backup
curl -X POST "http://localhost:8000/admin/config/models/backup?description=manual-backup"

# Restore from backup
curl -X POST http://localhost:8000/admin/config/models/restore/models_20240101_120000

# Validate current configuration
curl http://localhost:8000/admin/config/validation/models
```

## 📊 Web Dashboard

LLM Proxifier includes a comprehensive web dashboard for monitoring and managing your models:

### Accessing the Dashboard

```bash
# Navigate to the dashboard in your browser
http://localhost:8000/dashboard
```

### Dashboard Features

- **Real-time Model Status**: Live monitoring of all model states and resource usage
- **Priority Management**: Drag-and-drop interface for reordering model priorities  
- **Resource Group Control**: Visual management of model groups with bulk operations
- **Queue Monitoring**: Real-time queue depth and request tracking with clear queue functionality
- **Configuration Editor**: In-browser YAML editor with syntax highlighting and validation
- **Backup Management**: Create, restore, and manage configuration backups
- **Bulk Operations**: Start/stop multiple models or entire resource groups
- **Performance Metrics**: CPU, memory usage, and request statistics

### Enhanced Error Handling & Monitoring

LLM Proxifier now includes comprehensive error handling and connection monitoring:

- **Connection Health Monitoring**: Automatic health checks every 30 seconds with visual status indicators
- **Network Resilience**: Request timeouts (10s), exponential backoff retry logic, and graceful degradation
- **Offline Detection**: Browser connection state monitoring with automatic retry on reconnection
- **Enhanced Error Display**: Structured validation errors with location highlighting in configuration editor
- **Visual Feedback**: Error banners, health status indicators, and retry buttons throughout the UI
- **Robust Queue Monitoring**: Data validation, error recovery, and connection state awareness
- **Dark Theme Support**: Complete styling for all error states and health indicators

#### Error Handling Features

**Network Error Recovery:**
- Automatic retry with exponential backoff (up to 5 attempts)
- Request timeout protection (10 seconds)
- Connection state monitoring with visual feedback
- Graceful degradation when services are unavailable

**User Experience:**
- Clear error messages with specific HTTP status code handling
- Visual error banners with manual retry options
- Health status indicators at the top of the page
- Structured validation error display with "Show Location" buttons

**Configuration Validation:**
- Enhanced error display with HTML escaping and security
- Location highlighting for configuration errors
- Comprehensive validation with both errors and warnings
- Real-time validation feedback during editing

### Dashboard Screenshots

The dashboard provides:
- A clean, responsive interface that works on desktop and mobile
- Real-time WebSocket updates for live status monitoring
- Interactive charts and graphs for performance metrics
- Confirmation dialogs for destructive operations
- Syntax-highlighted configuration editing with live validation

## 🧪 Testing

Run the test suite:

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/ -v

# Run with coverage
pip install pytest-cov
pytest tests/ --cov=src --cov-report=html
```

## 🐛 Troubleshooting

### Model Won't Start

1. **Check model path**: Ensure the GGUF file exists and is readable
2. **Port conflicts**: Verify ports in config are available
3. **llama-server**: Ensure `llama-server` is in your PATH
4. **Memory**: Check if you have enough RAM for the model

```bash
# Test llama-server directly
llama-server --model ./path/to/model.gguf --port 11001 --ctx-size 4096
```

### Connection Issues

1. **Firewall**: Check if ports are blocked
2. **Binding**: Try binding to `127.0.0.1` instead of `0.0.0.0`
3. **Logs**: Check proxy logs for detailed error messages

### Performance Issues

1. **Resource limits**: Monitor CPU/memory usage with `/metrics`
2. **Concurrent models**: Reduce `MAX_CONCURRENT_MODELS` if system is overloaded
3. **Model size**: Consider using smaller quantized models

### Queue and Priority Issues

1. **Models not auto-starting**: Check `auto_start: true` in configuration
2. **Priority not working**: Ensure priority values are between 1-10
3. **Queue full errors**: Monitor queue depth with `/admin/queue/status`
4. **Resource group conflicts**: Verify models are in correct groups

```bash
# Check queue status
curl http://localhost:8000/admin/queue/status

# Clear stuck queue
curl -X POST http://localhost:8000/admin/queue/model-name/clear

# Verify priority configuration
curl http://localhost:8000/dashboard/api/models/priority
```

### Configuration Issues

1. **Config not reloading**: Use hot-reload endpoints instead of restarting
2. **Backup failures**: Check file permissions in config/backups directory
3. **Validation errors**: Use validation endpoints before applying changes
4. **Authentication problems**: Verify API keys in auth.yaml

```bash
# Validate configuration before applying
curl http://localhost:8000/admin/config/validation/models

# Create backup before changes
curl -X POST "http://localhost:8000/admin/config/models/backup?description=before-changes"

# Hot-reload specific model
curl -X POST http://localhost:8000/admin/models/model-name/reload
```

### Dashboard Issues

1. **Dashboard not loading**: Check if port 8000 is accessible
2. **Real-time updates not working**: Verify WebSocket connection  
3. **Authentication required**: Check `dashboard_auth_required` in auth.yaml
4. **Configuration editor errors**: Validate YAML syntax before saving

### Error Handling & Connection Issues

The dashboard now includes comprehensive error handling and monitoring:

1. **Connection health monitoring**: Automatic health checks every 30 seconds
2. **Network error recovery**: Exponential backoff retry with up to 5 attempts
3. **Offline detection**: Visual indicators when internet connection is lost
4. **Error banners**: Clear error messages with manual retry options

**If you see connection issues:**
```bash
# Test the dashboard health endpoint
curl http://localhost:8000/dashboard/api/health

# Check if queue manager is responsive
curl http://localhost:8000/dashboard/api/queue/status

# Verify basic connectivity
curl http://localhost:8000/health
```

**Dashboard error indicators:**
- **Red banner at top**: Connection issues detected
- **Warning icon in queue monitor**: Queue data validation failed  
- **Retry buttons**: Manual retry options for failed operations
- **Auto-refresh disabled**: After 5 consecutive failures (click refresh to re-enable)

## 📊 Monitoring

The proxy provides detailed metrics at `/metrics`:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "models": {
    "qwen-32b": {
      "status": "running",
      "request_count": 42,
      "memory_usage_mb": 8192.5,
      "cpu_usage_percent": 15.2,
      "uptime": "0:45:30",
      "last_accessed": "2024-01-15T10:29:45Z"
    }
  }
}
```

## 🔧 Development

### Project Structure

```
llm-proxifier/
├── src/
│   ├── main.py              # FastAPI application
│   ├── model_manager.py     # Model lifecycle management
│   ├── proxy_handler.py     # Request proxying
│   ├── dashboard.py         # Dashboard API endpoints
│   ├── queue_manager.py     # Queue management system
│   ├── config.py            # Configuration management
│   └── utils.py             # Utility functions
├── static/
│   ├── js/
│   │   ├── queue-monitor.js     # Enhanced queue monitoring with error handling
│   │   ├── config-editor.js     # Configuration editor with validation
│   │   ├── connection-health.js # Connection health monitoring system
│   │   └── dashboard.js         # Main dashboard functionality
│   └── css/
│       └── dashboard.css        # Dashboard styling with error states
├── templates/
│   └── dashboard.html       # Dashboard HTML template
├── config/
│   └── models.yaml          # Model configurations
├── scripts/
│   ├── start_proxy.sh       # Launch script
│   └── stop_proxy.sh        # Shutdown script
├── tests/                   # Test suite
└── requirements.txt
```

### Adding New Features

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass: `pytest tests/`
6. Commit your changes: `git commit -m 'Add amazing feature'`
7. Push to the branch: `git push origin feature/amazing-feature`
8. Open a Pull Request

### Code Style

- Follow PEP 8
- Use type hints
- Add docstrings for public functions
- Keep functions focused and small
- Write tests for new functionality

## 📄 License

This project is licensed under the BSD 3-Clause License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

### Reporting Bugs

1. Check existing issues first
2. Create a new issue with:
   - Clear description of the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - System information (OS, Python version, etc.)
   - Relevant log output

### Feature Requests

1. Check if the feature already exists or is planned
2. Open an issue describing:
   - The problem you're trying to solve
   - Your proposed solution
   - Any alternatives considered
   - Example use cases

### Pull Requests

1. Fork and create a feature branch
2. Write clear, focused commits
3. Add tests for new functionality
4. Update documentation as needed
5. Ensure CI passes
6. Request review from maintainers

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/llm-proxifier.git
cd llm-proxifier

# Set up development environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If it exists

# Install pre-commit hooks
pre-commit install

# Run tests to ensure everything works
pytest tests/
```

## 🙏 Acknowledgments

- [llama.cpp](https://github.com/ggerganov/llama.cpp) for the excellent model server
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- The open-source LLM community for making this possible

## 📞 Support

- 📖 Documentation: Check this README and inline code comments
- 🐛 Bug Reports: [GitHub Issues](https://github.com/fluffypony/llm-proxifier/issues)
- 💬 Questions: [GitHub Discussions](https://github.com/fluffypony/llm-proxifier/discussions)
- 📧 Security Issues: Email maintainers directly

---

**Happy LLM proxying! 🚀**
