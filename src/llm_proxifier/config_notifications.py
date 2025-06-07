"""
Configuration change notification system for LLM Proxifier.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional


class ConfigNotificationManager:
    def __init__(self, websocket_manager=None):
        """Initialize notification manager."""
        self.websocket_manager = websocket_manager
        self.notification_queue = asyncio.Queue()
        self.subscribers = set()

    def set_websocket_manager(self, websocket_manager):
        """Set the WebSocket manager for real-time notifications."""
        self.websocket_manager = websocket_manager

    async def notify_config_change(self, config_type: str, change_type: str, details: Dict[str, Any]):
        """Notify dashboard of configuration changes."""
        notification = {
            "type": "config_change",
            "config_type": config_type,
            "change_type": change_type,  # "updated", "restored", "backed_up"
            "details": details,
            "timestamp": datetime.now().isoformat()
        }

        # Add to notification queue
        await self.notification_queue.put(notification)

        # Broadcast via WebSocket if available
        if self.websocket_manager:
            try:
                await self.websocket_manager.broadcast_json(notification)
            except Exception as e:
                print(f"Error broadcasting config change notification: {e}")

    async def notify_model_reload(self, model_name: str, status: str, details: Optional[Dict[str, Any]] = None):
        """Notify dashboard of model reload status."""
        notification = {
            "type": "model_reload",
            "model_name": model_name,
            "status": status,  # "starting", "completed", "failed"
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }

        # Add to notification queue
        await self.notification_queue.put(notification)

        # Broadcast via WebSocket if available
        if self.websocket_manager:
            try:
                await self.websocket_manager.broadcast_json(notification)
            except Exception as e:
                print(f"Error broadcasting model reload notification: {e}")

    async def notify_queue_alert(self, model_name: str, alert_type: str, metrics: Dict[str, Any]):
        """Notify dashboard of queue alerts."""
        notification = {
            "type": "queue_alert",
            "model_name": model_name,
            "alert_type": alert_type,  # "high_depth", "high_wait_time", "error"
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }

        # Add to notification queue
        await self.notification_queue.put(notification)

        # Broadcast via WebSocket if available
        if self.websocket_manager:
            try:
                await self.websocket_manager.broadcast_json(notification)
            except Exception as e:
                print(f"Error broadcasting queue alert notification: {e}")

    async def notify_system_event(self, event_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Notify dashboard of system events."""
        notification = {
            "type": "system_event",
            "event_type": event_type,  # "startup", "shutdown", "error", "warning"
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }

        # Add to notification queue
        await self.notification_queue.put(notification)

        # Broadcast via WebSocket if available
        if self.websocket_manager:
            try:
                await self.websocket_manager.broadcast_json(notification)
            except Exception as e:
                print(f"Error broadcasting system event notification: {e}")

    async def get_recent_notifications(self, limit: int = 50) -> list:
        """Get recent notifications from the queue."""
        notifications = []
        temp_queue = []

        # Extract up to 'limit' notifications
        for _ in range(min(limit, self.notification_queue.qsize())):
            try:
                notification = self.notification_queue.get_nowait()
                notifications.append(notification)
                temp_queue.append(notification)
            except asyncio.QueueEmpty:
                break

        # Put them back in the queue
        for notification in temp_queue:
            await self.notification_queue.put(notification)

        return notifications

    def subscribe(self, subscriber_id: str):
        """Subscribe to notifications."""
        self.subscribers.add(subscriber_id)

    def unsubscribe(self, subscriber_id: str):
        """Unsubscribe from notifications."""
        self.subscribers.discard(subscriber_id)

# Global notification manager instance
config_notification_manager = ConfigNotificationManager()
