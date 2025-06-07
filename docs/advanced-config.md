# Advanced Configuration Guide

This guide covers advanced configuration strategies for LLM Proxifier in production environments.

## Priority System Best Practices

### Priority Allocation Strategy

**Priority 10**: Mission-critical models only
- Models that must always be available
- Customer-facing production models
- Limited to 1-2 models maximum

**Priority 8-9**: Production models
- Important business models
- Models with SLA requirements
- High-traffic endpoints

**Priority 5-7**: Standard models
- Regular business models
- Development and testing models
- Internal tools

**Priority 1-4**: Experimental models
- Research and development
- Unstable or testing models
- Personal projects

### Example Production Priority Setup

```yaml
models:
  # Customer-facing chat (highest priority)
  customer-support:
    priority: 10
    resource_group: "production"
    preload: true
    auto_start: true
    model_path: "./models/customer-support-model.gguf"
    port: 11001
    
  # Code generation for paid users
  premium-coder:
    priority: 9
    resource_group: "production"
    preload: true
    auto_start: true
    model_path: "./models/premium-coder.gguf"
    port: 11002
    
  # General purpose model
  general-chat:
    priority: 7
    resource_group: "production"
    preload: false
    auto_start: true
    model_path: "./models/general-chat.gguf"
    port: 11003
    
  # Development testing
  experimental-v2:
    priority: 3
    resource_group: "development"
    preload: false
    auto_start: false
    model_path: "./models/experimental-v2.gguf"
    port: 11004
```

## Resource Group Strategies

### Environment-Based Groups

```yaml
models:
  # Production environment
  prod-model-1:
    resource_group: "production"
    priority: 9
    
  prod-model-2:
    resource_group: "production"
    priority: 8
    
  # Staging environment
  staging-model:
    resource_group: "staging"
    priority: 6
    
  # Development environment
  dev-model:
    resource_group: "development"
    priority: 3
```

### Team-Based Groups

```yaml
models:
  # Team A models
  team-a-chat:
    resource_group: "team-a"
    priority: 7
    
  team-a-code:
    resource_group: "team-a"
    priority: 6
    
  # Team B models
  team-b-analysis:
    resource_group: "team-b"
    priority: 7
    
  # Shared models
  shared-general:
    resource_group: "shared"
    priority: 8
```

### Functional Groups

```yaml
models:
  # Chat models
  chat-gpt4-clone:
    resource_group: "chat"
    priority: 8
    
  chat-creative:
    resource_group: "chat"
    priority: 6
    
  # Code models
  code-completion:
    resource_group: "coding"
    priority: 9
    
  code-review:
    resource_group: "coding"
    priority: 7
    
  # Analysis models
  data-analysis:
    resource_group: "analysis"
    priority: 6
```

## Auto-Start and Preload for Production

### High-Availability Setup

```yaml
models:
  # Always available (preloaded)
  primary-chat:
    preload: true
    auto_start: true
    priority: 10
    resource_group: "always-on"
    
  # Backup model (auto-start but not preloaded)
  backup-chat:
    preload: false
    auto_start: true
    priority: 9
    resource_group: "backup"
    
  # On-demand models
  specialized-model:
    preload: false
    auto_start: false
    priority: 5
    resource_group: "on-demand"
```

### Memory Optimization Strategy

```yaml
models:
  # Small model - safe to preload
  small-efficient:
    preload: true       # ~2GB RAM
    auto_start: true
    priority: 8
    
  # Medium model - auto-start only
  medium-general:
    preload: false      # ~8GB RAM
    auto_start: true
    priority: 7
    
  # Large model - on-demand only
  large-specialized:
    preload: false      # ~24GB RAM
    auto_start: false
    priority: 5
```

## Memory and Resource Optimization

### GPU Memory Management

```yaml
models:
  # Full GPU utilization
  gpu-exclusive:
    gpu_layers: -1          # All layers on GPU
    resource_group: "gpu-primary"
    priority: 9
    preload: true
    
  # Partial GPU usage
  gpu-shared:
    gpu_layers: 20          # 20 layers on GPU
    resource_group: "gpu-shared"
    priority: 7
    preload: false
    
  # CPU fallback
  cpu-backup:
    gpu_layers: 0           # CPU only
    resource_group: "cpu-fallback"
    priority: 5
    auto_start: true
```

### CPU and Thread Configuration

```yaml
models:
  # High-performance model
  performance-model:
    additional_args:
      - "--threads=16"       # Use 16 CPU threads
      - "--n_batch=2048"     # Large batch size
      - "--mlock"            # Lock memory
    priority: 9
    
  # Balanced model
  balanced-model:
    additional_args:
      - "--threads=8"        # Moderate CPU usage
      - "--n_batch=512"      # Standard batch
    priority: 7
    
  # Low-resource model
  efficient-model:
    additional_args:
      - "--threads=4"        # Minimal CPU usage
      - "--n_batch=128"      # Small batch
    priority: 5
```

## Multi-Environment Configuration Management

### Development Environment

```yaml
# config/models-dev.yaml
models:
  dev-chat:
    priority: 5
    resource_group: "development"
    auto_start: false
    preload: false
    model_path: "./models/dev/chat-model.gguf"
    port: 11001
    context_length: 4096
    additional_args:
      - "--threads=4"
      - "--n_batch=256"
```

### Staging Environment

```yaml
# config/models-staging.yaml
models:
  staging-chat:
    priority: 7
    resource_group: "staging"
    auto_start: true
    preload: false
    model_path: "./models/staging/chat-model.gguf"
    port: 11001
    context_length: 8192
    additional_args:
      - "--threads=8"
      - "--n_batch=512"
```

### Production Environment

```yaml
# config/models-prod.yaml
models:
  prod-chat:
    priority: 10
    resource_group: "production"
    auto_start: true
    preload: true
    model_path: "./models/prod/chat-model.gguf"
    port: 11001
    context_length: 16384
    additional_args:
      - "--threads=16"
      - "--n_batch=1024"
      - "--mlock"
      - "--numa"
```

## Authentication Configuration for Production

### Multi-Tier API Keys

```yaml
# config/auth.yaml
enabled: true
dashboard_auth_required: true

api_keys:
  # System administrator
  system-admin:
    key: "admin-super-secret-key-change-this"
    permissions: ["admin", "models", "config", "queue"]
    expires: "2024-12-31T23:59:59Z"
    
  # Operations team
  ops-team:
    key: "ops-team-key-change-this"
    permissions: ["models", "queue"]
    expires: "2024-12-31T23:59:59Z"
    
  # Development team
  dev-team:
    key: "dev-team-key-change-this"
    permissions: ["models"]
    expires: "2024-06-30T23:59:59Z"
    
  # Monitoring systems
  monitoring:
    key: "monitoring-readonly-key"
    permissions: ["read"]
    # No expiration for monitoring
    
  # External API consumers
  api-consumer-1:
    key: "consumer-1-api-key"
    permissions: []  # Only basic API access
    expires: "2024-03-31T23:59:59Z"

rate_limits:
  admin: 10000      # High limit for admin operations
  ops: 5000         # Operations team
  dev: 1000         # Development team
  monitoring: 100   # Monitoring queries
  default: 50       # External consumers

public_endpoints:
  - "/health"
  - "/metrics"
  - "/v1/models"    # Allow model discovery
```

### Security Best Practices

1. **Rotate Keys Regularly**: Set expiration dates on all keys
2. **Principle of Least Privilege**: Give minimum required permissions
3. **Monitor Usage**: Track API key usage and rate limits
4. **Secure Storage**: Store keys securely, never in code
5. **Environment Variables**: Use environment variables for keys

```bash
# Environment variable override
export LLM_PROXY_API_KEY="your-production-key"
export LLM_PROXY_ADMIN_KEY="your-admin-key"
```

## Configuration Backup and Restore Procedures

### Automated Backup Strategy

```bash
#!/bin/bash
# backup-config.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./config/backups"

# Create automatic backup
curl -X POST "http://localhost:8000/admin/config/models/backup?description=automated-backup-${DATE}"
curl -X POST "http://localhost:8000/admin/config/auth/backup?description=automated-backup-${DATE}"

# Keep only last 30 backups
find ${BACKUP_DIR} -name "*.yaml" -mtime +30 -delete
find ${BACKUP_DIR} -name "*.json" -mtime +30 -delete
```

### Pre-Change Backup

```bash
# Before making changes
curl -X POST "http://localhost:8000/admin/config/models/backup?description=before-priority-update"

# Make changes
# Edit config or use API

# Validate changes
curl http://localhost:8000/admin/config/validation/models

# If validation fails, restore backup
curl -X POST http://localhost:8000/admin/config/models/restore/models_20240315_120000
```

### Configuration Version Control

```bash
# Track configuration changes in git
cd config/
git init
git add models.yaml auth.yaml
git commit -m "Initial configuration"

# After each change
git add -A
git commit -m "Update model priorities for production deployment"
git tag -a "v1.2.0" -m "Production configuration v1.2.0"
```

## Monitoring and Alerting Setup

### Health Check Configuration

```yaml
# config/monitoring.yaml
health_checks:
  interval: 30                    # seconds
  timeout: 10                     # seconds
  failure_threshold: 3            # failures before alert
  
alerts:
  webhook_url: "https://your-alerting-system.com/webhook"
  email: "admin@your-company.com"
  
metrics:
  export_interval: 60             # seconds
  retention_days: 30
```

### Production Monitoring Script

```bash
#!/bin/bash
# monitor-llm-proxy.sh

# Check overall health
curl -f http://localhost:8000/health || exit 1

# Check critical models
CRITICAL_MODELS=("customer-support" "premium-coder")
for model in "${CRITICAL_MODELS[@]}"; do
    STATUS=$(curl -s "http://localhost:8000/admin/models/${model}/status" | jq -r '.status')
    if [ "$STATUS" != "running" ]; then
        echo "ALERT: Critical model $model is not running"
        # Send alert
    fi
done

# Check queue depths
QUEUE_STATUS=$(curl -s "http://localhost:8000/admin/queue/status")
echo "$QUEUE_STATUS" | jq -r '.[] | select(.queue_size > 10) | "ALERT: High queue depth for " + .model_name'
```

## Troubleshooting Production Issues

### Common Production Problems

1. **Memory Exhaustion**: Too many preloaded models
2. **Startup Failures**: Port conflicts or missing models
3. **Queue Saturation**: Not enough concurrent models
4. **Authentication Issues**: Expired or invalid API keys

### Debug Configuration

```yaml
# Enable debug mode temporarily
debug:
  enabled: true
  log_level: "DEBUG"
  log_requests: true
  log_responses: false    # Don't log sensitive data
  
# Increase timeouts for debugging
timeouts:
  model_start: 300        # 5 minutes for slow models
  request_timeout: 120    # 2 minutes for complex requests
```

### Performance Tuning

```yaml
# High-performance production setup
performance:
  max_concurrent_models: 8        # Increase if you have resources
  cleanup_interval: 60            # Longer cleanup interval
  queue_size: 200                 # Larger queues
  
models:
  high-perf-model:
    additional_args:
      - "--n_gpu_layers=-1"       # All GPU layers
      - "--n_threads=32"          # Max CPU threads
      - "--n_batch=2048"          # Large batch size
      - "--use_mmap=false"        # Disable mmap for speed
      - "--use_mlock=true"        # Lock memory
      - "--numa=true"             # NUMA optimization
```

This advanced configuration guide provides the foundation for running LLM Proxifier in production environments with proper resource management, security, and monitoring.
