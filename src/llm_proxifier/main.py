"""FastAPI application entry point for the LLM proxy server."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from llm_proxifier.auth import AuthManager
from llm_proxifier.config import ConfigManager
from llm_proxifier.config_api import ConfigurationManager
from llm_proxifier.dashboard import dashboard_router
from llm_proxifier.middleware import AuthenticationMiddleware, RateLimitMiddleware
from llm_proxifier.model_manager import ModelManager
from llm_proxifier.proxy_handler import ProxyHandler
from llm_proxifier.queue_manager import QueueManager
from llm_proxifier.utils import format_error_response, get_system_memory_usage

# Global instances
model_manager: ModelManager = None
proxy_handler: ProxyHandler = None
config_manager: ConfigManager = None
auth_manager: AuthManager = None
queue_manager: QueueManager = None
configuration_manager: ConfigurationManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global model_manager, proxy_handler, config_manager, auth_manager, queue_manager, configuration_manager

    # Startup
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        # Initialize configuration
        config_manager = ConfigManager()
        proxy_config = config_manager.proxy_config

        # Load model configurations
        model_configs = config_manager.load_model_configs()
        logger.info(f"Loaded {len(model_configs)} model configurations")

        # Initialize queue manager
        queue_manager = QueueManager()

        # Initialize configuration manager
        configuration_manager = ConfigurationManager()

        # Initialize model manager with queue manager
        model_manager = ModelManager(
            timeout_minutes=proxy_config.timeout_minutes,
            max_concurrent=proxy_config.max_concurrent_models,
            queue_manager=queue_manager
        )
        model_manager.load_configs(model_configs)

        # Initialize proxy handler with queue manager
        proxy_handler = ProxyHandler(queue_manager=queue_manager)

        # Initialize authentication manager
        auth_manager = AuthManager(config_manager)

        # Connect notification manager to WebSocket manager
        from llm_proxifier.config_notifications import config_notification_manager
        from llm_proxifier.dashboard import manager as websocket_manager
        config_notification_manager.set_websocket_manager(websocket_manager)

        # Add authentication middleware
        app.add_middleware(AuthenticationMiddleware, auth_manager=auth_manager)
        app.add_middleware(RateLimitMiddleware, auth_manager=auth_manager)

        # Start cleanup tasks
        await model_manager.start_cleanup_task()
        await queue_manager.start_cleanup_task()

        # Start auto-start models
        await model_manager.start_all_auto_models()

        # Preload models
        await model_manager.preload_models()

        logger.info(f"LLM Proxy Server started on {proxy_config.host}:{proxy_config.port}")

    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down LLM Proxy Server")

    if queue_manager:
        await queue_manager.shutdown()

    if model_manager:
        await model_manager.shutdown_all()

    if proxy_handler:
        await proxy_handler.close()

    logger.info("LLM Proxy Server shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="LLM Proxifier",
    description="A lightweight, intelligent proxy server that manages multiple LLaMA models on-demand",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for dashboard
app.mount("/static", StaticFiles(directory="static"), name="static")

# Note: Authentication middleware will be added after startup in lifespan

# Include dashboard router
app.include_router(dashboard_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logging.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=format_error_response(500, "Internal server error", "internal_error")
    )


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """Handle OpenAI-compatible chat completions requests."""
    try:
        # Extract model name from request
        model_name = await proxy_handler.extract_model_from_request(request)
        if not model_name:
            raise HTTPException(
                status_code=400,
                detail=format_error_response(400, "Missing or invalid model name", "invalid_request")
            )

        # Check if model is configured
        if model_name not in config_manager.model_configs:
            available_models = list(config_manager.model_configs.keys())
            raise HTTPException(
                status_code=400,
                detail=format_error_response(
                    400,
                    f"Model '{model_name}' not found. Available models: {available_models}",
                    "model_not_found"
                )
            )

        # Use the proxy handler which will handle queueing if needed
        model_instance = await model_manager.get_or_start_model(model_name)
        if not model_instance:
            # Model failed to start, but proxy handler will handle queueing
            return await proxy_handler.handle_chat_completions(request, model_name, None)

        # Forward the request
        return await proxy_handler.handle_chat_completions(request, model_name, model_instance.api_url)

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in chat completions: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.post("/v1/completions")
async def completions(request: Request):
    """Handle OpenAI-compatible completions requests."""
    try:
        # Extract model name from request
        model_name = await proxy_handler.extract_model_from_request(request)
        if not model_name:
            raise HTTPException(
                status_code=400,
                detail=format_error_response(400, "Missing or invalid model name", "invalid_request")
            )

        # Check if model is configured
        if model_name not in config_manager.model_configs:
            available_models = list(config_manager.model_configs.keys())
            raise HTTPException(
                status_code=400,
                detail=format_error_response(
                    400,
                    f"Model '{model_name}' not found. Available models: {available_models}",
                    "model_not_found"
                )
            )

        # Use the proxy handler which will handle queueing if needed
        model_instance = await model_manager.get_or_start_model(model_name)
        if not model_instance:
            # Model failed to start, but proxy handler will handle queueing
            return await proxy_handler.handle_completions(request, model_name, None)

        # Forward the request
        return await proxy_handler.handle_completions(request, model_name, model_instance.api_url)

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in completions: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.get("/v1/models")
async def list_models():
    """List available models with their status."""
    try:
        model_status = model_manager.get_all_model_status()
        return await proxy_handler.create_models_response(model_status)

    except Exception as e:
        logging.error(f"Error listing models: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        model_status = model_manager.get_all_model_status()
        system_memory = get_system_memory_usage()

        response = await proxy_handler.create_health_response(model_status)
        response["system"] = {
            "memory": system_memory
        }

        return response

    except Exception as e:
        logging.error(f"Error in health check: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.get("/metrics")
async def get_metrics():
    """Get usage metrics for all models."""
    try:
        model_status = model_manager.get_all_model_status()
        return await proxy_handler.create_metrics_response(model_status)

    except Exception as e:
        logging.error(f"Error getting metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.post("/admin/models/{model_name}/start")
async def start_model(model_name: str):
    """Manually start a specific model."""
    try:
        model_instance = await model_manager.get_or_start_model(model_name)
        if not model_instance:
            raise HTTPException(
                status_code=400,
                detail=format_error_response(400, f"Failed to start model '{model_name}'", "start_failed")
            )

        return {"message": f"Model '{model_name}' started successfully", "status": "running"}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error starting model {model_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.post("/admin/models/{model_name}/stop")
async def stop_model(model_name: str):
    """Manually stop a specific model."""
    try:
        success = await model_manager.stop_model(model_name)
        if not success:
            raise HTTPException(
                status_code=500,
                detail=format_error_response(500, f"Failed to stop model '{model_name}'", "stop_failed")
            )

        return {"message": f"Model '{model_name}' stopped successfully", "status": "stopped"}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error stopping model {model_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.get("/admin/models/{model_name}/status")
async def get_model_status(model_name: str):
    """Get detailed status of a specific model."""
    try:
        if model_name not in config_manager.model_configs:
            raise HTTPException(
                status_code=404,
                detail=format_error_response(404, f"Model '{model_name}' not found", "model_not_found")
            )

        status = model_manager.get_model_status(model_name)
        return status

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting model status {model_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.post("/admin/models/start-all")
async def start_all_models():
    """Start all configured models."""
    try:
        results = await model_manager.start_all_models()
        success_count = sum(1 for success in results.values() if success)
        return {
            "message": f"Started {success_count}/{len(results)} models",
            "results": results
        }
    except Exception as e:
        logging.error(f"Error starting all models: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.post("/admin/models/stop-all")
async def stop_all_models():
    """Stop all running models except preloaded ones."""
    try:
        results = await model_manager.stop_all_models()
        success_count = sum(1 for success in results.values() if success)
        return {
            "message": f"Stopped {success_count}/{len(results)} models",
            "results": results
        }
    except Exception as e:
        logging.error(f"Error stopping all models: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.post("/admin/models/restart-all")
async def restart_all_models():
    """Restart all currently running models."""
    try:
        results = await model_manager.restart_all_models()
        success_count = sum(1 for success in results.values() if success)
        return {
            "message": f"Restarted {success_count}/{len(results)} models",
            "results": results
        }
    except Exception as e:
        logging.error(f"Error restarting all models: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.post("/admin/groups/{group_name}/start")
async def start_resource_group(group_name: str):
    """Start all models in specified resource group."""
    try:
        results = await model_manager.start_resource_group(group_name)
        success_count = sum(1 for success in results.values() if success)
        return {
            "message": f"Started {success_count}/{len(results)} models in group '{group_name}'",
            "results": results
        }
    except Exception as e:
        logging.error(f"Error starting resource group {group_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.post("/admin/groups/{group_name}/stop")
async def stop_resource_group(group_name: str):
    """Stop all models in specified resource group."""
    try:
        results = await model_manager.stop_resource_group(group_name)
        success_count = sum(1 for success in results.values() if success)
        return {
            "message": f"Stopped {success_count}/{len(results)} models in group '{group_name}'",
            "results": results
        }
    except Exception as e:
        logging.error(f"Error stopping resource group {group_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.get("/admin/groups")
async def list_resource_groups():
    """List all resource groups and their models."""
    try:
        return model_manager.get_resource_group_status()
    except Exception as e:
        logging.error(f"Error listing resource groups: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.post("/admin/models/reload-config")
async def reload_model_config():
    """Reload models.yaml configuration."""
    try:
        if config_manager.has_config_changed():
            old_configs = dict(config_manager.model_configs)
            new_configs = config_manager.load_model_configs()
            model_manager.load_configs(new_configs)

            # Compare changes
            added = set(new_configs.keys()) - set(old_configs.keys())
            removed = set(old_configs.keys()) - set(new_configs.keys())
            modified = set()

            for name in old_configs.keys() & new_configs.keys():
                if old_configs[name].__dict__ != new_configs[name].__dict__:
                    modified.add(name)

            return {
                "message": "Configuration reloaded",
                "changes": {
                    "added": list(added),
                    "removed": list(removed),
                    "modified": list(modified)
                }
            }
        else:
            return {"message": "No configuration changes detected"}
    except Exception as e:
        logging.error(f"Error reloading config: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.post("/admin/auth/reload-config")
async def reload_auth_config():
    """Reload auth.yaml configuration."""
    try:
        if config_manager.has_auth_config_changed():
            config_manager.auth_config = config_manager._load_auth_config()
            auth_manager.update_config(config_manager)
            return {"message": "Auth configuration reloaded"}
        else:
            return {"message": "No auth configuration changes detected"}
    except Exception as e:
        logging.error(f"Error reloading auth config: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.post("/admin/models/{model_name}/reload")
async def reload_model(model_name: str):
    """Hot reload a specific model."""
    try:
        result = await model_manager.reload_model(model_name)
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=400,
                detail=format_error_response(400, result["error"], "reload_failed")
            )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error reloading model {model_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.get("/admin/queue/status")
async def get_all_queue_status():
    """Get queue statistics for all models."""
    try:
        return queue_manager.get_queue_stats()
    except Exception as e:
        logging.error(f"Error getting queue status: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.get("/admin/queue/{model_name}/status")
async def get_model_queue_status(model_name: str):
    """Get queue status for specific model."""
    try:
        return queue_manager.get_queue_stats(model_name)
    except Exception as e:
        logging.error(f"Error getting queue status for {model_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.post("/admin/queue/{model_name}/clear")
async def clear_model_queue(model_name: str):
    """Clear queue for specific model."""
    try:
        queue_manager.clear_model_queue(model_name)
        return {"message": f"Queue cleared for model {model_name}"}
    except Exception as e:
        logging.error(f"Error clearing queue for {model_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


# Configuration Management Endpoints
@app.get("/admin/config/models/schema")
async def get_models_config_schema():
    """Return JSON schema for models configuration."""
    try:
        return configuration_manager.get_config_schema("models")
    except Exception as e:
        logging.error(f"Error getting models config schema: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.get("/admin/config/auth/schema")
async def get_auth_config_schema():
    """Return JSON schema for auth configuration."""
    try:
        return configuration_manager.get_config_schema("auth")
    except Exception as e:
        logging.error(f"Error getting auth config schema: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.get("/admin/config/models/backups")
async def list_models_config_backups():
    """List available models configuration backups."""
    try:
        backups = configuration_manager.list_backups("models")
        return [
            {
                "backup_id": backup.backup_id,
                "timestamp": backup.timestamp.isoformat(),
                "description": backup.description
            }
            for backup in backups
        ]
    except Exception as e:
        logging.error(f"Error listing models config backups: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.get("/admin/config/auth/backups")
async def list_auth_config_backups():
    """List available auth configuration backups."""
    try:
        backups = configuration_manager.list_backups("auth")
        return [
            {
                "backup_id": backup.backup_id,
                "timestamp": backup.timestamp.isoformat(),
                "description": backup.description
            }
            for backup in backups
        ]
    except Exception as e:
        logging.error(f"Error listing auth config backups: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.post("/admin/config/models/backup")
async def backup_models_config(description: str = "Manual backup"):
    """Create backup of models configuration."""
    try:
        result = configuration_manager.backup_config("models", description)
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=400,
                detail=format_error_response(400, result["error"], "backup_failed")
            )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error backing up models config: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.post("/admin/config/auth/backup")
async def backup_auth_config(description: str = "Manual backup"):
    """Create backup of auth configuration."""
    try:
        result = configuration_manager.backup_config("auth", description)
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=400,
                detail=format_error_response(400, result["error"], "backup_failed")
            )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error backing up auth config: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.post("/admin/config/models/restore/{backup_id}")
async def restore_models_config(backup_id: str):
    """Restore models configuration from backup."""
    try:
        result = configuration_manager.restore_config("models", backup_id)
        if result["success"]:
            # Reload configuration in the application
            new_configs = config_manager.load_model_configs()
            model_manager.reload_model_config(new_configs)
            return result
        else:
            raise HTTPException(
                status_code=400,
                detail=format_error_response(400, result["error"], "restore_failed")
            )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error restoring models config from {backup_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.post("/admin/config/auth/restore/{backup_id}")
async def restore_auth_config(backup_id: str):
    """Restore auth configuration from backup."""
    try:
        result = configuration_manager.restore_config("auth", backup_id)
        if result["success"]:
            # Reload configuration in the application
            # This would require reloading the entire config manager
            return result
        else:
            raise HTTPException(
                status_code=400,
                detail=format_error_response(400, result["error"], "restore_failed")
            )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error restoring auth config from {backup_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.get("/admin/config/validation/models")
async def validate_models_config():
    """Validate current models configuration."""
    try:
        config_data = configuration_manager.load_models_config()
        return configuration_manager.validate_config(config_data, "models")
    except Exception as e:
        logging.error(f"Error validating models config: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


@app.get("/admin/config/validation/auth")
async def validate_auth_config():
    """Validate current auth configuration."""
    try:
        config_data = configuration_manager.load_auth_config()
        return configuration_manager.validate_config(config_data, "auth")
    except Exception as e:
        logging.error(f"Error validating auth config: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(500, str(e), "internal_error")
        )


if __name__ == "__main__":
    import uvicorn

    # Load configuration for local development
    config_manager = ConfigManager()
    proxy_config = config_manager.proxy_config

    uvicorn.run(
        "src.main:app",
        host=proxy_config.host,
        port=proxy_config.port,
        log_level=proxy_config.log_level.lower(),
        reload=True
    )
