"""Command line interface for LLM Proxifier."""

import argparse
import asyncio
import logging
import os
import sys
import webbrowser
from typing import Optional

import httpx

from llm_proxifier._version import get_version, get_build_info
from llm_proxifier.config import ConfigManager


def setup_logging(level: str = "INFO"):
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


async def check_server_status(host: str, port: int) -> dict:
    """Check if the server is running and get status."""
    url = f"http://{host}:{port}/health"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)
            if response.status_code == 200:
                return {
                    "running": True,
                    "status": response.json()
                }
            else:
                return {
                    "running": False,
                    "error": f"Server returned status {response.status_code}"
                }
    except httpx.ConnectError:
        return {
            "running": False,
            "error": "Connection refused"
        }
    except Exception as e:
        return {
            "running": False,
            "error": str(e)
        }


def cmd_start(args):
    """Start the LLM Proxifier server."""
    import uvicorn
    from llm_proxifier.main import app
    
    setup_logging(args.log_level)
    
    # Load configuration
    config_manager = ConfigManager(
        config_path=args.config,
        auth_config_path=args.auth_config
    )
    proxy_config = config_manager.proxy_config
    
    # Override with command line arguments
    host = args.host or proxy_config.host
    port = args.port or proxy_config.port
    
    # Set environment variables for the application
    if args.dashboard_port:
        os.environ["DASHBOARD_PORT"] = str(args.dashboard_port)
    if args.disable_auth:
        os.environ["AUTH_ENABLED"] = "false"
    if args.disable_dashboard:
        os.environ["DASHBOARD_ENABLED"] = "false"
    
    print(f"Starting LLM Proxifier server on {host}:{port}")
    print(f"Dashboard URL: http://{host}:{args.dashboard_port or proxy_config.dashboard_port}")
    print(f"Config: {args.config}")
    print(f"Auth config: {args.auth_config}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=args.log_level.lower(),
        access_log=True
    )


async def cmd_status(args):
    """Check server status."""
    config_manager = ConfigManager(
        config_path=args.config,
        auth_config_path=args.auth_config
    )
    proxy_config = config_manager.proxy_config
    
    host = args.host or proxy_config.host
    port = args.port or proxy_config.port
    
    print(f"Checking server status at {host}:{port}...")
    
    result = await check_server_status(host, port)
    
    if result["running"]:
        print("✓ Server is running")
        status = result["status"]
        print(f"  Uptime: {status.get('uptime', 'unknown')}")
        print(f"  Models: {len(status.get('models', {}))}")
        
        # Show model details
        models = status.get("models", {})
        if models:
            print("\n  Active models:")
            for name, model_status in models.items():
                state = model_status.get("status", "unknown")
                port = model_status.get("port", "unknown")
                print(f"    {name}: {state} (port {port})")
        else:
            print("  No models currently active")
            
    else:
        print("✗ Server is not running")
        print(f"  Error: {result['error']}")
        sys.exit(1)


async def cmd_models(args):
    """List available models."""
    config_manager = ConfigManager(
        config_path=args.config,
        auth_config_path=args.auth_config
    )
    proxy_config = config_manager.proxy_config
    
    host = args.host or proxy_config.host
    port = args.port or proxy_config.port
    
    # First check if server is running
    result = await check_server_status(host, port)
    
    if result["running"]:
        # Get models from running server
        url = f"http://{host}:{port}/v1/models"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("data", [])
                    
                    print(f"Available models ({len(models)}):")
                    for model in models:
                        print(f"  {model['id']}")
                        
                else:
                    print(f"Error getting models: {response.status_code}")
                    sys.exit(1)
        except Exception as e:
            print(f"Error connecting to server: {e}")
            sys.exit(1)
    else:
        # Get models from configuration file
        try:
            model_configs = config_manager.load_model_configs()
            print(f"Configured models ({len(model_configs)}):")
            for name, config in model_configs.items():
                print(f"  {name} (port {config.port}, priority {config.priority})")
                if config.auto_start:
                    print(f"    - Auto-start: enabled")
                if config.preload:
                    print(f"    - Preload: enabled")
                if config.resource_group != "default":
                    print(f"    - Resource group: {config.resource_group}")
        except Exception as e:
            print(f"Error loading model configurations: {e}")
            sys.exit(1)


def cmd_dashboard(args):
    """Open the dashboard in browser."""
    config_manager = ConfigManager(
        config_path=args.config,
        auth_config_path=args.auth_config
    )
    proxy_config = config_manager.proxy_config
    
    host = args.host or proxy_config.host
    dashboard_port = args.dashboard_port or proxy_config.dashboard_port
    
    # Replace 0.0.0.0 with localhost for browser
    if host == "0.0.0.0":
        host = "localhost"
    
    url = f"http://{host}:{dashboard_port}"
    print(f"Opening dashboard at {url}")
    
    try:
        webbrowser.open(url)
        print("Dashboard opened in default browser")
    except Exception as e:
        print(f"Could not open browser: {e}")
        print(f"Please open {url} manually")


def cmd_config(args):
    """Configuration management commands."""
    config_manager = ConfigManager(
        config_path=args.config,
        auth_config_path=args.auth_config
    )
    
    if args.config_action == "validate":
        try:
            model_configs = config_manager.load_model_configs()
            print(f"✓ Configuration is valid ({len(model_configs)} models)")
            
            # Check for port conflicts
            if not config_manager.validate_model_ports():
                print("✗ Port conflicts detected!")
                sys.exit(1)
            else:
                print("✓ No port conflicts")
                
        except Exception as e:
            print(f"✗ Configuration error: {e}")
            sys.exit(1)
            
    elif args.config_action == "show":
        try:
            model_configs = config_manager.load_model_configs()
            
            print(f"Configuration file: {config_manager.config_path}")
            print(f"Auth config file: {config_manager.auth_config_path}")
            print(f"Models: {len(model_configs)}")
            
            for name, config in model_configs.items():
                print(f"\n{name}:")
                print(f"  Port: {config.port}")
                print(f"  Model path: {config.model_path}")
                print(f"  Context length: {config.context_length}")
                print(f"  GPU layers: {config.gpu_layers}")
                print(f"  Priority: {config.priority}")
                print(f"  Resource group: {config.resource_group}")
                print(f"  Auto-start: {config.auto_start}")
                print(f"  Preload: {config.preload}")
                
        except Exception as e:
            print(f"Error loading configuration: {e}")
            sys.exit(1)


def cmd_version(args):
    """Show version information."""
    if args.verbose:
        build_info = get_build_info()
        print(f"LLM Proxifier {build_info['version']}")
        print(f"Commit: {build_info['commit_hash']}")
        print(f"Date: {build_info['commit_date']}")
        if build_info['dirty']:
            print("Status: dirty (uncommitted changes)")
        else:
            print("Status: clean")
    else:
        print(f"LLM Proxifier {get_version()}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="LLM Proxifier - Intelligent proxy server for LLaMA models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  llm-proxifier start                    # Start server with default settings
  llm-proxifier start --port 8080       # Start on custom port
  llm-proxifier status                   # Check if server is running
  llm-proxifier models                   # List available models
  llm-proxifier dashboard                # Open dashboard in browser
  llm-proxifier config validate          # Validate configuration
        """
    )
    
    # Global options
    parser.add_argument("--version", action="version", version=f"LLM Proxifier {get_version()}")
    parser.add_argument("--config", "-c", help="Path to models config file", 
                       default=os.getenv("CONFIG_PATH", "./config/models.yaml"))
    parser.add_argument("--auth-config", help="Path to auth config file",
                       default=os.getenv("AUTH_CONFIG_PATH", "./config/auth.yaml"))
    parser.add_argument("--host", help="Host to bind to")
    parser.add_argument("--port", "-p", type=int, help="Port to bind to")
    parser.add_argument("--log-level", "-l", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       default="INFO", help="Log level")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start the server")
    start_parser.add_argument("--dashboard-port", type=int, help="Dashboard port")
    start_parser.add_argument("--disable-auth", action="store_true", help="Disable authentication")
    start_parser.add_argument("--disable-dashboard", action="store_true", help="Disable dashboard")
    start_parser.set_defaults(func=cmd_start)
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check server status")
    status_parser.set_defaults(func=lambda args: asyncio.run(cmd_status(args)))
    
    # Models command
    models_parser = subparsers.add_parser("models", help="List available models")
    models_parser.set_defaults(func=lambda args: asyncio.run(cmd_models(args)))
    
    # Dashboard command
    dashboard_parser = subparsers.add_parser("dashboard", help="Open dashboard in browser")
    dashboard_parser.add_argument("--dashboard-port", type=int, help="Dashboard port")
    dashboard_parser.set_defaults(func=cmd_dashboard)
    
    # Config command
    config_parser = subparsers.add_parser("config", help="Configuration management")
    config_parser.add_argument("config_action", choices=["validate", "show"], 
                              help="Configuration action")
    config_parser.set_defaults(func=cmd_config)
    
    # Version command
    version_parser = subparsers.add_parser("version", help="Show version information")
    version_parser.add_argument("--verbose", "-v", action="store_true", 
                               help="Show detailed version information")
    version_parser.set_defaults(func=cmd_version)
    
    # Parse arguments
    args = parser.parse_args()
    
    # If no command specified, show help
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Execute command
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
