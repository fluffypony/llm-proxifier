"""Tests for utility functions."""

import pytest
import json
from src.utils import (
    is_port_open,
    format_llama_cpp_command,
    validate_openai_request,
    extract_model_name,
    format_error_response,
    get_system_memory_usage
)
from src.config import ModelConfig


def test_is_port_open():
    """Test port availability checking."""
    # Test with a high port that should be available
    assert is_port_open(65000)
    
    # Test with a port that's likely in use (though this might be flaky)
    # We'll skip this test if it's unreliable in CI


def test_format_llama_cpp_command():
    """Test llama.cpp command formatting."""
    config = ModelConfig(
        name="test-model",
        port=11001,
        model_path="/path/to/model.gguf",
        context_length=4096,
        gpu_layers=-1,
        chat_format="chatml",
        additional_args=["--mlock", "--n_batch=512"]
    )
    
    cmd = format_llama_cpp_command(config)
    
    expected_parts = [
        "llama-server",
        "--model", "/path/to/model.gguf",
        "--port", "11001",
        "--ctx-size", "4096",
        "--n-gpu-layers", "-1",
        "--chat-template", "chatml",
        "--host", "127.0.0.1",
        "--mlock",
        "--n_batch=512"
    ]
    
    assert cmd == expected_parts


def test_validate_openai_request():
    """Test OpenAI request validation."""
    # Valid request
    valid_request = {
        "model": "test-model",
        "messages": [{"role": "user", "content": "Hello"}]
    }
    assert validate_openai_request(valid_request)
    
    # Missing model
    invalid_request = {
        "messages": [{"role": "user", "content": "Hello"}]
    }
    assert not validate_openai_request(invalid_request)
    
    # Empty request
    assert not validate_openai_request({})


def test_extract_model_name():
    """Test model name extraction."""
    request_data = {
        "model": "test-model",
        "messages": [{"role": "user", "content": "Hello"}]
    }
    
    assert extract_model_name(request_data) == "test-model"
    
    # Missing model
    assert extract_model_name({}) is None


def test_format_error_response():
    """Test error response formatting."""
    error = format_error_response(400, "Bad request", "invalid_request")
    
    expected = {
        "error": {
            "message": "Bad request",
            "type": "invalid_request",
            "code": 400
        }
    }
    
    assert error == expected


def test_get_system_memory_usage():
    """Test system memory usage retrieval."""
    memory = get_system_memory_usage()
    
    # Check that we get the expected fields
    assert "total" in memory
    assert "available" in memory
    assert "used" in memory
    assert "percent" in memory
    
    # Check that values are reasonable
    assert memory["total"] > 0
    assert memory["available"] >= 0
    assert memory["used"] >= 0
    assert 0 <= memory["percent"] <= 100
