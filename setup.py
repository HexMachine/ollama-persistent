#!/usr/bin/env python3
"""
Setup script for the Persistent Ollama Chat application.
Checks dependencies and Ollama installation.
"""

import subprocess
import sys
import os
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 or higher is required")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} is compatible")
    return True

def check_ollama_installation():
    """Check if Ollama is installed and accessible."""
    try:
        result = subprocess.run(['ollama', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Ollama is installed and accessible")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    print("❌ Ollama is not installed or not accessible")
    print("   Please install Ollama from: https://ollama.ai/")
    print("   Or run: curl -fsSL https://ollama.ai/install.sh | sh")
    return False

def check_ollama_models():
    """Check if any Ollama models are available."""
    try:
        result = subprocess.run(['ollama', 'list'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            # Skip header line
            model_lines = [line for line in lines[1:] if line.strip()]
            if model_lines:
                print(f"✅ Found {len(model_lines)} Ollama model(s)")
                for line in model_lines[:3]:  # Show first 3 models
                    model_name = line.split()[0]
                    print(f"   - {model_name}")
                if len(model_lines) > 3:
                    print(f"   ... and {len(model_lines) - 3} more")
                return True
            else:
                print("⚠️  No Ollama models found")
                print("   Please install a model, for example:")
                print("   ollama pull llama2")
                return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    print("❌ Could not check Ollama models")
    return False

def install_python_dependencies():
    """Install Python dependencies."""
    requirements_file = Path(__file__).parent / "requirements.txt"
    if not requirements_file.exists():
        print("❌ requirements.txt not found")
        return False
    
    try:
        print("📦 Installing Python dependencies...")
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Python dependencies installed successfully")
            return True
        else:
            print("❌ Failed to install dependencies:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def check_data_directory():
    """Check and create data directory if needed."""
    data_dir = Path(__file__).parent / "data"
    if data_dir.exists():
        print("✅ Data directory exists")
    else:
        try:
            data_dir.mkdir()
            print("✅ Created data directory")
        except Exception as e:
            print(f"❌ Failed to create data directory: {e}")
            return False
    return True

def main():
    """Main setup function."""
    print("🤖 Persistent Ollama Chat - Setup")
    print("=" * 40)
    
    checks_passed = []
    
    # Check Python version
    checks_passed.append(check_python_version())
    
    # Check data directory
    checks_passed.append(check_data_directory())
    
    # Install dependencies
    checks_passed.append(install_python_dependencies())
    
    # Check Ollama installation
    checks_passed.append(check_ollama_installation())
    
    # Check for models (warning only)
    models_available = check_ollama_models()
    
    print("\n" + "=" * 40)
    
    if all(checks_passed):
        print("✅ Setup completed successfully!")
        if models_available:
            print("\n🚀 You can now run the chat application with:")
            print("   python ollama_chat.py")
            print("   or")
            print("   python run_chat.py")
        else:
            print("\n⚠️  Setup completed, but no models found.")
            print("   Please install a model first:")
            print("   ollama pull llama2")
            print("   ollama pull codellama")
            print("   ollama pull mistral")
    else:
        print("❌ Setup incomplete. Please resolve the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
