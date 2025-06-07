"""Utility functions for the LLM proxy server."""

import asyncio
import json
import socket
import subprocess
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
import psutil

from llm_proxifier.config import ModelConfig


def is_port_open(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is available for binding."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            return True
    except OSError:
        return False


def is_port_listening(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is currently listening (in use)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex((host, port))
            return result == 0
    except OSError:
        return False


async def wait_for_server(url: str, timeout: int = 60) -> bool:
    """Wait for a server to respond to health checks."""
    start_time = time.time()

    async with httpx.AsyncClient() as client:
        while time.time() - start_time < timeout:
            try:
                response = await client.get(f"{url}/health", timeout=5.0)
                if response.status_code == 200:
                    return True
            except (httpx.RequestError, httpx.TimeoutException):
                pass

            await asyncio.sleep(1)

    return False


def format_llama_cpp_command(config: ModelConfig) -> List[str]:
    """Build command line arguments for llama.cpp server."""
    cmd = [
        "llama-server",
        "--model", config.model_path,
        "--port", str(config.port),
        "--ctx-size", str(config.context_length),
        "--n-gpu-layers", str(config.gpu_layers),
        "--chat-template", config.chat_format,
        "--host", "127.0.0.1"
    ]

    # Add additional arguments
    cmd.extend(config.additional_args)

    return cmd


async def parse_sse_stream(response: httpx.Response) -> AsyncGenerator[Dict[str, Any], None]:
    """Parse server-sent events from a streaming response."""
    async for line in response.aiter_lines():
        if line.startswith("data: "):
            data = line[6:]  # Remove "data: " prefix

            if data.strip() == "[DONE]":
                break

            try:
                yield json.loads(data)
            except json.JSONDecodeError:
                continue


def get_process_memory_usage(pid: int) -> Optional[float]:
    """Get memory usage of a process in MB."""
    try:
        process = psutil.Process(pid)
        memory_info = process.memory_info()
        return memory_info.rss / 1024 / 1024  # Convert to MB
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


def get_process_cpu_usage(pid: int) -> Optional[float]:
    """Get CPU usage percentage of a process."""
    try:
        process = psutil.Process(pid)
        return process.cpu_percent()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


async def graceful_shutdown(process: subprocess.Popen, timeout: int = 5) -> bool:
    """Gracefully shutdown a subprocess with timeout."""
    try:
        # Send SIGTERM
        process.terminate()

        # Wait for graceful shutdown
        try:
            await asyncio.wait_for(process.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            # Force kill if timeout
            process.kill()
            await process.wait()
            return False

    except Exception:
        return False


def validate_openai_request(request_data: Dict[str, Any]) -> bool:
    """Validate that request follows OpenAI API format."""
    required_fields = ["model"]

    for field in required_fields:
        if field not in request_data:
            return False

    return True


def extract_model_name(request_data: Dict[str, Any]) -> Optional[str]:
    """Extract model name from OpenAI API request."""
    return request_data.get("model")


def format_error_response(status_code: int, message: str, error_type: str = "error") -> Dict[str, Any]:
    """Format error response in OpenAI API format."""
    return {
        "error": {
            "message": message,
            "type": error_type,
            "code": status_code
        }
    }


def get_system_memory_usage() -> Dict[str, float]:
    """Get system memory usage statistics."""
    memory = psutil.virtual_memory()
    return {
        "total": memory.total / 1024 / 1024 / 1024,  # GB
        "available": memory.available / 1024 / 1024 / 1024,  # GB
        "used": memory.used / 1024 / 1024 / 1024,  # GB
        "percent": memory.percent
    }


def format_uptime(seconds: float) -> str:
    """Format uptime seconds into human-readable format."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes}m"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"
    else:
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        return f"{days}d {hours}h"
