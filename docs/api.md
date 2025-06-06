# API Documentation

LLM Proxifier provides both OpenAI-compatible endpoints and administrative endpoints for model management.

## Authentication

When authentication is enabled, include your API key in the Authorization header:

```
Authorization: Bearer your-api-key-here
```

## OpenAI-Compatible Endpoints

### Chat Completions

**POST** `/v1/chat/completions`

Compatible with OpenAI's chat completions API.

**Request Example:**
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "llama2-7b",
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "temperature": 0.7,
    "max_tokens": 100
  }'
```

**Response:**
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "llama2-7b",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! I'm doing well, thank you for asking."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 15,
    "total_tokens": 27
  }
}
```

### Text Completions

**POST** `/v1/completions`

Compatible with OpenAI's completions API.

**Request Example:**
```bash
curl -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "llama2-7b",
    "prompt": "The capital of France is",
    "temperature": 0.7,
    "max_tokens": 50
  }'
```

### List Models

**GET** `/v1/models`

List available models and their status.

**Response:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "llama2-7b",
      "object": "model",
      "created": 1677652288,
      "owned_by": "llm-proxifier",
      "permission": [],
      "root": "llama2-7b",
      "parent": null
    }
  ]
}
```

## Health and Monitoring

### Health Check

**GET** `/health`

Check server health and model status.

**Response:**
```json
{
  "status": "healthy",
  "uptime": "2h 15m 30s",
  "models": {
    "llama2-7b": {
      "status": "running",
      "port": 8001,
      "uptime": "1h 45m 12s"
    }
  },
  "system": {
    "memory": {
      "total": 16384,
      "available": 8192,
      "percent": 50.0
    }
  }
}
```

### Metrics

**GET** `/metrics`

Get usage metrics for all models.

**Response:**
```json
{
  "models": {
    "llama2-7b": {
      "request_count": 150,
      "memory_usage_mb": 4096.5,
      "cpu_usage_percent": 25.3,
      "uptime": "1h 45m 12s"
    }
  },
  "system": {
    "total_requests": 150,
    "active_models": 1
  }
}
```

## Administrative Endpoints

### Model Management

#### Start Model

**POST** `/admin/models/{model_name}/start`

Start a specific model.

**Response:**
```json
{
  "message": "Model 'llama2-7b' started successfully",
  "status": "running"
}
```

#### Stop Model

**POST** `/admin/models/{model_name}/stop`

Stop a specific model.

**Response:**
```json
{
  "message": "Model 'llama2-7b' stopped successfully", 
  "status": "stopped"
}
```

#### Model Status

**GET** `/admin/models/{model_name}/status`

Get detailed status of a specific model.

**Response:**
```json
{
  "status": "running",
  "port": 8001,
  "priority": 8,
  "resource_group": "small",
  "preload": false,
  "auto_start": true,
  "last_accessed": "2023-12-07T15:30:45.123456",
  "uptime": "1h 45m 12s",
  "memory_usage_mb": 4096.5,
  "cpu_usage_percent": 25.3,
  "request_count": 150
}
```

#### Reload Model

**POST** `/admin/models/{model_name}/reload`

Hot reload a specific model with current or new configuration.

**Response:**
```json
{
  "success": true,
  "message": "Model 'llama2-7b' reloaded successfully",
  "status": "running"
}
```

### Bulk Operations

#### Start All Models

**POST** `/admin/models/start-all`

Start all configured models.

**Response:**
```json
{
  "message": "Started 3/4 models",
  "results": {
    "llama2-7b": true,
    "codellama-13b": true,
    "mistral-7b": true,
    "llama2-70b": false
  }
}
```

#### Stop All Models

**POST** `/admin/models/stop-all`

Stop all running models except preloaded ones.

**Response:**
```json
{
  "message": "Stopped 2/3 models",
  "results": {
    "llama2-7b": true,
    "codellama-13b": true,
    "mistral-7b": false
  }
}
```

#### Restart All Models

**POST** `/admin/models/restart-all`

Restart all currently running models.

### Resource Group Management

#### Start Resource Group

**POST** `/admin/groups/{group_name}/start`

Start all models in a resource group.

**Response:**
```json
{
  "message": "Started 2/2 models in group 'small'",
  "results": {
    "llama2-7b": true,
    "mistral-7b": true
  }
}
```

#### Stop Resource Group

**POST** `/admin/groups/{group_name}/stop`

Stop all models in a resource group.

#### List Resource Groups

**GET** `/admin/groups`

List all resource groups and their status.

**Response:**
```json
{
  "small": {
    "total_models": 2,
    "running_models": 1,
    "models": ["llama2-7b", "mistral-7b"]
  },
  "medium": {
    "total_models": 1,
    "running_models": 0,
    "models": ["codellama-13b"]
  }
}
```

### Configuration Management

#### Reload Model Configuration

**POST** `/admin/models/reload-config`

Reload the models.yaml configuration file.

**Response:**
```json
{
  "message": "Configuration reloaded",
  "changes": {
    "added": ["new-model"],
    "removed": ["old-model"],
    "modified": ["llama2-7b"]
  }
}
```

#### Reload Auth Configuration

**POST** `/admin/auth/reload-config`

Reload the auth.yaml configuration file.

**Response:**
```json
{
  "message": "Auth configuration reloaded"
}
```

## Error Responses

All endpoints return structured error responses:

```json
{
  "error": {
    "code": "model_not_found",
    "message": "Model 'nonexistent' not found. Available models: ['llama2-7b', 'codellama-13b']",
    "type": "invalid_request"
  }
}
```

### Error Codes

- `model_not_found`: Requested model is not configured
- `model_not_running`: Model is not currently running
- `start_failed`: Failed to start model
- `stop_failed`: Failed to stop model
- `reload_failed`: Failed to reload model
- `invalid_request`: Request validation failed
- `internal_error`: Internal server error
- `rate_limit_exceeded`: API rate limit exceeded
- `unauthorized`: Authentication required or invalid

## Rate Limiting

When rate limiting is enabled, responses include rate limit headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1677652888
```

## Streaming Responses

For streaming completions, set `"stream": true` in your request:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2-7b",
    "messages": [{"role": "user", "content": "Count to 10"}],
    "stream": true
  }'
```

Streaming responses use Server-Sent Events (SSE) format:

```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"llama2-7b","choices":[{"index":0,"delta":{"content":"1"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"llama2-7b","choices":[{"index":0,"delta":{"content":", 2"},"finish_reason":null}]}

data: [DONE]
```
