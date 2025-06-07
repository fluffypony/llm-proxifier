"""Model lifecycle management for the LLM proxy server."""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
import subprocess
from dataclasses import dataclass

from src.config import ModelConfig
from src.queue_manager import QueueManager, ModelState
from src.utils import (
    format_llama_cpp_command,
    wait_for_server,
    is_port_listening,
    get_process_memory_usage,
    get_process_cpu_usage,
    graceful_shutdown
)


@dataclass
class ModelInstance:
    """Represents a running model instance."""
    config: ModelConfig
    process: Optional[subprocess.Popen] = None
    last_accessed: Optional[datetime] = None
    is_ready: bool = False
    start_time: Optional[datetime] = None
    request_count: int = 0
    
    @property
    def health_check_url(self) -> str:
        """Get the health check URL for this model."""
        return f"http://127.0.0.1:{self.config.port}"
    
    @property
    def api_url(self) -> str:
        """Get the API base URL for this model."""
        return f"http://127.0.0.1:{self.config.port}"
    
    async def start(self, queue_manager: QueueManager = None) -> bool:
        """Start the model server process."""
        if queue_manager:
            queue_manager.set_model_state(self.config.name, ModelState.STARTING)
            
        if self.process and self.process.poll() is None:
            logging.warning(f"Model {self.config.name} is already running")
            if queue_manager:
                queue_manager.set_model_state(self.config.name, ModelState.RUNNING)
            return True
        
        if is_port_listening(self.config.port):
            logging.error(f"Port {self.config.port} is already in use")
            if queue_manager:
                queue_manager.set_model_state(self.config.name, ModelState.STOPPED)
            return False
        
        try:
            cmd = format_llama_cpp_command(self.config)
            logging.info(f"Starting model {self.config.name} with command: {' '.join(cmd)}")
            
            # Start the process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.start_time = datetime.now()
            self.is_ready = False
            
            # Wait for the server to be ready
            server_ready = await wait_for_server(self.health_check_url, timeout=60)
            
            if server_ready and self.process.poll() is None:
                self.is_ready = True
                self.update_access_time()
                if queue_manager:
                    queue_manager.set_model_state(self.config.name, ModelState.RUNNING)
                logging.info(f"Model {self.config.name} started successfully on port {self.config.port}")
                return True
            else:
                logging.error(f"Model {self.config.name} failed to start or health check failed")
                if queue_manager:
                    queue_manager.set_model_state(self.config.name, ModelState.STOPPED)
                await self.stop()
                return False
                
        except Exception as e:
            logging.error(f"Error starting model {self.config.name}: {e}")
            if queue_manager:
                queue_manager.set_model_state(self.config.name, ModelState.STOPPED)
            await self.stop()
            return False
    
    async def stop(self, queue_manager: QueueManager = None) -> bool:
        """Stop the model server process."""
        if queue_manager:
            queue_manager.set_model_state(self.config.name, ModelState.STOPPING)
            
        if not self.process:
            if queue_manager:
                queue_manager.set_model_state(self.config.name, ModelState.STOPPED)
            return True
        
        try:
            logging.info(f"Stopping model {self.config.name}")
            
            # Try graceful shutdown first
            success = await graceful_shutdown(self.process, timeout=5)
            
            if success:
                logging.info(f"Model {self.config.name} stopped gracefully")
            else:
                logging.warning(f"Model {self.config.name} was force killed")
            
            self.process = None
            self.is_ready = False
            if queue_manager:
                queue_manager.set_model_state(self.config.name, ModelState.STOPPED)
            return True
            
        except Exception as e:
            logging.error(f"Error stopping model {self.config.name}: {e}")
            if queue_manager:
                queue_manager.set_model_state(self.config.name, ModelState.STOPPED)
            return False
    
    async def health_check(self) -> bool:
        """Check if the model server is healthy."""
        if not self.process or self.process.poll() is not None:
            self.is_ready = False
            return False
        
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.health_check_url}/health", timeout=5.0)
                healthy = response.status_code == 200
                self.is_ready = healthy
                return healthy
        except Exception:
            self.is_ready = False
            return False
    
    def update_access_time(self):
        """Update the last accessed timestamp."""
        self.last_accessed = datetime.now()
        self.request_count += 1
    
    def get_memory_usage(self) -> Optional[float]:
        """Get memory usage of the model process in MB."""
        if not self.process:
            return None
        return get_process_memory_usage(self.process.pid)
    
    def get_cpu_usage(self) -> Optional[float]:
        """Get CPU usage of the model process."""
        if not self.process:
            return None
        return get_process_cpu_usage(self.process.pid)
    
    def get_uptime(self) -> Optional[timedelta]:
        """Get uptime of the model instance."""
        if not self.start_time:
            return None
        return datetime.now() - self.start_time


class ModelManager:
    """Manages multiple model instances with lifecycle control."""
    
    def __init__(self, timeout_minutes: int = 2, max_concurrent: int = 4, queue_manager: QueueManager = None):
        self.models: Dict[str, ModelInstance] = {}
        self.configs: Dict[str, ModelConfig] = {}
        self.timeout_minutes = timeout_minutes
        self.max_concurrent = max_concurrent
        self.queue_manager = queue_manager
        self.cleanup_task: Optional[asyncio.Task] = None
        self.lock = asyncio.Lock()
        self.logger = logging.getLogger(__name__)
    
    def load_configs(self, configs: Dict[str, ModelConfig]):
        """Load model configurations."""
        self.configs = configs
        self.logger.info(f"Loaded configurations for {len(configs)} models")
    
    async def get_or_start_model(self, model_name: str) -> Optional[ModelInstance]:
        """Get a running model instance, starting it if necessary."""
        async with self.lock:
            # Check if model is configured
            if model_name not in self.configs:
                self.logger.error(f"Model {model_name} is not configured")
                return None
            
            # Check if model is already running
            if model_name in self.models:
                instance = self.models[model_name]
                if instance.is_ready and await instance.health_check():
                    instance.update_access_time()
                    return instance
                else:
                    # Remove unhealthy instance
                    await instance.stop()
                    del self.models[model_name]
            
            # Check concurrent limit
            active_count = len([m for m in self.models.values() if m.is_ready])
            if active_count >= self.max_concurrent:
                self.logger.error(f"Maximum concurrent models ({self.max_concurrent}) reached")
                return None
            
            # Start new instance
            config = self.configs[model_name]
            instance = ModelInstance(config=config)
            
            if await instance.start(self.queue_manager):
                self.models[model_name] = instance
                return instance
            else:
                return None
    
    async def stop_model(self, model_name: str) -> bool:
        """Stop a specific model."""
        async with self.lock:
            if model_name not in self.models:
                return True
            
            instance = self.models[model_name]
            success = await instance.stop(self.queue_manager)
            del self.models[model_name]
            return success
    
    async def cleanup_inactive_models(self):
        """Background task to cleanup inactive models."""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                async with self.lock:
                    current_time = datetime.now()
                    timeout_delta = timedelta(minutes=self.timeout_minutes)
                    
                    models_to_stop = []
                    for name, instance in self.models.items():
                        # Skip preloaded models
                        if instance.config.preload:
                            continue
                            
                        if (instance.last_accessed and 
                            current_time - instance.last_accessed > timeout_delta):
                            models_to_stop.append(name)
                    
                    for name in models_to_stop:
                        self.logger.info(f"Stopping inactive model: {name}")
                        await self.models[name].stop(self.queue_manager)
                        del self.models[name]
                        
            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}")
    
    def get_active_models(self) -> List[str]:
        """Get list of currently active model names."""
        return [name for name, instance in self.models.items() if instance.is_ready]
    
    def get_model_status(self, model_name: str) -> Dict:
        """Get detailed status of a model."""
        if model_name not in self.models:
            config = self.configs.get(model_name, {})
            return {
                "status": "stopped",
                "priority": getattr(config, 'priority', 5),
                "resource_group": getattr(config, 'resource_group', 'default'),
                "preload": getattr(config, 'preload', False),
                "auto_start": getattr(config, 'auto_start', False)
            }
        
        instance = self.models[model_name]
        return {
            "status": "running" if instance.is_ready else "starting",
            "port": instance.config.port,
            "priority": instance.config.priority,
            "resource_group": instance.config.resource_group,
            "preload": instance.config.preload,
            "auto_start": instance.config.auto_start,
            "last_accessed": instance.last_accessed.isoformat() if instance.last_accessed else None,
            "uptime": str(instance.get_uptime()) if instance.get_uptime() else None,
            "memory_usage_mb": instance.get_memory_usage(),
            "cpu_usage_percent": instance.get_cpu_usage(),
            "request_count": instance.request_count
        }
    
    def get_all_model_status(self) -> Dict[str, Dict]:
        """Get status of all configured models."""
        status = {}
        for name in self.configs.keys():
            status[name] = self.get_model_status(name)
        return status
    
    async def start_cleanup_task(self):
        """Start the background cleanup task."""
        if self.cleanup_task:
            return
        
        self.cleanup_task = asyncio.create_task(self.cleanup_inactive_models())
        self.logger.info("Started model cleanup task")
    
    async def stop_cleanup_task(self):
        """Stop the background cleanup task."""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            self.cleanup_task = None
            self.logger.info("Stopped model cleanup task")
    
    async def start_all_auto_models(self):
        """Start all models with auto_start=True, sorted by priority."""
        auto_start_configs = [
            config for config in self.configs.values() 
            if getattr(config, 'auto_start', False)
        ]
        
        # Sort by priority (higher priority first)
        auto_start_configs.sort(key=lambda x: getattr(x, 'priority', 5), reverse=True)
        
        self.logger.info(f"Starting {len(auto_start_configs)} auto-start models")
        
        for config in auto_start_configs:
            try:
                self.logger.info(f"Auto-starting model {config.name} (priority {config.priority})")
                instance = await self.get_or_start_model(config.name)
                if instance:
                    self.logger.info(f"Auto-started model {config.name} successfully")
                else:
                    self.logger.error(f"Failed to auto-start model {config.name}")
            except Exception as e:
                self.logger.error(f"Error auto-starting model {config.name}: {e}")
    
    async def preload_models(self):
        """Ensure all models with preload=True are running."""
        preload_configs = [
            config for config in self.configs.values()
            if getattr(config, 'preload', False)
        ]
        
        self.logger.info(f"Preloading {len(preload_configs)} models")
        
        for config in preload_configs:
            try:
                if config.name not in self.models or not self.models[config.name].is_ready:
                    self.logger.info(f"Preloading model {config.name}")
                    instance = await self.get_or_start_model(config.name)
                    if instance:
                        self.logger.info(f"Preloaded model {config.name} successfully")
                    else:
                        self.logger.error(f"Failed to preload model {config.name}")
            except Exception as e:
                self.logger.error(f"Error preloading model {config.name}: {e}")
    
    def get_models_by_priority(self) -> List[ModelConfig]:
        """Return models sorted by priority (higher priority first)."""
        configs = list(self.configs.values())
        configs.sort(key=lambda x: getattr(x, 'priority', 5), reverse=True)
        return configs
    
    def get_models_by_resource_group(self, resource_group: str = None) -> List[ModelConfig]:
        """Get models by resource group."""
        if resource_group is None:
            # Return all models grouped by resource group
            groups = {}
            for config in self.configs.values():
                group = getattr(config, 'resource_group', 'default')
                if group not in groups:
                    groups[group] = []
                groups[group].append(config)
            return groups
        else:
            # Return models in specific group
            return [
                config for config in self.configs.values()
                if getattr(config, 'resource_group', 'default') == resource_group
            ]
    
    async def stop_resource_group(self, resource_group: str) -> Dict[str, bool]:
        """Stop all models in a resource group."""
        models_in_group = self.get_models_by_resource_group(resource_group)
        results = {}
        
        for config in models_in_group:
            # Skip preloaded models with warning
            if getattr(config, 'preload', False):
                self.logger.warning(f"Skipping preloaded model {config.name} in group {resource_group}")
                results[config.name] = False
                continue
                
            try:
                success = await self.stop_model(config.name)
                results[config.name] = success
                self.logger.info(f"Stopped model {config.name} in group {resource_group}")
            except Exception as e:
                self.logger.error(f"Error stopping model {config.name}: {e}")
                results[config.name] = False
        
        return results
    
    async def start_resource_group(self, resource_group: str) -> Dict[str, bool]:
        """Start all models in a resource group, respecting priority."""
        models_in_group = self.get_models_by_resource_group(resource_group)
        # Sort by priority
        models_in_group.sort(key=lambda x: getattr(x, 'priority', 5), reverse=True)
        
        results = {}
        for config in models_in_group:
            try:
                instance = await self.get_or_start_model(config.name)
                results[config.name] = instance is not None
                if instance:
                    self.logger.info(f"Started model {config.name} in group {resource_group}")
                else:
                    self.logger.error(f"Failed to start model {config.name} in group {resource_group}")
            except Exception as e:
                self.logger.error(f"Error starting model {config.name}: {e}")
                results[config.name] = False
        
        return results
    
    async def stop_all_models(self) -> Dict[str, bool]:
        """Stop all running models except preloaded ones."""
        results = {}
        models_to_stop = list(self.models.keys())
        
        for model_name in models_to_stop:
            instance = self.models[model_name]
            # Skip preloaded models
            if getattr(instance.config, 'preload', False):
                self.logger.warning(f"Skipping preloaded model {model_name}")
                results[model_name] = False
                continue
                
            try:
                success = await self.stop_model(model_name)
                results[model_name] = success
            except Exception as e:
                self.logger.error(f"Error stopping model {model_name}: {e}")
                results[model_name] = False
        
        return results
    
    async def start_all_models(self) -> Dict[str, bool]:
        """Start all configured models."""
        results = {}
        models_by_priority = self.get_models_by_priority()
        
        for config in models_by_priority:
            try:
                instance = await self.get_or_start_model(config.name)
                results[config.name] = instance is not None
            except Exception as e:
                self.logger.error(f"Error starting model {config.name}: {e}")
                results[config.name] = False
        
        return results
    
    async def restart_all_models(self) -> Dict[str, bool]:
        """Restart all currently running models."""
        results = {}
        running_models = list(self.models.keys())
        
        for model_name in running_models:
            try:
                # Stop first
                await self.stop_model(model_name)
                # Start again
                instance = await self.get_or_start_model(model_name)
                results[model_name] = instance is not None
            except Exception as e:
                self.logger.error(f"Error restarting model {model_name}: {e}")
                results[model_name] = False
        
        return results
    
    def get_resource_group_status(self, resource_group: str = None) -> Dict:
        """Get status summary for resource groups."""
        if resource_group:
            models = self.get_models_by_resource_group(resource_group)
            running = sum(1 for m in models if m.name in self.models and self.models[m.name].is_ready)
            return {
                "resource_group": resource_group,
                "total_models": len(models),
                "running_models": running,
                "models": [m.name for m in models]
            }
        else:
            # Return all groups
            all_groups = self.get_models_by_resource_group()
            status = {}
            for group_name, models in all_groups.items():
                running = sum(1 for m in models if m.name in self.models and self.models[m.name].is_ready)
                status[group_name] = {
                    "total_models": len(models),
                    "running_models": running,
                    "models": [m.name for m in models]
                }
            return status
    
    async def reload_model(self, model_name: str, new_config: Optional[ModelConfig] = None) -> Dict[str, Any]:
        """Hot reload a specific model with optional new configuration."""
        async with self.lock:
            if model_name not in self.configs and not new_config:
                return {"success": False, "error": f"Model {model_name} not configured"}
            
            # Set model state to reloading
            if self.queue_manager:
                self.queue_manager.set_model_state(model_name, ModelState.RELOADING)
                # Clear any queued requests for this model
                self.queue_manager.clear_model_queue(model_name)
            
            # Use new config if provided, otherwise use current config
            config = new_config or self.configs[model_name]
            was_running = model_name in self.models and self.models[model_name].is_ready
            
            # Stop existing model if running
            if model_name in self.models:
                await self.models[model_name].stop(self.queue_manager)
                del self.models[model_name]
            
            # Update config if new one provided
            if new_config:
                self.configs[model_name] = new_config
            
            # Start with new configuration if it was running before
            if was_running:
                instance = ModelInstance(config=config)
                if await instance.start(self.queue_manager):
                    self.models[model_name] = instance
                    return {
                        "success": True,
                        "message": f"Model {model_name} reloaded successfully",
                        "status": "running"
                    }
                else:
                    if self.queue_manager:
                        self.queue_manager.set_model_state(model_name, ModelState.STOPPED)
                    return {
                        "success": False,
                        "error": f"Failed to start model {model_name} after reload"
                    }
            else:
                if self.queue_manager:
                    self.queue_manager.set_model_state(model_name, ModelState.STOPPED)
                return {
                    "success": True,
                    "message": f"Model {model_name} configuration updated (not running)",
                    "status": "stopped"
                }
    
    def reload_model_config(self, new_configs: Dict[str, ModelConfig]) -> Dict[str, Any]:
        """Reload model configurations and identify changes."""
        old_configs = dict(self.configs)
        self.configs = new_configs
        
        # Compare changes
        added = set(new_configs.keys()) - set(old_configs.keys())
        removed = set(old_configs.keys()) - set(new_configs.keys())
        modified = set()
        
        for name in old_configs.keys() & new_configs.keys():
            if old_configs[name].__dict__ != new_configs[name].__dict__:
                modified.add(name)
        
        return {
            "added": list(added),
            "removed": list(removed),
            "modified": list(modified),
            "total_models": len(new_configs)
        }

    async def shutdown_all(self):
        """Gracefully shutdown all models and cleanup tasks."""
        self.logger.info("Shutting down all models")
        
        await self.stop_cleanup_task()
        
        async with self.lock:
            tasks = []
            for instance in self.models.values():
                tasks.append(instance.stop(self.queue_manager))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            self.models.clear()
        
        self.logger.info("All models shut down")
