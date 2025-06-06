# LLM Proxifier

A lightweight, intelligent proxy server that manages multiple LLaMA models on-demand, providing OpenAI-compatible API endpoints with automatic lifecycle management.

## 🚀 Features

- **OpenAI-Compatible API**: Drop-in replacement for OpenAI endpoints (`/v1/chat/completions`, `/v1/completions`)
- **On-Demand Model Loading**: Models start automatically when requested and stop after inactivity
- **Multi-Model Support**: Run multiple models simultaneously with configurable limits
- **Automatic Lifecycle Management**: 2-minute timeout with graceful shutdown
- **Health Monitoring**: Built-in health checks and metrics endpoints
- **Admin Interface**: Manual model control and status monitoring
- **Streaming Support**: Full server-sent events (SSE) streaming support
- **Resource Monitoring**: Memory and CPU usage tracking per model

## 📋 Requirements

- Python 3.8+
- `llama-server` (from llama.cpp) in your PATH
- Model files in GGUF format

## 🛠️ Quick Start

### Linux/macOS

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

### Windows

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

### Docker (Alternative)

```bash
# TODO: Docker support coming soon
```

## ⚙️ Configuration

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
| `TIMEOUT_MINUTES` | `2` | Model inactivity timeout |
| `MAX_CONCURRENT_MODELS` | `4` | Maximum simultaneous models |
| `CONFIG_PATH` | `./config/models.yaml` | Path to model configuration |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

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

### Metrics

```bash
curl http://localhost:8000/metrics
```

## 🎮 Admin Endpoints

### Start a Model Manually

```bash
curl -X POST http://localhost:8000/admin/models/qwen-32b/start
```

### Stop a Model

```bash
curl -X POST http://localhost:8000/admin/models/qwen-32b/stop
```

### Get Model Status

```bash
curl http://localhost:8000/admin/models/qwen-32b/status
```

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
│   ├── config.py            # Configuration management
│   └── utils.py             # Utility functions
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
