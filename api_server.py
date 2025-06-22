#!/usr/bin/env python3
"""
REST API Server for News Agent
Provides comprehensive API access to news data and agent controls
"""

import os
import json
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query, Path as PathParam
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from fastapi.responses import JSONResponse, FileResponse
    from pydantic import BaseModel, Field
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    print("⚠️ FastAPI not available. Install with: pip install fastapi uvicorn")

try:
    from integrated_news_agent import IntegratedNewsAgent, NewsConfig, EnhancedNewsScheduler
    AGENT_AVAILABLE = True
except ImportError:
    AGENT_AVAILABLE = False
    print("⚠️ integrated_news_agent.py not found")

# Pydantic models for API
class ArticleResponse(BaseModel):
    id: Optional[int] = None
    title: str
    summary: str
    url: str
    source: str
    category: str
    scraped_at: str
    word_count: int
    reading_time: int
    tags: Optional[str] = None

class TrendingTopic(BaseModel):
    topic: str
    frequency: int
    percentage: float
    relevance_score: float

class ScrapingResult(BaseModel):
    total_new_articles: int
    processing_time: float
    timestamp: str
    summarization_method: str
    livemint: List[ArticleResponse]
    moneycontrol: List[ArticleResponse]
    additional_sources: List[ArticleResponse]

class AgentConfig(BaseModel):
    max_articles_per_source: int = Field(default=25, ge=1, le=100)
    max_articles_per_page: int = Field(default=5, ge=1, le=20)
    scraping_delay: float = Field(default=1.0, ge=0.1, le=10.0)
    page_delay: float = Field(default=2.0, ge=0.5, le=20.0)
    timeout: int = Field(default=15, ge=5, le=60)
    enable_logging: bool = True

class AgentInitRequest(BaseModel):
    openai_api_key: Optional[str] = None
    huggingface_api_key: Optional[str] = None
    config: Optional[AgentConfig] = None

class SchedulerRequest(BaseModel):
    action: str = Field(..., regex="^(start|stop)$")
    interval_hours: Optional[int] = Field(default=2, ge=1, le=24)
    max_runs: Optional[int] = None

class ExportRequest(BaseModel):
    hours: int = Field(default=24, ge=1, le=168)
    format: str = Field(default="json", regex="^(json|csv)$")
    include_content: bool = False

class NewsAgentAPI:
    """FastAPI-based REST API for News Agent"""
    
    def __init__(self):
        if not FASTAPI_AVAILABLE:
            raise ImportError("FastAPI is required for API server")
        if not AGENT_AVAILABLE:
            raise ImportError("integrated_news_agent.py is required")
        
        self.app = FastAPI(
            title="News Agent API",
            description="Comprehensive API for Indian Financial News Monitoring",
            version="2.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Security
        self.security = HTTPBearer(auto_error=False)
        self.api_key = os.getenv("NEWS_AGENT_API_KEY", "")
        
        # Agent instance
        self.agent: Optional[IntegratedNewsAgent] = None
        self.scheduler: Optional[EnhancedNewsScheduler] = None
        self.scraping_in_progress = False
        self.last_scraping_result: Optional[Dict] = None
        
        # Setup routes
        self.setup_routes()
    
    def verify_api_key(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))):
        """Verify API key if required"""
        if self.api_key and (not credentials or credentials.credentials != self.api_key):
            raise HTTPException(status_code=401, detail="Invalid API key")
        return True
    
    def setup_routes(self):
        """Setup all API routes"""
        
        @self.app.get("/", tags=["General"])
        async def root():
            """API root endpoint"""
            return {
                "name": "News Agent API",
                "version": "2.0.0",
                "status": "operational",
                "timestamp": datetime.now().isoformat(),
                "agent_initialized": self.agent is not None,
                "docs": "/docs"
            }
        
        @self.app.get("/health", tags=["General"])
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "agent_status": "initialized" if self.agent else "not_initialized",
                "database_exists": os.path.exists("news_agent.db"),
                "scraping_in_progress": self.scraping_in_progress
            }
        
        @self.app.post("/agent/initialize", tags=["Agent Management"])
        async def initialize_agent(
            request: AgentInitRequest,
            _: bool = Depends(self.verify_api_key)
        ):
            """Initialize the news agent"""
            try:
                config = NewsConfig()
                if request.config:
                    config.max_articles_per_source = request.config.max_articles_per_source
                    config.max_articles_per_page = request.config.max_articles_per_page
                    config.scraping_delay = request.config.scraping_delay
                    config.page_delay = request.config.page_delay
                    config.timeout = request.config.timeout
                    config.enable_logging = request.config.enable_logging
                
                self.agent = IntegratedNewsAgent(
                    openai_api_key=request.openai_api_key,
                    huggingface_api_key=request.huggingface_api_key,
                    config=config
                )
                
                return {
                    "success": True,
                    "message": "Agent initialized successfully",
                    "summarization_method": self.agent.summarization_method,
                    "config": {
                        "max_articles_per_source": config.max_articles_per_source,
                        "scraping_delay": config.scraping_delay,
                        "timeout": config.timeout
                    }
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/agent/status", tags=["Agent Management"])
        async def get_agent_status(_: bool = Depends(self.verify_api_key)):
            """Get current agent status"""
            return {
                "initialized": self.agent is not None,
                "scraping_in_progress": self.scraping_in_progress,
                "scheduler_running": self.scheduler is not None and getattr(self.scheduler, 'is_running', False),
                "last_scraping": self.last_scraping_result,
                "summarization_method": self.agent.summarization_method if self.agent else None
            }
        
        @self.app.post("/scraping/start", tags=["Scraping Operations"])
        async def start_scraping(
            background_tasks: BackgroundTasks,
            _: bool = Depends(self.verify_api_key)
        ):
            """Start a scraping cycle"""
            if not self.agent:
                raise HTTPException(status_code=400, detail="Agent not initialized")
            
            if self.scraping_in_progress:
                raise HTTPException(status_code=409, detail="Scraping already in progress")
            
            async def run_scraping():
                self.scraping_in_progress = True
                try:
                    # Run in thread to avoid blocking
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    result = self.agent.run_complete_scraping_cycle()
                    self.last_scraping_result = {
                        "total_articles": result['total_new_articles'],
                        "processing_time": result['processing_time'],
                        "timestamp": result['timestamp'],
                        "success": True
                    }
                    
                except Exception as e:
                    self.last_scraping_result = {
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                        "success": False
                    }
                finally:
                    self.scraping_in_progress = False
            
            background_tasks.add_task(run_scraping)
            
            return {
                "success": True,
                "message": "Scraping started",
                "estimated_duration": "5-20 minutes"
            }
        
        @self.app.get("/scraping/status", tags=["Scraping Operations"])
        async def get_scraping_status(_: bool = Depends(self.verify_api_key)):
            """Get current scraping status"""
            return {
                "in_progress": self.scraping_in_progress,
                "last_result": self.last_scraping_result
            }
        
        @self.app.post("/scheduler/control", tags=["Scheduler"])
        async def control_scheduler(
            request: SchedulerRequest,
            _: bool = Depends(self.verify_api_key)
        ):
            """Start or stop the scheduler"""
            if not self.agent:
                raise HTTPException(status_code=400, detail="Agent not initialized")
            
            if request.action == "start":
                if self.scheduler and getattr(self.scheduler, 'is_running', False):
                    raise HTTPException(status_code=409, detail="Scheduler already running")
                
                def run_scheduler():
                    self.scheduler = EnhancedNewsScheduler(self.agent)
                    self.scheduler.start_scheduler(
                        interval_hours=request.interval_hours,
                        max_runs=request.max_runs
                    )
                
                threading.Thread(target=run_scheduler, daemon=True).start()
                
                return {
                    "success": True,
                    "message": f"Scheduler started (every {request.interval_hours} hours)",
                    "interval_hours": request.interval_hours,
                    "max_runs": request.max_runs
                }
            
            elif request.action == "stop":
                if self.scheduler:
                    self.scheduler.is_running = False
                    self.scheduler = None
                
                return {
                    "success": True,
                    "message": "Scheduler stopped"
                }
        
        @self.app.get("/articles", response_model=List[ArticleResponse], tags=["Data Access"])
        async def get_articles(
            hours: int = Query(default=24, ge=1, le=168, description="Hours to look back"),
            source: Optional[str] = Query(default=None, description="Filter by source"),
            category: Optional[str] = Query(default=None, description="Filter by category"),
            limit: int = Query(default=100, ge=1, le=1000, description="Maximum articles to return"),
            offset: int = Query(default=0, ge=0, description="Pagination offset"),
            _: bool = Depends(self.verify_api_key)
        ):
            """Get articles with filtering and pagination"""
            if not self.agent:
                raise HTTPException(status_code=400, detail="Agent not initialized")
            
            try:
                articles = self.agent.get_recent_summaries(hours, source, category)
                
                # Apply pagination
                paginated = articles[offset:offset + limit]
                
                return [
                    ArticleResponse(
                        title=article['title'],
                        summary=article['summary'],
                        url=article['url'],
                        source=article['source'],
                        category=article['category'],
                        scraped_at=article['scraped_at'],
                        word_count=article.get('word_count', 0),
                        reading_time=article.get('reading_time', 1),
                        tags=article.get('tags')
                    )
                    for article in paginated
                ]
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/articles/{article_id}", response_model=ArticleResponse, tags=["Data Access"])
        async def get_article(
            article_id: int = PathParam(..., description="Article ID"),
            _: bool = Depends(self.verify_api_key)
        ):
            """Get specific article by ID"""
            if not self.agent:
                raise HTTPException(status_code=400, detail="Agent not initialized")
            
            try:
                cursor = self.agent.conn.execute(
                    "SELECT * FROM articles WHERE id = ?", (article_id,)
                )
                row = cursor.fetchone()
                
                if not row:
                    raise HTTPException(status_code=404, detail="Article not found")
                
                # Map database columns to response model
                return ArticleResponse(
                    id=row[0],
                    title=row[2],
                    summary=row[4],
                    url=row[1],
                    source=row[5],
                    category=row[6] or "general",
                    scraped_at=row[7],
                    word_count=row[9] or 0,
                    reading_time=row[10] or 1,
                    tags=row[12]
                )
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/trending", response_model=List[TrendingTopic], tags=["Analytics"])
        async def get_trending_topics(
            hours: int = Query(default=24, ge=1, le=168, description="Hours to analyze"),
            limit: int = Query(default=15, ge=1, le=50, description="Number of topics"),
            _: bool = Depends(self.verify_api_key)
        ):
            """Get trending topics"""
            if not self.agent:
                raise HTTPException(status_code=400, detail="Agent not initialized")
            
            try:
                trending = self.agent.get_trending_topics(hours, limit)
                
                return [
                    TrendingTopic(
                        topic=topic['topic'],
                        frequency=topic['frequency'],
                        percentage=topic['percentage'],
                        relevance_score=topic.get('relevance_score', 0)
                    )
                    for topic in trending
                ]
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/statistics", tags=["Analytics"])
        async def get_statistics(
            hours: int = Query(default=24, ge=1, le=168, description="Hours to analyze"),
            _: bool = Depends(self.verify_api_key)
        ):
            """Get comprehensive statistics"""
            if not self.agent:
                raise HTTPException(status_code=400, detail="Agent not initialized")
            
            try:
                import sqlite3
                conn = sqlite3.connect(self.agent.config.database_path)
                
                # Basic counts
                total_articles = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
                
                cutoff_time = datetime.now() - timedelta(hours=hours)
                recent_articles = conn.execute(
                    "SELECT COUNT(*) FROM articles WHERE scraped_at > ?", 
                    (cutoff_time,)
                ).fetchone()[0]
                
                # Source distribution
                source_stats = conn.execute("""
                    SELECT source, COUNT(*) as count 
                    FROM articles 
                    WHERE scraped_at > ? 
                    GROUP BY source 
                    ORDER BY count DESC
                """, (cutoff_time,)).fetchall()
                
                # Category distribution
                category_stats = conn.execute("""
                    SELECT category, COUNT(*) as count 
                    FROM articles 
                    WHERE scraped_at > ? 
                    GROUP BY category 
                    ORDER BY count DESC
                """, (cutoff_time,)).fetchall()
                
                # Hourly distribution
                hourly_stats = conn.execute("""
                    SELECT strftime('%H', scraped_at) as hour, COUNT(*) as count
                    FROM articles
                    WHERE scraped_at > ?
                    GROUP BY strftime('%H', scraped_at)
                    ORDER BY hour
                """, (cutoff_time,)).fetchall()
                
                conn.close()
                
                return {
                    "total_articles": total_articles,
                    "recent_articles": recent_articles,
                    "analysis_period_hours": hours,
                    "source_distribution": [
                        {"source": row[0], "count": row[1]} for row in source_stats
                    ],
                    "category_distribution": [
                        {"category": row[0], "count": row[1]} for row in category_stats
                    ],
                    "hourly_distribution": [
                        {"hour": int(row[0]), "count": row[1]} for row in hourly_stats
                    ],
                    "generated_at": datetime.now().isoformat()
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/report", tags=["Reports"])
        async def generate_report(
            hours: int = Query(default=24, ge=1, le=168, description="Hours to include"),
            format: str = Query(default="json", regex="^(json|text)$", description="Report format"),
            _: bool = Depends(self.verify_api_key)
        ):
            """Generate comprehensive report"""
            if not self.agent:
                raise HTTPException(status_code=400, detail="Agent not initialized")
            
            try:
                if format == "text":
                    report = self.agent.generate_comprehensive_report(hours)
                    return {"report": report, "format": "text"}
                else:
                    articles = self.agent.get_recent_summaries(hours)
                    trending = self.agent.get_trending_topics(hours)
                    
                    return {
                        "summary": {
                            "total_articles": len(articles),
                            "analysis_period_hours": hours,
                            "generated_at": datetime.now().isoformat()
                        },
                        "articles": articles[:20],  # Top 20 articles
                        "trending_topics": trending[:10],  # Top 10 trends
                        "format": "json"
                    }
                    
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/export", tags=["Data Export"])
        async def export_data(
            request: ExportRequest,
            _: bool = Depends(self.verify_api_key)
        ):
            """Export data to file"""
            if not self.agent:
                raise HTTPException(status_code=400, detail="Agent not initialized")
            
            try:
                filename = self.agent.export_to_json(
                    hours=request.hours,
                    filename=f"api_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                
                return FileResponse(
                    path=filename,
                    filename=f"news_export_{datetime.now().strftime('%Y%m%d')}.json",
                    media_type="application/json"
                )
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.delete("/articles/cleanup", tags=["Data Management"])
        async def cleanup_articles(
            days: int = Query(default=30, ge=1, le=365, description="Delete articles older than X days"),
            _: bool = Depends(self.verify_api_key)
        ):
            """Clean up old articles"""
            if not self.agent:
                raise HTTPException(status_code=400, detail="Agent not initialized")
            
            try:
                deleted_count = self.agent.cleanup_old_articles(days)
                
                return {
                    "success": True,
                    "deleted_count": deleted_count,
                    "days": days,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/sources", tags=["Configuration"])
        async def get_available_sources(_: bool = Depends(self.verify_api_key)):
            """Get list of available news sources"""
            return {
                "sources": [
                    {
                        "id": "livemint",
                        "name": "LiveMint",
                        "url": "https://www.livemint.com",
                        "categories": ["homepage", "news", "india", "market", "companies", "economy"]
                    },
                    {
                        "id": "moneycontrol", 
                        "name": "MoneyControl",
                        "url": "https://www.moneycontrol.com",
                        "categories": ["news", "business", "markets", "economy", "companies", "india"]
                    },
                    {
                        "id": "economic_times",
                        "name": "Economic Times",
                        "url": "https://economictimes.indiatimes.com",
                        "categories": ["homepage", "markets", "economy", "industry"]
                    },
                    {
                        "id": "business_standard",
                        "name": "Business Standard", 
                        "url": "https://www.business-standard.com",
                        "categories": ["homepage", "markets", "economy", "companies"]
                    },
                    {
                        "id": "financial_express",
                        "name": "Financial Express",
                        "url": "https://www.financialexpress.com",
                        "categories": ["homepage", "market", "economy", "industry"]
                    }
                ]
            }
    
    def run(self, host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
        """Run the API server"""
        print("🚀 NEWS AGENT API SERVER")
        print("=" * 40)
        print(f"📡 Starting API server...")
        print(f"🌐 API URL: http://{host}:{port}")
        print(f"📚 Documentation: http://{host}:{port}/docs")
        print(f"🔧 Interactive API: http://{host}:{port}/redoc")
        print(f"🔑 API Key Required: {'Yes' if self.api_key else 'No'}")
        print("🛑 Press Ctrl+C to stop")
        print("=" * 40)
        
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )

def create_api_client_example():
    """Create example API client code"""
    client_code = '''
import requests
import json
from datetime import datetime

class NewsAgentClient:
    """Python client for News Agent API"""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = None):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})
    
    def get_health(self):
        """Check API health"""
        response = self.session.get(f"{self.base_url}/health")
        return response.json()
    
    def initialize_agent(self, openai_key=None, hf_key=None, config=None):
        """Initialize the news agent"""
        data = {}
        if openai_key:
            data['openai_api_key'] = openai_key
        if hf_key:
            data['huggingface_api_key'] = hf_key
        if config:
            data['config'] = config
            
        response = self.session.post(f"{self.base_url}/agent/initialize", json=data)
        return response.json()
    
    def start_scraping(self):
        """Start a scraping cycle"""
        response = self.session.post(f"{self.base_url}/scraping/start")
        return response.json()
    
    def get_articles(self, hours=24, source=None, limit=100):
        """Get recent articles"""
        params = {"hours": hours, "limit": limit}
        if source:
            params["source"] = source
            
        response = self.session.get(f"{self.base_url}/articles", params=params)
        return response.json()
    
    def get_trending(self, hours=24, limit=15):
        """Get trending topics"""
        params = {"hours": hours, "limit": limit}
        response = self.session.get(f"{self.base_url}/trending", params=params)
        return response.json()
    
    def get_statistics(self, hours=24):
        """Get statistics"""
        params = {"hours": hours}
        response = self.session.get(f"{self.base_url}/statistics", params=params)
        return response.json()

# Example usage
if __name__ == "__main__":
    # Initialize client
    client = NewsAgentClient("http://localhost:8000")
    
    # Check health
    health = client.get_health()
    print("API Health:", health)
    
    # Initialize agent
    result = client.initialize_agent()
    print("Agent Init:", result)
    
    # Start scraping
    scraping = client.start_scraping()
    print("Scraping Started:", scraping)
    
    # Get articles
    articles = client.get_articles(hours=24, limit=10)
    print(f"Recent Articles: {len(articles)}")
    
    # Get trending topics
    trending = client.get_trending(hours=24, limit=5)
    print("Trending Topics:", [t['topic'] for t in trending])
'''
    
    with open('api_client_example.py', 'w') as f:
        f.write(client_code)
    
    print("📝 Created: api_client_example.py")

def main():
    """Main function to run API server"""
    if not FASTAPI_AVAILABLE:
        print("❌ FastAPI is required for API server")
        print("📥 Install with: pip install fastapi uvicorn")
        return
    
    if not AGENT_AVAILABLE:
        print("❌ integrated_news_agent.py is required")
        print("📁 Make sure integrated_news_agent.py is in the same directory")
        return
    
    # Create API client example
    create_api_client_example()
    
    try:
        # Create and run API server
        api = NewsAgentAPI()
        api.run(host="0.0.0.0", port=8000, reload=False)
        
    except KeyboardInterrupt:
        print("\n🛑 API server stopped")
    except Exception as e:
        print(f"❌ Failed to start API server: {e}")

if __name__ == "__main__":
    main()
