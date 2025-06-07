#!/usr/bin/env python3
"""
Alternative setup script for Windows with virtual environment issues
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

def run_command(command):
    """Run a command and return success status"""
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def try_create_venv_method1():
    """Try creating virtual environment with standard method"""
    print("\n📦 Method 1: Standard venv creation...")
    success, output = run_command("python -m venv venv")
    if success:
        print("✅ Virtual environment created successfully")
        return True
    else:
        print(f"❌ Method 1 failed: {output}")
        return False

def try_create_venv_method2():
    """Try creating virtual environment with virtualenv package"""
    print("\n📦 Method 2: Using virtualenv package...")
    
    # First install virtualenv
    print("   Installing virtualenv...")
    success, output = run_command("pip install virtualenv")
    if not success:
        print(f"❌ Failed to install virtualenv: {output}")
        return False
    
    # Create venv with virtualenv
    success, output = run_command("virtualenv venv")
    if success:
        print("✅ Virtual environment created with virtualenv")
        return True
    else:
        print(f"❌ Method 2 failed: {output}")
        return False

def try_create_venv_method3():
    """Try creating virtual environment with conda (if available)"""
    print("\n📦 Method 3: Using conda...")
    
    # Check if conda is available
    success, output = run_command("conda --version")
    if not success:
        print("❌ Conda not available")
        return False
    
    print(f"   Found conda: {output.strip()}")
    
    # Create conda environment
    success, output = run_command("conda create -n news_agent python=3.11 -y")
    if success:
        print("✅ Conda environment created")
        print("   To activate: conda activate news_agent")
        return True
    else:
        print(f"❌ Method 3 failed: {output}")
        return False

def install_without_venv():
    """Install packages directly to system Python"""
    print("\n📦 Method 4: Installing directly to system Python...")
    print("⚠️  Warning: This will install packages globally")
    
    response = input("Continue with global installation? (y/N): ").lower().strip()
    if response != 'y':
        return False
    
    success, output = run_command("pip install --upgrade pip")
    if not success:
        print(f"❌ Failed to upgrade pip: {output}")
        return False
    
    success, output = run_command("pip install -r requirements.txt")
    if success:
        print("✅ Requirements installed globally")
        return True
    else:
        print(f"❌ Method 4 failed: {output}")
        return False

def install_requirements_venv():
    """Install requirements in virtual environment"""
    print("\n📥 Installing requirements in virtual environment...")
    
    # Try different pip paths
    pip_commands = [
        "venv\\Scripts\\pip",
        "venv\\Scripts\\pip.exe",
        "venv\\bin\\pip"
    ]
    
    for pip_cmd in pip_commands:
        if os.path.exists(pip_cmd) or os.path.exists(pip_cmd + ".exe"):
            print(f"   Using {pip_cmd}")
            break
    else:
        pip_cmd = "venv\\Scripts\\pip"  # Default
    
    # Upgrade pip
    success, output = run_command(f"{pip_cmd} install --upgrade pip")
    if not success:
        print(f"⚠️  Warning: Failed to upgrade pip: {output}")
    
    # Install requirements
    success, output = run_command(f"{pip_cmd} install -r requirements.txt")
    if success:
        print("✅ Requirements installed successfully")
        return True
    else:
        print(f"❌ Failed to install requirements: {output}")
        return False

def download_nltk_data(use_venv=True):
    """Download required NLTK data"""
    print("\n📚 Downloading NLTK data...")
    
    if use_venv:
        python_cmd = "venv\\Scripts\\python"
    else:
        python_cmd = "python"
    
    nltk_downloads = ["punkt", "stopwords"]
    
    for data in nltk_downloads:
        success, output = run_command(f'{python_cmd} -c "import nltk; nltk.download(\'{data}\')"')
        if success:
            print(f"✅ Downloaded {data}")
        else:
            print(f"⚠️  Warning: Failed to download {data}")
    
    return True

def create_env_file():
    """Create .env file from template"""
    print("\n⚙️  Setting up environment file...")
    
    if os.path.exists(".env"):
        print("   .env file already exists")
        return True
    
    env_content = """# Add your API keys here
OPENAI_API_KEY=
HUGGINGFACE_API_KEY=

# Database Configuration
DATABASE_PATH=news_agent.db

# Scraping Configuration
SCRAPING_DELAY=1
MAX_ARTICLES_PER_SOURCE=15
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("✅ Created .env file")
    print("   📝 Please add your API keys to .env file")
    return True

def create_batch_files():
    """Create Windows batch files for easy execution"""
    print("\n📝 Creating Windows batch files...")
    
    # Activation batch file
    activate_content = """@echo off
echo Activating virtual environment...
call venv\\Scripts\\activate.bat
echo Virtual environment activated!
echo.
echo Available commands:
echo   python news_agent_free.py  (Free version)
echo   python news_agent.py       (OpenAI version)
echo.
cmd /k
"""
    
    with open("activate.bat", "w") as f:
        f.write(activate_content)
    
    # Run agent batch file
    run_content = """@echo off
echo Starting News Agent...
call venv\\Scripts\\activate.bat
python news_agent_free.py
pause
"""
    
    with open("run_agent.bat", "w") as f:
        f.write(run_content)
    
    print("✅ Created batch files:")
    print("   - activate.bat (activate environment)")
    print("   - run_agent.bat (run the agent)")

def print_manual_instructions():
    """Print manual setup instructions"""
    print("\n" + "="*60)
    print("📋 MANUAL SETUP INSTRUCTIONS")
    print("="*60)
    print("\nIf automatic setup fails, follow these steps:")
    print("\n1. Skip virtual environment (install globally):")
    print("   pip install requests beautifulsoup4 lxml nltk textstat")
    print("   python -c \"import nltk; nltk.download('punkt'); nltk.download('stopwords')\"")
    
    print("\n2. Or try alternative virtual environment:")
    print("   pip install virtualenv")
    print("   virtualenv venv")
    print("   venv\\Scripts\\activate")
    print("   pip install -r requirements.txt")
    
    print("\n3. Or use conda (if installed):")
    print("   conda create -n news_agent python=3.11")
    print("   conda activate news_agent")
    print("   pip install -r requirements.txt")
    
    print("\n4. Test installation:")
    print("   python -c \"import requests, bs4, nltk; print('All imports work!')\"")

def main():
    """Main setup function with multiple fallback methods"""
    print("🚀 News Scraping Agent Setup (Windows)")
    print("="*45)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Try different methods to create virtual environment
    venv_created = False
    use_venv = False
    
    if os.path.exists("venv"):
        print("📦 Virtual environment already exists")
        venv_created = True
        use_venv = True
    else:
        # Try Method 1: Standard venv
        if try_create_venv_method1():
            venv_created = True
            use_venv = True
        # Try Method 2: virtualenv package
        elif try_create_venv_method2():
            venv_created = True
            use_venv = True
        # Try Method 3: conda
        elif try_create_venv_method3():
            print("✅ Using conda environment instead")
            print("   Please run: conda activate news_agent")
            print("   Then: pip install -r requirements.txt")
            return True
        # Method 4: Global installation
        else:
            print("\n⚠️  All virtual environment methods failed")
            if install_without_venv():
                download_nltk_data(use_venv=False)
                create_env_file()
                print("\n✅ Setup completed with global installation")
                print("   You can run: python news_agent_free.py")
                return True
            else:
                print("\n❌ All installation methods failed")
                print_manual_instructions()
                return False
    
    # Install requirements if venv was created
    if venv_created and use_venv:
        if not install_requirements_venv():
            print("\n⚠️  Failed to install in venv, trying global installation...")
            if install_without_venv():
                use_venv = False
            else:
                print_manual_instructions()
                return False
    
    # Download NLTK data
    download_nltk_data(use_venv)
    
    # Create .env file
    create_env_file()
    
    # Create batch files for Windows
    if use_venv:
        create_batch_files()
    
    # Print success message
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETE!")
    print("="*60)
    
    if use_venv:
        print("\n📋 To run the agent:")
        print("1. Double-click 'activate.bat' to activate environment")
        print("2. Or manually:")
        print("   venv\\Scripts\\activate")
        print("   python news_agent_free.py")
    else:
        print("\n📋 To run the agent:")
        print("   python news_agent_free.py")
    
    print("\n📝 Don't forget to:")
    print("   - Edit .env file and add your API keys")
    print("   - Read README.md for detailed instructions")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        input("\nPress Enter to exit...")
    sys.exit(0 if success else 1)