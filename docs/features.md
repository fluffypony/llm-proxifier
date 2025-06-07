# LLM Proxifier Features Documentation

This document provides detailed explanations of LLM Proxifier's advanced features.

## Model Priority System

The priority system allows you to control the order in which models are started, ensuring that critical models are available first.

### How Priority Works

- **Priority Range**: 1-10 (10 = highest priority, 1 = lowest priority)
- **Startup Order**: Models with higher priority start first during auto-start
- **Resource Allocation**: In resource-constrained environments, higher priority models get preference
- **Default Priority**: Models without explicit priority default to 5

### Configuration Example

```yaml
models:
  critical-model:
    priority: 10        # Starts first
    auto_start: true
    model_path: "./models/critical.gguf"
    port: 11001
    
  standard-model:
    priority: 5         # Starts after critical
    auto_start: true
    model_path: "./models/standard.gguf"
    port: 11002
    
  experimental-model:
    priority: 1         # Starts last
    auto_start: false   # Only when requested
    model_path: "./models/experimental.gguf"
    port: 11003
```

### Best Practices

1. **Reserve Priority 10**: For mission-critical models only
2. **Use Priority 8-9**: For production models that need quick availability
3. **Use Priority 5-7**: For standard models
4. **Use Priority 1-3**: For experimental or development models
5. **Avoid Too Many High Priorities**: Spread priorities to ensure clear ordering

## Resource Groups

Resource groups allow you to organize models for bulk operations and logical grouping.

### Use Cases

- **Environment Separation**: production, staging, development
- **Functional Grouping**: coding, chat, analysis
- **Resource Management**: gpu-models, cpu-models
- **Team Organization**: team-a, team-b, shared

### Configuration Example

```yaml
models:
  production-chat:
    resource_group: "production"
    priority: 9
    preload: true
    
  production-code:
    resource_group: "production"
    priority: 8
    preload: true
    
  dev-experimental:
    resource_group: "development"
    priority: 3
    auto_start: false
```

### Bulk Operations

```bash
# Start all production models
curl -X POST http://localhost:8000/admin/groups/production/start

# Stop all development models
curl -X POST http://localhost:8000/admin/groups/development/stop

# Get status of all groups
curl http://localhost:8000/admin/groups/status
```

## Auto-Start and Preload System

### Auto-Start

Models with `auto_start: true` will automatically start when the server starts, following priority order.

**Best for:**
- Models used frequently throughout the day
- Production models that should always be available
- Models with fast startup times

### Preload

Models with `preload: true` will stay running permanently and won't be stopped during cleanup.

**Best for:**
- Mission-critical models that must always be available
- Models with very slow startup times
- Models that receive constant traffic

### Memory Considerations

**Warning**: Preloaded models consume memory permanently. Use sparingly!

```yaml
models:
  always-ready:
    preload: true       # Never stops, always available
    auto_start: true    # Starts on server startup
    priority: 10        # Highest priority
    
  frequently-used:
    preload: false      # Can be stopped during cleanup
    auto_start: true    # Starts on server startup
    priority: 8
    
  on-demand:
    preload: false      # Can be stopped
    auto_start: false   # Only starts when requested
    priority: 5
```

## Hot Model Swapping

Update model configurations without restarting the entire server.

### Supported Operations

1. **Configuration Updates**: Change model parameters, paths, ports
2. **Hot Reload**: Restart a specific model with new configuration
3. **Runtime Addition**: Add new models to running server
4. **Parameter Updates**: Update priority, resource groups, flags

### Example Workflow

```bash
# 1. Update model configuration in models.yaml
# 2. Hot reload the specific model
curl -X POST http://localhost:8000/admin/models/qwen-32b/reload

# 3. Verify the change
curl http://localhost:8000/admin/models/qwen-32b/status
```

### Limitations

- Port changes require model restart
- Model path changes require model restart
- Cannot change fundamental model architecture

## Request Queuing System

Handles requests gracefully during model transitions and startup.

### How It Works

1. **Request Received**: Client makes API request
2. **Model State Check**: Check if model is starting/reloading
3. **Queue Decision**: If model transitioning, queue the request
4. **Queue Response**: Return 202 Accepted with queue position
5. **Process When Ready**: Execute requests when model is available

### Queue Responses

```bash
# Request queued (model starting)
HTTP/202 Accepted
{
  "message": "Request queued",
  "request_id": "abc123",
  "position": 3,
  "model_state": "starting"
}

# Queue full (too many waiting requests)  
HTTP/503 Service Unavailable
Retry-After: 60
{
  "error": {
    "message": "Service temporarily unavailable - queue is full",
    "type": "service_unavailable"
  }
}
```

### Queue Management

```bash
# Monitor queue status
curl http://localhost:8000/admin/queue/status

# Clear stuck requests
curl -X POST http://localhost:8000/admin/queue/model-name/clear
```

### Configuration

Queue settings in the QueueManager:
- **Max Queue Size**: 100 requests per model (default)
- **Request Timeout**: 30 seconds (default)
- **Cleanup Interval**: 10 seconds (default)

## Authentication and Security

### API Key Management

```yaml
# config/auth.yaml
enabled: true
dashboard_auth_required: true

api_keys:
  admin-key:
    key: "your-secure-admin-key"
    permissions: ["admin", "models", "config"]
    expires: "2024-12-31T23:59:59Z"
    
  readonly-key:
    key: "readonly-monitoring-key"
    permissions: ["read"]
    
  team-key:
    key: "team-development-key"
    permissions: ["models"]

rate_limits:
  admin: 1000    # requests per minute
  default: 100
  readonly: 50

public_endpoints:
  - "/health"
  - "/metrics"
```

### Permission Types

- **admin**: Full access to all endpoints
- **models**: Start/stop models, view status
- **config**: Configuration management
- **read**: Read-only access to status and metrics

### Rate Limiting

- Per-API-key rate limiting
- Configurable limits by key type
- Automatic cleanup of rate limit counters

## Advanced Configuration Tips

### Multi-Environment Setup

```yaml
# Production configuration
models:
  prod-chat:
    resource_group: "production"
    priority: 10
    preload: true
    auto_start: true
    
  prod-code:
    resource_group: "production"
    priority: 9
    preload: true
    auto_start: true

# Development configuration  
  dev-experimental:
    resource_group: "development"
    priority: 3
    auto_start: false
    preload: false
```

### Resource Optimization

```yaml
# High-memory model (use preload sparingly)
large-model:
  preload: false      # Allow cleanup
  auto_start: true    # Start on demand
  priority: 6
  
# Fast-startup model (safe to preload)
small-model:
  preload: true       # Keep running
  auto_start: true
  priority: 8
```

### GPU Resource Management

```yaml
# GPU-intensive models
gpu-model-1:
  resource_group: "gpu-cluster"
  gpu_layers: -1      # All layers on GPU
  priority: 9
  
gpu-model-2:
  resource_group: "gpu-cluster"  
  gpu_layers: 20      # Partial GPU usage
  priority: 7
  
# CPU-only models
cpu-model:
  resource_group: "cpu-cluster"
  gpu_layers: 0       # CPU only
  priority: 5
```

## Best Practices Summary

1. **Use Priority Wisely**: Reserve high priorities for critical models
2. **Limit Preloading**: Only preload models that must always be available
3. **Group Logically**: Use resource groups for environment/team separation
4. **Monitor Queues**: Watch queue depth to identify bottlenecks
5. **Regular Backups**: Create configuration backups before major changes
6. **Test Hot Reloads**: Use hot reload for configuration updates
7. **Security First**: Use API keys and rate limiting in production
8. **Resource Planning**: Monitor memory usage with multiple preloaded models
