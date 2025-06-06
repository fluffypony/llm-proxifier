"""Request proxying logic for the LLM proxy server."""

import json
import logging
from typing import Dict, Any, Optional, AsyncGenerator
import httpx
from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse

from src.utils import (
    extract_model_name,
    validate_openai_request,
    format_error_response,
    parse_sse_stream
)


class ProxyHandler:
    """Handles proxying requests to model servers."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(300.0))  # 5 minute timeout
    
    async def extract_model_from_request(self, request: Request) -> Optional[str]:
        """Extract model name from the request body."""
        try:
            body = await request.body()
            if not body:
                return None
            
            request_data = json.loads(body)
            
            if not validate_openai_request(request_data):
                return None
            
            return extract_model_name(request_data)
            
        except json.JSONDecodeError:
            self.logger.error("Invalid JSON in request body")
            return None
        except Exception as e:
            self.logger.error(f"Error extracting model from request: {e}")
            return None
    
    async def forward_request(self, request: Request, target_url: str, endpoint: str) -> Any:
        """Forward request to the target model server."""
        try:
            # Get original request body
            body = await request.body()
            
            # Prepare headers (exclude host and other problematic headers)
            headers = dict(request.headers)
            headers_to_remove = ['host', 'content-length', 'connection']
            for header in headers_to_remove:
                headers.pop(header, None)
            
            # Forward the request
            url = f"{target_url}{endpoint}"
            self.logger.debug(f"Forwarding request to {url}")
            
            response = await self.client.request(
                method=request.method,
                url=url,
                content=body,
                headers=headers,
                params=dict(request.query_params)
            )
            
            # Check if this is a streaming response
            content_type = response.headers.get('content-type', '')
            if 'text/event-stream' in content_type or 'stream' in str(dict(request.query_params)):
                return await self._handle_streaming_response(response)
            else:
                return await self._handle_regular_response(response)
                
        except httpx.RequestError as e:
            self.logger.error(f"Request error when forwarding to {target_url}: {e}")
            raise HTTPException(
                status_code=502,
                detail=format_error_response(502, f"Bad gateway: {str(e)}", "bad_gateway")
            )
        except httpx.TimeoutException:
            self.logger.error(f"Timeout when forwarding to {target_url}")
            raise HTTPException(
                status_code=504,
                detail=format_error_response(504, "Gateway timeout", "timeout")
            )
        except Exception as e:
            self.logger.error(f"Unexpected error when forwarding to {target_url}: {e}")
            raise HTTPException(
                status_code=500,
                detail=format_error_response(500, f"Internal server error: {str(e)}", "internal_error")
            )
    
    async def _handle_streaming_response(self, response: httpx.Response) -> StreamingResponse:
        """Handle streaming server-sent events response."""
        async def stream_generator():
            try:
                async for line in response.aiter_lines():
                    if line:
                        yield f"{line}\n"
            except Exception as e:
                self.logger.error(f"Error in streaming response: {e}")
                # Send error in SSE format
                error_data = format_error_response(500, str(e), "stream_error")
                yield f"data: {json.dumps(error_data)}\n\n"
        
        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "*"
            }
        )
    
    async def _handle_regular_response(self, response: httpx.Response) -> JSONResponse:
        """Handle regular JSON response."""
        try:
            content = response.json()
            
            return JSONResponse(
                content=content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
        except json.JSONDecodeError:
            # If response is not JSON, return as text
            return JSONResponse(
                content={"text": response.text},
                status_code=response.status_code,
                headers=dict(response.headers)
            )
    
    def transform_error_response(self, error: Exception, status_code: int = 500) -> Dict[str, Any]:
        """Transform error into OpenAI API format."""
        if isinstance(error, httpx.RequestError):
            return format_error_response(502, f"Connection error: {str(error)}", "connection_error")
        elif isinstance(error, httpx.TimeoutException):
            return format_error_response(504, "Request timeout", "timeout")
        elif isinstance(error, HTTPException):
            return format_error_response(error.status_code, str(error.detail), "http_error")
        else:
            return format_error_response(status_code, str(error), "unknown_error")
    
    async def handle_chat_completions(self, request: Request, target_url: str) -> Any:
        """Handle /v1/chat/completions endpoint."""
        return await self.forward_request(request, target_url, "/v1/chat/completions")
    
    async def handle_completions(self, request: Request, target_url: str) -> Any:
        """Handle /v1/completions endpoint."""
        return await self.forward_request(request, target_url, "/v1/completions")
    
    async def handle_models(self, request: Request, target_url: str) -> Any:
        """Handle /v1/models endpoint."""
        return await self.forward_request(request, target_url, "/v1/models")
    
    async def create_models_response(self, available_models: Dict[str, Any]) -> Dict[str, Any]:
        """Create a models list response in OpenAI format."""
        models = []
        
        for name, status in available_models.items():
            model_info = {
                "id": name,
                "object": "model",
                "created": 0,  # Unix timestamp - would be model creation time
                "owned_by": "llama-cpp",
                "permission": [],
                "root": name,
                "parent": None
            }
            
            # Add status information as metadata
            if status.get("status") == "running":
                model_info["status"] = "available"
            else:
                model_info["status"] = "unavailable"
            
            models.append(model_info)
        
        return {
            "object": "list",
            "data": models
        }
    
    async def create_health_response(self, model_status: Dict[str, Any]) -> Dict[str, Any]:
        """Create a health check response."""
        active_models = len([s for s in model_status.values() if s.get("status") == "running"])
        total_models = len(model_status)
        
        return {
            "status": "healthy",
            "timestamp": json.dumps(None),  # Would use current timestamp
            "models": {
                "total": total_models,
                "active": active_models,
                "details": model_status
            }
        }
    
    async def create_metrics_response(self, model_status: Dict[str, Any]) -> Dict[str, Any]:
        """Create a metrics response."""
        metrics = {
            "timestamp": json.dumps(None),  # Would use current timestamp
            "models": {}
        }
        
        for name, status in model_status.items():
            metrics["models"][name] = {
                "status": status.get("status", "unknown"),
                "request_count": status.get("request_count", 0),
                "memory_usage_mb": status.get("memory_usage_mb"),
                "cpu_usage_percent": status.get("cpu_usage_percent"),
                "uptime": status.get("uptime"),
                "last_accessed": status.get("last_accessed")
            }
        
        return metrics
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
