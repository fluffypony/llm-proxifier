"""Web dashboard for monitoring LLM Proxifier status and metrics."""

import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.utils import get_system_memory_usage, format_uptime

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
    from src.main import model_manager, config_manager
    
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
    from src.main import model_manager
    
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
    from src.main import model_manager
    
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
    from src.main import model_manager
    
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
