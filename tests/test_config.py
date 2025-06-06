"""Tests for configuration module."""

import pytest
import tempfile
import os
from src.config import ModelConfig, ProxyConfig, ConfigManager


def test_model_config_validation():
    """Test ModelConfig validation."""
    # Valid config
    config = ModelConfig(
        name="test-model",
        port=11001,
        model_path="/tmp/test.gguf",
        context_length=4096
    )
    assert config.name == "test-model"
    assert config.port == 11001
    
    # Invalid port range
    with pytest.raises(ValueError):
        ModelConfig(
            name="test",
            port=80,  # Too low
            model_path="/tmp/test.gguf"
        )
    
    with pytest.raises(ValueError):
        ModelConfig(
            name="test",
            port=70000,  # Too high
            model_path="/tmp/test.gguf"
        )


def test_proxy_config_validation():
    """Test ProxyConfig validation."""
    # Valid config
    config = ProxyConfig(port=8000, timeout_minutes=2)
    assert config.port == 8000
    assert config.timeout_minutes == 2
    
    # Invalid values
    with pytest.raises(ValueError):
        ProxyConfig(port=80)  # Too low
    
    with pytest.raises(ValueError):
        ProxyConfig(timeout_minutes=0)  # Too low
    
    with pytest.raises(ValueError):
        ProxyConfig(max_concurrent_models=0)  # Too low


def test_config_manager():
    """Test ConfigManager functionality."""
    # Create temporary config file
    config_yaml = """
models:
  test-model:
    port: 11001
    model_path: "/tmp/test.gguf"
    context_length: 4096
    gpu_layers: -1
    chat_format: "chatml"
    additional_args:
      - "--mlock"
  
  another-model:
    port: 11002
    model_path: "/tmp/another.gguf"
    context_length: 8192
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_yaml)
        config_path = f.name
    
    try:
        # Test loading valid config
        manager = ConfigManager(config_path)
        configs = manager.load_model_configs()
        
        assert len(configs) == 2
        assert "test-model" in configs
        assert "another-model" in configs
        
        test_config = configs["test-model"]
        assert test_config.port == 11001
        assert test_config.context_length == 4096
        assert "--mlock" in test_config.additional_args
        
        # Test port validation
        assert manager.validate_model_ports()
        
        # Test get_model_config
        config = manager.get_model_config("test-model")
        assert config is not None
        assert config.name == "test-model"
        
        # Test non-existent model
        config = manager.get_model_config("non-existent")
        assert config is None
        
        # Test list_model_names
        names = manager.list_model_names()
        assert set(names) == {"test-model", "another-model"}
        
    finally:
        os.unlink(config_path)


def test_config_manager_invalid_file():
    """Test ConfigManager with invalid files."""
    manager = ConfigManager("/non/existent/path.yaml")
    
    with pytest.raises(ValueError, match="Configuration file not found"):
        manager.load_model_configs()


def test_config_manager_invalid_yaml():
    """Test ConfigManager with invalid YAML."""
    invalid_yaml = "invalid: yaml: content: ["
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(invalid_yaml)
        config_path = f.name
    
    try:
        manager = ConfigManager(config_path)
        with pytest.raises(ValueError, match="Invalid YAML"):
            manager.load_model_configs()
    finally:
        os.unlink(config_path)


def test_config_manager_missing_models_section():
    """Test ConfigManager with missing models section."""
    config_yaml = """
proxy:
  port: 8000
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_yaml)
        config_path = f.name
    
    try:
        manager = ConfigManager(config_path)
        with pytest.raises(ValueError, match="must contain 'models' section"):
            manager.load_model_configs()
    finally:
        os.unlink(config_path)
