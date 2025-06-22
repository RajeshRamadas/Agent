#!/usr/bin/env python3
"""
Simplified News Scraper - Working Version
This is a streamlined version that focuses on core functionality
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse
import re

class SimpleNewsScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache'
        })
        self.articles = []
    
    def get_page(self, url, retries=3):
        """Get webpage with retry logic"""
        for attempt in range(retries):
            try:
                print(f"  📡 Fetching: {url} (attempt {attempt + 1})")
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                return BeautifulSoup(response.content, 'html.parser')
            except Exception as e:
                print(f"    ⚠️ Attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        return None
    
    def extract_article_links(self, soup, base_url):
        """Extract article links from a page"""
        links = set()
        
        # Updated selectors for 2024/2025 website structures
        selectors = [
            'a[href*="/news/"]',
            'a[href*="/story/"]', 
            'a[href*="/article/"]',
            'a[href*="/market/"]',
            'a[href*="/business/"]',
            'a[href*="/economy/"]',
            'h1 a', 'h2 a', 'h3 a',
            '.story-title a',
            '.headline a',
            '.news-item a',
            'article a'
        ]
        
        for selector in selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    href = element.get('href')
                    if href:
                        full_url = urljoin(base_url, href)
                        if self.is_valid_article_url(full_url):
                            links.add(full_url)
            except Exception as e:
                print(f"    ⚠️ Selector error: {e}")
        
        return list(links)
    
    def is_valid_article_url(self, url):
        """Check if URL looks like a news article"""
        url_lower = url.lower()
        
        # Must contain news-related paths
        valid_paths = ['news', 'story', 'article', 'market', 'business', 'economy']
        has_valid_path = any(path in url_lower for path in valid_paths)
        
        # Should not contain these
        invalid_paths = ['video', 'photo', 'gallery', 'login', 'register', 'subscribe']
        has_invalid_path = any(path in url_lower for path in invalid_paths)
        
        # Basic checks
        is_long_enough = len(url) > 40
        has_extension = url_lower.endswith(('.html', '.htm', '/')) or '?' in url
        
        return has_valid_path and not has_invalid_path and is_long_enough
    
    def extract_article_content(self, url):
        """Extract title and content from article page"""
        soup = self.get_page(url)
        if not soup:
            return None
        
        # Extract title
        title = None
        title_selectors = [
            'h1[class*="headline"]',
            'h1[class*="title"]', 
            'h1',
            '.story-headline',
            '.article-title',
            '[data-testid="headline"]'
        ]
        
        for selector in title_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    title = element.get_text().strip()
                    if len(title) > 10:
                        break
            except:
                continue
        
        if not title:
            title = soup.title.get_text().strip() if soup.title else "No title"
        
        # Clean title
        title = re.sub(r'\s*[-|]\s*.*$', '', title)  # Remove site name
        title = re.sub(r'\s+', ' ', title).strip()
        
        # Extract content
        content = ""
        content_selectors = [
            '[data-testid="article-body"]',
            '.story-content',
            '.article-content', 
            '.story-body',
            '.content',
            'article .body',
            '[itemprop="articleBody"]'
        ]
        
        for selector in content_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    # Remove unwanted elements
                    for unwanted in element.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                        unwanted.decompose()
                    content = element.get_text()
                    break
            except:
                continue
        
        # Fallback to paragraphs
        if not content:
            paragraphs = soup.find_all('p')
            content = ' '.join([p.get_text() for p in paragraphs if len(p.get_text().strip()) > 20])
        
        # Clean content
        content = re.sub(r'\s+', ' ', content).strip()
        
        if len(content) < 100:  # Too short
            return None
        
        return {
            'title': title,
            'content': content[:1000],  # Limit content length
            'url': url,
            'scraped_at': datetime.now().isoformat()
        }
    
    def scrape_livemint(self, max_articles=5):
        """Scrape LiveMint news"""
        print("📰 Scraping LiveMint...")
        
        base_urls = [
            'https://www.livemint.com',
            'https://www.livemint.com/news',
            'https://www.livemint.com/market'
        ]
        
        articles_found = 0
        for base_url in base_urls:
            if articles_found >= max_articles:
                break
                
            print(f"  🔍 Checking: {base_url}")
            soup = self.get_page(base_url)
            if not soup:
                continue
            
            links = self.extract_article_links(soup, base_url)
            print(f"    Found {len(links)} potential articles")
            
            for link in links[:3]:  # Limit per page
                if articles_found >= max_articles:
                    break
                    
                article = self.extract_article_content(link)
                if article:
                    article['source'] = 'livemint'
                    self.articles.append(article)
                    articles_found += 1
                    print(f"    ✅ Article {articles_found}: {article['title'][:50]}...")
                
                time.sleep(1)  # Be respectful
            
            time.sleep(2)
        
        return articles_found
    
    def scrape_moneycontrol(self, max_articles=5):
        """Scrape MoneyControl news"""
        print("💰 Scraping MoneyControl...")
        
        base_urls = [
            'https://www.moneycontrol.com/news/',
            'https://www.moneycontrol.com/news/business/',
            'https://www.moneycontrol.com/news/markets/'
        ]
        
        articles_found = 0
        for base_url in base_urls:
            if articles_found >= max_articles:
                break
                
            print(f"  🔍 Checking: {base_url}")
            soup = self.get_page(base_url)
            if not soup:
                continue
            
            links = self.extract_article_links(soup, base_url)
            print(f"    Found {len(links)} potential articles")
            
            for link in links[:3]:  # Limit per page
                if articles_found >= max_articles:
                    break
                    
                article = self.extract_article_content(link)
                if article:
                    article['source'] = 'moneycontrol'
                    self.articles.append(article)
                    articles_found += 1
                    print(f"    ✅ Article {articles_found}: {article['title'][:50]}...")
                
                time.sleep(1)  # Be respectful
            
            time.sleep(2)
        
        return articles_found
    
    def simple_summarize(self, content, max_sentences=3):
        """Simple extractive summarization"""
        sentences = re.split(r'[.!?]+', content)
        good_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if 20 < len(sentence) < 200:  # Good length
                good_sentences.append(sentence)
                if len(good_sentences) >= max_sentences:
                    break
        
        return '. '.join(good_sentences) + '.' if good_sentences else content[:200] + "..."
    
    def run(self):
        """Run the scraper"""
        print("🚀 Starting Simple News Scraper")
        print("=" * 50)
        
        start_time = datetime.now()
        
        # Scrape sources
        livemint_count = self.scrape_livemint(max_articles=3)
        moneycontrol_count = self.scrape_moneycontrol(max_articles=3)
        
        # Add summaries
        for article in self.articles:
            article['summary'] = self.simple_summarize(article['content'])
        
        # Results
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n{'='*50}")
        print("📊 SCRAPING RESULTS")
        print(f"{'='*50}")
        print(f"Total articles: {len(self.articles)}")
        print(f"LiveMint: {livemint_count}")
        print(f"MoneyControl: {moneycontrol_count}")
        print(f"Processing time: {duration:.1f} seconds")
        
        # Show articles
        if self.articles:
            print(f"\n📰 ARTICLES FOUND:")
            for i, article in enumerate(self.articles, 1):
                print(f"\n{i}. {article['title']}")
                print(f"   Source: {article['source']}")
                print(f"   Summary: {article['summary']}")
                print(f"   URL: {article['url']}")
        
        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"news_simple_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'scraping_info': {
                    'timestamp': start_time.isoformat(),
                    'duration_seconds': duration,
                    'total_articles': len(self.articles)
                },
                'articles': self.articles
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {filename}")
        
        return self.articles

def main():
    """Main function"""
    try:
        scraper = SimpleNewsScraper()
        articles = scraper.run()
        
        if not articles:
            print("\n❌ No articles found. This could mean:")
            print("1. Websites are blocking the scraper")
            print("2. Website structure has changed")
            print("3. Network connectivity issues")
            print("4. Run the diagnostic script first to identify issues")
        else:
            print(f"\n✅ Successfully scraped {len(articles)} articles!")
            
    except KeyboardInterrupt:
        print("\n🛑 Scraping stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Run the diagnostic script to identify the issue")

if __name__ == "__main__":
    main()