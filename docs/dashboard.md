# Dashboard Guide

The LLM Proxifier dashboard provides a comprehensive web interface for monitoring and managing your models in real-time.

## Accessing the Dashboard

The dashboard is available at `http://localhost:8000/dashboard` when the server is running.

### Authentication

If authentication is enabled in your configuration:

```yaml
# config/auth.yaml
enabled: true
dashboard_auth_required: true
```

You'll need to provide an API key with appropriate permissions to access the dashboard.

## Dashboard Overview

The dashboard consists of several main sections:

### 1. Model Status Overview
- Real-time status of all configured models
- Color-coded status indicators (Running, Stopped, Starting, etc.)
- Resource usage metrics (CPU, Memory)
- Request counts and uptime information

### 2. Priority Management Panel
- Visual representation of model priorities
- Drag-and-drop interface for reordering priorities
- Bulk priority updates
- Auto-start and preload indicators

### 3. Resource Group Management
- Grouped view of models by resource group
- Bulk operations for entire groups
- Group-level statistics and health indicators
- Visual group organization

### 4. Queue Status Monitor
- Real-time queue depth monitoring
- Queue statistics and trends
- Clear queue functionality
- Request timeout visualization

### 5. Configuration Editor
- In-browser YAML editor with syntax highlighting
- Real-time validation
- Configuration backup and restore
- Split-view editing

## Feature Details

### Real-Time Model Status

The dashboard displays comprehensive information about each model:

**Status Indicators:**
- 🟢 **Running**: Model is active and accepting requests
- 🟡 **Starting**: Model is in the startup process
- 🔴 **Stopped**: Model is not running
- 🟠 **Stopping**: Model is shutting down
- 🔵 **Reloading**: Model is being reloaded with new configuration

**Resource Metrics:**
- CPU usage percentage
- Memory consumption in MB
- Request count since startup
- Uptime duration
- Last access timestamp

### Priority Management Interface

The priority management panel allows you to:

**View Current Priorities:**
```
Priority 10: customer-support (Running) [Production]
Priority 9:  premium-coder (Running) [Production]  
Priority 8:  general-chat (Stopped) [Production]
Priority 5:  dev-model (Stopped) [Development]
```

**Drag-and-Drop Reordering:**
- Simply drag models to reorder priorities
- Changes are applied immediately
- Visual feedback during dragging
- Automatic priority number updates

**Bulk Priority Updates:**
- Select multiple models
- Set priorities in batch
- Confirm changes before applying

### Resource Group Control

Organize and manage models by resource groups:

**Group Overview:**
```
Production Group (2/3 running)
├── customer-support: Running
├── premium-coder: Running  
└── general-chat: Stopped

Development Group (0/2 running)
├── dev-model: Stopped
└── experimental: Stopped
```

**Group Operations:**
- **Start Group**: Start all models in the group (respects priority order)
- **Stop Group**: Stop all non-preloaded models in the group
- **Restart Group**: Restart all currently running models in the group
- **Group Stats**: View aggregate statistics for the group

### Queue Status Monitoring

Monitor request queues in real-time:

**Queue Dashboard:**
```
Model: customer-support
├── Queue Depth: 3 requests
├── Max Queue Size: 100
├── Pending Requests: 2
├── Queue State: Normal
└── Average Wait Time: 1.2s

Model: premium-coder
├── Queue Depth: 0 requests
├── Max Queue Size: 100
├── Pending Requests: 0
├── Queue State: Empty
└── Average Wait Time: 0s
```

**Queue Actions:**
- **Clear Queue**: Remove all queued requests for a model
- **View Queue Details**: See individual queued requests
- **Queue Alerts**: Visual warnings when queues are full or backed up

### Configuration Management

#### Configuration Editor Features

**Syntax Highlighting:**
- YAML syntax highlighting
- Error highlighting for invalid syntax
- Auto-completion for common fields
- Collapsible sections for better organization

**Real-Time Validation:**
- Validates configuration as you type
- Shows validation errors inline
- Prevents saving invalid configurations
- Suggests fixes for common issues

**Split-View Editing:**
```
┌─────────────────┬─────────────────┐
│ Configuration   │ Live Preview    │
│ Editor          │                 │
│                 │                 │
│ models:         │ ✓ 3 models      │
│   model-1:      │ ✓ Valid ports   │
│     port: 11001 │ ✓ Paths exist   │
│     priority: 9 │ ⚠ High memory   │
│                 │   usage         │
└─────────────────┴─────────────────┘
```

#### Backup Management Interface

**Backup List:**
```
Configuration Backups
├── models_20240315_143022 (2 hours ago)
│   Description: Before priority update
│   Size: 2.3 KB
│   [Restore] [Download] [Delete]
│
├── models_20240315_120000 (5 hours ago)
│   Description: Automated backup
│   Size: 2.1 KB
│   [Restore] [Download] [Delete]
│
└── models_20240314_180000 (1 day ago)
    Description: Production deployment
    Size: 2.0 KB
    [Restore] [Download] [Delete]
```

**Backup Operations:**
- **Create Backup**: Manual backup with custom description
- **Automatic Backups**: Created before configuration changes
- **Restore**: One-click restore from any backup
- **Compare**: Side-by-side comparison of configurations
- **Download**: Export backup files

## Dashboard API Endpoints

The dashboard uses these API endpoints for dynamic functionality:

### Model Management
```bash
GET /dashboard/api/models/priority        # Get models by priority
POST /dashboard/api/models/priority       # Update priorities
GET /dashboard/api/groups                 # Get resource groups
POST /dashboard/api/groups/{group}/start  # Start group
POST /dashboard/api/groups/{group}/stop   # Stop group
```

### Queue Management
```bash
GET /dashboard/api/queue/status           # Get queue status
POST /dashboard/api/queue/{model}/clear   # Clear model queue
```

### Bulk Operations
```bash
POST /dashboard/api/models/bulk-action    # Bulk operations
```

Example bulk operation:
```json
{
  "operation": "start",
  "resource_group": "production"
}
```

### Configuration Management
```bash
GET /dashboard/api/config/models          # Get model config
POST /dashboard/api/config/models         # Update model config
GET /dashboard/api/config/auth            # Get auth config (sanitized)
```

## Real-Time Updates

The dashboard uses WebSocket connections for real-time updates:

**Update Types:**
- Model status changes
- Resource usage updates
- Queue depth changes
- Configuration changes
- Error notifications

**WebSocket Events:**
```javascript
{
  "type": "status_update",
  "data": {
    "models": {
      "qwen-32b": {
        "status": "running",
        "cpu_usage": 45.2,
        "memory_usage": 8192,
        "request_count": 156
      }
    }
  }
}
```

## Customization and Themes

### Color Coding

**Status Colors:**
- 🟢 Green: Healthy/Running
- 🟡 Yellow: Warning/Starting
- 🔴 Red: Error/Stopped
- 🟠 Orange: Transitioning
- 🔵 Blue: Information/Reloading

**Priority Colors:**
- Dark Green: Priority 9-10 (Critical)
- Green: Priority 7-8 (Important)
- Blue: Priority 5-6 (Standard)
- Gray: Priority 1-4 (Low)

### Responsive Design

The dashboard is fully responsive and works on:
- Desktop computers (optimal experience)
- Tablets (adapted layout)
- Mobile phones (condensed view)

## Keyboard Shortcuts

**Navigation:**
- `Ctrl+1`: Switch to Overview tab
- `Ctrl+2`: Switch to Priority Management
- `Ctrl+3`: Switch to Resource Groups
- `Ctrl+4`: Switch to Queue Monitor
- `Ctrl+5`: Switch to Configuration

**Actions:**
- `Ctrl+S`: Save configuration
- `Ctrl+B`: Create backup
- `Ctrl+R`: Refresh all data
- `Esc`: Close modals/dialogs

## Troubleshooting Dashboard Issues

### Dashboard Won't Load

1. **Check Server Status**: Ensure the server is running on the correct port
2. **Browser Console**: Check for JavaScript errors
3. **Network**: Verify WebSocket connections
4. **Authentication**: Ensure you have proper API keys if auth is enabled

### Real-Time Updates Not Working

1. **WebSocket Connection**: Check browser developer tools for WebSocket errors
2. **Firewall**: Ensure WebSocket traffic isn't blocked
3. **Proxy Configuration**: If behind a proxy, ensure WebSocket support

### Configuration Editor Issues

1. **Validation Errors**: Check YAML syntax and indentation
2. **Permission Errors**: Ensure you have configuration management permissions
3. **File Locks**: Check if configuration files are locked by other processes

### Performance Issues

1. **Large Configurations**: Dashboard may slow with 50+ models
2. **Memory Usage**: Monitor browser memory usage during long sessions
3. **Update Frequency**: Reduce real-time update frequency if needed

## Dashboard Configuration

You can customize dashboard behavior:

```yaml
# config/dashboard.yaml
dashboard:
  update_interval: 5000      # milliseconds
  max_models_display: 100    # maximum models to show
  theme: "auto"              # auto, light, dark
  enable_animations: true    # UI animations
  show_advanced_metrics: true # detailed metrics
```

The dashboard provides a powerful, user-friendly interface for managing your LLM Proxifier deployment, making complex operations simple and providing deep visibility into your system's operation.
