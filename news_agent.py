import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
import hashlib
import sqlite3
from typing import List, Dict, Optional
import openai
import re

class NewsAgent:
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize the News Agent
        
        Args:
            openai_api_key: OpenAI API key for summarization (optional)
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Initialize database
        self.init_database()
        
        # Set up OpenAI if API key provided
        if openai_api_key:
            openai.api_key = openai_api_key
            self.use_openai = True
        else:
            self.use_openai = False
            print("Note: No OpenAI API key provided. Using extractive summarization.")
    
    def init_database(self):
        """Initialize SQLite database to track processed articles"""
        self.conn = sqlite3.connect('news_agent.db')
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY,
                url TEXT UNIQUE,
                title TEXT,
                summary TEXT,
                source TEXT,
                scraped_at TIMESTAMP,
                content_hash TEXT
            )
        ''')
        self.conn.commit()
    
    def get_page_content(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse webpage content"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def scrape_livemint(self) -> List[Dict]:
        """Scrape latest news from LiveMint"""
        base_url = "https://www.livemint.com"
        soup = self.get_page_content(base_url)
        
        if not soup:
            return []
        
        articles = []
        
        # Look for article links (LiveMint specific selectors)
        article_selectors = [
            'h2 a[href*="/news/"]',
            'h3 a[href*="/news/"]',
            '.headline a',
            '.listingNew a[href*="/news/"]'
        ]
        
        links = set()
        for selector in article_selectors:
            elements = soup.select(selector)
            for element in elements[:10]:  # Limit to recent articles
                href = element.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    links.add(full_url)
        
        for link in list(links)[:15]:  # Process top 15 articles
            article_content = self.extract_article_content(link, 'livemint')
            if article_content:
                articles.append(article_content)
                time.sleep(1)  # Be respectful to the server
        
        return articles
    
    def scrape_moneycontrol(self) -> List[Dict]:
        """Scrape latest news from MoneyControl"""
        base_url = "https://www.moneycontrol.com"
        soup = self.get_page_content(f"{base_url}/news/")
        
        if not soup:
            return []
        
        articles = []
        
        # MoneyControl specific selectors
        article_selectors = [
            'h2 a[href*="/news/"]',
            'h3 a[href*="/news/"]',
            '.news_list a',
            '.list_item a[href*="/news/"]'
        ]
        
        links = set()
        for selector in article_selectors:
            elements = soup.select(selector)
            for element in elements[:10]:
                href = element.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    links.add(full_url)
        
        for link in list(links)[:15]:
            article_content = self.extract_article_content(link, 'moneycontrol')
            if article_content:
                articles.append(article_content)
                time.sleep(1)
        
        return articles
    
    def extract_article_content(self, url: str, source: str) -> Optional[Dict]:
        """Extract title and content from article URL"""
        soup = self.get_page_content(url)
        if not soup:
            return None
        
        try:
            # Generic selectors that work for most news sites
            title_selectors = ['h1', '.headline', '.story-headline', 'title']
            content_selectors = [
                '.story-content', '.article-content', '.content', 
                '.story-body', 'article', '.post-content'
            ]
            
            # Extract title
            title = None
            for selector in title_selectors:
                element = soup.select_one(selector)
                if element:
                    title = element.get_text().strip()
                    break
            
            if not title:
                title = soup.title.get_text().strip() if soup.title else "Unknown Title"
            
            # Extract content
            content = ""
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    for element in elements:
                        # Remove script and style elements
                        for script in element(["script", "style"]):
                            script.decompose()
                        content += element.get_text() + " "
                    break
            
            # If no content found, try getting all paragraphs
            if not content.strip():
                paragraphs = soup.find_all('p')
                content = " ".join([p.get_text() for p in paragraphs])
            
            # Clean and validate content
            content = re.sub(r'\s+', ' ', content).strip()
            
            if len(content) < 100:  # Skip if too short
                return None
            
            # Check if already processed
            content_hash = hashlib.md5(content.encode()).hexdigest()
            cursor = self.conn.execute(
                "SELECT id FROM articles WHERE url = ? OR content_hash = ?", 
                (url, content_hash)
            )
            if cursor.fetchone():
                return None  # Already processed
            
            return {
                'url': url,
                'title': title,
                'content': content,
                'source': source,
                'content_hash': content_hash
            }
            
        except Exception as e:
            print(f"Error extracting content from {url}: {e}")
            return None
    
    def summarize_openai(self, content: str) -> str:
        """Summarize content using OpenAI API"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a news summarizer. Create concise, informative summaries of news articles in 2-3 sentences."},
                    {"role": "user", "content": f"Summarize this news article:\n\n{content[:4000]}"}
                ],
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error with OpenAI summarization: {e}")
            return self.summarize_extractive(content)
    
    def summarize_extractive(self, content: str) -> str:
        """Simple extractive summarization (first few sentences)"""
        sentences = re.split(r'[.!?]+', content)
        # Take first 2-3 substantial sentences
        summary_sentences = []
        for sentence in sentences[:5]:
            sentence = sentence.strip()
            if len(sentence) > 50:  # Skip very short sentences
                summary_sentences.append(sentence)
                if len(summary_sentences) >= 3:
                    break
        
        return '. '.join(summary_sentences) + '.' if summary_sentences else content[:200] + "..."
    
    def summarize_article(self, content: str) -> str:
        """Summarize article content"""
        if self.use_openai:
            return self.summarize_openai(content)
        else:
            return self.summarize_extractive(content)
    
    def save_article(self, article: Dict, summary: str):
        """Save article and summary to database"""
        try:
            self.conn.execute('''
                INSERT INTO articles (url, title, summary, source, scraped_at, content_hash)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                article['url'],
                article['title'],
                summary,
                article['source'],
                datetime.now(),
                article['content_hash']
            ))
            self.conn.commit()
        except sqlite3.IntegrityError:
            pass  # Article already exists
    
    def run_scraping_cycle(self) -> Dict:
        """Run a complete scraping cycle for all sources"""
        print(f"Starting news scraping cycle at {datetime.now()}")
        
        results = {
            'livemint': [],
            'moneycontrol': [],
            'total_new_articles': 0
        }
        
        # Scrape LiveMint
        print("Scraping LiveMint...")
        livemint_articles = self.scrape_livemint()
        for article in livemint_articles:
            summary = self.summarize_article(article['content'])
            self.save_article(article, summary)
            results['livemint'].append({
                'title': article['title'],
                'url': article['url'],
                'summary': summary
            })
        
        # Scrape MoneyControl
        print("Scraping MoneyControl...")
        moneycontrol_articles = self.scrape_moneycontrol()
        for article in moneycontrol_articles:
            summary = self.summarize_article(article['content'])
            self.save_article(article, summary)
            results['moneycontrol'].append({
                'title': article['title'],
                'url': article['url'],
                'summary': summary
            })
        
        results['total_new_articles'] = len(results['livemint']) + len(results['moneycontrol'])
        print(f"Scraping cycle completed. Found {results['total_new_articles']} new articles.")
        
        return results
    
    def get_recent_summaries(self, hours: int = 24) -> List[Dict]:
        """Get recent article summaries from database"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cursor = self.conn.execute('''
            SELECT title, summary, source, url, scraped_at 
            FROM articles 
            WHERE scraped_at > ? 
            ORDER BY scraped_at DESC
        ''', (cutoff_time,))
        
        return [{
            'title': row[0],
            'summary': row[1],
            'source': row[2],
            'url': row[3],
            'scraped_at': row[4]
        } for row in cursor.fetchall()]
    
    def generate_daily_report(self) -> str:
        """Generate a daily news report"""
        recent_articles = self.get_recent_summaries(24)
        
        if not recent_articles:
            return "No new articles found in the last 24 hours."
        
        report = f"Daily News Report - {datetime.now().strftime('%Y-%m-%d')}\n"
        report += "=" * 50 + "\n\n"
        
        # Group by source
        livemint_articles = [a for a in recent_articles if a['source'] == 'livemint']
        moneycontrol_articles = [a for a in recent_articles if a['source'] == 'moneycontrol']
        
        if livemint_articles:
            report += "LiveMint News:\n" + "-" * 20 + "\n"
            for article in livemint_articles:
                report += f"• {article['title']}\n"
                report += f"  {article['summary']}\n"
                report += f"  Link: {article['url']}\n\n"
        
        if moneycontrol_articles:
            report += "MoneyControl News:\n" + "-" * 20 + "\n"
            for article in moneycontrol_articles:
                report += f"• {article['title']}\n"
                report += f"  {article['summary']}\n"
                report += f"  Link: {article['url']}\n\n"
        
        return report

# Example usage
def main():
    # Initialize the agent (add your OpenAI API key for better summaries)
    agent = NewsAgent(openai_api_key="your_openai_api_key_here")  # Optional
    
    # Run a scraping cycle
    results = agent.run_scraping_cycle()
    
    # Print results
    print("\n" + "="*60)
    print("SCRAPING RESULTS")
    print("="*60)
    
    print(f"\nLiveMint Articles ({len(results['livemint'])}):")
    for article in results['livemint']:
        print(f"\n• {article['title']}")
        print(f"  Summary: {article['summary']}")
        print(f"  URL: {article['url']}")
    
    print(f"\nMoneyControl Articles ({len(results['moneycontrol'])}):")
    for article in results['moneycontrol']:
        print(f"\n• {article['title']}")
        print(f"  Summary: {article['summary']}")
        print(f"  URL: {article['url']}")
    
    # Generate daily report
    print("\n" + "="*60)
    print("DAILY REPORT")
    print("="*60)
    print(agent.generate_daily_report())

if __name__ == "__main__":
    main()
