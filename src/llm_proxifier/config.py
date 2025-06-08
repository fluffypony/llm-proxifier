"""Configuration module for the LLM proxy server."""

import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import yaml


@dataclass
class ModelConfig:
    """Configuration for a single model."""
    name: str
    port: int
    model_path: str
    context_length: int = 4096
    gpu_layers: int = -1
    chat_format: str = "chatml"
    auto_start: bool = False
    preload: bool = False
    priority: int = 5
    resource_group: str = "default"
    additional_args: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.port < 1024 or self.port > 65535:
            raise ValueError(f"Port {self.port} is out of valid range")

        # Only validate model path if it's not a placeholder path
        if not self.model_path.startswith("./models/") and not os.path.exists(self.model_path):
            raise ValueError(f"Model path {self.model_path} does not exist")


@dataclass
class ProxyConfig:
    """Configuration for the proxy server."""
    host: str = "0.0.0.0"
    port: int = 8000
    timeout_minutes: int = 5
    health_check_interval: int = 30
    max_concurrent_models: int = 4
    log_level: str = "INFO"
    config_path: str = "./config/models.yaml"
    dashboard_port: int = 3000
    dashboard_enabled: bool = True
    auth_enabled: bool = True

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.port < 1024 or self.port > 65535:
            raise ValueError(f"Port {self.port} is out of valid range")

        if self.timeout_minutes < 1:
            raise ValueError("Timeout must be at least 1 minute")

        if self.max_concurrent_models < 1:
            raise ValueError("Must allow at least 1 concurrent model")


class ConfigManager:
    """Manages loading and validation of configurations."""

    def __init__(self, config_path: Optional[str] = None, auth_config_path: Optional[str] = None):
        self.config_path = config_path or os.getenv("CONFIG_PATH", "./config/models.yaml")
        self.auth_config_path = auth_config_path or os.getenv("AUTH_CONFIG_PATH", "./config/auth.yaml")
        self.proxy_config = self._load_proxy_config()
        self.auth_config = self._load_auth_config()
        self.model_configs: Dict[str, ModelConfig] = {}
        self._config_version = None
        self._auth_version = None

    def _load_proxy_config(self) -> ProxyConfig:
        """Load proxy configuration from environment variables."""
        return ProxyConfig(
            host=os.getenv("PROXY_HOST", "0.0.0.0"),
            port=int(os.getenv("PROXY_PORT", "8000")),
            timeout_minutes=int(os.getenv("TIMEOUT_MINUTES", "5")),
            health_check_interval=int(os.getenv("HEALTH_CHECK_INTERVAL", "30")),
            max_concurrent_models=int(os.getenv("MAX_CONCURRENT_MODELS", "4")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            config_path=self.config_path,
            dashboard_port=int(os.getenv("DASHBOARD_PORT", "3000")),
            dashboard_enabled=os.getenv("DASHBOARD_ENABLED", "true").lower() == "true",
            auth_enabled=os.getenv("AUTH_ENABLED", "true").lower() == "true"
        )

    def load_model_configs(self) -> Dict[str, ModelConfig]:
        """Load model configurations from YAML file."""
        try:
            with open(self.config_path) as f:
                data = yaml.safe_load(f)

            if 'models' not in data:
                raise ValueError("Configuration file must contain 'models' section")

            configs = {}
            for name, config_data in data['models'].items():
                config_data['name'] = name
                configs[name] = ModelConfig(**config_data)

            self.model_configs = configs
            return configs

        except FileNotFoundError:
            raise ValueError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")
        except Exception as e:
            raise ValueError(f"Error loading configuration: {e}")

    def get_model_config(self, name: str) -> Optional[ModelConfig]:
        """Get configuration for a specific model."""
        return self.model_configs.get(name)

    def list_model_names(self) -> List[str]:
        """Get list of configured model names."""
        return list(self.model_configs.keys())

    def _load_auth_config(self) -> 'AuthConfig':
        """Load authentication configuration from YAML file."""
        try:
            with open(self.auth_config_path) as f:
                data = yaml.safe_load(f)

            if 'authentication' not in data:
                return AuthConfig()  # Return default config if no auth section

            auth_data = data['authentication']

            # Parse API keys
            keys = []
            for key_data in auth_data.get('api_keys', []):
                keys.append(APIKeyConfig(**key_data))

            return AuthConfig(
                enabled=auth_data.get('enabled', False),
                keys=keys,
                public_endpoints=auth_data.get('public_endpoints', ["/health", "/metrics"]),
                dashboard_auth_required=auth_data.get('dashboard_auth_required', True),
                rate_limits=auth_data.get('rate_limits', {"default": 100})
            )

        except FileNotFoundError:
            # Return default config if auth file doesn't exist
            return AuthConfig()
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in auth configuration file: {e}")
        except Exception as e:
            raise ValueError(f"Error loading auth configuration: {e}")

    def validate_model_ports(self) -> bool:
        """Validate that all model ports are unique."""
        ports = [config.port for config in self.model_configs.values()]
        return len(ports) == len(set(ports))

    def get_config_hash(self, file_path: str) -> str:
        """Get hash of configuration file content."""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return hashlib.md5(content).hexdigest()
        except FileNotFoundError:
            return ""

    def has_config_changed(self) -> bool:
        """Check if model configuration has changed."""
        current_hash = self.get_config_hash(self.config_path)
        if self._config_version != current_hash:
            self._config_version = current_hash
            return True
        return False

    def has_auth_config_changed(self) -> bool:
        """Check if auth configuration has changed."""
        current_hash = self.get_config_hash(self.auth_config_path)
        if self._auth_version != current_hash:
            self._auth_version = current_hash
            return True
        return False


@dataclass
class APIKeyConfig:
    """Configuration for a single API key."""
    key: str
    name: str
    permissions: List[str] = field(default_factory=lambda: ["*"])
    expires: Optional[str] = None

    def is_expired(self) -> bool:
        """Check if the key has expired."""
        if not self.expires:
            return False
        try:
            expiry_date = datetime.fromisoformat(self.expires)
            return datetime.now() > expiry_date
        except ValueError:
            return False

    def has_permission(self, endpoint: str) -> bool:
        """Check if key has permission for endpoint."""
        if "*" in self.permissions:
            return True
        return any(endpoint.startswith(perm) for perm in self.permissions)


@dataclass
class AuthConfig:
    """Configuration for authentication."""
    enabled: bool = False
    keys: List[APIKeyConfig] = field(default_factory=list)
    public_endpoints: List[str] = field(default_factory=lambda: ["/health", "/metrics"])
    dashboard_auth_required: bool = True
    rate_limits: Dict[str, int] = field(default_factory=lambda: {"default": 100})

    def get_api_key(self, key: str) -> Optional[APIKeyConfig]:
        """Get API key configuration by key value."""
        return next((api_key for api_key in self.keys if api_key.key == key), None)

    def is_public_endpoint(self, endpoint: str) -> bool:
        """Check if endpoint is public (no auth required)."""
        return any(endpoint.startswith(pub) for pub in self.public_endpoints)
