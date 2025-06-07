"""Configuration management API for LLM Proxifier."""

import os
import json
import yaml
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path

import logging

logger = logging.getLogger(__name__)


@dataclass
class ConfigBackup:
    """Represents a configuration backup."""
    backup_id: str
    config_type: str  # "models" or "auth"
    timestamp: datetime
    description: str
    file_path: str


class ConfigurationManager:
    """Manages configuration files and their validation."""
    
    def __init__(self, config_dir: str = "config", backup_dir: str = "config/backups"):
        self.config_dir = Path(config_dir)
        self.backup_dir = Path(backup_dir)
        self.models_config_path = self.config_dir / "models.yaml"
        self.auth_config_path = self.config_dir / "auth.yaml"
        
        # Ensure directories exist
        self.config_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
    
    def load_models_config(self) -> Dict[str, Any]:
        """Load and validate models.yaml configuration."""
        try:
            if not self.models_config_path.exists():
                self.logger.warning(f"Models config file not found: {self.models_config_path}")
                return {}
            
            with open(self.models_config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
            
            self.logger.info(f"Loaded models configuration with {len(config.get('models', {}))} models")
            return config
        except Exception as e:
            self.logger.error(f"Error loading models config: {e}")
            return {}
    
    def save_models_config(self, config_data: Dict[str, Any], backup: bool = True) -> Dict[str, Any]:
        """Save models.yaml configuration with validation."""
        try:
            # Validate configuration first
            validation_result = self.validate_config(config_data, "models")
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": "Configuration validation failed",
                    "validation_errors": validation_result["errors"]
                }
            
            # Create backup if requested
            backup_info = None
            if backup and self.models_config_path.exists():
                backup_info = self.backup_config("models", "Auto-backup before save")
            
            # Save new configuration
            with open(self.models_config_path, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
            
            self.logger.info(f"Saved models configuration")
            
            return {
                "success": True,
                "message": "Models configuration saved successfully",
                "backup_created": backup_info["backup_id"] if backup_info else None,
                "validation_warnings": validation_result.get("warnings", [])
            }
        except Exception as e:
            self.logger.error(f"Error saving models config: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def load_auth_config(self) -> Dict[str, Any]:
        """Load and validate auth.yaml configuration."""
        try:
            if not self.auth_config_path.exists():
                self.logger.warning(f"Auth config file not found: {self.auth_config_path}")
                return {"enabled": False}
            
            with open(self.auth_config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
            
            self.logger.info(f"Loaded auth configuration")
            return config
        except Exception as e:
            self.logger.error(f"Error loading auth config: {e}")
            return {"enabled": False}
    
    def save_auth_config(self, config_data: Dict[str, Any], backup: bool = True) -> Dict[str, Any]:
        """Save auth.yaml configuration with validation."""
        try:
            # Validate configuration first
            validation_result = self.validate_config(config_data, "auth")
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": "Configuration validation failed",
                    "validation_errors": validation_result["errors"]
                }
            
            # Create backup if requested
            backup_info = None
            if backup and self.auth_config_path.exists():
                backup_info = self.backup_config("auth", "Auto-backup before save")
            
            # Save new configuration
            with open(self.auth_config_path, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
            
            self.logger.info(f"Saved auth configuration")
            
            return {
                "success": True,
                "message": "Auth configuration saved successfully",
                "backup_created": backup_info["backup_id"] if backup_info else None,
                "validation_warnings": validation_result.get("warnings", [])
            }
        except Exception as e:
            self.logger.error(f"Error saving auth config: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def backup_config(self, config_type: str, description: str = "") -> Dict[str, Any]:
        """Create timestamped backup of configuration."""
        try:
            timestamp = datetime.now()
            backup_id = f"{config_type}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
            
            source_path = self.models_config_path if config_type == "models" else self.auth_config_path
            backup_path = self.backup_dir / f"{backup_id}.yaml"
            
            if not source_path.exists():
                return {
                    "success": False,
                    "error": f"Source config file does not exist: {source_path}"
                }
            
            # Copy file to backup location
            shutil.copy2(source_path, backup_path)
            
            # Create metadata file
            metadata = {
                "backup_id": backup_id,
                "config_type": config_type,
                "timestamp": timestamp.isoformat(),
                "description": description,
                "original_file": str(source_path),
                "backup_file": str(backup_path)
            }
            
            metadata_path = self.backup_dir / f"{backup_id}.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            self.logger.info(f"Created config backup: {backup_id}")
            
            return {
                "success": True,
                "backup_id": backup_id,
                "backup_path": str(backup_path),
                "timestamp": timestamp.isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error creating config backup: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def restore_config(self, config_type: str, backup_id: str) -> Dict[str, Any]:
        """Restore configuration from backup."""
        try:
            backup_path = self.backup_dir / f"{backup_id}.yaml"
            metadata_path = self.backup_dir / f"{backup_id}.json"
            
            if not backup_path.exists() or not metadata_path.exists():
                return {
                    "success": False,
                    "error": f"Backup not found: {backup_id}"
                }
            
            # Load and verify metadata
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            if metadata["config_type"] != config_type:
                return {
                    "success": False,
                    "error": f"Config type mismatch: expected {config_type}, got {metadata['config_type']}"
                }
            
            # Create backup of current config before restore
            current_backup = self.backup_config(config_type, f"Before restore from {backup_id}")
            
            # Restore from backup
            target_path = self.models_config_path if config_type == "models" else self.auth_config_path
            shutil.copy2(backup_path, target_path)
            
            self.logger.info(f"Restored {config_type} config from backup: {backup_id}")
            
            return {
                "success": True,
                "message": f"Configuration restored from backup {backup_id}",
                "current_backup_id": current_backup.get("backup_id"),
                "restored_from": metadata["timestamp"]
            }
        except Exception as e:
            self.logger.error(f"Error restoring config from backup {backup_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def list_backups(self, config_type: str = None) -> List[ConfigBackup]:
        """List available configuration backups."""
        try:
            backups = []
            
            for metadata_file in self.backup_dir.glob("*.json"):
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    # Filter by config type if specified
                    if config_type and metadata["config_type"] != config_type:
                        continue
                    
                    backup = ConfigBackup(
                        backup_id=metadata["backup_id"],
                        config_type=metadata["config_type"],
                        timestamp=datetime.fromisoformat(metadata["timestamp"]),
                        description=metadata["description"],
                        file_path=metadata["backup_file"]
                    )
                    backups.append(backup)
                except Exception as e:
                    self.logger.warning(f"Error reading backup metadata {metadata_file}: {e}")
            
            # Sort by timestamp (newest first)
            backups.sort(key=lambda x: x.timestamp, reverse=True)
            
            return backups
        except Exception as e:
            self.logger.error(f"Error listing backups: {e}")
            return []
    
    def validate_config(self, config_data: Dict[str, Any], config_type: str) -> Dict[str, Any]:
        """Validate configuration before saving."""
        errors = []
        warnings = []
        
        try:
            if config_type == "models":
                errors.extend(self._validate_models_config(config_data))
            elif config_type == "auth":
                errors.extend(self._validate_auth_config(config_data))
            else:
                errors.append(f"Unknown config type: {config_type}")
            
            is_valid = len(errors) == 0
            
            return {
                "valid": is_valid,
                "errors": errors,
                "warnings": warnings,
                "validated_at": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": warnings,
                "validated_at": datetime.now().isoformat()
            }
    
    def _validate_models_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate models configuration structure."""
        errors = []
        
        if "models" not in config:
            errors.append("Missing 'models' section")
            return errors
        
        models = config["models"]
        if not isinstance(models, dict):
            errors.append("'models' must be a dictionary")
            return errors
        
        for model_name, model_config in models.items():
            # Required fields
            required_fields = ["model_path", "port"]
            for field in required_fields:
                if field not in model_config:
                    errors.append(f"Model '{model_name}' missing required field: {field}")
            
            # Validate port
            if "port" in model_config:
                port = model_config["port"]
                if not isinstance(port, int) or port < 1024 or port > 65535:
                    errors.append(f"Model '{model_name}' invalid port: {port}")
            
            # Validate optional fields
            if "priority" in model_config:
                priority = model_config["priority"]
                if not isinstance(priority, int) or priority < 1 or priority > 10:
                    errors.append(f"Model '{model_name}' priority must be between 1-10")
            
            if "auto_start" in model_config:
                if not isinstance(model_config["auto_start"], bool):
                    errors.append(f"Model '{model_name}' auto_start must be boolean")
            
            if "preload" in model_config:
                if not isinstance(model_config["preload"], bool):
                    errors.append(f"Model '{model_name}' preload must be boolean")
        
        return errors
    
    def _validate_auth_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate auth configuration structure."""
        errors = []
        
        # Validate enabled field
        if "enabled" not in config:
            errors.append("Missing 'enabled' field")
        elif not isinstance(config["enabled"], bool):
            errors.append("'enabled' must be boolean")
        
        # If auth is enabled, validate other fields
        if config.get("enabled", False):
            if "api_keys" in config:
                api_keys = config["api_keys"]
                if not isinstance(api_keys, dict):
                    errors.append("'api_keys' must be a dictionary")
                else:
                    for key_name, key_config in api_keys.items():
                        if not isinstance(key_config, dict):
                            errors.append(f"API key '{key_name}' config must be a dictionary")
                        elif "key" not in key_config:
                            errors.append(f"API key '{key_name}' missing 'key' field")
            
            if "rate_limits" in config:
                rate_limits = config["rate_limits"]
                if not isinstance(rate_limits, dict):
                    errors.append("'rate_limits' must be a dictionary")
                else:
                    for limit_name, limit_value in rate_limits.items():
                        if not isinstance(limit_value, int) or limit_value <= 0:
                            errors.append(f"Rate limit '{limit_name}' must be positive integer")
        
        return errors
    
    def get_config_schema(self, config_type: str) -> Dict[str, Any]:
        """Return JSON schema for configuration validation."""
        if config_type == "models":
            return {
                "type": "object",
                "properties": {
                    "models": {
                        "type": "object",
                        "patternProperties": {
                            ".*": {
                                "type": "object",
                                "required": ["model_path", "port"],
                                "properties": {
                                    "model_path": {"type": "string"},
                                    "port": {"type": "integer", "minimum": 1024, "maximum": 65535},
                                    "priority": {"type": "integer", "minimum": 1, "maximum": 10},
                                    "resource_group": {"type": "string"},
                                    "auto_start": {"type": "boolean"},
                                    "preload": {"type": "boolean"},
                                    "context_size": {"type": "integer", "minimum": 1},
                                    "gpu_layers": {"type": "integer", "minimum": 0},
                                    "threads": {"type": "integer", "minimum": 1}
                                }
                            }
                        }
                    }
                },
                "required": ["models"]
            }
        elif config_type == "auth":
            return {
                "type": "object",
                "required": ["enabled"],
                "properties": {
                    "enabled": {"type": "boolean"},
                    "dashboard_auth_required": {"type": "boolean"},
                    "api_keys": {
                        "type": "object",
                        "patternProperties": {
                            ".*": {
                                "type": "object",
                                "required": ["key"],
                                "properties": {
                                    "key": {"type": "string"},
                                    "permissions": {"type": "array", "items": {"type": "string"}},
                                    "expires": {"type": "string", "format": "date-time"}
                                }
                            }
                        }
                    },
                    "rate_limits": {
                        "type": "object",
                        "patternProperties": {
                            ".*": {"type": "integer", "minimum": 1}
                        }
                    },
                    "public_endpoints": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            }
        else:
            return {}
