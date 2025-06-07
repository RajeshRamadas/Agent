#!/usr/bin/env python3
"""
Setup script for News Scraping Agent
Automates the installation and configuration process
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

def create_virtual_environment():
    """Create and activate virtual environment"""
    print("\n📦 Setting up virtual environment...")
    
    if os.path.exists("venv"):
        print("   Virtual environment already exists")
        return True
    
    success, output = run_command("python -m venv venv")
    if success:
        print("✅ Virtual environment created")
        return True
    else:
        print(f"❌ Failed to create virtual environment: {output}")
        return False

def install_requirements():
    """Install required packages"""
    print("\n📥 Installing requirements...")
    
    # Determine pip command based on OS
    pip_cmd = "venv\\Scripts\\pip" if os.name == 'nt' else "venv/bin/pip"
    
    success, output = run_command(f"{pip_cmd} install --upgrade pip")
    if not success:
        print(f"❌ Failed to upgrade pip: {output}")
        return False
    
    success, output = run_command(f"{pip_cmd} install -r requirements.txt")
    if success:
        print("✅ Requirements installed successfully")
        return True
    else:
        print(f"❌ Failed to install requirements: {output}")
        return False

def download_nltk_data():
    """Download required NLTK data"""
    print("\n📚 Downloading NLTK data...")
    
    python_cmd = "venv\\Scripts\\python" if os.name == 'nt' else "venv/bin/python"
    
    nltk_downloads = [
        "punkt",
        "stopwords",
        "vader_lexicon"
    ]
    
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
    
    if os.path.exists(".env.example"):
        shutil.copy(".env.example", ".env")
        print("✅ Created .env file from template")
        print("   📝 Please edit .env file and add your API keys")
        return True
    else:
        # Create basic .env file
        with open(".env", "w") as f:
            f.write("# Add your API keys here\n")
            f.write("OPENAI_API_KEY=\n")
            f.write("HUGGINGFACE_API_KEY=\n")
        print("✅ Created basic .env file")
        print("   📝 Please add your API keys to .env file")
        return True

def test_installation():
    """Test if installation works"""
    print("\n🧪 Testing installation...")
    
    python_cmd = "venv\\Scripts\\python" if os.name == 'nt' else "venv/bin/python"
    
    test_script = '''
import sys
try:
    import requests
    import bs4
    import nltk
    from news_agent_free import NewsAgentFree
    print("✅ All imports successful")
    
    # Test agent creation
    agent = NewsAgentFree()
    print("✅ Agent creation successful")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
'''
    
    with open("test_setup.py", "w") as f:
        f.write(test_script)
    
    success, output = run_command(f"{python_cmd} test_setup.py")
    
    # Clean up test file
    os.remove("test_setup.py")
    
    if success:
        print("✅ Installation test passed")
        return True
    else:
        print(f"❌ Installation test failed: {output}")
        return False

def print_next_steps():
    """Print next steps for the user"""
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETE!")
    print("="*60)
    print("\n📋 Next Steps:")
    print("1. Edit .env file and add your API keys:")
    print("   - OpenAI API key (for premium summarization)")
    print("   - Hugging Face API key (for free AI summarization)")
    print("\n2. Activate virtual environment:")
    if os.name == 'nt':
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    
    print("\n3. Run the agent:")
    print("   python news_agent_free.py  # For free version")
    print("   python news_agent.py       # For OpenAI version")
    
    print("\n4. Optional - Set up scheduling:")
    print("   - Modify the scheduling section in the code")
    print("   - Set up cron job (Linux/Mac) or Task Scheduler (Windows)")
    
    print("\n📚 Documentation:")
    print("   - Read README.md for detailed usage instructions")
    print("   - Check requirements.txt for all dependencies")
    
    print("\n🆘 Need help?")
    print("   - Check the troubleshooting section in README.md")
    print("   - Ensure your .env file has valid API keys")

def main():
    """Main setup function"""
    print("🚀 News Scraping Agent Setup")
    print("="*40)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Create virtual environment
    if not create_virtual_environment():
        return False
    
    # Install requirements
    if not install_requirements():
        return False
    
    # Download NLTK data
    if not download_nltk_data():
        print("⚠️  NLTK data download had issues, but continuing...")
    
    # Create .env file
    if not create_env_file():
        return False
    
    # Test installation
    if not test_installation():
        return False
    
    # Print next steps
    print_next_steps()
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
