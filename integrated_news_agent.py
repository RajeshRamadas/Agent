#!/usr/bin/env python3
"""
Complete Integrated News Scraping Agent - FIXED VERSION
Combines enhanced scraping with comprehensive features
Author: AI Assistant
Version: 2.1 - Fixed based on diagnostic results
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import logging
import os
import sys
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
import hashlib
import sqlite3
from typing import List, Dict, Optional, Union
import re
from pathlib import Path
import schedule
from dataclasses import dataclass
import threading

# Optional imports with fallbacks
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("📝 OpenAI not available. Install with: pip install openai")

try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
    from nltk.stem import PorterStemmer
    from collections import Counter
    import textstat
    NLTK_AVAILABLE = True
    
    # Download required data
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        print("📚 Downloading NLTK punkt data...")
        nltk.download('punkt', quiet=True)
    
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        print("📚 Downloading NLTK stopwords data...")
        nltk.download('stopwords', quiet=True)
        
except ImportError:
    NLTK_AVAILABLE = False
    print("📝 NLTK not available. Install with: pip install nltk textstat")

try:
    from dotenv import load_dotenv
    load_dotenv()
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    print("📝 python-dotenv not available. Install with: pip install python-dotenv")

@dataclass
class NewsConfig:
    """Configuration for the news agent"""
    max_articles_per_source: int = 25
    max_articles_per_page: int = 5
    scraping_delay: float = 2.0  # Increased from 1.0
    page_delay: float = 3.0      # Increased from 2.0
    timeout: int = 15
    min_content_length: int = 200
    user_agent: str = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'  # Updated
    database_path: str = 'news_agent.db'
    log_level: str = 'INFO'
    enable_logging: bool = True

class IntegratedNewsAgent:
    """
    Comprehensive News Scraping Agent with Enhanced Features - FIXED VERSION
    Combines multiple sources with intelligent content extraction and summarization
    """
    
    def __init__(self, 
                 openai_api_key: Optional[str] = None,
                 huggingface_api_key: Optional[str] = None,
                 config: Optional[NewsConfig] = None):
        """
        Initialize the Integrated News Agent
        
        Args:
            openai_api_key: OpenAI API key for premium summarization
            huggingface_api_key: Hugging Face API key for free AI summarization
            config: Configuration object
        """
        self.config = config or NewsConfig()
        
        # Setup logging
        if self.config.enable_logging:
            self.setup_logging()
        
        # Initialize session with robust headers - FIXED
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.config.user_agent,  # Updated user agent
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache'  # Added cache control
        })
        
        # Initialize database
        self.init_database()
        
        # Setup summarization
        self.setup_summarization(openai_api_key, huggingface_api_key)
        
        # Initialize NLTK if available
        if NLTK_AVAILABLE:
            self.init_nltk()
        
        # Statistics tracking - ENHANCED
        self.stats = {
            'total_requests': 0,
            'successful_scrapes': 0,
            'failed_scrapes': 0,
            'articles_processed': 0,
            'duplicates_found': 0,
            'blocked_sites': 0  # Added blocked sites tracking
        }
        
        if self.config.enable_logging:
            self.logger.info("🤖 Integrated News Agent (FIXED v2.1) initialized successfully")
        else:
            print("🤖 Integrated News Agent (FIXED v2.1) initialized successfully")
    
    def setup_logging(self):
        """Setup comprehensive logging"""
        # Create logs directory
        Path("logs").mkdir(exist_ok=True)
        
        # Setup logger
        self.logger = logging.getLogger("NewsAgent")
        self.logger.setLevel(getattr(logging, self.config.log_level))
        
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # File handler
        file_handler = logging.FileHandler(
            f"logs/news_agent_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def log(self, level: str, message: str):
        """Unified logging method"""
        if self.config.enable_logging:
            getattr(self.logger, level.lower())(message)
        else:
            print(f"[{level.upper()}] {message}")
    
    def init_database(self):
        """Initialize SQLite database with enhanced schema"""
        self.conn = sqlite3.connect(self.config.database_path)
        
        # Create articles table with enhanced fields
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                summary TEXT,
                source TEXT NOT NULL,
                category TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                content_hash TEXT,
                word_count INTEGER,
                reading_time INTEGER,
                sentiment_score REAL,
                tags TEXT
            )
        ''')
        
        # Create indexes for performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_source ON articles(source)",
            "CREATE INDEX IF NOT EXISTS idx_scraped_at ON articles(scraped_at)",
            "CREATE INDEX IF NOT EXISTS idx_content_hash ON articles(content_hash)",
            "CREATE INDEX IF NOT EXISTS idx_category ON articles(category)"
        ]
        
        for index in indexes:
            self.conn.execute(index)
        
        # Create scraping_stats table
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS scraping_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_articles INTEGER,
                processing_time REAL,
                sources_scraped TEXT,
                success_rate REAL
            )
        ''')
        
        self.conn.commit()
    
    def setup_summarization(self, openai_api_key: Optional[str], huggingface_api_key: Optional[str]):
        """Setup multiple summarization methods"""
        # Get API keys from environment if not provided
        if not openai_api_key:
            openai_api_key = os.getenv('OPENAI_API_KEY')
        if not huggingface_api_key:
            huggingface_api_key = os.getenv('HUGGINGFACE_API_KEY')
        
        # Setup OpenAI
        self.use_openai = False
        if openai_api_key and OPENAI_AVAILABLE:
            try:
                openai.api_key = openai_api_key
                self.use_openai = True
                self.log("info", "✅ OpenAI API configured")
            except Exception as e:
                self.log("error", f"❌ Failed to setup OpenAI: {e}")
        
        # Setup Hugging Face
        self.use_huggingface = False
        if huggingface_api_key:
            self.hf_headers = {"Authorization": f"Bearer {huggingface_api_key}"}
            self.use_huggingface = True
            self.log("info", "✅ Hugging Face API configured")
        
        # Determine active summarization method
        if self.use_openai:
            self.summarization_method = "OpenAI GPT"
        elif self.use_huggingface:
            self.summarization_method = "Hugging Face"
        else:
            self.summarization_method = "Local Extractive"
        
        self.log("info", f"📝 Using {self.summarization_method} summarization")
    
    def init_nltk(self):
        """Initialize NLTK components"""
        try:
            self.stop_words = set(stopwords.words('english'))
            self.stemmer = PorterStemmer()
            self.log("info", "✅ NLTK components initialized")
        except Exception as e:
            self.log("warning", f"⚠️ NLTK initialization failed: {e}")
            self.stop_words = set()
            self.stemmer = None
    
    def get_page_content(self, url: str) -> Optional[BeautifulSoup]:
        """Enhanced webpage fetching with error handling and retries - FIXED"""
        self.stats['total_requests'] += 1
        
        for attempt in range(3):  # 3 retry attempts
            try:
                self.log("debug", f"Fetching: {url} (attempt {attempt + 1})")
                
                response = self.session.get(url, timeout=self.config.timeout)
                
                # FIXED: Handle blocked sites (403)
                if response.status_code == 403:
                    self.log("warning", f"🚫 Site blocking detected (HTTP 403): {url}")
                    self.stats['blocked_sites'] += 1
                    return None
                
                response.raise_for_status()
                
                # Check content type
                content_type = response.headers.get('content-type', '').lower()
                if 'html' not in content_type:
                    self.log("warning", f"Non-HTML content type: {content_type} for {url}")
                    return None
                
                soup = BeautifulSoup(response.content, 'html.parser')
                self.stats['successful_scrapes'] += 1
                return soup
                
            except requests.exceptions.Timeout:
                self.log("warning", f"Timeout fetching {url} (attempt {attempt + 1})")
                time.sleep(2 ** attempt)  # Exponential backoff
            except requests.exceptions.RequestException as e:
                self.log("error", f"Request error for {url}: {e}")
                if attempt == 2:  # Last attempt
                    self.stats['failed_scrapes'] += 1
                    return None
                time.sleep(2 ** attempt)
            except Exception as e:
                self.log("error", f"Unexpected error fetching {url}: {e}")
                self.stats['failed_scrapes'] += 1
                return None
        
        return None
    
    def scrape_livemint_enhanced(self) -> List[Dict]:
        """Enhanced LiveMint scraping with FIXED selectors based on diagnostic"""
        self.log("info", "🔍 Starting enhanced LiveMint scraping...")
        articles = []
        
        # Comprehensive LiveMint URLs with categories
        livemint_urls = [
            ("https://www.livemint.com", "homepage"),
            ("https://www.livemint.com/news", "news"),
            ("https://www.livemint.com/news/india", "india"),
            ("https://www.livemint.com/market", "market"),
            ("https://www.livemint.com/companies", "companies"),
            ("https://www.livemint.com/money", "money"),
            ("https://www.livemint.com/economy", "economy"),
            ("https://www.livemint.com/politics", "politics"),
            ("https://www.livemint.com/industry", "industry")
        ]
        
        # FIXED: Use only working selectors from diagnostic
        working_selectors = [
            'h2 a',                    # ✅ Works - Found 15 elements
            'h3 a',                    # ✅ Works - Found 69 elements  
            'a[href*="/news/"]'        # ✅ Works - Found 42 elements
        ]
        
        # Removed non-working selectors:
        # 'h1 a', 'h4 a', '.headline a', '.story-card a', etc.
        
        for url, category in livemint_urls:
            try:
                self.log("info", f"📰 Scraping LiveMint {category}: {url}")
                soup = self.get_page_content(url)
                if not soup:
                    continue
                
                links = set()
                for selector in working_selectors:
                    try:
                        elements = soup.select(selector)
                        for element in elements[:8]:  # Limit per selector
                            href = element.get('href')
                            if href:
                                full_url = urljoin(url, href)
                                # Enhanced filtering for recent and relevant news
                                if self.is_recent_article(full_url) and self.is_valid_news_url(full_url):
                                    links.add(full_url)
                    except Exception as e:
                        self.log("debug", f"Selector error: {selector} - {e}")
                        continue
                
                # Process links from this page
                processed = 0
                for link in list(links):
                    if processed >= self.config.max_articles_per_page:
                        break
                    
                    article_content = self.extract_article_content(link, 'livemint', category)
                    if article_content:
                        articles.append(article_content)
                        processed += 1
                        time.sleep(self.config.scraping_delay)  # Increased delay
                
                self.log("info", f"✅ LiveMint {category}: {processed} articles processed")
                time.sleep(self.config.page_delay)  # Increased delay
                
            except Exception as e:
                self.log("error", f"❌ Error scraping LiveMint {category}: {e}")
                continue
        
        self.log("info", f"🎉 LiveMint scraping completed: {len(articles)} articles")
        return articles
    
    def scrape_moneycontrol_enhanced(self) -> List[Dict]:
        """Enhanced MoneyControl scraping - FIXED to handle blocking gracefully"""
        self.log("info", "🔍 Starting enhanced MoneyControl scraping...")
        articles = []
        
        # MoneyControl URLs (will likely be blocked, but we'll try gracefully)
        moneycontrol_urls = [
            ("https://www.moneycontrol.com/news/", "news"),
            ("https://www.moneycontrol.com/news/business/", "business"),
            ("https://www.moneycontrol.com/news/markets/", "markets"),
            ("https://www.moneycontrol.com/news/economy/", "economy"),
            ("https://www.moneycontrol.com/news/companies/", "companies")
        ]
        
        # Basic selectors to try
        basic_selectors = [
            'h1 a', 'h2 a', 'h3 a',
            'a[href*="/news/"]'
        ]
        
        blocked_count = 0
        
        for url, category in moneycontrol_urls:
            try:
                self.log("info", f"💰 Attempting MoneyControl {category}: {url}")
                soup = self.get_page_content(url)
                
                if not soup:
                    blocked_count += 1
                    self.log("warning", f"⚠️ MoneyControl {category} not accessible (likely blocked)")
                    continue
                
                # If we get here, the site is accessible
                links = set()
                for selector in basic_selectors:
                    try:
                        elements = soup.select(selector)
                        for element in elements[:8]:
                            href = element.get('href')
                            if href:
                                full_url = urljoin(url, href)
                                if self.is_recent_article(full_url) and self.is_valid_news_url(full_url):
                                    links.add(full_url)
                    except Exception as e:
                        self.log("debug", f"Selector error: {selector} - {e}")
                        continue
                
                # Process links from this page
                processed = 0
                for link in list(links):
                    if processed >= self.config.max_articles_per_page:
                        break
                    
                    article_content = self.extract_article_content(link, 'moneycontrol', category)
                    if article_content:
                        articles.append(article_content)
                        processed += 1
                        time.sleep(self.config.scraping_delay)
                
                self.log("info", f"✅ MoneyControl {category}: {processed} articles processed")
                time.sleep(self.config.page_delay)
                
            except Exception as e:
                self.log("error", f"❌ Error scraping MoneyControl {category}: {e}")
                continue
        
        if blocked_count >= len(moneycontrol_urls):
            self.log("warning", f"🚫 MoneyControl appears to be completely blocked")
        
        self.log("info", f"🎉 MoneyControl scraping completed: {len(articles)} articles")
        return articles
    
    def scrape_additional_sources(self) -> List[Dict]:
        """Scrape additional Indian financial news sources - FIXED"""
        self.log("info", "🔍 Starting additional sources scraping...")
        all_articles = []
        
        # Enhanced additional sources configuration with working selectors
        additional_sources = {
            'economic_times': {
                'urls': [
                    ("https://economictimes.indiatimes.com/", "homepage"),
                    ("https://economictimes.indiatimes.com/markets", "markets"),
                    ("https://economictimes.indiatimes.com/news/economy", "economy"),
                    ("https://economictimes.indiatimes.com/industry", "industry"),
                    ("https://economictimes.indiatimes.com/news/company", "companies")
                ],
                # FIXED: Use working selectors from diagnostic
                'selectors': [
                    'h1 a',           # ✅ Works - Found 1 element
                    'h2 a',           # ✅ Works - Found 23 elements
                    'a[href*="/news/"]'  # ✅ Works - Found 248 elements
                ]
            },
            'business_standard': {
                'urls': [
                    ("https://www.business-standard.com/", "homepage"),
                    ("https://www.business-standard.com/markets", "markets"),
                    ("https://www.business-standard.com/economy", "economy"),
                    ("https://www.business-standard.com/companies", "companies"),
                    ("https://www.business-standard.com/finance", "finance")
                ],
                'selectors': [
                    'h1 a', 'h2 a', 'h3 a',
                    'a[href*="/news/"]'
                ]
            },
            'financial_express': {
                'urls': [
                    ("https://www.financialexpress.com/", "homepage"),
                    ("https://www.financialexpress.com/market/", "market"),
                    ("https://www.financialexpress.com/economy/", "economy"),
                    ("https://www.financialexpress.com/industry/", "industry"),
                    ("https://www.financialexpress.com/money/", "money")
                ],
                'selectors': [
                    'h1 a', 'h2 a', 'h3 a',
                    'a[href*="/news/"]'
                ]
            }
        }
        
        for source_name, source_config in additional_sources.items():
            try:
                self.log("info", f"📊 Scraping {source_name.replace('_', ' ').title()}...")
                source_articles = 0
                
                for url, category in source_config['urls']:
                    try:
                        soup = self.get_page_content(url)
                        if not soup:
                            continue
                        
                        links = set()
                        for selector in source_config['selectors']:
                            try:
                                elements = soup.select(selector)
                                for element in elements[:5]:
                                    href = element.get('href')
                                    if href:
                                        # Handle both relative and absolute URLs
                                        if href.startswith('http'):
                                            full_url = href
                                        else:
                                            full_url = urljoin(url, href)
                                        
                                        if self.is_valid_news_url(full_url):
                                            links.add(full_url)
                            except Exception as e:
                                self.log("debug", f"Selector error for {source_name}: {e}")
                                continue
                        
                        # Process articles from this page
                        processed = 0
                        for link in list(links):
                            if processed >= 3:  # Limit per source page
                                break
                            
                            article_content = self.extract_article_content(link, source_name, category)
                            if article_content:
                                all_articles.append(article_content)
                                source_articles += 1
                                processed += 1
                                time.sleep(self.config.scraping_delay)
                        
                        time.sleep(self.config.page_delay)
                        
                    except Exception as e:
                        self.log("error", f"❌ Error scraping {source_name} {category}: {e}")
                        continue
                
                self.log("info", f"✅ {source_name.replace('_', ' ').title()}: {source_articles} articles")
                
            except Exception as e:
                self.log("error", f"❌ Error scraping {source_name}: {e}")
                continue
        
        self.log("info", f"🎉 Additional sources completed: {len(all_articles)} articles")
        return all_articles
    
    def is_recent_article(self, url: str) -> bool:
        """Enhanced check for recent articles"""
        url_lower = url.lower()
        current_year = datetime.now().year
        
        # Recent indicators
        recent_indicators = [
            str(current_year),
            str(current_year - 1),
            'latest', 'today', 'breaking', 'live', 'update',
            'new', 'fresh', 'current', '2024', '2025'
        ]
        
        # Date patterns in URL
        import re
        date_patterns = [
            rf'{current_year}',
            rf'{current_year - 1}',
            r'\d{4}\/\d{1,2}\/\d{1,2}',  # YYYY/MM/DD
            r'\d{4}-\d{1,2}-\d{1,2}'     # YYYY-MM-DD
        ]
        
        has_indicator = any(indicator in url_lower for indicator in recent_indicators)
        has_date_pattern = any(re.search(pattern, url) for pattern in date_patterns)
        
        return has_indicator or has_date_pattern
    
    def is_valid_news_url(self, url: str) -> bool:
        """Enhanced validation for news URLs"""
        url_lower = url.lower()
        
        # Valid indicators
        valid_indicators = [
            'news', 'article', 'story', 'market', 'economy', 
            'business', 'finance', 'companies', 'industry',
            'politics', 'india', 'world', 'breaking'
        ]
        
        # Invalid indicators
        invalid_indicators = [
            'video', 'photo', 'gallery', 'podcast', 'advertisement',
            'subscribe', 'login', 'register', 'privacy', 'terms',
            'contact', 'about', 'careers', 'advertise', 'rss',
            'sitemap', 'archive', 'tags', 'category'
        ]
        
        has_valid = any(indicator in url_lower for indicator in valid_indicators)
        has_invalid = any(indicator in url_lower for indicator in invalid_indicators)
        
        # Additional checks
        is_long_enough = len(url) > 30
        is_not_homepage = url.count('/') > 3
        
        return has_valid and not has_invalid and is_long_enough and is_not_homepage
    
    def extract_article_content(self, url: str, source: str, category: str = "general") -> Optional[Dict]:
        """Enhanced article content extraction with multiple fallbacks"""
        soup = self.get_page_content(url)
        if not soup:
            return None
        
        try:
            # Enhanced title extraction
            title = self.extract_title(soup)
            if not title or len(title) < 10:
                self.log("debug", f"Title too short or missing for {url}")
                return None
            
            # Enhanced content extraction
            content = self.extract_content(soup)
            if not content or len(content) < self.config.min_content_length:
                self.log("debug", f"Content too short for {url}: {len(content) if content else 0} chars")
                return None
            
            # Check for duplicates
            content_hash = hashlib.md5((title + content).encode()).hexdigest()
            if self.is_duplicate(url, content_hash):
                self.stats['duplicates_found'] += 1
                return None
            
            # Calculate metrics
            word_count = len(content.split())
            reading_time = max(1, word_count // 200)  # Approximate reading time
            
            # Extract tags/keywords
            tags = self.extract_tags(title, content)
            
            self.stats['articles_processed'] += 1
            
            return {
                'url': url,
                'title': title,
                'content': content,
                'source': source,
                'category': category,
                'content_hash': content_hash,
                'word_count': word_count,
                'reading_time': reading_time,
                'tags': ', '.join(tags) if tags else None
            }
            
        except Exception as e:
            self.log("error", f"❌ Error extracting content from {url}: {e}")
            return None
    
    def extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Enhanced title extraction with multiple selectors"""
        title_selectors = [
            'h1.headline', 'h1.title', 'h1.story-headline', 'h1.article-title',
            'h1.news-title', 'h1.post-title', 'h1[itemprop="headline"]',
            'h1', '.headline', '.story-headline', '.article-title',
            '.news-title', '.post-title', '[itemprop="headline"]'
        ]
        
        for selector in title_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    title = element.get_text().strip()
                    if len(title) > 10:  # Ensure meaningful title
                        # Clean title
                        title = re.sub(r'\s*\|\s*.*$', '', title)  # Remove site name after |
                        title = re.sub(r'\s*-\s*.*$', '', title)  # Remove site name after -
                        title = re.sub(r'\s+', ' ', title).strip()
                        return title
            except Exception:
                continue
        
        # Fallback to page title
        try:
            if soup.title:
                title = soup.title.get_text().strip()
                title = re.sub(r'\s*\|\s*.*$', '', title)
                title = re.sub(r'\s*-\s*.*$', '', title)
                return title
        except Exception:
            pass
        
        return None
    
    def extract_content(self, soup: BeautifulSoup) -> Optional[str]:
        """Enhanced content extraction with multiple selectors and cleaning"""
        content_selectors = [
            '[itemprop="articleBody"]',
            '.story-content', '.article-content', '.content',
            '.story-body', '.article-body', '.post-content',
            '.news-content', '.article-text', '.story-text',
            '.content-body', '.main-content', '.entry-content',
            'article .body', 'main article'
        ]
        
        content = ""
        
        # Try specific content selectors
        for selector in content_selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    for element in elements:
                        # Remove unwanted elements
                        for unwanted in element.find_all(["script", "style", "nav", "header", 
                                                         "footer", "aside", "iframe", "form",
                                                         ".advertisement", ".ad", ".social-share"]):
                            unwanted.decompose()
                        
                        text = element.get_text()
                        if len(text) > 100:  # Only substantial content
                            content += text + " "
                    
                    if content.strip():
                        break
            except Exception:
                continue
        
        # Fallback to paragraphs if no content found
        if not content.strip():
            try:
                paragraphs = soup.find_all('p')
                content = " ".join([
                    p.get_text() for p in paragraphs 
                    if len(p.get_text().strip()) > 50
                ])
            except Exception:
                pass
        
        # Clean content
        if content:
            content = re.sub(r'\s+', ' ', content).strip()
            content = re.sub(r'\n+', ' ', content)
            # Remove common footer text
            content = re.sub(r'(follow us on|subscribe to|download app).*$', '', content, flags=re.IGNORECASE)
            
        return content if content and len(content) >= self.config.min_content_length else None
    
    def extract_tags(self, title: str, content: str) -> List[str]:
        """Extract relevant tags/keywords from title and content"""
        if not NLTK_AVAILABLE:
            return []
        
        try:
            # Combine title and first part of content
            text = (title + " " + content[:500]).lower()
            
            # Tokenize and filter
            words = word_tokenize(text)
            words = [
                word for word in words 
                if word.isalnum() and len(word) > 3 and word not in self.stop_words
            ]
            
            # Count frequencies
            word_freq = Counter(words)
            
            # Get top keywords
            top_words = [word for word, count in word_freq.most_common(10) if count >= 2]
            
            return top_words[:5]  # Return top 5 tags
            
        except Exception:
            return []
    
    def is_duplicate(self, url: str, content_hash: str) -> bool:
        """Check if article is duplicate"""
        try:
            cursor = self.conn.execute(
                "SELECT id FROM articles WHERE url = ? OR content_hash = ?",
                (url, content_hash)
            )
            return cursor.fetchone() is not None
        except Exception:
            return False
    
    def summarize_openai(self, content: str) -> str:
        """Summarize using OpenAI API with enhanced prompts"""
        try:
            # Use the newer OpenAI client format
            client = openai.OpenAI(api_key=openai.api_key)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert financial news summarizer. Create concise, informative summaries of Indian financial news articles in 2-3 sentences. Focus on key facts, numbers, market impact, and implications. Use professional financial terminology."
                    },
                    {
                        "role": "user", 
                        "content": f"Summarize this financial news article:\n\n{content[:4000]}"
                    }
                ],
                max_tokens=150,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            self.log("error", f"❌ OpenAI summarization failed: {e}")
            return self.summarize_advanced_extractive(content)
    
    def summarize_huggingface(self, content: str) -> str:
        """Summarize using Hugging Face API"""
        try:
            api_url = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
            
            # Truncate content for API limits
            max_length = 1000
            truncated_content = content[:max_length] if len(content) > max_length else content
            
            payload = {"inputs": truncated_content}
            response = requests.post(api_url, headers=self.hf_headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    summary = result[0].get('summary_text', '')
                    if summary:
                        return summary
            
            self.log("warning", f"⚠️ Hugging Face API issue: {response.status_code}")
            return self.summarize_advanced_extractive(content)
            
        except Exception as e:
            self.log("error", f"❌ Hugging Face summarization failed: {e}")
            return self.summarize_advanced_extractive(content)
    
    def summarize_advanced_extractive(self, content: str) -> str:
        """Advanced extractive summarization with sentence scoring"""
        if not NLTK_AVAILABLE:
            return self.summarize_simple_extractive(content)
        
        try:
            sentences = sent_tokenize(content)
            if len(sentences) <= 3:
                return content
            
            # Calculate word frequencies
            words = word_tokenize(content.lower())
            words = [word for word in words if word.isalnum() and word not in self.stop_words]
            
            word_freq = Counter(words)
            max_freq = max(word_freq.values()) if word_freq else 1
            
            # Normalize frequencies
            for word in word_freq:
                word_freq[word] = word_freq[word] / max_freq
            
            # Score sentences
            sentence_scores = {}
            for i, sentence in enumerate(sentences):
                words_in_sentence = word_tokenize(sentence.lower())
                words_in_sentence = [word for word in words_in_sentence if word.isalnum()]
                
                if len(words_in_sentence) > 0:
                    score = sum(word_freq.get(word, 0) for word in words_in_sentence)
                    
                    # Position-based scoring
                    if i < 3:  # First 3 sentences
                        score *= 1.5
                    elif i >= len(sentences) - 2:  # Last 2 sentences
                        score *= 1.2
                    
                    # Length-based scoring
                    sentence_length = len(words_in_sentence)
                    if sentence_length < 5:
                        score *= 0.5
                    elif sentence_length > 30:
                        score *= 0.8
                    
                    sentence_scores[i] = score / len(words_in_sentence)
            
            # Select top sentences
            num_sentences = min(3, max(2, len(sentences) // 8))
            top_sentences = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)[:num_sentences]
            summary_sentences = [sentences[i] for i, _ in sorted(top_sentences)]
            
            return ' '.join(summary_sentences)
            
        except Exception as e:
            self.log("error", f"❌ Advanced extractive summarization failed: {e}")
            return self.summarize_simple_extractive(content)
    
    def summarize_simple_extractive(self, content: str) -> str:
        """Simple fallback summarization"""
        sentences = re.split(r'[.!?]+', content)
        summary_sentences = []
        
        for sentence in sentences[:7]:
            sentence = sentence.strip()
            if 30 < len(sentence) < 200:  # Good length sentences
                summary_sentences.append(sentence)
                if len(summary_sentences) >= 3:
                    break
        
        return '. '.join(summary_sentences) + '.' if summary_sentences else content[:300] + "..."
    
    def summarize_article(self, content: str) -> str:
        """Main summarization method with fallbacks"""
        if self.use_openai:
            return self.summarize_openai(content)
        elif self.use_huggingface:
            return self.summarize_huggingface(content)
        else:
            return self.summarize_advanced_extractive(content)
    
    def save_article(self, article: Dict, summary: str):
        """Save article to database with enhanced fields"""
        try:
            self.conn.execute('''
                INSERT INTO articles (
                    url, title, content, summary, source, category,
                    content_hash, word_count, reading_time, tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                article['url'],
                article['title'],
                article['content'],
                summary,
                article['source'],
                article['category'],
                article['content_hash'],
                article['word_count'],
                article['reading_time'],
                article.get('tags')
            ))
            self.conn.commit()
            self.log("debug", f"💾 Saved: {article['title'][:50]}...")
        except sqlite3.IntegrityError:
            self.log("debug", f"🔄 Duplicate skipped: {article['url']}")
        except Exception as e:
            self.log("error", f"❌ Database save error: {e}")
    
    def run_complete_scraping_cycle(self) -> Dict:
        """Run complete integrated scraping cycle - ENHANCED with blocking detection"""
        start_time = datetime.now()
        self.log("info", f"🚀 Starting complete news scraping cycle at {start_time}")
        
        # Reset stats
        self.stats.update({
            'total_requests': 0,
            'successful_scrapes': 0,
            'failed_scrapes': 0,
            'articles_processed': 0,
            'duplicates_found': 0,
            'blocked_sites': 0
        })
        
        results = {
            'livemint': [],
            'moneycontrol': [],
            'additional_sources': [],
            'total_new_articles': 0,
            'processing_time': 0,
            'timestamp': start_time.isoformat(),
            'stats': {},
            'summarization_method': self.summarization_method
        }
        
        try:
            # Enhanced LiveMint scraping
            livemint_articles = self.scrape_livemint_enhanced()
            for article in livemint_articles:
                try:
                    summary = self.summarize_article(article['content'])
                    self.save_article(article, summary)
                    results['livemint'].append({
                        'title': article['title'],
                        'url': article['url'],
                        'summary': summary,
                        'category': article['category'],
                        'word_count': article['word_count'],
                        'reading_time': article['reading_time'],
                        'tags': article.get('tags')
                    })
                except Exception as e:
                    self.log("error", f"❌ Error processing LiveMint article: {e}")
            
            # Enhanced MoneyControl scraping (with blocking handling)
            moneycontrol_articles = self.scrape_moneycontrol_enhanced()
            for article in moneycontrol_articles:
                try:
                    summary = self.summarize_article(article['content'])
                    self.save_article(article, summary)
                    results['moneycontrol'].append({
                        'title': article['title'],
                        'url': article['url'],
                        'summary': summary,
                        'category': article['category'],
                        'word_count': article['word_count'],
                        'reading_time': article['reading_time'],
                        'tags': article.get('tags')
                    })
                except Exception as e:
                    self.log("error", f"❌ Error processing MoneyControl article: {e}")
            
            # Additional sources scraping
            additional_articles = self.scrape_additional_sources()
            for article in additional_articles:
                try:
                    summary = self.summarize_article(article['content'])
                    self.save_article(article, summary)
                    results['additional_sources'].append({
                        'title': article['title'],
                        'url': article['url'],
                        'summary': summary,
                        'source': article['source'],
                        'category': article['category'],
                        'word_count': article['word_count'],
                        'reading_time': article['reading_time'],
                        'tags': article.get('tags')
                    })
                except Exception as e:
                    self.log("error", f"❌ Error processing additional source article: {e}")
            
            # Calculate final results
            results['total_new_articles'] = (
                len(results['livemint']) + 
                len(results['moneycontrol']) + 
                len(results['additional_sources'])
            )
            
            end_time = datetime.now()
            results['processing_time'] = (end_time - start_time).total_seconds()
            results['stats'] = self.stats.copy()
            
            # Save scraping statistics
            self.save_scraping_stats(results)
            
            # ENHANCED: Report blocking statistics
            success_rate = (self.stats['successful_scrapes'] / max(1, self.stats['total_requests']) * 100)
            self.log("info", f"🎉 Scraping cycle completed! Found {results['total_new_articles']} new articles in {results['processing_time']:.1f}s")
            self.log("info", f"📊 Success rate: {success_rate:.1f}%")
            if self.stats['blocked_sites'] > 0:
                self.log("warning", f"🚫 Blocked sites encountered: {self.stats['blocked_sites']}")
            
            return results
            
        except Exception as e:
            self.log("error", f"❌ Critical error in scraping cycle: {e}")
            return results
    
    def save_scraping_stats(self, results: Dict):
        """Save scraping statistics to database"""
        try:
            sources_scraped = ['livemint', 'moneycontrol'] + list(set([
                article['source'] for article in results['additional_sources']
            ]))
            
            success_rate = (
                self.stats['successful_scrapes'] / max(1, self.stats['total_requests']) * 100
            )
            
            self.conn.execute('''
                INSERT INTO scraping_stats (
                    total_articles, processing_time, sources_scraped, success_rate
                ) VALUES (?, ?, ?, ?)
            ''', (
                results['total_new_articles'],
                results['processing_time'],
                ', '.join(sources_scraped),
                success_rate
            ))
            self.conn.commit()
        except Exception as e:
            self.log("error", f"❌ Error saving stats: {e}")
    
    def get_recent_summaries(self, hours: int = 24, source: str = None, category: str = None) -> List[Dict]:
        """Get recent articles with optional filtering"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        query = '''
            SELECT title, summary, source, category, url, scraped_at, 
                   word_count, reading_time, tags
            FROM articles WHERE scraped_at > ?
        '''
        params = [cutoff_time]
        
        if source:
            query += ' AND source = ?'
            params.append(source)
        
        if category:
            query += ' AND category = ?'
            params.append(category)
        
        query += ' ORDER BY scraped_at DESC'
        
        try:
            cursor = self.conn.execute(query, params)
            return [{
                'title': row[0],
                'summary': row[1],
                'source': row[2],
                'category': row[3],
                'url': row[4],
                'scraped_at': row[5],
                'word_count': row[6],
                'reading_time': row[7],
                'tags': row[8]
            } for row in cursor.fetchall()]
        except Exception as e:
            self.log("error", f"❌ Error getting recent summaries: {e}")
            return []
    
    def generate_comprehensive_report(self, hours: int = 24) -> str:
        """Generate comprehensive news report with statistics"""
        recent_articles = self.get_recent_summaries(hours)
        
        if not recent_articles:
            return f"📰 No new articles found in the last {hours} hours."
        
        report = f"📰 COMPREHENSIVE NEWS REPORT\n"
        report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"Period: Last {hours} hours\n"
        report += "=" * 80 + "\n\n"
        
        # Statistics
        total_articles = len(recent_articles)
        sources = {}
        categories = {}
        total_reading_time = 0
        
        for article in recent_articles:
            source = article['source']
            category = article['category']
            
            sources[source] = sources.get(source, 0) + 1
            categories[category] = categories.get(category, 0) + 1
            total_reading_time += article.get('reading_time', 0)
        
        report += f"📊 SUMMARY STATISTICS\n"
        report += f"{'='*40}\n"
        report += f"Total Articles: {total_articles}\n"
        report += f"Total Reading Time: {total_reading_time} minutes\n"
        report += f"Average Article Length: {total_reading_time/total_articles:.1f} minutes\n\n"
        
        report += f"Sources Distribution:\n"
        for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_articles) * 100
            report += f"  • {source.replace('_', ' ').title()}: {count} articles ({percentage:.1f}%)\n"
        
        report += f"\nCategories Distribution:\n"
        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_articles) * 100
            report += f"  • {category.title()}: {count} articles ({percentage:.1f}%)\n"
        
        report += "\n" + "="*80 + "\n\n"
        
        # Group articles by source
        sources_grouped = {}
        for article in recent_articles:
            source = article['source']
            if source not in sources_grouped:
                sources_grouped[source] = []
            sources_grouped[source].append(article)
        
        # Generate detailed sections
        for source, articles in sources_grouped.items():
            source_title = source.replace('_', ' ').title()
            report += f"📈 {source_title} ({len(articles)} articles)\n"
            report += f"{'='*50}\n"
            
            for i, article in enumerate(articles, 1):
                report += f"\n{i}. {article['title']}\n"
                report += f"   📂 Category: {article['category'].title()}\n"
                report += f"   ⏱️  Reading Time: {article['reading_time']} min | Words: {article['word_count']}\n"
                if article['tags']:
                    report += f"   🏷️  Tags: {article['tags']}\n"
                report += f"   📝 Summary: {article['summary']}\n"
                report += f"   🔗 URL: {article['url']}\n"
        
        report += "\n" + "="*80 + "\n"
        report += f"Report generated by Integrated News Agent (Fixed v2.1)\n"
        report += f"Summarization: {self.summarization_method}\n"
        
        return report
    
    def export_to_json(self, hours: int = 24, filename: str = None) -> str:
        """Export recent articles to JSON"""
        articles = self.get_recent_summaries(hours)
        
        if not filename:
            filename = f"news_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Create exports directory
        Path("exports").mkdir(exist_ok=True)
        filepath = Path("exports") / filename
        
        export_data = {
            'export_info': {
                'timestamp': datetime.now().isoformat(),
                'total_articles': len(articles),
                'period_hours': hours,
                'summarization_method': self.summarization_method,
                'agent_version': '2.1-fixed'
            },
            'articles': articles,
            'statistics': {
                'sources': {},
                'categories': {},
                'total_reading_time': sum(a.get('reading_time', 0) for a in articles)
            }
        }
        
        # Calculate statistics
        for article in articles:
            source = article['source']
            category = article['category']
            export_data['statistics']['sources'][source] = export_data['statistics']['sources'].get(source, 0) + 1
            export_data['statistics']['categories'][category] = export_data['statistics']['categories'].get(category, 0) + 1
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        self.log("info", f"📁 Exported {len(articles)} articles to {filepath}")
        return str(filepath)
    
    def cleanup_old_articles(self, days: int = 30) -> int:
        """Clean up old articles"""
        cutoff_date = datetime.now() - timedelta(days=days)
        try:
            cursor = self.conn.execute(
                "DELETE FROM articles WHERE scraped_at < ?",
                (cutoff_date,)
            )
            deleted_count = cursor.rowcount
            self.conn.commit()
            
            self.log("info", f"🧹 Cleaned up {deleted_count} articles older than {days} days")
            return deleted_count
        except Exception as e:
            self.log("error", f"❌ Cleanup error: {e}")
            return 0
    
    def get_trending_topics(self, hours: int = 24, limit: int = 15) -> List[Dict]:
        """Enhanced trending topics analysis"""
        if not NLTK_AVAILABLE:
            return []
        
        articles = self.get_recent_summaries(hours)
        if not articles:
            return []
        
        try:
            # Extract and analyze text
            all_text = []
            for article in articles:
                text = (article['title'] + ' ' + article['summary']).lower()
                words = word_tokenize(text)
                words = [
                    word for word in words 
                    if word.isalnum() and len(word) > 3 and word not in self.stop_words
                ]
                all_text.extend(words)
            
            # Count frequencies
            word_freq = Counter(all_text)
            trending = []
            
            total_articles = len(articles)
            for word, count in word_freq.most_common(limit * 2):  # Get more to filter
                if count >= 2:  # Minimum frequency
                    percentage = (count / total_articles) * 100
                    trending.append({
                        'topic': word.title(),
                        'frequency': count,
                        'percentage': round(percentage, 1),
                        'relevance_score': count * (len(word) / 10)  # Favor longer, more specific terms
                    })
            
            # Sort by relevance and return top results
            trending.sort(key=lambda x: x['relevance_score'], reverse=True)
            return trending[:limit]
            
        except Exception as e:
            self.log("error", f"❌ Trending topics analysis failed: {e}")
            return []
    
    def close(self):
        """Clean shutdown"""
        try:
            if hasattr(self, 'conn'):
                self.conn.close()
            self.log("info", "🔒 Database connection closed")
        except Exception as e:
            self.log("error", f"❌ Error during shutdown: {e}")

# Scheduler class for automated operation
class EnhancedNewsScheduler:
    """Enhanced scheduler with better error handling and reporting"""
    
    def __init__(self, agent: IntegratedNewsAgent):
        self.agent = agent
        self.is_running = False
        self.run_count = 0
        self.last_run_time = None
        self.last_run_articles = 0
    
    def start_scheduler(self, interval_hours: int = 2, max_runs: int = None):
        """Start enhanced scheduled news scraping"""
        schedule.every(interval_hours).hours.do(self.scheduled_job)
        self.is_running = True
        
        print(f"📅 Enhanced News Scheduler Started")
        print(f"⏰ Running every {interval_hours} hours")
        if max_runs:
            print(f"🔢 Maximum runs: {max_runs}")
        print(f"🛑 Press Ctrl+C to stop")
        print("=" * 50)
        
        try:
            while self.is_running:
                schedule.run_pending()
                
                # Stop if max runs reached
                if max_runs and self.run_count >= max_runs:
                    print(f"\n✅ Maximum runs ({max_runs}) completed. Stopping scheduler.")
                    break
                
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            print(f"\n🛑 Scheduler stopped by user after {self.run_count} runs")
        finally:
            self.is_running = False
    
    def scheduled_job(self):
        """Enhanced scheduled job with better reporting"""
        self.run_count += 1
        run_start = datetime.now()
        
        print(f"\n{'='*60}")
        print(f"🔄 SCHEDULED RUN #{self.run_count}")
        print(f"⏰ Started: {run_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        try:
            # Run scraping cycle
            results = self.agent.run_complete_scraping_cycle()
            
            # Update tracking
            self.last_run_time = run_start
            self.last_run_articles = results['total_new_articles']
            
            # Print summary
            print(f"\n📊 RUN #{self.run_count} SUMMARY:")
            print(f"   🆕 New Articles: {results['total_new_articles']}")
            print(f"   ⏱️  Processing Time: {results['processing_time']:.1f}s")
            print(f"   📝 Summarization: {results['summarization_method']}")
            print(f"   📈 Success Rate: {results['stats']['successful_scrapes']}/{results['stats']['total_requests']}")
            
            # Show blocking info
            if results['stats']['blocked_sites'] > 0:
                print(f"   🚫 Blocked Sites: {results['stats']['blocked_sites']}")
            
            if results['total_new_articles'] > 0:
                print(f"   📰 LiveMint: {len(results['livemint'])}")
                print(f"   💰 MoneyControl: {len(results['moneycontrol'])}")
                print(f"   📊 Others: {len(results['additional_sources'])}")
                
                # Auto-export if significant articles found
                if results['total_new_articles'] >= 10:
                    export_file = self.agent.export_to_json(
                        hours=2, 
                        filename=f"scheduled_export_run_{self.run_count}_{run_start.strftime('%Y%m%d_%H%M')}.json"
                    )
                    print(f"   💾 Auto-exported: {export_file}")
            
            print(f"   ✅ Next run in {schedule.jobs[0].interval} hours")
            
        except Exception as e:
            print(f"   ❌ Error in scheduled run: {e}")
            self.agent.log("error", f"Scheduled run #{self.run_count} failed: {e}")
        
        print(f"{'='*60}")

# Main execution function
def main():
    """Enhanced main function with interactive options - FIXED VERSION"""
    print("🤖 INTEGRATED NEWS SCRAPING AGENT v2.1 - FIXED")
    print("=" * 60)
    print("🌍 Sources: LiveMint, MoneyControl*, Economic Times, Business Standard, Financial Express")
    print("🧠 AI Summarization: OpenAI, Hugging Face, Local")
    print("📊 Features: Trending Analysis, Reports, Exports, Scheduling")
    print("🛠️ FIXES: Updated selectors, blocking detection, better error handling")
    print("*MoneyControl may be blocked (handled gracefully)")
    print("=" * 60)
    
    # Configuration with improved settings
    config = NewsConfig(
        max_articles_per_source=30,
        max_articles_per_page=5,
        scraping_delay=2.0,  # Increased
        page_delay=3.0,      # Increased
        timeout=15,
        enable_logging=True
    )
    
    # Get API keys from environment or user input
    openai_key = os.getenv('OPENAI_API_KEY')
    hf_key = os.getenv('HUGGINGFACE_API_KEY')
    
    if not openai_key and not hf_key:
        print("\n🔑 API KEY SETUP:")
        print("1. No API keys found in environment")
        print("2. You can:")
        print("   a) Use local summarization (free)")
        print("   b) Enter OpenAI API key")
        print("   c) Enter Hugging Face API key")
        
        choice = input("\nChoose (a/b/c) [default: a]: ").lower().strip()
        
        if choice == 'b':
            openai_key = input("Enter OpenAI API key: ").strip() or None
        elif choice == 'c':
            hf_key = input("Enter Hugging Face API key: ").strip() or None
    
    # Initialize agent
    print("\n🚀 Initializing Fixed Integrated News Agent...")
    try:
        agent = IntegratedNewsAgent(
            openai_api_key=openai_key,
            huggingface_api_key=hf_key,
            config=config
        )
        print("✅ Agent initialized successfully!")
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        return
    
    try:
        # Execution mode selection
        print("\n⚙️ EXECUTION MODE:")
        print("1. Single run (run once and exit)")
        print("2. Scheduled operation (run automatically)")
        print("3. Interactive mode (multiple options)")
        
        mode = input("\nSelect mode (1/2/3) [default: 1]: ").strip() or "1"
        
        if mode == "1":
            # Single run
            print("\n🔄 Starting single scraping cycle...")
            results = agent.run_complete_scraping_cycle()
            
            # Display results with blocking info
            print(f"\n{'='*60}")
            print("📊 RESULTS SUMMARY")
            print(f"{'='*60}")
            print(f"🆕 Total New Articles: {results['total_new_articles']}")
            print(f"⏱️  Processing Time: {results['processing_time']:.1f}s")
            print(f"📝 Summarization Method: {results['summarization_method']}")
            
            # Show blocking statistics
            if results['stats']['blocked_sites'] > 0:
                print(f"🚫 Blocked Sites: {results['stats']['blocked_sites']} (handled gracefully)")
            
            success_rate = (results['stats']['successful_scrapes'] / max(1, results['stats']['total_requests']) * 100)
            print(f"📈 Success Rate: {success_rate:.1f}%")
            
            if results['total_new_articles'] > 0:
                print(f"\n📰 Source Breakdown:")
                print(f"   LiveMint: {len(results['livemint'])} articles")
                print(f"   MoneyControl: {len(results['moneycontrol'])} articles")
                print(f"   Other Sources: {len(results['additional_sources'])} articles")
                
                # Show sample headlines
                print(f"\n📰 Sample Headlines:")
                count = 0
                for source_results in [results['livemint'], results['moneycontrol'], results['additional_sources']]:
                    for article in source_results[:2]:
                        if count >= 6:
                            break
                        print(f"   • {article['title'][:70]}...")
                        count += 1
                
                # Generate report
                print(f"\n📋 Generating comprehensive report...")
                report = agent.generate_comprehensive_report()
                
                # Save report
                report_file = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"✅ Report saved: {report_file}")
                
                # Export option
                export_choice = input("\n💾 Export data to JSON? (y/N): ").lower().strip()
                if export_choice == 'y':
                    export_file = agent.export_to_json()
                    print(f"✅ Data exported: {export_file}")
                
                # Trending topics
                trending = agent.get_trending_topics(hours=24, limit=10)
                if trending:
                    print(f"\n🔥 TRENDING TOPICS:")
                    for topic in trending[:8]:
                        print(f"   • {topic['topic']}: {topic['frequency']} mentions ({topic['percentage']}%)")
            else:
                print(f"\n⚠️ No articles found. This may be due to:")
                if results['stats']['blocked_sites'] > 0:
                    print(f"   • Some sites are blocking scraping ({results['stats']['blocked_sites']} blocked)")
                print(f"   • Website structure changes")
                print(f"   • Network connectivity issues")
                print(f"   • All articles might be duplicates")
            
        elif mode == "2":
            # Scheduled operation
            hours = input("\n⏰ Run every X hours [default: 2]: ").strip()
            try:
                hours = int(hours) if hours else 2
            except ValueError:
                hours = 2
            
            max_runs = input("🔢 Maximum runs (empty for unlimited): ").strip()
            try:
                max_runs = int(max_runs) if max_runs else None
            except ValueError:
                max_runs = None
            
            # Run initial cycle
            print(f"\n🚀 Running initial scraping cycle...")
            initial_results = agent.run_complete_scraping_cycle()
            print(f"✅ Initial run completed: {initial_results['total_new_articles']} articles")
            
            # Start scheduler
            scheduler = EnhancedNewsScheduler(agent)
            scheduler.start_scheduler(interval_hours=hours, max_runs=max_runs)
            
        elif mode == "3":
            # Interactive mode
            while True:
                print(f"\n{'='*50}")
                print("🎛️ INTERACTIVE MODE - FIXED VERSION")
                print(f"{'='*50}")
                print("1. Run scraping cycle")
                print("2. Generate report")
                print("3. Export data")
                print("4. Show trending topics")
                print("5. Database statistics")
                print("6. Cleanup old articles")
                print("7. Start scheduled operation")
                print("8. Exit")
                
                choice = input("\nSelect option (1-8): ").strip()
                
                if choice == "1":
                    results = agent.run_complete_scraping_cycle()
                    print(f"✅ Found {results['total_new_articles']} new articles")
                    if results['stats']['blocked_sites'] > 0:
                        print(f"🚫 {results['stats']['blocked_sites']} sites were blocked")
                
                elif choice == "2":
                    hours = input("Report period in hours [24]: ").strip()
                    hours = int(hours) if hours and hours.isdigit() else 24
                    report = agent.generate_comprehensive_report(hours)
                    print(f"\n{report}")
                    
                    save = input("\nSave report to file? (y/N): ").lower().strip()
                    if save == 'y':
                        filename = f"interactive_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(report)
                        print(f"✅ Saved: {filename}")
                
                elif choice == "3":
                    hours = input("Export period in hours [24]: ").strip()
                    hours = int(hours) if hours and hours.isdigit() else 24
                    export_file = agent.export_to_json(hours)
                    print(f"✅ Exported: {export_file}")
                
                elif choice == "4":
                    trending = agent.get_trending_topics(hours=24, limit=15)
                    if trending:
                        print(f"\n🔥 TRENDING TOPICS (Last 24 hours):")
                        for i, topic in enumerate(trending, 1):
                            print(f"{i:2}. {topic['topic']}: {topic['frequency']} mentions ({topic['percentage']}%)")
                    else:
                        print("No trending topics available")
                
                elif choice == "5":
                    recent_articles = agent.get_recent_summaries(24)
                    total_articles = len(agent.conn.execute("SELECT id FROM articles").fetchall())
                    print(f"\n📊 DATABASE STATISTICS:")
                    print(f"   Total articles in database: {total_articles}")
                    print(f"   Articles in last 24h: {len(recent_articles)}")
                    if recent_articles:
                        sources = {}
                        for article in recent_articles:
                            sources[article['source']] = sources.get(article['source'], 0) + 1
                        print(f"   Recent sources: {', '.join([f'{k}({v})' for k, v in sources.items()])}")
                
                elif choice == "6":
                    days = input("Delete articles older than X days [30]: ").strip()
                    days = int(days) if days and days.isdigit() else 30
                    deleted = agent.cleanup_old_articles(days)
                    print(f"✅ Cleaned up {deleted} old articles")
                
                elif choice == "7":
                    hours = input("Run every X hours [2]: ").strip()
                    hours = int(hours) if hours and hours.isdigit() else 2
                    scheduler = EnhancedNewsScheduler(agent)
                    scheduler.start_scheduler(interval_hours=hours)
                
                elif choice == "8":
                    print("👋 Exiting interactive mode...")
                    break
                
                else:
                    print("❌ Invalid option. Please try again.")
        
        print(f"\n🎉 Operation completed successfully!")
        
    except KeyboardInterrupt:
        print(f"\n🛑 Operation stopped by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if hasattr(agent, 'logger'):
            agent.logger.error(f"Main execution error: {e}")
    finally:
        # Cleanup
        agent.close()
        print(f"\n👋 Thanks for using the Fixed Integrated News Agent!")

if __name__ == "__main__":
    main()