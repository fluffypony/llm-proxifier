"""Request proxying logic for the LLM proxy server."""

import json
import logging
import time
import uuid
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from llm_proxifier.queue_manager import QueueManager
from llm_proxifier.utils import (
    extract_model_name,
    format_error_response,
    validate_openai_request,
)


class ProxyHandler:
    """Handles proxying requests to model servers."""

    def __init__(self, queue_manager: QueueManager = None):
        self.logger = logging.getLogger(__name__)
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(300.0))  # 5 minute timeout
        self.queue_manager = queue_manager

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

    async def should_queue_request(self, model_name: str) -> bool:
        """Check if request should be queued for the model."""
        if not self.queue_manager:
            return False
        return self.queue_manager.should_queue_request(model_name)

    async def queue_request(self, model_name: str, endpoint: str) -> Dict[str, Any]:
        """Queue a request for later processing."""
        if not self.queue_manager:
            return {"queued": False, "error": "Queue manager not available"}

        request_id = str(uuid.uuid4())
        client_id = str(uuid.uuid4())  # In a real implementation, you'd extract this from auth

        success = await self.queue_manager.queue_request(model_name, request_id, client_id, endpoint)

        if success:
            queue_stats = self.queue_manager.get_queue_stats(model_name)
            return {
                "queued": True,
                "request_id": request_id,
                "position": queue_stats.get("queue_size", 0),
                "model_state": queue_stats.get("state", "unknown")
            }
        else:
            return {"queued": False, "error": "Queue is full"}

    def get_queue_headers(self, model_name: str) -> Dict[str, str]:
        """Get queue-related headers for responses."""
        if not self.queue_manager:
            return {}

        stats = self.queue_manager.get_queue_stats(model_name)
        headers = {}

        if stats.get("queue_size", 0) > 0:
            headers["X-Queue-Position"] = str(stats["queue_size"])
            headers["X-Queue-Model-State"] = stats.get("state", "unknown")

        return headers

    async def handle_chat_completions(self, request: Request, model_name: str, target_url: str) -> Any:
        """Handle chat completions with queueing support."""
        # Check if request should be queued
        if await self.should_queue_request(model_name):
            queue_result = await self.queue_request(model_name, "/v1/chat/completions")

            if queue_result["queued"]:
                # Return 202 Accepted with queue information
                return JSONResponse(
                    status_code=202,
                    content={
                        "message": "Request queued",
                        "request_id": queue_result["request_id"],
                        "position": queue_result["position"],
                        "model_state": queue_result["model_state"]
                    },
                    headers={
                        "Retry-After": "30",  # Suggest retry after 30 seconds
                        "X-Queue-Position": str(queue_result["position"]),
                        "X-Queue-Model-State": queue_result["model_state"]
                    }
                )
            else:
                # Queue is full, return 503
                return JSONResponse(
                    status_code=503,
                    content=format_error_response(
                        503,
                        "Service temporarily unavailable - queue is full",
                        "service_unavailable"
                    ),
                    headers={"Retry-After": "60"}
                )

        # Normal request processing - model should be running
        if not target_url:
            raise HTTPException(
                status_code=503,
                detail=format_error_response(
                    503,
                    f"Model {model_name} is not available",
                    "service_unavailable"
                )
            )
        return await self.forward_request(request, target_url, "/v1/chat/completions", model_name)

    async def handle_completions(self, request: Request, model_name: str, target_url: str) -> Any:
        """Handle completions with queueing support."""
        # Check if request should be queued
        if await self.should_queue_request(model_name):
            queue_result = await self.queue_request(model_name, "/v1/completions")

            if queue_result["queued"]:
                # Return 202 Accepted with queue information
                return JSONResponse(
                    status_code=202,
                    content={
                        "message": "Request queued",
                        "request_id": queue_result["request_id"],
                        "position": queue_result["position"],
                        "model_state": queue_result["model_state"]
                    },
                    headers={
                        "Retry-After": "30",
                        "X-Queue-Position": str(queue_result["position"]),
                        "X-Queue-Model-State": queue_result["model_state"]
                    }
                )
            else:
                # Queue is full, return 503
                return JSONResponse(
                    status_code=503,
                    content=format_error_response(
                        503,
                        "Service temporarily unavailable - queue is full",
                        "service_unavailable"
                    ),
                    headers={"Retry-After": "60"}
                )

        # Normal request processing - model should be running
        if not target_url:
            raise HTTPException(
                status_code=503,
                detail=format_error_response(
                    503,
                    f"Model {model_name} is not available",
                    "service_unavailable"
                )
            )
        return await self.forward_request(request, target_url, "/v1/completions", model_name)

    async def forward_request(self, request: Request, target_url: str, endpoint: str, model_name: str = None) -> Any:
        """Forward request to the target model server."""
        start_time = time.time()
        success = False

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

            # Track success if we get a response
            success = 200 <= response.status_code < 400

            # Check if this is a streaming response
            content_type = response.headers.get('content-type', '')
            if 'text/event-stream' in content_type or 'stream' in str(dict(request.query_params)):
                result = await self._handle_streaming_response(response)
            else:
                result = await self._handle_regular_response(response, model_name)

            return result

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
        finally:
            # Track metrics for this request
            if model_name and self.queue_manager:
                processing_time = time.time() - start_time
                wait_time = 0.0  # TODO: track actual wait time from queue

                try:
                    await self.queue_manager.track_request_metrics(
                        model_name=model_name,
                        wait_time=wait_time,
                        processing_time=processing_time,
                        success=success
                    )
                except Exception as e:
                    self.logger.error(f"Error tracking metrics for {model_name}: {e}")

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

    async def _handle_regular_response(self, response: httpx.Response, model_name: str = None) -> JSONResponse:
        """Handle regular JSON response."""
        try:
            content = response.json()

            # Get response headers and add queue headers if available
            response_headers = dict(response.headers)
            if model_name:
                queue_headers = self.get_queue_headers(model_name)
                response_headers.update(queue_headers)

            return JSONResponse(
                content=content,
                status_code=response.status_code,
                headers=response_headers
            )

        except json.JSONDecodeError:
            # If response is not JSON, return as text
            response_headers = dict(response.headers)
            if model_name:
                queue_headers = self.get_queue_headers(model_name)
                response_headers.update(queue_headers)

            return JSONResponse(
                content={"text": response.text},
                status_code=response.status_code,
                headers=response_headers
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
