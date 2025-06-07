"""
Audit logging system for LLM Proxifier configuration changes.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional


class AuditLogger:
    def __init__(self, log_file: str = "logs/audit.log"):
        """Initialize audit logger."""
        self.log_file = log_file

        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        # Configure logger
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)

        # Avoid duplicate handlers
        if not self.logger.handlers:
            handler = logging.FileHandler(log_file)
            formatter = logging.Formatter('%(asctime)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_config_change(self, user: str, config_type: str, action: str, details: Dict[str, Any]):
        """Log configuration changes."""
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user or "system",
            "action": f"config_{action}",
            "config_type": config_type,
            "details": details
        }
        self.logger.info(json.dumps(audit_entry))

    def log_model_action(self, user: str, model_name: str, action: str, details: Optional[Dict[str, Any]] = None):
        """Log model management actions."""
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user or "system",
            "action": f"model_{action}",
            "model_name": model_name,
            "details": details or {}
        }
        self.logger.info(json.dumps(audit_entry))

    def log_bulk_action(self, user: str, action: str, targets: list, details: Optional[Dict[str, Any]] = None):
        """Log bulk operations."""
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user or "system",
            "action": f"bulk_{action}",
            "targets": targets,
            "target_count": len(targets),
            "details": details or {}
        }
        self.logger.info(json.dumps(audit_entry))

    def log_auth_event(self, user: str, event: str, details: Optional[Dict[str, Any]] = None):
        """Log authentication events."""
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user or "anonymous",
            "action": f"auth_{event}",
            "details": details or {}
        }
        self.logger.info(json.dumps(audit_entry))

# Global audit logger instance
audit_logger = AuditLogger()
