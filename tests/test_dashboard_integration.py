"""
Basic integration tests for dashboard functionality.
"""

import pytest
from fastapi.testclient import TestClient
import json

def test_dashboard_imports():
    """Test that all dashboard modules can be imported."""
    try:
        from src.dashboard import dashboard_router
        from src.audit_logger import audit_logger
        from src.config_notifications import config_notification_manager
        assert dashboard_router is not None
        assert audit_logger is not None
        assert config_notification_manager is not None
    except ImportError as e:
        pytest.fail(f"Failed to import dashboard modules: {e}")

def test_dashboard_endpoints_exist():
    """Test that all new dashboard endpoints are defined."""
    from src.dashboard import dashboard_router
    
    # Get all route paths from the router
    route_paths = [route.path for route in dashboard_router.routes]
    
    # Check for new endpoints
    expected_endpoints = [
        "/api/models/priority",
        "/api/groups",
        "/api/queue/status",
        "/api/config/models",
        "/api/config/auth",
        "/api/models/bulk-action"
    ]
    
    for endpoint in expected_endpoints:
        assert any(endpoint in path for path in route_paths), f"Endpoint {endpoint} not found"

def test_audit_logger_functionality():
    """Test basic audit logger functionality."""
    from src.audit_logger import AuditLogger
    import tempfile
    import os
    
    # Create temporary log file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        log_file = f.name
    
    try:
        logger = AuditLogger(log_file)
        
        # Test logging methods
        logger.log_config_change("test_user", "models", "update", {"model": "test"})
        logger.log_model_action("test_user", "test_model", "start")
        logger.log_bulk_action("test_user", "start", ["model1", "model2"])
        
        # Check that log file was created and has content
        assert os.path.exists(log_file)
        with open(log_file, 'r') as f:
            content = f.read()
            assert "config_update" in content
            assert "model_start" in content
            assert "bulk_start" in content
            assert "test_user" in content
    finally:
        # Clean up
        if os.path.exists(log_file):
            os.unlink(log_file)

def test_config_notification_manager():
    """Test basic notification manager functionality."""
    from src.config_notifications import ConfigNotificationManager
    import asyncio
    
    async def run_test():
        manager = ConfigNotificationManager()
        
        # Test notification creation
        await manager.notify_config_change("models", "updated", {"change": "test"})
        await manager.notify_model_reload("test_model", "starting")
        await manager.notify_system_event("test", "Test event")
        
        # Test getting recent notifications
        notifications = await manager.get_recent_notifications(10)
        assert len(notifications) == 3
        
        # Check notification content
        config_notification = notifications[0]
        assert config_notification["type"] == "config_change"
        assert config_notification["config_type"] == "models"
        
        model_notification = notifications[1]
        assert model_notification["type"] == "model_reload"
        assert model_notification["model_name"] == "test_model"
        
        system_notification = notifications[2]
        assert system_notification["type"] == "system_event"
        assert system_notification["event_type"] == "test"
    
    # Run async test
    asyncio.run(run_test())

def test_dashboard_data_models():
    """Test that Pydantic models are valid."""
    from src.dashboard import PriorityUpdateModel, BulkOperationModel, ConfigUpdateModel
    
    # Test PriorityUpdateModel
    priority_data = {"model_priorities": {"model1": 5, "model2": 8}}
    priority_model = PriorityUpdateModel(**priority_data)
    assert priority_model.model_priorities["model1"] == 5
    
    # Test BulkOperationModel
    bulk_data = {"operation": "start", "models": ["model1", "model2"]}
    bulk_model = BulkOperationModel(**bulk_data)
    assert bulk_model.operation == "start"
    assert len(bulk_model.models) == 2
    
    # Test ConfigUpdateModel
    config_data = {"config_data": {"test": "value"}}
    config_model = ConfigUpdateModel(**config_data)
    assert config_model.config_data["test"] == "value"

if __name__ == "__main__":
    # Run tests individually if script is executed directly
    test_dashboard_imports()
    test_dashboard_endpoints_exist()
    test_audit_logger_functionality()
    test_config_notification_manager()
    test_dashboard_data_models()
    print("All basic integration tests passed!")
