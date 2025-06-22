#!/usr/bin/env python3
"""
Web Dashboard for Integrated News Agent
Flask-based web interface for monitoring and controlling the news agent
"""

import os
import json
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

try:
    from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
    from flask_socketio import SocketIO, emit
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("⚠️ Flask not available. Install with: pip install flask flask-socketio")

# Import our news agent
try:
    from integrated_news_agent import IntegratedNewsAgent, NewsConfig, EnhancedNewsScheduler
    AGENT_AVAILABLE = True
except ImportError:
    AGENT_AVAILABLE = False
    print("⚠️ integrated_news_agent.py not found")

class NewsAgentWebInterface:
    """Web interface for the news agent"""
    
    def __init__(self):
        if not FLASK_AVAILABLE:
            raise ImportError("Flask is required for web interface")
        if not AGENT_AVAILABLE:
            raise ImportError("integrated_news_agent.py is required")
        
        self.app = Flask(__name__)
        self.app.secret_key = 'news_agent_secret_key_change_in_production'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # Initialize agent
        self.agent = None
        self.scheduler = None
        self.is_running = False
        self.current_stats = {}
        
        # Setup routes
        self.setup_routes()
        self.setup_socketio_events()
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def dashboard():
            """Main dashboard"""
            return render_template('dashboard.html')
        
        @self.app.route('/api/status')
        def api_status():
            """Get current status"""
            return jsonify({
                'agent_initialized': self.agent is not None,
                'is_running': self.is_running,
                'scheduler_active': self.scheduler is not None and getattr(self.scheduler, 'is_running', False),
                'database_exists': os.path.exists('news_agent.db'),
                'stats': self.current_stats
            })
        
        @self.app.route('/api/articles')
        def api_articles():
            """Get recent articles"""
            hours = request.args.get('hours', 24, type=int)
            source = request.args.get('source', None)
            category = request.args.get('category', None)
            
            if not self.agent:
                return jsonify({'error': 'Agent not initialized'}), 400
            
            articles = self.agent.get_recent_summaries(hours, source, category)
            return jsonify({
                'articles': articles,
                'total': len(articles),
                'hours': hours
            })
        
        @self.app.route('/api/trending')
        def api_trending():
            """Get trending topics"""
            hours = request.args.get('hours', 24, type=int)
            limit = request.args.get('limit', 15, type=int)
            
            if not self.agent:
                return jsonify({'error': 'Agent not initialized'}), 400
            
            trending = self.agent.get_trending_topics(hours, limit)
            return jsonify({
                'trending': trending,
                'hours': hours
            })
        
        @self.app.route('/api/statistics')
        def api_statistics():
            """Get database statistics"""
            if not os.path.exists('news_agent.db'):
                return jsonify({'error': 'Database not found'}), 404
            
            try:
                conn = sqlite3.connect('news_agent.db')
                
                # Total articles
                total_articles = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
                
                # Recent articles (24h)
                recent_cutoff = datetime.now() - timedelta(hours=24)
                recent_articles = conn.execute(
                    "SELECT COUNT(*) FROM articles WHERE scraped_at > ?", 
                    (recent_cutoff,)
                ).fetchone()[0]
                
                # Source distribution
                source_stats = conn.execute("""
                    SELECT source, COUNT(*) as count 
                    FROM articles 
                    WHERE scraped_at > ? 
                    GROUP BY source 
                    ORDER BY count DESC
                """, (recent_cutoff,)).fetchall()
                
                # Category distribution
                category_stats = conn.execute("""
                    SELECT category, COUNT(*) as count 
                    FROM articles 
                    WHERE scraped_at > ? 
                    GROUP BY category 
                    ORDER BY count DESC
                """, (recent_cutoff,)).fetchall()
                
                # Daily trend (last 7 days)
                daily_stats = conn.execute("""
                    SELECT DATE(scraped_at) as date, COUNT(*) as count
                    FROM articles
                    WHERE scraped_at > DATE('now', '-7 days')
                    GROUP BY DATE(scraped_at)
                    ORDER BY date
                """).fetchall()
                
                conn.close()
                
                return jsonify({
                    'total_articles': total_articles,
                    'recent_articles': recent_articles,
                    'source_distribution': [{'source': row[0], 'count': row[1]} for row in source_stats],
                    'category_distribution': [{'category': row[0], 'count': row[1]} for row in category_stats],
                    'daily_trend': [{'date': row[0], 'count': row[1]} for row in daily_stats]
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/initialize', methods=['POST'])
        def api_initialize():
            """Initialize the news agent"""
            data = request.get_json() or {}
            
            try:
                config = NewsConfig(
                    max_articles_per_page=data.get('max_articles_per_page', 5),
                    scraping_delay=data.get('scraping_delay', 1.0),
                    page_delay=data.get('page_delay', 2.0),
                    enable_logging=data.get('enable_logging', True)
                )
                
                self.agent = IntegratedNewsAgent(
                    openai_api_key=data.get('openai_api_key'),
                    huggingface_api_key=data.get('huggingface_api_key'),
                    config=config
                )
                
                return jsonify({
                    'success': True,
                    'message': 'News agent initialized successfully',
                    'summarization_method': self.agent.summarization_method
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/scrape', methods=['POST'])
        def api_scrape():
            """Start scraping cycle"""
            if not self.agent:
                return jsonify({'error': 'Agent not initialized'}), 400
            
            if self.is_running:
                return jsonify({'error': 'Scraping already in progress'}), 400
            
            # Start scraping in background thread
            def run_scraping():
                self.is_running = True
                try:
                    # Emit start event
                    self.socketio.emit('scraping_started', {'message': 'Scraping started'})
                    
                    # Run scraping
                    results = self.agent.run_complete_scraping_cycle()
                    
                    # Update stats
                    self.current_stats = {
                        'last_run': datetime.now().isoformat(),
                        'total_articles': results['total_new_articles'],
                        'processing_time': results['processing_time'],
                        'summarization_method': results['summarization_method']
                    }
                    
                    # Emit completion event
                    self.socketio.emit('scraping_completed', {
                        'results': results,
                        'stats': self.current_stats
                    })
                    
                except Exception as e:
                    self.socketio.emit('scraping_error', {'error': str(e)})
                finally:
                    self.is_running = False
            
            threading.Thread(target=run_scraping, daemon=True).start()
            
            return jsonify({'success': True, 'message': 'Scraping started'})
        
        @self.app.route('/api/schedule', methods=['POST'])
        def api_schedule():
            """Start/stop scheduled operation"""
            data = request.get_json() or {}
            action = data.get('action')
            
            if action == 'start':
                if not self.agent:
                    return jsonify({'error': 'Agent not initialized'}), 400
                
                if self.scheduler and getattr(self.scheduler, 'is_running', False):
                    return jsonify({'error': 'Scheduler already running'}), 400
                
                interval_hours = data.get('interval_hours', 2)
                
                def run_scheduler():
                    self.scheduler = EnhancedNewsScheduler(self.agent)
                    self.scheduler.start_scheduler(interval_hours=interval_hours)
                
                threading.Thread(target=run_scheduler, daemon=True).start()
                
                return jsonify({
                    'success': True,
                    'message': f'Scheduler started (every {interval_hours} hours)'
                })
            
            elif action == 'stop':
                if self.scheduler:
                    self.scheduler.is_running = False
                    self.scheduler = None
                
                return jsonify({
                    'success': True,
                    'message': 'Scheduler stopped'
                })
            
            else:
                return jsonify({'error': 'Invalid action'}), 400
        
        @self.app.route('/api/export')
        def api_export():
            """Export data"""
            hours = request.args.get('hours', 24, type=int)
            format_type = request.args.get('format', 'json')
            
            if not self.agent:
                return jsonify({'error': 'Agent not initialized'}), 400
            
            try:
                if format_type == 'json':
                    filename = self.agent.export_to_json(hours=hours)
                    return send_file(filename, as_attachment=True)
                else:
                    return jsonify({'error': 'Unsupported format'}), 400
                    
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/report')
        def api_report():
            """Generate report"""
            hours = request.args.get('hours', 24, type=int)
            
            if not self.agent:
                return jsonify({'error': 'Agent not initialized'}), 400
            
            try:
                report = self.agent.generate_comprehensive_report(hours)
                return jsonify({
                    'report': report,
                    'hours': hours
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/cleanup', methods=['POST'])
        def api_cleanup():
            """Cleanup old articles"""
            data = request.get_json() or {}
            days = data.get('days', 30)
            
            if not self.agent:
                return jsonify({'error': 'Agent not initialized'}), 400
            
            try:
                deleted_count = self.agent.cleanup_old_articles(days)
                return jsonify({
                    'success': True,
                    'deleted_count': deleted_count,
                    'days': days
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
    
    def setup_socketio_events(self):
        """Setup SocketIO events for real-time updates"""
        
        @self.socketio.on('connect')
        def handle_connect():
            print('Client connected')
            emit('status_update', {
                'agent_initialized': self.agent is not None,
                'is_running': self.is_running,
                'stats': self.current_stats
            })
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            print('Client disconnected')
    
    def create_templates(self):
        """Create HTML templates"""
        # Create templates directory
        templates_dir = Path('templates')
        templates_dir.mkdir(exist_ok=True)
        
        # Main dashboard template
        dashboard_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>News Agent Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
        }
        .status-online { background-color: #28a745; }
        .status-offline { background-color: #dc3545; }
        .status-running { background-color: #ffc107; animation: pulse 2s infinite; }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        .card-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .metric-card {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            border: none;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
        }
        .article-card {
            transition: transform 0.2s;
            border-left: 4px solid #667eea;
        }
        .article-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        .log-container {
            background: #1a1a1a;
            color: #00ff00;
            font-family: 'Courier New', monospace;
            height: 300px;
            overflow-y: auto;
            padding: 15px;
            border-radius: 5px;
        }
    </style>
</head>
<body class="bg-light">
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
        <div class="container">
            <a class="navbar-brand" href="#"><i class="fas fa-newspaper"></i> News Agent Dashboard</a>
            <div class="ms-auto">
                <span class="badge bg-light text-dark me-2">
                    <span id="status-indicator" class="status-indicator status-offline"></span>
                    <span id="status-text">Offline</span>
                </span>
                <span class="badge bg-light text-dark" id="last-update">Never</span>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <!-- Control Panel -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="fas fa-cogs"></i> Control Panel</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-4">
                                <button class="btn btn-primary w-100 mb-2" onclick="initializeAgent()">
                                    <i class="fas fa-power-off"></i> Initialize Agent
                                </button>
                                <button class="btn btn-success w-100 mb-2" onclick="startScraping()" id="scrape-btn">
                                    <i class="fas fa-play"></i> Start Scraping
                                </button>
                            </div>
                            <div class="col-md-4">
                                <button class="btn btn-warning w-100 mb-2" onclick="toggleScheduler()" id="schedule-btn">
                                    <i class="fas fa-clock"></i> Start Scheduler
                                </button>
                                <button class="btn btn-info w-100 mb-2" onclick="generateReport()">
                                    <i class="fas fa-file-alt"></i> Generate Report
                                </button>
                            </div>
                            <div class="col-md-4">
                                <button class="btn btn-secondary w-100 mb-2" onclick="exportData()">
                                    <i class="fas fa-download"></i> Export Data
                                </button>
                                <button class="btn btn-danger w-100 mb-2" onclick="cleanupData()">
                                    <i class="fas fa-trash"></i> Cleanup Old Data
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Statistics Cards -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="card-body text-center">
                        <i class="fas fa-newspaper fa-2x mb-2"></i>
                        <h3 id="total-articles">0</h3>
                        <p class="mb-0">Total Articles</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="card-body text-center">
                        <i class="fas fa-clock fa-2x mb-2"></i>
                        <h3 id="recent-articles">0</h3>
                        <p class="mb-0">Last 24h</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="card-body text-center">
                        <i class="fas fa-chart-line fa-2x mb-2"></i>
                        <h3 id="processing-time">0s</h3>
                        <p class="mb-0">Last Processing</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="card-body text-center">
                        <i class="fas fa-brain fa-2x mb-2"></i>
                        <h3 id="summarization-method">Local</h3>
                        <p class="mb-0">AI Method</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Charts Row -->
        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="fas fa-chart-pie"></i> Sources Distribution</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="sourcesChart" height="200"></canvas>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="fas fa-chart-line"></i> Daily Trend</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="trendChart" height="200"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <!-- Content Tabs -->
        <div class="row">
            <div class="col-12">
                <ul class="nav nav-tabs" id="contentTabs" role="tablist">
                    <li class="nav-item" role="presentation">
                        <button class="nav-link active" id="articles-tab" data-bs-toggle="tab" data-bs-target="#articles" type="button">
                            <i class="fas fa-newspaper"></i> Recent Articles
                        </button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="trending-tab" data-bs-toggle="tab" data-bs-target="#trending" type="button">
                            <i class="fas fa-fire"></i> Trending Topics
                        </button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="logs-tab" data-bs-toggle="tab" data-bs-target="#logs" type="button">
                            <i class="fas fa-terminal"></i> Live Logs
                        </button>
                    </li>
                </ul>
                <div class="tab-content" id="contentTabsContent">
                    <!-- Articles Tab -->
                    <div class="tab-pane fade show active" id="articles" role="tabpanel">
                        <div class="card">
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-center mb-3">
                                    <h5 class="mb-0">Recent Articles</h5>
                                    <button class="btn btn-outline-primary btn-sm" onclick="refreshArticles()">
                                        <i class="fas fa-refresh"></i> Refresh
                                    </button>
                                </div>
                                <div id="articles-container">
                                    <p class="text-muted text-center py-4">No articles loaded. Initialize agent and start scraping to see articles.</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Trending Tab -->
                    <div class="tab-pane fade" id="trending" role="tabpanel">
                        <div class="card">
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-center mb-3">
                                    <h5 class="mb-0">Trending Topics</h5>
                                    <button class="btn btn-outline-primary btn-sm" onclick="refreshTrending()">
                                        <i class="fas fa-refresh"></i> Refresh
                                    </button>
                                </div>
                                <div id="trending-container">
                                    <p class="text-muted text-center py-4">No trending data available.</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Logs Tab -->
                    <div class="tab-pane fade" id="logs" role="tabpanel">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="mb-3">Live Activity Logs</h5>
                                <div class="log-container" id="logs-container">
                                    <div>News Agent Dashboard - Ready</div>
                                    <div>Waiting for agent initialization...</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Global variables
        let socket = null;
        let sourcesChart = null;
        let trendChart = null;
        let isSchedulerRunning = false;

        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            initializeSocket();
            initializeCharts();
            loadStatus();
            loadStatistics();
        });

        // Socket.IO connection
        function initializeSocket() {
            socket = io();
            
            socket.on('connect', function() {
                addLog('Connected to News Agent server');
                updateStatus('Connected', 'online');
            });
            
            socket.on('disconnect', function() {
                addLog('Disconnected from server');
                updateStatus('Disconnected', 'offline');
            });
            
            socket.on('scraping_started', function(data) {
                addLog('Scraping cycle started...');
                updateStatus('Scraping', 'running');
                document.getElementById('scrape-btn').disabled = true;
            });
            
            socket.on('scraping_completed', function(data) {
                addLog(`Scraping completed: ${data.results.total_new_articles} articles found`);
                updateStatus('Online', 'online');
                document.getElementById('scrape-btn').disabled = false;
                
                // Update statistics
                loadStatistics();
                refreshArticles();
            });
            
            socket.on('scraping_error', function(data) {
                addLog(`Scraping error: ${data.error}`);
                updateStatus('Error', 'offline');
                document.getElementById('scrape-btn').disabled = false;
            });
        }

        // Initialize charts
        function initializeCharts() {
            // Sources pie chart
            const sourcesCtx = document.getElementById('sourcesChart').getContext('2d');
            sourcesChart = new Chart(sourcesCtx, {
                type: 'doughnut',
                data: {
                    labels: [],
                    datasets: [{
                        data: [],
                        backgroundColor: [
                            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });

            // Daily trend line chart
            const trendCtx = document.getElementById('trendChart').getContext('2d');
            trendChart = new Chart(trendCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Articles per Day',
                        data: [],
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }

        // Update status indicator
        function updateStatus(text, status) {
            document.getElementById('status-text').textContent = text;
            const indicator = document.getElementById('status-indicator');
            indicator.className = `status-indicator status-${status}`;
            document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
        }

        // Add log entry
        function addLog(message) {
            const container = document.getElementById('logs-container');
            const timestamp = new Date().toLocaleTimeString();
            const logEntry = document.createElement('div');
            logEntry.innerHTML = `[${timestamp}] ${message}`;
            container.appendChild(logEntry);
            container.scrollTop = container.scrollHeight;
        }

        // API functions
        async function loadStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                if (data.agent_initialized) {
                    updateStatus('Online', 'online');
                    addLog('Agent is initialized and ready');
                } else {
                    updateStatus('Agent Not Initialized', 'offline');
                }
                
                if (data.stats.last_run) {
                    document.getElementById('processing-time').textContent = 
                        data.stats.processing_time ? `${data.stats.processing_time.toFixed(1)}s` : '0s';
                }
                
            } catch (error) {
                console.error('Error loading status:', error);
                updateStatus('Error', 'offline');
            }
        }

        async function loadStatistics() {
            try {
                const response = await fetch('/api/statistics');
                const data = await response.json();
                
                // Update metric cards
                document.getElementById('total-articles').textContent = data.total_articles || 0;
                document.getElementById('recent-articles').textContent = data.recent_articles || 0;
                
                // Update charts
                if (data.source_distribution) {
                    sourcesChart.data.labels = data.source_distribution.map(s => s.source.replace('_', ' ').toUpperCase());
                    sourcesChart.data.datasets[0].data = data.source_distribution.map(s => s.count);
                    sourcesChart.update();
                }
                
                if (data.daily_trend) {
                    trendChart.data.labels = data.daily_trend.map(d => d.date);
                    trendChart.data.datasets[0].data = data.daily_trend.map(d => d.count);
                    trendChart.update();
                }
                
            } catch (error) {
                console.error('Error loading statistics:', error);
            }
        }

        async function initializeAgent() {
            const openaiKey = prompt('OpenAI API Key (optional, leave empty for local summarization):');
            const hfKey = prompt('Hugging Face API Key (optional):');
            
            try {
                const response = await fetch('/api/initialize', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        openai_api_key: openaiKey || undefined,
                        huggingface_api_key: hfKey || undefined,
                        max_articles_per_page: 5,
                        enable_logging: true
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    addLog('Agent initialized successfully');
                    updateStatus('Online', 'online');
                    document.getElementById('summarization-method').textContent = 
                        data.summarization_method || 'Local';
                } else {
                    addLog(`Initialization failed: ${data.error}`);
                    alert(`Error: ${data.error}`);
                }
                
            } catch (error) {
                console.error('Error initializing agent:', error);
                addLog(`Initialization error: ${error.message}`);
            }
        }

        async function startScraping() {
            try {
                const response = await fetch('/api/scrape', {
                    method: 'POST'
                });
                
                const data = await response.json();
                
                if (!data.success) {
                    alert(`Error: ${data.error}`);
                }
                
            } catch (error) {
                console.error('Error starting scraping:', error);
                addLog(`Scraping error: ${error.message}`);
            }
        }

        async function toggleScheduler() {
            const action = isSchedulerRunning ? 'stop' : 'start';
            let intervalHours = 2;
            
            if (action === 'start') {
                const input = prompt('Run every X hours:', '2');
                intervalHours = parseInt(input) || 2;
            }
            
            try {
                const response = await fetch('/api/schedule', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        action: action,
                        interval_hours: intervalHours
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    isSchedulerRunning = !isSchedulerRunning;
                    const btn = document.getElementById('schedule-btn');
                    btn.innerHTML = isSchedulerRunning ? 
                        '<i class="fas fa-stop"></i> Stop Scheduler' : 
                        '<i class="fas fa-clock"></i> Start Scheduler';
                    btn.className = isSchedulerRunning ? 'btn btn-danger w-100 mb-2' : 'btn btn-warning w-100 mb-2';
                    addLog(data.message);
                } else {
                    alert(`Error: ${data.error}`);
                }
                
            } catch (error) {
                console.error('Error with scheduler:', error);
                addLog(`Scheduler error: ${error.message}`);
            }
        }

        async function refreshArticles() {
            try {
                const response = await fetch('/api/articles?hours=24');
                const data = await response.json();
                
                const container = document.getElementById('articles-container');
                
                if (data.articles && data.articles.length > 0) {
                    container.innerHTML = data.articles.map(article => `
                        <div class="article-card card mb-3">
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-start mb-2">
                                    <h6 class="card-title mb-1">${article.title}</h6>
                                    <small class="text-muted">${article.source.toUpperCase()}</small>
                                </div>
                                <p class="card-text text-muted small mb-2">${article.summary}</p>
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <span class="badge bg-secondary me-1">${article.category}</span>
                                        <span class="badge bg-info">${article.reading_time || 1} min read</span>
                                    </div>
                                    <a href="${article.url}" target="_blank" class="btn btn-outline-primary btn-sm">
                                        <i class="fas fa-external-link-alt"></i> Read
                                    </a>
                                </div>
                            </div>
                        </div>
                    `).join('');
                } else {
                    container.innerHTML = '<p class="text-muted text-center py-4">No articles found in the last 24 hours.</p>';
                }
                
            } catch (error) {
                console.error('Error loading articles:', error);
                addLog(`Error loading articles: ${error.message}`);
            }
        }

        async function refreshTrending() {
            try {
                const response = await fetch('/api/trending?hours=24&limit=15');
                const data = await response.json();
                
                const container = document.getElementById('trending-container');
                
                if (data.trending && data.trending.length > 0) {
                    container.innerHTML = `
                        <div class="row">
                            ${data.trending.map((topic, index) => `
                                <div class="col-md-6 mb-3">
                                    <div class="card h-100">
                                        <div class="card-body d-flex align-items-center">
                                            <div class="me-3">
                                                <h4 class="text-primary mb-0">#${index + 1}</h4>
                                            </div>
                                            <div class="flex-grow-1">
                                                <h6 class="mb-1">${topic.topic}</h6>
                                                <small class="text-muted">${topic.frequency} mentions (${topic.percentage}%)</small>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    `;
                } else {
                    container.innerHTML = '<p class="text-muted text-center py-4">No trending topics available.</p>';
                }
                
            } catch (error) {
                console.error('Error loading trending topics:', error);
                addLog(`Error loading trending: ${error.message}`);
            }
        }

        async function generateReport() {
            const hours = prompt('Generate report for last X hours:', '24');
            const hoursNum = parseInt(hours) || 24;
            
            try {
                const response = await fetch(`/api/report?hours=${hoursNum}`);
                const data = await response.json();
                
                if (data.report) {
                    // Create modal or new window to show report
                    const reportWindow = window.open('', '_blank');
                    reportWindow.document.write(`
                        <html>
                            <head><title>News Report</title></head>
                            <body style="font-family: monospace; white-space: pre-wrap; padding: 20px;">
                                ${data.report}
                            </body>
                        </html>
                    `);
                    addLog(`Report generated for last ${hoursNum} hours`);
                } else {
                    alert(`Error: ${data.error}`);
                }
                
            } catch (error) {
                console.error('Error generating report:', error);
                addLog(`Report error: ${error.message}`);
            }
        }

        async function exportData() {
            const hours = prompt('Export data from last X hours:', '24');
            const hoursNum = parseInt(hours) || 24;
            
            try {
                const response = await fetch(`/api/export?hours=${hoursNum}&format=json`);
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = `news_export_${new Date().toISOString().slice(0,10)}.json`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    addLog(`Data exported for last ${hoursNum} hours`);
                } else {
                    const error = await response.json();
                    alert(`Export error: ${error.error}`);
                }
                
            } catch (error) {
                console.error('Error exporting data:', error);
                addLog(`Export error: ${error.message}`);
            }
        }

        async function cleanupData() {
            const days = prompt('Delete articles older than X days:', '30');
            const daysNum = parseInt(days) || 30;
            
            if (confirm(`This will permanently delete all articles older than ${daysNum} days. Continue?`)) {
                try {
                    const response = await fetch('/api/cleanup', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            days: daysNum
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        addLog(`Cleanup completed: ${data.deleted_count} articles deleted`);
                        loadStatistics();
                    } else {
                        alert(`Error: ${data.error}`);
                    }
                    
                } catch (error) {
                    console.error('Error during cleanup:', error);
                    addLog(`Cleanup error: ${error.message}`);
                }
            }
        }

        // Auto-refresh data every 30 seconds
        setInterval(function() {
            loadStatus();
            loadStatistics();
        }, 30000);
    </script>
</body>
</html>'''
        
        with open(templates_dir / 'dashboard.html', 'w', encoding='utf-8') as f:
            f.write(dashboard_html)
    
    def run(self, host='127.0.0.1', port=5000, debug=False):
        """Run the web dashboard"""
        # Create templates
        self.create_templates()
        
        print("🌐 NEWS AGENT WEB DASHBOARD")
        print("=" * 50)
        print(f"🚀 Starting web server...")
        print(f"📱 Access dashboard at: http://{host}:{port}")
        print(f"🔧 Debug mode: {'Enabled' if debug else 'Disabled'}")
        print("🛑 Press Ctrl+C to stop")
        print("=" * 50)
        
        try:
            self.socketio.run(self.app, host=host, port=port, debug=debug)
        except KeyboardInterrupt:
            print("\n🛑 Web dashboard stopped")
        except Exception as e:
            print(f"\n❌ Error running web dashboard: {e}")

def main():
    """Main function to run web dashboard"""
    if not FLASK_AVAILABLE:
        print("❌ Flask is required for web dashboard")
        print("📥 Install with: pip install flask flask-socketio")
        return
    
    if not AGENT_AVAILABLE:
        print("❌ integrated_news_agent.py is required")
        print("📁 Make sure integrated_news_agent.py is in the same directory")
        return
    
    try:
        # Create and run web interface
        web_interface = NewsAgentWebInterface()
        web_interface.run(host='0.0.0.0', port=5000, debug=False)
        
    except Exception as e:
        print(f"❌ Failed to start web dashboard: {e}")

if __name__ == "__main__":
    main()
