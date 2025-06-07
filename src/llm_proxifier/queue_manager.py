"""Request queuing system for model transitions."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


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

        # Enhanced metrics tracking
        self.queue_metrics: Dict[str, Dict[str, Any]] = {}
        self.historical_metrics: Dict[str, List[Dict[str, Any]]] = {}
        self.metrics_lock = asyncio.Lock()
        self.max_history_entries = 100  # Keep last 100 entries per model

    def create_queue_for_model(self, model_name: str, max_size: int = 100):
        """Create a request queue for a model."""
        if model_name not in self.queues:
            self.queues[model_name] = RequestQueue(model_name, max_size)
            self.model_states[model_name] = ModelState.STOPPED
            # Initialize metrics for this model
            self.queue_metrics[model_name] = {
                "total_requests": 0,
                "total_wait_time": 0,
                "total_processing_time": 0,
                "peak_depth": 0,
                "requests_per_minute": 0,
                "last_activity": None,
                "avg_wait_time": 0,
                "avg_processing_time": 0,
                "successful_requests": 0,
                "failed_requests": 0
            }
            self.historical_metrics[model_name] = []
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

    async def track_request_metrics(self, model_name: str, wait_time: float, processing_time: float, success: bool = True):
        """Track detailed metrics for a request."""
        async with self.metrics_lock:
            if model_name not in self.queue_metrics:
                self.create_queue_for_model(model_name)

            metrics = self.queue_metrics[model_name]
            metrics["total_requests"] += 1
            metrics["total_wait_time"] += wait_time
            metrics["total_processing_time"] += processing_time
            metrics["last_activity"] = datetime.now().isoformat()

            if success:
                metrics["successful_requests"] += 1
            else:
                metrics["failed_requests"] += 1

            # Update averages
            if metrics["total_requests"] > 0:
                metrics["avg_wait_time"] = metrics["total_wait_time"] / metrics["total_requests"]
                metrics["avg_processing_time"] = metrics["total_processing_time"] / metrics["total_requests"]

            # Update peak depth
            current_depth = self.get_queue_depth(model_name)
            if current_depth > metrics["peak_depth"]:
                metrics["peak_depth"] = current_depth

            # Update requests per minute (calculate for last 60 seconds)
            metrics["requests_per_minute"] = self.calculate_requests_per_minute(model_name)

            # Add to historical metrics
            self.add_historical_metric(model_name, {
                "timestamp": datetime.now().isoformat(),
                "queue_depth": current_depth,
                "wait_time": wait_time,
                "processing_time": processing_time,
                "success": success,
                "avg_wait_time": metrics["avg_wait_time"],
                "requests_per_minute": metrics["requests_per_minute"]
            })

    def add_historical_metric(self, model_name: str, metric_entry: Dict[str, Any]):
        """Add a metric entry to historical data."""
        if model_name not in self.historical_metrics:
            self.historical_metrics[model_name] = []

        self.historical_metrics[model_name].append(metric_entry)

        # Keep only the last N entries
        if len(self.historical_metrics[model_name]) > self.max_history_entries:
            self.historical_metrics[model_name] = self.historical_metrics[model_name][-self.max_history_entries:]

    def calculate_requests_per_minute(self, model_name: str) -> float:
        """Calculate requests per minute for the last 5 minutes."""
        if model_name not in self.historical_metrics:
            return 0.0

        now = datetime.now()
        five_minutes_ago = now - timedelta(minutes=5)

        recent_requests = 0
        for entry in self.historical_metrics[model_name]:
            try:
                entry_time = datetime.fromisoformat(entry["timestamp"])
                if entry_time >= five_minutes_ago:
                    recent_requests += 1
            except (ValueError, KeyError):
                continue

        # Convert to requests per minute
        return recent_requests / 5.0

    def get_queue_depth(self, model_name: str) -> int:
        """Get current queue depth for a model."""
        if model_name in self.queues:
            return self.queues[model_name].queue.qsize()
        return 0

    def get_queue_stats(self, model_name: str = None) -> Dict[str, Any]:
        """Get comprehensive queue statistics."""
        if model_name:
            if model_name in self.queues:
                stats = self.queues[model_name].get_queue_stats()
                stats["state"] = self.get_model_state(model_name).value

                # Add enhanced metrics
                if model_name in self.queue_metrics:
                    metrics = self.queue_metrics[model_name]
                    stats.update({
                        "depth": self.get_queue_depth(model_name),
                        "total_processed": metrics["total_requests"],
                        "avg_wait_time": metrics["avg_wait_time"],
                        "avg_processing_time": metrics["avg_processing_time"],
                        "peak_depth": metrics["peak_depth"],
                        "requests_per_minute": metrics["requests_per_minute"],
                        "last_activity": metrics["last_activity"],
                        "successful_requests": metrics["successful_requests"],
                        "failed_requests": metrics["failed_requests"],
                        "success_rate": (metrics["successful_requests"] / max(metrics["total_requests"], 1)) * 100
                    })
                return stats
            else:
                return {
                    "model_name": model_name,
                    "state": self.get_model_state(model_name).value,
                    "queue_size": 0,
                    "depth": 0,
                    "pending_requests": 0,
                    "total_processed": 0,
                    "avg_wait_time": 0,
                    "avg_processing_time": 0,
                    "peak_depth": 0,
                    "requests_per_minute": 0,
                    "last_activity": None,
                    "successful_requests": 0,
                    "failed_requests": 0,
                    "success_rate": 0
                }
        else:
            # Return stats for all models
            all_stats = {}
            for name in set(self.queues.keys()) | set(self.model_states.keys()) | set(self.queue_metrics.keys()):
                all_stats[name] = self.get_queue_stats(name)
            return all_stats

    def get_historical_metrics(self, model_name: str = None, limit: int = None) -> Dict[str, Any]:
        """Get historical metrics data for charts and analysis."""
        if model_name:
            if model_name in self.historical_metrics:
                data = self.historical_metrics[model_name]
                if limit:
                    data = data[-limit:]
                return {model_name: data}
            else:
                return {model_name: []}
        else:
            # Return historical data for all models
            result = {}
            for name, data in self.historical_metrics.items():
                if limit:
                    result[name] = data[-limit:]
                else:
                    result[name] = data
            return result

    def reset_metrics(self, model_name: str = None):
        """Reset metrics for a model or all models."""
        if model_name:
            if model_name in self.queue_metrics:
                self.queue_metrics[model_name] = {
                    "total_requests": 0,
                    "total_wait_time": 0,
                    "total_processing_time": 0,
                    "peak_depth": 0,
                    "requests_per_minute": 0,
                    "last_activity": None,
                    "avg_wait_time": 0,
                    "avg_processing_time": 0,
                    "successful_requests": 0,
                    "failed_requests": 0
                }
            if model_name in self.historical_metrics:
                self.historical_metrics[model_name] = []
        else:
            # Reset all metrics
            for name in self.queue_metrics.keys():
                self.reset_metrics(name)

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
