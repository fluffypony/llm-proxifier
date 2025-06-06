"""FastAPI application entry point for the LLM proxy server."""

import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.config import ConfigManager
from src.model_manager import ModelManager
from src.proxy_handler import ProxyHandler
from src.utils import format_error_response, get_system_memory_usage


# Global instances
model_manager: ModelManager = None
proxy_handler: ProxyHandler = None
config_manager: ConfigManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global model_manager, proxy_handler, config_manager
    
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
        
        # Initialize model manager
        model_manager = ModelManager(
            timeout_minutes=proxy_config.timeout_minutes,
            max_concurrent=proxy_config.max_concurrent_models
        )
        model_manager.load_configs(model_configs)
        
        # Initialize proxy handler
        proxy_handler = ProxyHandler()
        
        # Start cleanup task
        await model_manager.start_cleanup_task()
        
        logger.info(f"LLM Proxy Server started on {proxy_config.host}:{proxy_config.port}")
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down LLM Proxy Server")
    
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
        
        # Get or start the model
        model_instance = await model_manager.get_or_start_model(model_name)
        if not model_instance:
            available_models = list(config_manager.model_configs.keys())
            raise HTTPException(
                status_code=400,
                detail=format_error_response(
                    400, 
                    f"Model '{model_name}' not found. Available models: {available_models}",
                    "model_not_found"
                )
            )
        
        # Forward the request
        return await proxy_handler.handle_chat_completions(request, model_instance.api_url)
        
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
        
        # Get or start the model
        model_instance = await model_manager.get_or_start_model(model_name)
        if not model_instance:
            available_models = list(config_manager.model_configs.keys())
            raise HTTPException(
                status_code=400,
                detail=format_error_response(
                    400,
                    f"Model '{model_name}' not found. Available models: {available_models}",
                    "model_not_found"
                )
            )
        
        # Forward the request
        return await proxy_handler.handle_completions(request, model_instance.api_url)
        
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
