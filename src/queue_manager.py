"""Request queuing system for model transitions."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class ModelState(Enum):
    """Model state enumeration."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    RELOADING = "reloading"


@dataclass
class QueuedRequest:
    """Represents a queued request."""
    request_id: str
    client_id: str
    endpoint: str
    timestamp: datetime
    timeout: int = 30  # seconds
    
    def is_expired(self) -> bool:
        """Check if request has expired."""
        return datetime.now() - self.timestamp > timedelta(seconds=self.timeout)


class RequestQueue:
    """Manages request queuing for a single model."""
    
    def __init__(self, model_name: str, max_size: int = 100):
        self.model_name = model_name
        self.max_size = max_size
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self.pending_requests: Dict[str, QueuedRequest] = {}
        self.logger = logging.getLogger(f"{__name__}.{model_name}")
        
    async def enqueue_request(self, request_id: str, client_id: str, endpoint: str) -> bool:
        """Add a request to the queue."""
        if self.queue.full():
            self.logger.warning(f"Queue full for model {self.model_name}")
            return False
        
        queued_request = QueuedRequest(
            request_id=request_id,
            client_id=client_id,
            endpoint=endpoint,
            timestamp=datetime.now()
        )
        
        try:
            await self.queue.put(queued_request)
            self.pending_requests[request_id] = queued_request
            self.logger.info(f"Queued request {request_id} for model {self.model_name}")
            return True
        except asyncio.QueueFull:
            return False
    
    async def dequeue_request(self) -> Optional[QueuedRequest]:
        """Get the next request from the queue."""
        try:
            request = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            if request.request_id in self.pending_requests:
                del self.pending_requests[request.request_id]
            return request
        except asyncio.TimeoutError:
            return None
    
    def remove_request(self, request_id: str):
        """Remove a specific request from pending."""
        if request_id in self.pending_requests:
            del self.pending_requests[request_id]
    
    def cleanup_expired_requests(self):
        """Remove expired requests from pending."""
        expired_ids = [
            req_id for req_id, req in self.pending_requests.items()
            if req.is_expired()
        ]
        
        for req_id in expired_ids:
            del self.pending_requests[req_id]
            self.logger.info(f"Removed expired request {req_id}")
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            "model_name": self.model_name,
            "queue_size": self.queue.qsize(),
            "max_size": self.max_size,
            "pending_requests": len(self.pending_requests),
            "is_full": self.queue.full()
        }


class QueueManager:
    """Manages request queues for all models."""
    
    def __init__(self):
        self.queues: Dict[str, RequestQueue] = {}
        self.model_states: Dict[str, ModelState] = {}
        self.logger = logging.getLogger(__name__)
        self._cleanup_task: Optional[asyncio.Task] = None
    
    def create_queue_for_model(self, model_name: str, max_size: int = 100):
        """Create a request queue for a model."""
        if model_name not in self.queues:
            self.queues[model_name] = RequestQueue(model_name, max_size)
            self.model_states[model_name] = ModelState.STOPPED
            self.logger.info(f"Created queue for model {model_name}")
    
    def set_model_state(self, model_name: str, state: ModelState):
        """Update model state."""
        self.model_states[model_name] = state
        self.logger.info(f"Model {model_name} state changed to {state.value}")
        
        # Process queued requests if model is now running
        if state == ModelState.RUNNING and model_name in self.queues:
            asyncio.create_task(self._process_queue(model_name))
    
    def get_model_state(self, model_name: str) -> ModelState:
        """Get model state."""
        return self.model_states.get(model_name, ModelState.STOPPED)
    
    def should_queue_request(self, model_name: str) -> bool:
        """Check if requests should be queued for this model."""
        state = self.get_model_state(model_name)
        return state in [ModelState.STARTING, ModelState.RELOADING]
    
    async def queue_request(self, model_name: str, request_id: str, client_id: str, endpoint: str) -> bool:
        """Queue a request for a model."""
        self.create_queue_for_model(model_name)
        return await self.queues[model_name].enqueue_request(request_id, client_id, endpoint)
    
    async def _process_queue(self, model_name: str):
        """Process queued requests for a model."""
        if model_name not in self.queues:
            return
        
        queue = self.queues[model_name]
        
        while self.get_model_state(model_name) == ModelState.RUNNING:
            request = await queue.dequeue_request()
            if not request:
                break
            
            if request.is_expired():
                self.logger.warning(f"Expired request {request.request_id} for model {model_name}")
                continue
            
            self.logger.info(f"Processing queued request {request.request_id} for model {model_name}")
            # Request will be processed by the normal flow since model is now running
    
    def get_queue_stats(self, model_name: str = None) -> Dict[str, Any]:
        """Get queue statistics."""
        if model_name:
            if model_name in self.queues:
                stats = self.queues[model_name].get_queue_stats()
                stats["state"] = self.get_model_state(model_name).value
                return stats
            else:
                return {
                    "model_name": model_name,
                    "state": self.get_model_state(model_name).value,
                    "queue_size": 0,
                    "pending_requests": 0
                }
        else:
            # Return stats for all models
            all_stats = {}
            for name in set(self.queues.keys()) | set(self.model_states.keys()):
                all_stats[name] = self.get_queue_stats(name)
            return all_stats
    
    async def start_cleanup_task(self):
        """Start the cleanup task."""
        if self._cleanup_task:
            return
        
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_requests())
        self.logger.info("Started queue cleanup task")
    
    async def stop_cleanup_task(self):
        """Stop the cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            self.logger.info("Stopped queue cleanup task")
    
    async def _cleanup_expired_requests(self):
        """Background task to cleanup expired requests."""
        while True:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                for queue in self.queues.values():
                    queue.cleanup_expired_requests()
                    
            except Exception as e:
                self.logger.error(f"Error in queue cleanup task: {e}")
    
    def clear_model_queue(self, model_name: str):
        """Clear all queued requests for a model."""
        if model_name in self.queues:
            queue = self.queues[model_name]
            # Clear the queue
            while not queue.queue.empty():
                try:
                    queue.queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            
            # Clear pending requests
            queue.pending_requests.clear()
            self.logger.info(f"Cleared queue for model {model_name}")
    
    async def shutdown(self):
        """Shutdown the queue manager."""
        await self.stop_cleanup_task()
        
        # Clear all queues
        for model_name in list(self.queues.keys()):
            self.clear_model_queue(model_name)
        
        self.queues.clear()
        self.model_states.clear()
        self.logger.info("Queue manager shutdown complete")
