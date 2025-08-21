#!/usr/bin/env python3
"""
Quick setup script for Content Workflow Agent (GitHub Deployment).

This script helps set up the application environment and validates
the installation for local deployment from GitHub.
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.11 or higher."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print("❌ Python 3.11 or higher is required.")
        print(f"Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")
    return True

def check_env_file():
    """Check if .env file exists and has required variables."""
    env_path = Path(".env")
    
    if not env_path.exists():
        print("❌ .env file not found")
        print("📝 Creating .env file from example...")
        
        example_path = Path(".env.example")
        if example_path.exists():
            # Copy example to .env
            with open(example_path, 'r') as src, open(env_path, 'w') as dst:
                dst.write(src.read())
            print("✅ .env file created from .env.example")
            print("⚠️  Please edit .env and add your OpenAI API key")
            return False
        else:
            print("❌ .env.example not found, creating basic .env file")
            with open(env_path, 'w') as f:
                f.write("OPENAI_API_KEY=your_openai_api_key_here\n")
                f.write("FACT_CHECK_PROVIDER=duckduckgo\n")
                f.write("COMPLIANCE_MODE=standard\n")
                f.write("TIMEZONE=US/Eastern\n")
            print("✅ Basic .env file created")
            print("⚠️  Please edit .env and add your OpenAI API key")
            return False
    
    # Check if API key is set
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_openai_api_key_here":
        print("❌ OpenAI API key not set in .env file")
        print("⚠️  Please edit .env and add your OpenAI API key")
        return False
    
    print("✅ .env file configured with API key")
    return True

def install_dependencies():
    """Install required dependencies."""
    requirements_file = "requirements_github.txt"
    
    if not Path(requirements_file).exists():
        print(f"❌ {requirements_file} not found")
        return False
    
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", requirements_file
        ])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def test_imports():
    """Test if all required modules can be imported."""
    print("🔍 Testing imports...")
    
    required_modules = [
        "streamlit",
        "fastapi",
        "openai", 
        "langchain",
        "langgraph",
        "ddgs",
        "wikipedia",
        "numpy",
        "sklearn"
    ]
    
    failed_imports = []
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError:
            print(f"  ❌ {module}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"\n❌ Failed to import: {', '.join(failed_imports)}")
        print("💡 Try running: pip install -r requirements_github.txt")
        return False
    
    print("✅ All imports successful")
    return True

def validate_app_structure():
    """Validate that all required files and directories exist."""
    print("📁 Checking application structure...")
    
    required_paths = [
        "app/__init__.py",
        "app/api.py",
        "app/config.py", 
        "app/graph.py",
        "app/models.py",
        "app/prompts.py",
        "app/tools/__init__.py",
        "app/tools/compliance.py",
        "app/tools/embeddings.py",
        "app/tools/factcheck.py",
        "app/tools/schedule.py",
        "app/tools/search.py",
        "ui_standalone.py",
        "requirements_github.txt"
    ]
    
    missing_files = []
    
    for path in required_paths:
        if not Path(path).exists():
            missing_files.append(path)
            print(f"  ❌ {path}")
        else:
            print(f"  ✅ {path}")
    
    if missing_files:
        print(f"\n❌ Missing files: {', '.join(missing_files)}")
        return False
    
    print("✅ Application structure validated")
    return True

def main():
    """Main setup function."""
    print("🚀 Content Workflow Agent - GitHub Setup")
    print("=" * 50)
    
    all_checks_passed = True
    
    # Run all checks
    checks = [
        ("Python Version", check_python_version),
        ("Application Structure", validate_app_structure),
        ("Dependencies Installation", install_dependencies),
        ("Import Testing", test_imports),
        ("Environment Configuration", check_env_file),
    ]
    
    for check_name, check_func in checks:
        print(f"\n📋 {check_name}")
        print("-" * 30)
        if not check_func():
            all_checks_passed = False
    
    print("\n" + "=" * 50)
    
    if all_checks_passed:
        print("🎉 Setup completed successfully!")
        print("\n🚀 Ready to start the application:")
        print("   streamlit run ui_standalone.py --server.port 8501")
        print("\n🌐 Then open: http://localhost:8501")
    else:
        print("⚠️  Setup completed with issues.")
        print("📝 Please address the issues above before running the application.")
        
    return all_checks_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)