"""Web dashboard for monitoring LLM Proxifier status and metrics."""

import logging
from datetime import datetime
from typing import Dict, Any, List

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .utils import get_system_memory_usage, format_uptime

logger = logging.getLogger(__name__)

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Create router for dashboard endpoints
dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class ConnectionManager:
    """Manage WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast_json(self, data: dict):
        """Broadcast JSON data to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except:
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)


# Global connection manager
manager = ConnectionManager()


@dashboard_router.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Serve the main dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@dashboard_router.get("/api/status")
async def get_dashboard_status():
    """Get current system and model status for dashboard."""
    from .main import model_manager, config_manager
    
    try:
        # Get model status
        model_status = model_manager.get_all_model_status()
        
        # Get system info
        system_memory = get_system_memory_usage()
        
        # Count active models
        active_models = sum(1 for status in model_status.values() if status.get("status") == "running")
        total_models = len(model_status)
        
        # Calculate total memory usage
        total_memory_mb = sum(
            status.get("memory_usage_mb", 0) 
            for status in model_status.values() 
            if status.get("status") == "running"
        )
        
        response = {
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "memory": system_memory,
                "active_models": active_models,
                "total_models": total_models,
                "total_memory_usage_mb": total_memory_mb
            },
            "models": {}
        }
        
        # Format model data for dashboard
        for model_name, status in model_status.items():
            config = config_manager.model_configs.get(model_name, {})
            response["models"][model_name] = {
                "name": model_name,
                "status": status.get("status", "unknown"),
                "port": status.get("port", config.get("port", "N/A")),
                "uptime": format_uptime(status.get("uptime", 0)),
                "memory_usage_mb": status.get("memory_usage_mb", 0),
                "cpu_usage_percent": status.get("cpu_usage_percent", 0),
                "request_count": status.get("request_count", 0),
                "last_accessed": status.get("last_accessed"),
                "model_path": config.get("model_path", "N/A"),
                "context_length": config.get("context_length", "N/A"),
                "gpu_layers": config.get("gpu_layers", "N/A")
            }
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting dashboard status: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@dashboard_router.get("/api/metrics")
async def get_dashboard_metrics():
    """Get detailed metrics for dashboard charts."""
    from .main import model_manager
    
    try:
        model_status = model_manager.get_all_model_status()
        
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "models": []
        }
        
        for model_name, status in model_status.items():
            if status.get("status") == "running":
                metrics["models"].append({
                    "name": model_name,
                    "memory_usage_mb": status.get("memory_usage_mb", 0),
                    "cpu_usage_percent": status.get("cpu_usage_percent", 0),
                    "request_count": status.get("request_count", 0),
                    "uptime_seconds": status.get("uptime", 0)
                })
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting dashboard metrics: {e}")
        return {"error": str(e)}


@dashboard_router.post("/api/models/{model_name}/start")
async def dashboard_start_model(model_name: str):
    """Start a model via dashboard."""
    from .main import model_manager
    
    try:
        model_instance = await model_manager.get_or_start_model(model_name)
        if not model_instance:
            return {"success": False, "message": f"Failed to start model '{model_name}'"}
        
        # Broadcast update to connected clients
        status_data = await get_dashboard_status()
        await manager.broadcast_json({"type": "status_update", "data": status_data})
        
        return {"success": True, "message": f"Model '{model_name}' started successfully"}
        
    except Exception as e:
        logger.error(f"Error starting model {model_name}: {e}")
        return {"success": False, "message": str(e)}


@dashboard_router.post("/api/models/{model_name}/stop")
async def dashboard_stop_model(model_name: str):
    """Stop a model via dashboard."""
    from .main import model_manager
    
    try:
        success = await model_manager.stop_model(model_name)
        if not success:
            return {"success": False, "message": f"Failed to stop model '{model_name}'"}
        
        # Broadcast update to connected clients
        status_data = await get_dashboard_status()
        await manager.broadcast_json({"type": "status_update", "data": status_data})
        
        return {"success": True, "message": f"Model '{model_name}' stopped successfully"}
        
    except Exception as e:
        logger.error(f"Error stopping model {model_name}: {e}")
        return {"success": False, "message": str(e)}


@dashboard_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Wait for client messages (ping/keepalive)
            await websocket.receive_text()
            
            # Send current status
            status_data = await get_dashboard_status()
            await websocket.send_json({"type": "status_update", "data": status_data})
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# Data models for new endpoints
class PriorityUpdateModel(BaseModel):
    model_priorities: Dict[str, int]


class BulkOperationModel(BaseModel):
    operation: str  # "start", "stop", "restart"
    models: List[str] = []  # Empty list means all models
    resource_group: str = None  # Optional resource group filter


class ConfigUpdateModel(BaseModel):
    config_data: Dict[str, Any]
    config_type: str = "models"  # "models" or "auth"


# Priority Management Endpoints
@dashboard_router.get("/api/models/priority")
async def get_models_by_priority():
    """Get models sorted by priority."""
    try:
        from .main import model_manager
        if not model_manager:
            raise HTTPException(status_code=503, detail="Model manager not available")
        
        models_by_priority = model_manager.get_models_by_priority()
        return [
            {
                "name": config.name,
                "priority": config.priority,
                "resource_group": config.resource_group,
                "auto_start": config.auto_start,
                "preload": config.preload,
                "status": model_manager.get_model_status(config.name)["status"]
            }
            for config in models_by_priority
        ]
    except Exception as e:
        logger.error(f"Error getting models by priority: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@dashboard_router.post("/api/models/priority")
async def update_model_priorities(priority_update: PriorityUpdateModel):
    """Update model priorities."""
    try:
        from .main import model_manager, config_manager
        if not model_manager or not config_manager:
            raise HTTPException(status_code=503, detail="Managers not available")
        
        # Update priorities in configurations
        updated_models = []
        for model_name, priority in priority_update.model_priorities.items():
            if model_name in model_manager.configs:
                old_priority = model_manager.configs[model_name].priority
                model_manager.configs[model_name].priority = priority
                updated_models.append({
                    "name": model_name,
                    "old_priority": old_priority,
                    "new_priority": priority
                })
        
        return {
            "success": True,
            "updated_models": updated_models,
            "message": f"Updated priorities for {len(updated_models)} models"
        }
    except Exception as e:
        logger.error(f"Error updating model priorities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Resource Group Management Endpoints
@dashboard_router.get("/api/groups")
async def get_resource_groups():
    """Get resource group information."""
    try:
        from .main import model_manager
        if not model_manager:
            raise HTTPException(status_code=503, detail="Model manager not available")
        
        return model_manager.get_resource_group_status()
    except Exception as e:
        logger.error(f"Error getting resource groups: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@dashboard_router.post("/api/groups/{resource_group}/start")
async def start_resource_group(resource_group: str):
    """Start all models in a resource group."""
    try:
        from .main import model_manager
        if not model_manager:
            raise HTTPException(status_code=503, detail="Model manager not available")
        
        results = await model_manager.start_resource_group(resource_group)
        return {
            "success": True,
            "resource_group": resource_group,
            "results": results
        }
    except Exception as e:
        logger.error(f"Error starting resource group {resource_group}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@dashboard_router.post("/api/groups/{resource_group}/stop")
async def stop_resource_group(resource_group: str):
    """Stop all models in a resource group."""
    try:
        from .main import model_manager
        if not model_manager:
            raise HTTPException(status_code=503, detail="Model manager not available")
        
        results = await model_manager.stop_resource_group(resource_group)
        return {
            "success": True,
            "resource_group": resource_group,
            "results": results
        }
    except Exception as e:
        logger.error(f"Error stopping resource group {resource_group}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Queue Status Endpoints
@dashboard_router.get("/api/queue/status")
async def get_queue_status():
    """Get queue status for dashboard."""
    try:
        from .main import queue_manager
        if not queue_manager:
            raise HTTPException(status_code=503, detail="Queue manager not available")
        
        return queue_manager.get_queue_stats()
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@dashboard_router.post("/api/queue/{model_name}/clear")
async def clear_queue_dashboard(model_name: str):
    """Clear queue for specific model (dashboard endpoint)."""
    try:
        from .main import queue_manager
        if not queue_manager:
            raise HTTPException(status_code=503, detail="Queue manager not available")
        
        queue_manager.clear_model_queue(model_name)
        return {
            "success": True,
            "message": f"Queue cleared for model {model_name}"
        }
    except Exception as e:
        logger.error(f"Error clearing queue for {model_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Bulk Operations Endpoints
@dashboard_router.post("/api/models/bulk-action")
async def bulk_model_operation(operation: BulkOperationModel):
    """Handle bulk operations on models."""
    try:
        from .main import model_manager
        if not model_manager:
            raise HTTPException(status_code=503, detail="Model manager not available")
        
        results = {}
        
        if operation.operation == "start":
            if operation.resource_group:
                results = await model_manager.start_resource_group(operation.resource_group)
            elif operation.models:
                for model_name in operation.models:
                    instance = await model_manager.get_or_start_model(model_name)
                    results[model_name] = instance is not None
            else:
                results = await model_manager.start_all_models()
                
        elif operation.operation == "stop":
            if operation.resource_group:
                results = await model_manager.stop_resource_group(operation.resource_group)
            elif operation.models:
                for model_name in operation.models:
                    results[model_name] = await model_manager.stop_model(model_name)
            else:
                results = await model_manager.stop_all_models()
                
        elif operation.operation == "restart":
            if operation.models:
                for model_name in operation.models:
                    await model_manager.stop_model(model_name)
                    instance = await model_manager.get_or_start_model(model_name)
                    results[model_name] = instance is not None
            else:
                results = await model_manager.restart_all_models()
        else:
            raise HTTPException(status_code=400, detail=f"Unknown operation: {operation.operation}")
        
        return {
            "success": True,
            "operation": operation.operation,
            "results": results
        }
    except Exception as e:
        logger.error(f"Error in bulk operation {operation.operation}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Configuration Management Endpoints (Mock implementations for now)
@dashboard_router.get("/api/config/models")
async def get_models_config():
    """Get current model configuration."""
    try:
        from .main import config_manager
        if not config_manager:
            raise HTTPException(status_code=503, detail="Config manager not available")
        
        # Return a simplified version of the config for the dashboard
        return {
            "models": {
                name: {
                    "priority": getattr(config, 'priority', 5),
                    "resource_group": getattr(config, 'resource_group', 'default'),
                    "auto_start": getattr(config, 'auto_start', False),
                    "preload": getattr(config, 'preload', False),
                    "port": config.port,
                    "model_path": config.model_path
                }
                for name, config in config_manager.model_configs.items()
            }
        }
    except Exception as e:
        logger.error(f"Error getting models config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@dashboard_router.post("/api/config/models")
async def update_models_config(config_update: ConfigUpdateModel):
    """Update model configuration using ConfigurationManager."""
    try:
        from .main import configuration_manager, model_manager, config_manager
        if not configuration_manager:
            raise HTTPException(status_code=503, detail="Configuration manager not available")
        
        # Save configuration with backup
        result = configuration_manager.save_models_config(config_update.config_data, backup=True)
        
        if result["success"]:
            # Reload application configuration
            try:
                new_configs = config_manager.load_model_configs()
                model_manager.load_configs(new_configs)
                
                # Broadcast configuration change via WebSocket
                await manager.broadcast_json({
                    "type": "config_updated",
                    "config_type": "models",
                    "timestamp": datetime.utcnow().isoformat(),
                    "backup_id": result.get("backup_created")
                })
                
            except Exception as reload_error:
                logger.error(f"Error reloading config after save: {reload_error}")
                result["warnings"] = result.get("warnings", [])
                result["warnings"].append(f"Configuration saved but reload failed: {reload_error}")
        
        return result
    except Exception as e:
        logger.error(f"Error updating models config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@dashboard_router.get("/api/config/auth")
async def get_auth_config():
    """Get current auth configuration (sanitized)."""
    try:
        from .main import config_manager
        if not config_manager:
            raise HTTPException(status_code=503, detail="Config manager not available")
        
        # Return sanitized auth config (no actual keys)
        auth_config = config_manager.auth_config
        return {
            "enabled": auth_config.enabled,
            "dashboard_auth_required": auth_config.dashboard_auth_required,
            "api_key_count": len(auth_config.api_keys) if auth_config.api_keys else 0,
            "rate_limits": auth_config.rate_limits,
            "public_endpoints": auth_config.public_endpoints
        }
    except Exception as e:
        logger.error(f"Error getting auth config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@dashboard_router.post("/api/config/auth")
async def update_auth_config(config_update: ConfigUpdateModel):
    """Update auth configuration using ConfigurationManager."""
    try:
        from .main import configuration_manager, config_manager
        if not configuration_manager:
            raise HTTPException(status_code=503, detail="Configuration manager not available")
        
        # Save configuration with backup
        result = configuration_manager.save_auth_config(config_update.config_data, backup=True)
        
        if result["success"]:
            # Reload application configuration
            try:
                config_manager.auth_config = config_manager._load_auth_config()
                
                # Broadcast configuration change via WebSocket
                await manager.broadcast_json({
                    "type": "config_updated",
                    "config_type": "auth",
                    "timestamp": datetime.utcnow().isoformat(),
                    "backup_id": result.get("backup_created")
                })
                
            except Exception as reload_error:
                logger.error(f"Error reloading auth config after save: {reload_error}")
                result["warnings"] = result.get("warnings", [])
                result["warnings"].append(f"Configuration saved but reload failed: {reload_error}")
        
        return result
    except Exception as e:
        logger.error(f"Error updating auth config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Configuration Backup/Restore Endpoints
@dashboard_router.get("/api/config/backups")
async def list_config_backups(config_type: str = None):
    """List available configuration backups."""
    try:
        from .main import configuration_manager
        if not configuration_manager:
            raise HTTPException(status_code=503, detail="Configuration manager not available")
        
        backups = configuration_manager.list_backups(config_type)
        
        return {
            "backups": [
                {
                    "backup_id": backup.backup_id,
                    "config_type": backup.config_type,
                    "timestamp": backup.timestamp.isoformat(),
                    "description": backup.description,
                    "file_path": backup.file_path
                }
                for backup in backups
            ]
        }
    except Exception as e:
        logger.error(f"Error listing backups: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@dashboard_router.post("/api/config/backup")
async def create_config_backup(config_type: str, description: str = "Manual backup"):
    """Create a backup of current configuration."""
    try:
        from .main import configuration_manager
        if not configuration_manager:
            raise HTTPException(status_code=503, detail="Configuration manager not available")
        
        result = configuration_manager.backup_config(config_type, description)
        
        if result["success"]:
            # Broadcast backup creation via WebSocket
            await manager.broadcast_json({
                "type": "backup_created",
                "config_type": config_type,
                "backup_id": result["backup_id"],
                "timestamp": datetime.utcnow().isoformat()
            })
        
        return result
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@dashboard_router.post("/api/config/restore")
async def restore_config_backup(config_type: str, backup_id: str):
    """Restore configuration from backup."""
    try:
        from .main import configuration_manager, model_manager, config_manager
        if not configuration_manager:
            raise HTTPException(status_code=503, detail="Configuration manager not available")
        
        result = configuration_manager.restore_config(config_type, backup_id)
        
        if result["success"]:
            # Reload application configuration
            try:
                if config_type == "models":
                    new_configs = config_manager.load_model_configs()
                    model_manager.load_configs(new_configs)
                elif config_type == "auth":
                    config_manager.auth_config = config_manager._load_auth_config()
                
                # Broadcast restore event via WebSocket
                await manager.broadcast_json({
                    "type": "config_restored",
                    "config_type": config_type,
                    "backup_id": backup_id,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
            except Exception as reload_error:
                logger.error(f"Error reloading config after restore: {reload_error}")
                result["warnings"] = result.get("warnings", [])
                result["warnings"].append(f"Configuration restored but reload failed: {reload_error}")
        
        return result
    except Exception as e:
        logger.error(f"Error restoring backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@dashboard_router.post("/api/config/preview")
async def preview_config_changes(config_update: ConfigUpdateModel):
    """Preview configuration changes without applying."""
    try:
        from .main import configuration_manager
        if not configuration_manager:
            raise HTTPException(status_code=503, detail="Configuration manager not available")
        
        config_type = config_update.config_type
        new_config = config_update.config_data
        
        # Load current configuration
        if config_type == "models":
            current_config = configuration_manager.load_models_config()
        else:
            current_config = configuration_manager.load_auth_config()
        
        # Validate new configuration
        validation_result = configuration_manager.validate_config(new_config, config_type)
        
        # Generate simple diff information
        changes = []
        if config_type == "models" and "models" in new_config and "models" in current_config:
            current_models = set(current_config["models"].keys())
            new_models = set(new_config["models"].keys())
            
            # Added models
            for model in new_models - current_models:
                changes.append(f"Added model: {model}")
            
            # Removed models
            for model in current_models - new_models:
                changes.append(f"Removed model: {model}")
            
            # Modified models
            for model in new_models & current_models:
                if new_config["models"][model] != current_config["models"][model]:
                    changes.append(f"Modified model: {model}")
        
        return {
            "validation": validation_result,
            "changes": changes,
            "total_changes": len(changes)
        }
    except Exception as e:
        logger.error(f"Error previewing config changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health Check Endpoint
@dashboard_router.get("/api/health")
async def health_check():
    """Simple health check endpoint for connection monitoring."""
    try:
        from .main import queue_manager
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "queue_manager_available": queue_manager is not None,
            "version": "1.0.0"
        }
        
        # Basic queue manager connectivity test
        if queue_manager:
            try:
                # Try to get a simple stat to verify queue manager is responsive
                test_stats = queue_manager.get_queue_stats()
                health_status["queue_manager_responsive"] = True
                health_status["model_count"] = len(test_stats) if test_stats else 0
            except Exception as e:
                health_status["queue_manager_responsive"] = False
                health_status["queue_manager_error"] = str(e)
        
        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")


# Queue Management Endpoints
@dashboard_router.get("/api/queue/status")
async def get_queue_status():
    """Get comprehensive queue status for all models."""
    try:
        from .main import queue_manager
        if not queue_manager:
            raise HTTPException(status_code=503, detail="Queue manager not available")
        
        # Get queue statistics from enhanced queue manager
        queue_stats = queue_manager.get_queue_stats()
        
        return queue_stats
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@dashboard_router.get("/api/queue/history")
async def get_queue_history(model_name: str = None, limit: int = 50):
    """Get historical queue metrics for charts."""
    try:
        from .main import queue_manager
        if not queue_manager:
            raise HTTPException(status_code=503, detail="Queue manager not available")
        
        # Get historical metrics from enhanced queue manager
        historical_data = queue_manager.get_historical_metrics(model_name, limit)
        
        return {
            "historical_data": historical_data,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting queue history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@dashboard_router.post("/api/queue/{model_name}/clear")
async def clear_model_queue(model_name: str):
    """Clear queue for a specific model."""
    try:
        from .main import queue_manager
        if not queue_manager:
            raise HTTPException(status_code=503, detail="Queue manager not available")
        
        # Clear the queue for the model
        queue_manager.clear_model_queue(model_name)
        
        # Broadcast queue clear event via WebSocket
        await manager.broadcast_json({
            "type": "queue_cleared",
            "model_name": model_name,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return {
            "success": True,
            "message": f"Queue cleared for model {model_name}"
        }
    except Exception as e:
        logger.error(f"Error clearing queue for {model_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@dashboard_router.post("/api/queue/reset-metrics")
async def reset_queue_metrics(model_name: str = None):
    """Reset queue metrics for a model or all models."""
    try:
        from .main import queue_manager
        if not queue_manager:
            raise HTTPException(status_code=503, detail="Queue manager not available")
        
        # Reset metrics
        queue_manager.reset_metrics(model_name)
        
        # Broadcast metrics reset event via WebSocket
        await manager.broadcast_json({
            "type": "metrics_reset",
            "model_name": model_name or "all",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return {
            "success": True,
            "message": f"Metrics reset for {model_name or 'all models'}"
        }
    except Exception as e:
        logger.error(f"Error resetting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
