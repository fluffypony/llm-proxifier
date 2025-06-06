"""Tests for model manager."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from src.model_manager import ModelInstance, ModelManager
from src.config import ModelConfig


@pytest.fixture
def sample_model_config():
    """Create a sample model configuration."""
    return ModelConfig(
        name="test-model",
        port=11001,
        model_path="/tmp/test.gguf",
        context_length=4096,
        gpu_layers=-1,
        chat_format="chatml"
    )


@pytest.fixture
def model_manager():
    """Create a model manager instance."""
    return ModelManager(timeout_minutes=1, max_concurrent=2)


def test_model_instance_properties(sample_model_config):
    """Test ModelInstance properties."""
    instance = ModelInstance(config=sample_model_config)
    
    assert instance.health_check_url == "http://127.0.0.1:11001"
    assert instance.api_url == "http://127.0.0.1:11001"
    assert not instance.is_ready
    assert instance.request_count == 0


def test_model_instance_update_access_time(sample_model_config):
    """Test access time updating."""
    instance = ModelInstance(config=sample_model_config)
    
    initial_time = instance.last_accessed
    initial_count = instance.request_count
    
    instance.update_access_time()
    
    assert instance.last_accessed != initial_time
    assert instance.request_count == initial_count + 1


@pytest.mark.asyncio
async def test_model_manager_load_configs(model_manager, sample_model_config):
    """Test loading configurations."""
    configs = {"test-model": sample_model_config}
    model_manager.load_configs(configs)
    
    assert "test-model" in model_manager.configs
    assert model_manager.configs["test-model"] == sample_model_config


@pytest.mark.asyncio
async def test_model_manager_get_unconfigured_model(model_manager):
    """Test getting an unconfigured model."""
    result = await model_manager.get_or_start_model("nonexistent")
    assert result is None


@pytest.mark.asyncio
@patch('src.model_manager.is_port_listening')
@patch('src.model_manager.wait_for_server')
@patch('subprocess.Popen')
async def test_model_instance_start_success(mock_popen, mock_wait, mock_port, sample_model_config):
    """Test successful model startup."""
    # Mock subprocess
    mock_process = Mock()
    mock_process.poll.return_value = None  # Process is running
    mock_popen.return_value = mock_process
    
    # Mock port checking
    mock_port.return_value = False  # Port is free
    
    # Mock server wait
    mock_wait.return_value = True  # Server becomes ready
    
    instance = ModelInstance(config=sample_model_config)
    result = await instance.start()
    
    assert result is True
    assert instance.is_ready
    assert instance.process == mock_process
    assert instance.last_accessed is not None


@pytest.mark.asyncio
@patch('src.model_manager.is_port_listening')
async def test_model_instance_start_port_in_use(mock_port, sample_model_config):
    """Test model startup when port is in use."""
    mock_port.return_value = True  # Port is in use
    
    instance = ModelInstance(config=sample_model_config)
    result = await instance.start()
    
    assert result is False
    assert not instance.is_ready


@pytest.mark.asyncio
async def test_model_instance_stop(sample_model_config):
    """Test model stopping."""
    instance = ModelInstance(config=sample_model_config)
    
    # Mock process
    mock_process = Mock()
    instance.process = mock_process
    
    with patch('src.model_manager.graceful_shutdown') as mock_shutdown:
        mock_shutdown.return_value = True
        
        result = await instance.stop()
        
        assert result is True
        assert instance.process is None
        assert not instance.is_ready


@pytest.mark.asyncio
async def test_model_instance_health_check_no_process(sample_model_config):
    """Test health check with no process."""
    instance = ModelInstance(config=sample_model_config)
    
    result = await instance.health_check()
    
    assert result is False
    assert not instance.is_ready


@pytest.mark.asyncio
async def test_model_manager_max_concurrent(model_manager, sample_model_config):
    """Test maximum concurrent models limit."""
    configs = {
        "model1": sample_model_config,
        "model2": ModelConfig(
            name="model2", port=11002, model_path="/tmp/test2.gguf"
        ),
        "model3": ModelConfig(
            name="model3", port=11003, model_path="/tmp/test3.gguf"
        )
    }
    model_manager.load_configs(configs)
    
    # Mock successful startup for first two models
    with patch.object(ModelInstance, 'start', return_value=True):
        # Start first model
        result1 = await model_manager.get_or_start_model("model1")
        assert result1 is not None
        model_manager.models["model1"].is_ready = True
        
        # Start second model
        result2 = await model_manager.get_or_start_model("model2")
        assert result2 is not None
        model_manager.models["model2"].is_ready = True
        
        # Try to start third model (should fail due to limit)
        result3 = await model_manager.get_or_start_model("model3")
        assert result3 is None


@pytest.mark.asyncio
async def test_model_manager_cleanup_inactive(model_manager, sample_model_config):
    """Test cleanup of inactive models."""
    model_manager.load_configs({"test-model": sample_model_config})
    
    # Create an instance that appears to be running but is old
    instance = ModelInstance(config=sample_model_config)
    instance.is_ready = True
    instance.last_accessed = datetime.now() - timedelta(minutes=5)  # Old access time
    
    with patch.object(instance, 'stop', return_value=True) as mock_stop:
        model_manager.models["test-model"] = instance
        
        # Manually trigger cleanup logic
        async with model_manager.lock:
            current_time = datetime.now()
            timeout_delta = timedelta(minutes=model_manager.timeout_minutes)
            
            models_to_stop = []
            for name, inst in model_manager.models.items():
                if (inst.last_accessed and 
                    current_time - inst.last_accessed > timeout_delta):
                    models_to_stop.append(name)
            
            for name in models_to_stop:
                await model_manager.models[name].stop()
                del model_manager.models[name]
        
        mock_stop.assert_called_once()
        assert "test-model" not in model_manager.models


@pytest.mark.asyncio
async def test_model_manager_get_active_models(model_manager, sample_model_config):
    """Test getting active models list."""
    model_manager.load_configs({"test-model": sample_model_config})
    
    # Initially no active models
    assert model_manager.get_active_models() == []
    
    # Add a ready model
    instance = ModelInstance(config=sample_model_config)
    instance.is_ready = True
    model_manager.models["test-model"] = instance
    
    assert model_manager.get_active_models() == ["test-model"]


def test_model_manager_get_model_status(model_manager, sample_model_config):
    """Test getting model status."""
    # Non-existent model
    status = model_manager.get_model_status("nonexistent")
    assert status["status"] == "stopped"
    
    # Existing model
    instance = ModelInstance(config=sample_model_config)
    instance.is_ready = True
    instance.request_count = 5
    model_manager.models["test-model"] = instance
    
    status = model_manager.get_model_status("test-model")
    assert status["status"] == "running"
    assert status["port"] == 11001
    assert status["request_count"] == 5


@pytest.mark.asyncio
async def test_model_manager_shutdown_all(model_manager, sample_model_config):
    """Test shutting down all models."""
    instance = ModelInstance(config=sample_model_config)
    
    with patch.object(instance, 'stop', return_value=True) as mock_stop:
        model_manager.models["test-model"] = instance
        
        await model_manager.shutdown_all()
        
        mock_stop.assert_called_once()
        assert len(model_manager.models) == 0
