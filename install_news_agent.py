#!/usr/bin/env python3
"""
Comprehensive Installer for News Agent System
Automatically sets up everything needed to run the news agent
"""

import os
import sys
import subprocess
import platform
import urllib.request
import shutil
import json
from pathlib import Path
from typing import List, Dict, Optional

class NewsAgentInstaller:
    """Comprehensive installer for the News Agent system"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.python_executable = sys.executable
        self.install_dir = Path.cwd()
        self.required_files = [
            'integrated_news_agent.py',
            'run_news_agent.py', 
            'web_dashboard.py',
            'notification_system.py',
            'requirements.txt',
            'QUICK_START.md',
            'README.md'
        ]
        self.optional_files = [
            'config.ini',
            '.env.example'
        ]
        
    def print_banner(self):
        """Print installation banner"""
        print("=" * 70)
        print("🤖 NEWS AGENT COMPREHENSIVE INSTALLER")
        print("=" * 70)
        print("🌐 Sources: LiveMint, MoneyControl, Economic Times, Business Standard")
        print("🧠 AI: OpenAI GPT, Hugging Face, Local Summarization")
        print("📊 Features: Web Dashboard, Notifications, Scheduling, Reports")
        print("📱 Interfaces: CLI, Web UI, API")
        print("=" * 70)
        print()
    
    def check_python_version(self) -> bool:
        """Check if Python version is compatible"""
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print(f"❌ Error: Python 3.8+ required, found {version.major}.{version.minor}")
            print("📥 Please install Python 3.8 or higher from https://python.org")
            return False
        
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
        return True
    
    def check_internet_connection(self) -> bool:
        """Check internet connectivity"""
        try:
            urllib.request.urlopen('https://www.google.com', timeout=5)
            print("✅ Internet connection - Available")
            return True
        except:
            print("❌ Internet connection - Not available")
            print("📶 Please check your internet connection")
            return False
    
    def install_package(self, package: str) -> bool:
        """Install a Python package using pip"""
        try:
            print(f"📦 Installing {package}...")
            result = subprocess.run(
                [self.python_executable, '-m', 'pip', 'install', package],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                print(f"✅ {package} installed successfully")
                return True
            else:
                print(f"❌ Failed to install {package}: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ Timeout installing {package}")
            return False
        except Exception as e:
            print(f"❌ Error installing {package}: {e}")
            return False
    
    def install_requirements(self) -> bool:
        """Install all required packages"""
        print("\n📦 INSTALLING PYTHON PACKAGES")
        print("-" * 40)
        
        # Core packages (always install)
        core_packages = [
            'requests>=2.31.0',
            'beautifulsoup4>=4.12.0', 
            'lxml>=4.9.0',
            'nltk>=3.8',
            'textstat>=0.7.3',
            'python-dotenv>=1.0.0',
            'schedule>=1.2.0'
        ]
        
        # Optional packages (ask user)
        optional_packages = {
            'Web Dashboard': ['flask>=2.3.0', 'flask-socketio>=5.3.0'],
            'OpenAI Integration': ['openai>=1.0.0'],
            'Data Analysis': ['pandas>=2.0.0', 'numpy>=1.24.0'],
            'Enhanced Features': ['colorlog>=6.7.0', 'tqdm>=4.65.0']
        }
        
        success_count = 0
        total_packages = len(core_packages)
        
        # Install core packages
        print("Installing core packages...")
        for package in core_packages:
            if self.install_package(package):
                success_count += 1
        
        # Ask about optional packages
        print(f"\n✅ Core packages: {success_count}/{total_packages} installed")
        print("\n🔧 Optional Features:")
        
        for feature, packages in optional_packages.items():
            install_feature = input(f"📦 Install {feature}? (y/N): ").lower().strip()
            if install_feature == 'y':
                print(f"Installing {feature}...")
                for package in packages:
                    if self.install_package(package):
                        success_count += 1
                    total_packages += 1
        
        return success_count >= len(core_packages)
    
    def download_nltk_data(self) -> bool:
        """Download required NLTK data"""
        print("\n📚 DOWNLOADING NLTK DATA")
        print("-" * 40)
        
        try:
            import nltk
            
            nltk_data = ['punkt', 'stopwords', 'vader_lexicon']
            
            for data in nltk_data:
                try:
                    print(f"📖 Downloading NLTK {data}...")
                    nltk.download(data, quiet=True)
                    print(f"✅ {data} downloaded")
                except Exception as e:
                    print(f"⚠️ Warning: Failed to download {data}: {e}")
            
            print("✅ NLTK data setup completed")
            return True
            
        except ImportError:
            print("❌ NLTK not installed, skipping data download")
            return False
        except Exception as e:
            print(f"⚠️ NLTK data download had issues: {e}")
            return True  # Continue anyway
    
    def create_directory_structure(self):
        """Create necessary directories"""
        print("\n📁 CREATING DIRECTORY STRUCTURE")
        print("-" * 40)
        
        directories = [
            'logs',
            'exports', 
            'templates',
            'static',
            'data',
            'config'
        ]
        
        for directory in directories:
            dir_path = self.install_dir / directory
            dir_path.mkdir(exist_ok=True)
            print(f"📂 Created: {directory}/")
        
        print("✅ Directory structure created")
    
    def create_configuration_files(self):
        """Create configuration files"""
        print("\n⚙️ CREATING CONFIGURATION FILES")
        print("-" * 40)
        
        # Create .env example
        env_example = """# News Agent Configuration
# Copy to .env and configure as needed

# === API KEYS (Optional) ===
OPENAI_API_KEY=
HUGGINGFACE_API_KEY=

# === DATABASE ===
DATABASE_PATH=news_agent.db

# === SCRAPING SETTINGS ===
MAX_ARTICLES_PER_SOURCE=25
SCRAPING_DELAY=1.0
PAGE_DELAY=2.0
TIMEOUT=15

# === LOGGING ===
LOG_LEVEL=INFO
ENABLE_LOGGING=true

# === WEB DASHBOARD ===
WEB_HOST=0.0.0.0
WEB_PORT=5000
WEB_DEBUG=false

# === EMAIL NOTIFICATIONS ===
EMAIL_NOTIFICATIONS_ENABLED=false
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USERNAME=
EMAIL_PASSWORD=
EMAIL_FROM=
EMAIL_TO=

# === SLACK NOTIFICATIONS ===
SLACK_NOTIFICATIONS_ENABLED=false
SLACK_WEBHOOK_URL=
SLACK_CHANNEL=#news

# === DISCORD NOTIFICATIONS ===
DISCORD_NOTIFICATIONS_ENABLED=false
DISCORD_WEBHOOK_URL=

# === TELEGRAM NOTIFICATIONS ===
TELEGRAM_NOTIFICATIONS_ENABLED=false
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
"""
        
        with open('.env.example', 'w') as f:
            f.write(env_example)
        print("✅ Created: .env.example")
        
        # Create config.ini
        config_ini = """[DEFAULT]
# News Agent Configuration File

[AGENT]
max_articles_per_source = 25
scraping_delay = 1.0
page_delay = 2.0
timeout = 15
enable_logging = true

[DATABASE]
path = news_agent.db
cleanup_days = 30

[WEB_DASHBOARD]
host = 0.0.0.0
port = 5000
debug = false

[NOTIFICATIONS]
email_enabled = false
slack_enabled = false
discord_enabled = false
telegram_enabled = false

[SOURCES]
livemint_enabled = true
moneycontrol_enabled = true
economic_times_enabled = true
business_standard_enabled = true
financial_express_enabled = true
"""
        
        with open('config/config.ini', 'w') as f:
            f.write(config_ini)
        print("✅ Created: config/config.ini")
    
    def create_startup_scripts(self):
        """Create startup scripts for different platforms"""
        print("\n🚀 CREATING STARTUP SCRIPTS")
        print("-" * 40)
        
        # Windows batch file
        if self.system == 'windows':
            batch_content = f"""@echo off
echo Starting News Agent...
cd /d "{self.install_dir}"
"{self.python_executable}" run_news_agent.py
pause
"""
            with open('start_news_agent.bat', 'w') as f:
                f.write(batch_content)
            print("✅ Created: start_news_agent.bat")
        
        # Unix shell script
        else:
            shell_content = f"""#!/bin/bash
echo "Starting News Agent..."
cd "{self.install_dir}"
"{self.python_executable}" run_news_agent.py
read -p "Press Enter to exit..."
"""
            with open('start_news_agent.sh', 'w') as f:
                f.write(shell_content)
            
            # Make executable
            os.chmod('start_news_agent.sh', 0o755)
            print("✅ Created: start_news_agent.sh")
        
        # Web dashboard startup
        web_startup = f"""#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from web_dashboard import main
    main()
except ImportError:
    print("❌ Web dashboard not available")
    print("📦 Install with: pip install flask flask-socketio")
except Exception as e:
    print(f"❌ Error starting web dashboard: {{e}}")
    input("Press Enter to exit...")
"""
        
        with open('start_web_dashboard.py', 'w') as f:
            f.write(web_startup)
        print("✅ Created: start_web_dashboard.py")
    
    def create_documentation(self):
        """Create documentation files"""
        print("\n📚 CREATING DOCUMENTATION")
        print("-" * 40)
        
        # Installation guide
        install_guide = f"""# Installation Completed! 🎉

## ✅ What's Installed

Your News Agent system is now ready with:

### 📁 File Structure
```
{self.install_dir.name}/
├── integrated_news_agent.py     # Main agent
├── run_news_agent.py            # Easy runner
├── web_dashboard.py             # Web interface
├── notification_system.py       # Alerts system
├── start_news_agent.bat/.sh     # Quick starter
├── start_web_dashboard.py       # Web UI starter
├── .env.example                 # Configuration template
├── config/
│   └── config.ini              # Settings file
├── logs/                       # Log files
├── exports/                    # Data exports
└── data/                       # Database storage

```

## 🚀 Quick Start

### Option 1: Command Line
```bash
# Windows
start_news_agent.bat

# Linux/Mac  
./start_news_agent.sh

# Or directly
python run_news_agent.py
```

### Option 2: Web Dashboard
```bash
python start_web_dashboard.py
# Then visit: http://localhost:5000
```

## ⚙️ Configuration

1. **Copy configuration template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit .env file** and add your API keys (optional):
   ```
   OPENAI_API_KEY=sk-your-key-here
   HUGGINGFACE_API_KEY=hf_your-key-here
   ```

3. **For notifications**, configure email/Slack/Discord settings

## 📊 Usage Modes

1. **Quick Scan** (5-10 min): Fast daily updates
2. **Complete Analysis** (15-20 min): Comprehensive coverage
3. **Scheduled Operation**: Automatic monitoring
4. **Web Dashboard**: Visual interface with charts

## 🔗 Getting API Keys

- **OpenAI**: https://platform.openai.com/api-keys
- **Hugging Face**: https://huggingface.co/settings/tokens

## 📞 Support

- Check README.md for detailed documentation
- Review QUICK_START.md for usage examples
- Logs are stored in logs/ directory

**Happy News Monitoring! 📰🤖**
"""
        
        with open('INSTALLATION_COMPLETE.md', 'w') as f:
            f.write(install_guide)
        print("✅ Created: INSTALLATION_COMPLETE.md")
    
    def test_installation(self) -> bool:
        """Test if installation works"""
        print("\n🧪 TESTING INSTALLATION")
        print("-" * 40)
        
        try:
            # Test core imports
            print("🔍 Testing core imports...")
            
            import requests
            print("✅ requests")
            
            import bs4
            print("✅ beautifulsoup4")
            
            import nltk
            print("✅ nltk")
            
            # Test if main files exist
            print("\n🔍 Testing file structure...")
            required_exists = 0
            
            for file in self.required_files:
                if Path(file).exists():
                    print(f"✅ {file}")
                    required_exists += 1
                else:
                    print(f"❌ {file} - Missing")
            
            # Test basic functionality
            print("\n🔍 Testing basic functionality...")
            
            try:
                # Import and test news agent
                import integrated_news_agent
                config = integrated_news_agent.NewsConfig(enable_logging=False)
                agent = integrated_news_agent.IntegratedNewsAgent(config=config)
                print("✅ News agent initialization")
                agent.close()
            except Exception as e:
                print(f"❌ News agent test failed: {e}")
                return False
            
            success_rate = required_exists / len(self.required_files)
            print(f"\n📊 Installation Success Rate: {success_rate:.1%}")
            
            return success_rate >= 0.8
            
        except ImportError as e:
            print(f"❌ Import test failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Installation test failed: {e}")
            return False
    
    def get_user_preferences(self) -> Dict:
        """Get user preferences for installation"""
        print("\n🎛️ INSTALLATION PREFERENCES")
        print("-" * 40)
        
        preferences = {}
        
        # Installation type
        print("📦 Installation Type:")
        print("1. Minimal (Core features only)")
        print("2. Standard (Recommended)")
        print("3. Complete (All features)")
        
        install_type = input("\nChoose (1/2/3) [default: 2]: ").strip() or "2"
        preferences['install_type'] = install_type
        
        # Web dashboard
        if install_type in ['2', '3']:
            web_dashboard = input("🌐 Install Web Dashboard? (Y/n): ").lower().strip()
            preferences['web_dashboard'] = web_dashboard != 'n'
        else:
            preferences['web_dashboard'] = False
        
        # Notifications
        if install_type == '3':
            notifications = input("📧 Install Notification System? (Y/n): ").lower().strip()
            preferences['notifications'] = notifications != 'n'
        else:
            preferences['notifications'] = False
        
        # API keys
        setup_apis = input("🔑 Set up API keys now? (y/N): ").lower().strip()
        preferences['setup_apis'] = setup_apis == 'y'
        
        return preferences
    
    def setup_api_keys(self):
        """Interactive API key setup"""
        print("\n🔑 API KEY SETUP")
        print("-" * 40)
        
        env_content = ""
        
        # OpenAI
        print("\n🧠 OpenAI GPT (Premium Summarization)")
        print("   Get key: https://platform.openai.com/api-keys")
        openai_key = input("   Enter OpenAI API key (or press Enter to skip): ").strip()
        
        if openai_key:
            env_content += f"OPENAI_API_KEY={openai_key}\n"
            print("   ✅ OpenAI key saved")
        
        # Hugging Face
        print("\n🤗 Hugging Face (Free AI Summarization)")
        print("   Get key: https://huggingface.co/settings/tokens")
        hf_key = input("   Enter Hugging Face API key (or press Enter to skip): ").strip()
        
        if hf_key:
            env_content += f"HUGGINGFACE_API_KEY={hf_key}\n"
            print("   ✅ Hugging Face key saved")
        
        # Email notifications
        setup_email = input("\n📧 Set up email notifications? (y/N): ").lower().strip()
        if setup_email == 'y':
            print("   Email Configuration:")
            email_user = input("     Gmail address: ").strip()
            email_pass = input("     App password: ").strip()
            email_to = input("     Send alerts to (email): ").strip()
            
            if email_user and email_pass and email_to:
                env_content += f"""
EMAIL_NOTIFICATIONS_ENABLED=true
EMAIL_USERNAME={email_user}
EMAIL_PASSWORD={email_pass}
EMAIL_FROM={email_user}
EMAIL_TO={email_to}
"""
                print("   ✅ Email notifications configured")
        
        # Save .env file
        if env_content:
            with open('.env', 'w') as f:
                f.write(env_content)
            print("\n✅ Configuration saved to .env file")
        else:
            print("\n📝 No API keys configured (you can add them later)")
    
    def run_installation(self):
        """Run the complete installation process"""
        self.print_banner()
        
        # Pre-installation checks
        if not self.check_python_version():
            return False
        
        if not self.check_internet_connection():
            return False
        
        # Get user preferences
        preferences = self.get_user_preferences()
        
        # Install packages
        if not self.install_requirements():
            print("\n❌ Package installation failed")
            return False
        
        # Download NLTK data
        self.download_nltk_data()
        
        # Create directory structure
        self.create_directory_structure()
        
        # Create configuration files
        self.create_configuration_files()
        
        # Create startup scripts
        self.create_startup_scripts()
        
        # Create documentation
        self.create_documentation()
        
        # Set up API keys if requested
        if preferences.get('setup_apis'):
            self.setup_api_keys()
        
        # Test installation
        print("\n🧪 Running installation tests...")
        if self.test_installation():
            print("\n🎉 INSTALLATION COMPLETED SUCCESSFULLY!")
            print("=" * 50)
            print("✅ All components installed and tested")
            print("📚 Check INSTALLATION_COMPLETE.md for next steps")
            print("🚀 Quick start:")
            
            if self.system == 'windows':
                print("   Double-click: start_news_agent.bat")
            else:
                print("   Run: ./start_news_agent.sh")
            
            if preferences.get('web_dashboard'):
                print("   Web UI: python start_web_dashboard.py")
            
            print("\n🎯 Ready to monitor Indian financial news!")
            return True
        else:
            print("\n⚠️ Installation completed with warnings")
            print("📝 Check the error messages above")
            print("🔧 You may need to install missing components manually")
            return False

def main():
    """Main installer function"""
    try:
        installer = NewsAgentInstaller()
        success = installer.run_installation()
        
        if success:
            input("\nPress Enter to exit...")
        else:
            print("\n🔧 Troubleshooting:")
            print("1. Check internet connection")
            print("2. Ensure Python 3.8+ is installed")
            print("3. Try running as administrator (Windows)")
            print("4. Check firewall/antivirus settings")
            input("\nPress Enter to exit...")
            
    except KeyboardInterrupt:
        print("\n\n🛑 Installation cancelled by user")
    except Exception as e:
        print(f"\n❌ Installation failed: {e}")
        print("🔧 Please check your system and try again")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()