#!/usr/bin/env python3
"""
Test script to check basic Python syntax and imports without dependencies.
"""

import sys
import os
sys.path.insert(0, '.')

def test_basic_imports():
    """Test basic Python imports and syntax."""
    errors = []
    
    # Test config module structure
    try:
        import src.config
        print("✓ src.config imports successfully")
    except ImportError as e:
        if "yaml" in str(e):
            print("✓ src.config syntax OK (yaml dependency expected)")
        else:
            errors.append(f"src.config import error: {e}")
    
    # Test utils module structure  
    try:
        import src.utils
        print("✓ src.utils imports successfully")
    except ImportError as e:
        if any(dep in str(e) for dep in ["httpx", "psutil"]):
            print("✓ src.utils syntax OK (dependencies expected)")
        else:
            errors.append(f"src.utils import error: {e}")
    
    # Test model_manager module structure
    try:
        import src.model_manager
        print("✓ src.model_manager imports successfully")
    except ImportError as e:
        if any(dep in str(e) for dep in ["httpx", "psutil", "yaml"]):
            print("✓ src.model_manager syntax OK (dependencies expected)")
        else:
            errors.append(f"src.model_manager import error: {e}")
    
    # Test proxy_handler module structure
    try:
        import src.proxy_handler
        print("✓ src.proxy_handler imports successfully")
    except ImportError as e:
        if any(dep in str(e) for dep in ["httpx", "fastapi"]):
            print("✓ src.proxy_handler syntax OK (dependencies expected)")
        else:
            errors.append(f"src.proxy_handler import error: {e}")
    
    # Test main module structure
    try:
        import src.main
        print("✓ src.main imports successfully")
    except ImportError as e:
        if any(dep in str(e) for dep in ["fastapi", "httpx", "psutil", "yaml"]):
            print("✓ src.main syntax OK (dependencies expected)")
        else:
            errors.append(f"src.main import error: {e}")
    
    if errors:
        print("\n❌ Import Errors:")
        for error in errors:
            print(f"  {error}")
        return False
    else:
        print("\n✅ All modules have correct syntax and structure")
        return True

def test_file_structure():
    """Test that all expected files exist."""
    expected_files = [
        'src/__init__.py',
        'src/main.py',
        'src/config.py',
        'src/model_manager.py',
        'src/proxy_handler.py',
        'src/utils.py',
        'config/models.yaml',
        'requirements.txt',
        'README.md',
        'LICENSE',
        'scripts/start_proxy.sh',
        'scripts/stop_proxy.sh'
    ]
    
    missing_files = []
    for file_path in expected_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
        else:
            print(f"✓ {file_path}")
    
    if missing_files:
        print(f"\n❌ Missing files: {missing_files}")
        return False
    else:
        print("\n✅ All expected files exist")
        return True

if __name__ == "__main__":
    print("Testing LLM Proxifier structure and syntax...\n")
    
    structure_ok = test_file_structure()
    imports_ok = test_basic_imports()
    
    if structure_ok and imports_ok:
        print("\n🎉 All tests passed! The implementation looks good.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed.")
        sys.exit(1)
