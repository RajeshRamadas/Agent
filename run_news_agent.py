#!/usr/bin/env python3
"""
Easy Runner for Integrated News Agent
Simple interface for running the complete news scraping system
"""

import os
import sys
from datetime import datetime

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = {
        'requests': 'requests',
        'bs4': 'beautifulsoup4',
        'nltk': 'nltk',
        'schedule': 'schedule'
    }
    
    missing = []
    for module, package in required_packages.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    
    if missing:
        print("❌ Missing required packages:")
        for package in missing:
            print(f"   • {package}")
        print("\n📥 Install with:")
        print(f"   pip install {' '.join(missing)}")
        return False
    
    return True

def download_nltk_data():
    """Download required NLTK data"""
    try:
        import nltk
        
        required_data = ['punkt', 'stopwords']
        for data in required_data:
            try:
                nltk.data.find(f'tokenizers/{data}' if data == 'punkt' else f'corpora/{data}')
                print(f"✅ NLTK {data} data available")
            except LookupError:
                print(f"📚 Downloading NLTK {data} data...")
                nltk.download(data, quiet=True)
                print(f"✅ NLTK {data} data downloaded")
    
    except Exception as e:
        print(f"⚠️ NLTK setup warning: {e}")

def print_banner():
    """Print welcome banner"""
    print("=" * 70)
    print("🤖 INTEGRATED NEWS SCRAPING AGENT v2.0")
    print("=" * 70)
    print("🌐 Sources: LiveMint, MoneyControl, Economic Times, Business Standard")
    print("🧠 AI Summarization: OpenAI, Hugging Face, Local")
    print("📊 Features: Reports, Exports, Trending Analysis, Scheduling")
    print("=" * 70)

def get_api_setup():
    """Get API key setup from user"""
    print("\n🔑 API KEY SETUP:")
    print("Choose your summarization method:")
    print("1. Local summarization (Free, Basic quality)")
    print("2. OpenAI GPT (Paid, Excellent quality)")
    print("3. Hugging Face (Free tier, Good quality)")
    
    choice = input("\nSelect option (1/2/3) [default: 1]: ").strip() or "1"
    
    openai_key = None
    hf_key = None
    
    if choice == "2":
        openai_key = input("Enter OpenAI API key: ").strip()
        if not openai_key:
            print("⚠️ No OpenAI key provided, falling back to local summarization")
    elif choice == "3":
        hf_key = input("Enter Hugging Face API key: ").strip()
        if not hf_key:
            print("⚠️ No HF key provided, falling back to local summarization")
    
    return openai_key, hf_key

def get_execution_mode():
    """Get execution mode from user"""
    print("\n⚙️ EXECUTION MODE:")
    print("1. Quick run (5-10 minutes, get latest news)")
    print("2. Complete run (15-20 minutes, comprehensive)")
    print("3. Scheduled operation (run automatically)")
    print("4. Interactive mode (full control)")
    
    mode = input("\nSelect mode (1/2/3/4) [default: 1]: ").strip() or "1"
    return mode

def run_quick_mode(agent):
    """Run quick mode - faster, fewer articles"""
    print("\n🚀 Starting Quick News Scan...")
    print("⚡ This will take 5-10 minutes")
    
    # Configure for speed
    agent.config.max_articles_per_page = 3
    agent.config.scraping_delay = 0.5
    agent.config.page_delay = 1.0
    
    results = agent.run_complete_scraping_cycle()
    
    print(f"\n✅ Quick scan completed!")
    print(f"📰 Found {results['total_new_articles']} new articles")
    print(f"⏱️ Processing time: {results['processing_time']:.1f} seconds")
    
    if results['total_new_articles'] > 0:
        print(f"\n📊 Quick Summary:")
        print(f"   LiveMint: {len(results['livemint'])} articles")
        print(f"   MoneyControl: {len(results['moneycontrol'])} articles")
        print(f"   Other Sources: {len(results['additional_sources'])} articles")
        
        # Show top headlines
        print(f"\n📰 Top Headlines:")
        count = 0
        for source_results in [results['livemint'], results['moneycontrol'], results['additional_sources']]:
            for article in source_results[:2]:
                if count >= 5:
                    break
                print(f"   • {article['title'][:65]}...")
                count += 1
        
        # Quick export
        export_file = agent.export_to_json(hours=1, filename=f"quick_news_{datetime.now().strftime('%Y%m%d_%H%M')}.json")
        print(f"\n💾 Exported to: {export_file}")
    
    return results

def run_complete_mode(agent):
    """Run complete mode - comprehensive, more articles"""
    print("\n🚀 Starting Complete News Analysis...")
    print("🔍 This will take 15-20 minutes for comprehensive coverage")
    
    results = agent.run_complete_scraping_cycle()
    
    print(f"\n✅ Complete analysis finished!")
    print(f"📰 Total articles: {results['total_new_articles']}")
    print(f"⏱️ Processing time: {results['processing_time']:.1f} seconds")
    print(f"📝 Summarization: {results['summarization_method']}")
    
    if results['total_new_articles'] > 0:
        # Generate comprehensive report
        print(f"\n📋 Generating comprehensive report...")
        report = agent.generate_comprehensive_report()
        
        # Save report
        report_file = f"complete_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"✅ Report saved: {report_file}")
        
        # Export data
        export_file = agent.export_to_json(filename=f"complete_export_{datetime.now().strftime('%Y%m%d_%H%M')}.json")
        print(f"✅ Data exported: {export_file}")
        
        # Show trending topics
        trending = agent.get_trending_topics(hours=24, limit=10)
        if trending:
            print(f"\n🔥 Top Trending Topics:")
            for i, topic in enumerate(trending[:5], 1):
                print(f"   {i}. {topic['topic']}: {topic['frequency']} mentions")
        
        # Source breakdown
        print(f"\n📊 Detailed Breakdown:")
        print(f"   📈 LiveMint: {len(results['livemint'])} articles")
        print(f"   💰 MoneyControl: {len(results['moneycontrol'])} articles")
        print(f"   📊 Additional Sources: {len(results['additional_sources'])} articles")
        
        if results['additional_sources']:
            sources = {}
            for article in results['additional_sources']:
                source = article['source']
                sources[source] = sources.get(source, 0) + 1
            print(f"       Additional breakdown: {', '.join([f'{k}({v})' for k, v in sources.items()])}")
    
    return results

def run_scheduled_mode(agent):
    """Run scheduled mode"""
    print("\n📅 Setting up Scheduled Operation...")
    
    # Get schedule preferences
    hours = input("⏰ Run every X hours [default: 2]: ").strip()
    try:
        hours = int(hours) if hours else 2
    except ValueError:
        hours = 2
    
    max_runs = input("🔢 Maximum runs (leave empty for unlimited): ").strip()
    try:
        max_runs = int(max_runs) if max_runs else None
    except ValueError:
        max_runs = None
    
    print(f"\n🚀 Running initial cycle...")
    initial_results = agent.run_complete_scraping_cycle()
    print(f"✅ Initial run: {initial_results['total_new_articles']} articles")
    
    # Import scheduler
    from integrated_news_agent import EnhancedNewsScheduler
    scheduler = EnhancedNewsScheduler(agent)
    
    print(f"\n📅 Starting scheduled operation...")
    print(f"⏰ Will run every {hours} hours")
    if max_runs:
        print(f"🔢 Maximum {max_runs} runs")
    print(f"🛑 Press Ctrl+C to stop")
    
    scheduler.start_scheduler(interval_hours=hours, max_runs=max_runs)

def main():
    """Main execution function"""
    print_banner()
    
    # Check dependencies
    if not check_dependencies():
        input("\nPress Enter to exit...")
        return
    
    # Download NLTK data
    download_nltk_data()
    
    # Check for existing API keys in environment
    env_openai = os.getenv('OPENAI_API_KEY')
    env_hf = os.getenv('HUGGINGFACE_API_KEY')
    
    if env_openai or env_hf:
        print("\n🔑 Found API keys in environment variables")
        use_env = input("Use existing environment API keys? (Y/n): ").lower().strip()
        if use_env != 'n':
            openai_key, hf_key = env_openai, env_hf
        else:
            openai_key, hf_key = get_api_setup()
    else:
        openai_key, hf_key = get_api_setup()
    
    # Get execution mode
    mode = get_execution_mode()
    
    # Initialize agent
    print(f"\n🤖 Initializing News Agent...")
    try:
        # Import the main agent class
        from integrated_news_agent import IntegratedNewsAgent, NewsConfig
        
        # Configure based on mode
        if mode == "1":  # Quick mode
            config = NewsConfig(
                max_articles_per_page=3,
                scraping_delay=0.5,
                page_delay=1.0,
                enable_logging=False
            )
        else:  # Complete mode
            config = NewsConfig(
                max_articles_per_page=5,
                scraping_delay=1.0,
                page_delay=2.0,
                enable_logging=True
            )
        
        agent = IntegratedNewsAgent(
            openai_api_key=openai_key,
            huggingface_api_key=hf_key,
            config=config
        )
        
        print("✅ Agent initialized successfully!")
        
    except ImportError:
        print("❌ Error: integrated_news_agent.py not found in current directory")
        print("   Make sure both files are in the same folder")
        input("Press Enter to exit...")
        return
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        input("Press Enter to exit...")
        return
    
    try:
        # Execute based on mode
        if mode == "1":
            results = run_quick_mode(agent)
        elif mode == "2":
            results = run_complete_mode(agent)
        elif mode == "3":
            run_scheduled_mode(agent)
        elif mode == "4":
            # Interactive mode - import and run the main function
            from integrated_news_agent import main as interactive_main
            interactive_main()
        else:
            print("❌ Invalid mode selected")
            return
        
        if mode in ["1", "2"]:
            print(f"\n🎉 Operation completed successfully!")
            print(f"📁 Check the current directory for reports and exports")
            
            # Offer to run again
            if mode == "1":
                again = input("\n🔄 Run another quick scan? (y/N): ").lower().strip()
                if again == 'y':
                    run_quick_mode(agent)
    
    except KeyboardInterrupt:
        print(f"\n🛑 Operation stopped by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        try:
            agent.close()
        except:
            pass
        print(f"\n👋 Thanks for using the Integrated News Agent!")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()