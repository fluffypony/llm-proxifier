#!/usr/bin/env python3
"""
Simple test runner for dashboard functionality without external dependencies.
"""

import sys
import os
import tempfile
import asyncio
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_dashboard_imports():
    """Test that all dashboard modules can be imported."""
    print("Testing dashboard imports...")
    try:
        from dashboard import dashboard_router
        from audit_logger import audit_logger
        from config_notifications import config_notification_manager
        assert dashboard_router is not None
        assert audit_logger is not None
        assert config_notification_manager is not None
        print("✅ Dashboard imports successful")
        return True
    except Exception as e:
        print(f"❌ Failed to import dashboard modules: {e}")
        return False

def test_audit_logger_functionality():
    """Test basic audit logger functionality."""
    print("Testing audit logger...")
    try:
        from audit_logger import AuditLogger
        
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
            print("✅ Audit logger functionality successful")
            return True
        finally:
            # Clean up
            if os.path.exists(log_file):
                os.unlink(log_file)
    except Exception as e:
        print(f"❌ Audit logger test failed: {e}")
        return False

def test_config_notification_manager():
    """Test basic notification manager functionality."""
    print("Testing config notification manager...")
    try:
        from config_notifications import ConfigNotificationManager
        
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
        print("✅ Config notification manager successful")
        return True
    except Exception as e:
        print(f"❌ Config notification manager test failed: {e}")
        return False

def test_dashboard_data_models():
    """Test that Pydantic models are valid."""
    print("Testing dashboard data models...")
    try:
        from dashboard import PriorityUpdateModel, BulkOperationModel, ConfigUpdateModel
        
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
        
        print("✅ Dashboard data models successful")
        return True
    except Exception as e:
        print(f"❌ Dashboard data models test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Running dashboard integration tests...\n")
    
    tests = [
        test_dashboard_imports,
        test_audit_logger_functionality, 
        test_config_notification_manager,
        test_dashboard_data_models
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
        print()
    
    print(f"Test Summary: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed!")
        return True
    else:
        print("💥 Some tests failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
