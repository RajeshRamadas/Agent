#!/usr/bin/env python3
"""
Performance Benchmarking Suite for News Agent System
Comprehensive performance testing and optimization recommendations
"""

import time
import statistics
import threading
import concurrent.futures
import psutil
import memory_profiler
import sqlite3
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import tempfile
import shutil

# Import our components
try:
    from integrated_news_agent import IntegratedNewsAgent, NewsConfig
    AGENT_AVAILABLE = True
except ImportError:
    AGENT_AVAILABLE = False
    print("⚠️ integrated_news_agent.py not available")

class PerformanceBenchmark:
    """Comprehensive performance benchmarking for News Agent"""
    
    def __init__(self):
        self.results = {}
        self.test_dir = None
        self.agent = None
        
    def setup_test_environment(self):
        """Setup isolated test environment"""
        self.test_dir = tempfile.mkdtemp()
        original_cwd = Path.cwd()
        
        # Create test configuration optimized for benchmarking
        config = NewsConfig(
            max_articles_per_source=20,
            max_articles_per_page=5,
            scraping_delay=0.5,
            page_delay=1.0,
            timeout=10,
            enable_logging=False,
            database_path=str(Path(self.test_dir) / "benchmark.db")
        )
        
        self.agent = IntegratedNewsAgent(config=config)
        return original_cwd
    
    def cleanup_test_environment(self, original_cwd):
        """Cleanup test environment"""
        if self.agent:
            self.agent.close()
        if self.test_dir:
            shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def measure_execution_time(self, func, *args, **kwargs) -> Tuple[Any, float]:
        """Measure function execution time"""
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        return result, execution_time
    
    def measure_memory_usage(self, func, *args, **kwargs) -> Tuple[Any, float]:
        """Measure peak memory usage during function execution"""
        @memory_profiler.profile
        def wrapper():
            return func(*args, **kwargs)
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        result = wrapper()
        
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_delta = peak_memory - initial_memory
        
        return result, memory_delta
    
    def benchmark_database_operations(self) -> Dict[str, Any]:
        """Benchmark database operations"""
        print("🗄️ Benchmarking Database Operations...")
        
        results = {
            'insert_performance': {},
            'query_performance': {},
            'index_performance': {},
            'cleanup_performance': {}
        }
        
        # Test article insertion performance
        print("  📝 Testing article insertion...")
        article_counts = [10, 50, 100, 500, 1000]
        
        for count in article_counts:
            articles = self.generate_test_articles(count)
            
            _, insert_time = self.measure_execution_time(
                self.bulk_insert_articles, articles
            )
            
            results['insert_performance'][count] = {
                'time': insert_time,
                'rate': count / insert_time,  # articles per second
                'avg_time_per_article': insert_time / count
            }
            
            print(f"    ✅ {count} articles: {insert_time:.2f}s ({count/insert_time:.1f} articles/s)")
        
        # Test query performance
        print("  🔍 Testing query performance...")
        query_tests = {
            'recent_articles': lambda: self.agent.get_recent_summaries(24),
            'source_filter': lambda: self.agent.get_recent_summaries(24, source='test_source'),
            'category_filter': lambda: self.agent.get_recent_summaries(24, category='test_category'),
            'trending_topics': lambda: self.agent.get_trending_topics(24, 10)
        }
        
        for query_name, query_func in query_tests.items():
            times = []
            for _ in range(5):  # Run 5 times for average
                _, query_time = self.measure_execution_time(query_func)
                times.append(query_time)
            
            results['query_performance'][query_name] = {
                'avg_time': statistics.mean(times),
                'min_time': min(times),
                'max_time': max(times),
                'std_dev': statistics.stdev(times) if len(times) > 1 else 0
            }
            
            print(f"    ✅ {query_name}: {statistics.mean(times):.3f}s avg")
        
        # Test cleanup performance
        print("  🧹 Testing cleanup performance...")
        cleanup_counts = [100, 500, 1000]
        
        for count in cleanup_counts:
            # Insert old articles
            old_articles = self.generate_old_test_articles(count)
            self.bulk_insert_articles(old_articles)
            
            _, cleanup_time = self.measure_execution_time(
                self.agent.cleanup_old_articles, 30
            )
            
            results['cleanup_performance'][count] = {
                'time': cleanup_time,
                'rate': count / cleanup_time
            }
            
            print(f"    ✅ Cleanup {count} articles: {cleanup_time:.2f}s")
        
        return results
    
    def benchmark_scraping_performance(self) -> Dict[str, Any]:
        """Benchmark web scraping performance"""
        print("🌐 Benchmarking Web Scraping Performance...")
        
        results = {
            'page_fetch_performance': {},
            'content_extraction_performance': {},
            'summarization_performance': {},
            'concurrent_performance': {}
        }
        
        # Test page fetching
        print("  📄 Testing page fetch performance...")
        test_urls = [
            "https://httpbin.org/html",
            "https://httpbin.org/delay/1",
            "https://httpbin.org/delay/2"
        ]
        
        for url in test_urls:
            times = []
            for _ in range(3):
                try:
                    _, fetch_time = self.measure_execution_time(
                        self.agent.get_page_content, url
                    )
                    times.append(fetch_time)
                except:
                    continue
            
            if times:
                results['page_fetch_performance'][url] = {
                    'avg_time': statistics.mean(times),
                    'min_time': min(times),
                    'max_time': max(times)
                }
                print(f"    ✅ {url}: {statistics.mean(times):.2f}s avg")
        
        # Test content extraction performance
        print("  ✂️ Testing content extraction...")
        test_html_sizes = [1000, 5000, 10000, 50000]  # bytes
        
        for size in test_html_sizes:
            html_content = self.generate_test_html(size)
            
            _, extract_time = self.measure_execution_time(
                self.extract_test_content, html_content
            )
            
            results['content_extraction_performance'][size] = {
                'time': extract_time,
                'rate': size / extract_time  # bytes per second
            }
            
            print(f"    ✅ {size} bytes HTML: {extract_time:.3f}s")
        
        # Test summarization performance
        print("  📝 Testing summarization performance...")
        content_lengths = [500, 1000, 2000, 5000, 10000]  # characters
        
        for length in content_lengths:
            test_content = self.generate_test_content(length)
            
            _, summarize_time = self.measure_execution_time(
                self.agent.summarize_advanced_extractive, test_content
            )
            
            results['summarization_performance'][length] = {
                'time': summarize_time,
                'rate': length / summarize_time  # chars per second
            }
            
            print(f"    ✅ {length} chars: {summarize_time:.3f}s")
        
        # Test concurrent performance
        print("  🔀 Testing concurrent operations...")
        thread_counts = [1, 2, 4, 8]
        
        for thread_count in thread_counts:
            test_tasks = [self.generate_test_content(1000) for _ in range(20)]
            
            _, concurrent_time = self.measure_execution_time(
                self.run_concurrent_summarization, test_tasks, thread_count
            )
            
            results['concurrent_performance'][thread_count] = {
                'time': concurrent_time,
                'throughput': len(test_tasks) / concurrent_time
            }
            
            print(f"    ✅ {thread_count} threads: {concurrent_time:.2f}s ({len(test_tasks)/concurrent_time:.1f} tasks/s)")
        
        return results
    
    def benchmark_memory_usage(self) -> Dict[str, Any]:
        """Benchmark memory usage patterns"""
        print("🧠 Benchmarking Memory Usage...")
        
        results = {
            'baseline_memory': {},
            'scraping_memory': {},
            'database_memory': {},
            'memory_leaks': {}
        }
        
        # Baseline memory usage
        process = psutil.Process()
        baseline_memory = process.memory_info().rss / 1024 / 1024
        results['baseline_memory']['initial'] = baseline_memory
        
        print(f"  📊 Baseline memory: {baseline_memory:.1f} MB")
        
        # Memory usage during operations
        operations = {
            'article_insertion': lambda: self.bulk_insert_articles(self.generate_test_articles(100)),
            'content_summarization': lambda: [self.agent.summarize_advanced_extractive(self.generate_test_content(2000)) for _ in range(50)],
            'database_query': lambda: [self.agent.get_recent_summaries(24) for _ in range(20)]
        }
        
        for op_name, operation in operations.items():
            initial_memory = process.memory_info().rss / 1024 / 1024
            
            operation()
            
            peak_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = peak_memory - initial_memory
            
            results['scraping_memory'][op_name] = {
                'initial': initial_memory,
                'peak': peak_memory,
                'increase': memory_increase
            }
            
            print(f"  ✅ {op_name}: +{memory_increase:.1f} MB (peak: {peak_memory:.1f} MB)")
        
        # Memory leak detection
        print("  🔍 Testing for memory leaks...")
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        # Simulate prolonged operation
        for i in range(10):
            self.bulk_insert_articles(self.generate_test_articles(50))
            self.agent.get_recent_summaries(24)
            
            if i % 5 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_growth = current_memory - initial_memory
                results['memory_leaks'][f'iteration_{i}'] = {
                    'memory': current_memory,
                    'growth': memory_growth
                }
        
        final_memory = process.memory_info().rss / 1024 / 1024
        total_growth = final_memory - initial_memory
        
        results['memory_leaks']['summary'] = {
            'initial': initial_memory,
            'final': final_memory,
            'total_growth': total_growth,
            'growth_rate': total_growth / 10  # per iteration
        }
        
        print(f"  📈 Memory growth: {total_growth:.1f} MB over 10 iterations")
        
        return results
    
    def benchmark_api_performance(self) -> Dict[str, Any]:
        """Benchmark API endpoint performance"""
        print("🌐 Benchmarking API Performance...")
        
        results = {
            'endpoint_performance': {},
            'concurrent_requests': {},
            'load_testing': {}
        }
        
        # Start API server in background for testing
        # Note: This would require actual API server setup
        api_base_url = "http://localhost:8000"
        
        # Test individual endpoints
        endpoints = {
            'health': '/health',
            'status': '/agent/status',
            'articles': '/articles?limit=10',
            'trending': '/trending?limit=5',
            'statistics': '/statistics'
        }
        
        print("  🔍 Testing individual endpoints...")
        for endpoint_name, endpoint_path in endpoints.items():
            times = []
            success_count = 0
            
            for _ in range(10):
                try:
                    start_time = time.perf_counter()
                    response = requests.get(f"{api_base_url}{endpoint_path}", timeout=10)
                    end_time = time.perf_counter()
                    
                    if response.status_code == 200:
                        times.append(end_time - start_time)
                        success_count += 1
                except:
                    continue
            
            if times:
                results['endpoint_performance'][endpoint_name] = {
                    'avg_response_time': statistics.mean(times),
                    'min_response_time': min(times),
                    'max_response_time': max(times),
                    'success_rate': success_count / 10,
                    'requests_per_second': 1 / statistics.mean(times) if times else 0
                }
                
                print(f"    ✅ {endpoint_name}: {statistics.mean(times):.3f}s avg ({success_count}/10 success)")
        
        # Test concurrent requests
        print("  🔀 Testing concurrent requests...")
        concurrent_levels = [1, 5, 10, 20]
        
        for concurrency in concurrent_levels:
            def make_request():
                try:
                    start_time = time.perf_counter()
                    response = requests.get(f"{api_base_url}/health", timeout=10)
                    end_time = time.perf_counter()
                    return end_time - start_time, response.status_code == 200
                except:
                    return None, False
            
            start_time = time.perf_counter()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [executor.submit(make_request) for _ in range(50)]
                responses = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            end_time = time.perf_counter()
            
            valid_responses = [r for r in responses if r[0] is not None]
            success_count = sum(1 for r in valid_responses if r[1])
            
            if valid_responses:
                response_times = [r[0] for r in valid_responses]
                
                results['concurrent_requests'][concurrency] = {
                    'total_time': end_time - start_time,
                    'avg_response_time': statistics.mean(response_times),
                    'success_rate': success_count / len(valid_responses),
                    'throughput': len(valid_responses) / (end_time - start_time)
                }
                
                print(f"    ✅ {concurrency} concurrent: {statistics.mean(response_times):.3f}s avg, {success_count}/{len(valid_responses)} success")
        
        return results
    
    def generate_test_articles(self, count: int) -> List[Dict]:
        """Generate test articles for benchmarking"""
        articles = []
        for i in range(count):
            articles.append({
                'url': f'https://example.com/test-article-{i}',
                'title': f'Test Article {i} - Performance Benchmark',
                'content': f'This is test content for article {i}. ' * 20,  # ~400 chars
                'source': 'test_source',
                'category': 'test_category',
                'content_hash': f'test_hash_{i}',
                'word_count': 80,
                'reading_time': 1,
                'tags': f'test, benchmark, article{i}'
            })
        return articles
    
    def generate_old_test_articles(self, count: int) -> List[Dict]:
        """Generate old test articles for cleanup testing"""
        articles = []
        old_date = datetime.now() - timedelta(days=35)
        
        for i in range(count):
            articles.append({
                'url': f'https://example.com/old-article-{i}',
                'title': f'Old Test Article {i}',
                'content': f'Old test content for article {i}. ' * 20,
                'source': 'test_source',
                'category': 'test_category',
                'content_hash': f'old_hash_{i}',
                'word_count': 80,
                'reading_time': 1,
                'tags': f'old, test, article{i}',
                'scraped_at': old_date
            })
        return articles
    
    def bulk_insert_articles(self, articles: List[Dict]):
        """Bulk insert articles for testing"""
        for article in articles:
            summary = f"Test summary for {article['title']}"
            
            # Handle old articles with custom timestamp
            if 'scraped_at' in article:
                self.agent.conn.execute('''
                    INSERT INTO articles (
                        url, title, content, summary, source, category,
                        content_hash, word_count, reading_time, tags, scraped_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    article['url'], article['title'], article['content'],
                    summary, article['source'], article['category'],
                    article['content_hash'], article['word_count'],
                    article['reading_time'], article['tags'], article['scraped_at']
                ))
            else:
                self.agent.save_article(article, summary)
        
        self.agent.conn.commit()
    
    def generate_test_html(self, size: int) -> str:
        """Generate test HTML content of specified size"""
        base_html = """
        <html>
            <head><title>Test Article</title></head>
            <body>
                <h1>Test Article Headline</h1>
                <article>
                    <p>TEST_CONTENT_PLACEHOLDER</p>
                </article>
            </body>
        </html>
        """
        
        # Calculate content needed
        content_size = size - len(base_html) + len("TEST_CONTENT_PLACEHOLDER")
        test_content = "This is test content for benchmarking. " * (content_size // 40 + 1)
        test_content = test_content[:content_size]
        
        return base_html.replace("TEST_CONTENT_PLACEHOLDER", test_content)
    
    def generate_test_content(self, length: int) -> str:
        """Generate test content of specified length"""
        base_text = "This is test content for performance benchmarking. It contains multiple sentences with various topics. "
        repetitions = length // len(base_text) + 1
        content = base_text * repetitions
        return content[:length]
    
    def extract_test_content(self, html_content: str) -> str:
        """Extract content from test HTML"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        return self.agent.extract_content(soup)
    
    def run_concurrent_summarization(self, tasks: List[str], thread_count: int):
        """Run summarization tasks concurrently"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = [executor.submit(self.agent.summarize_advanced_extractive, task) for task in tasks]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        return results
    
    def generate_performance_report(self, results: Dict[str, Any]) -> str:
        """Generate comprehensive performance report"""
        report = f"""
📊 NEWS AGENT PERFORMANCE BENCHMARK REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'=' * 60}

🗄️ DATABASE PERFORMANCE
{'=' * 30}
Article Insertion Performance:
"""
        
        # Database performance
        if 'database' in results:
            db_results = results['database']['insert_performance']
            for count, metrics in db_results.items():
                report += f"  • {count:4d} articles: {metrics['time']:6.2f}s ({metrics['rate']:6.1f} articles/s)\n"
            
            report += "\nQuery Performance:\n"
            for query, metrics in results['database']['query_performance'].items():
                report += f"  • {query:20s}: {metrics['avg_time']:6.3f}s avg\n"
        
        # Scraping performance
        if 'scraping' in results:
            report += f"\n🌐 SCRAPING PERFORMANCE\n{'=' * 30}\n"
            
            if 'summarization_performance' in results['scraping']:
                report += "Summarization Performance:\n"
                for length, metrics in results['scraping']['summarization_performance'].items():
                    rate = metrics['rate']
                    report += f"  • {length:5d} chars: {metrics['time']:6.3f}s ({rate:8.0f} chars/s)\n"
        
        # Memory performance
        if 'memory' in results:
            report += f"\n🧠 MEMORY USAGE\n{'=' * 30}\n"
            baseline = results['memory']['baseline_memory']['initial']
            report += f"Baseline Memory: {baseline:.1f} MB\n\n"
            
            if 'scraping_memory' in results['memory']:
                report += "Memory Usage by Operation:\n"
                for op, metrics in results['memory']['scraping_memory'].items():
                    report += f"  • {op:20s}: +{metrics['increase']:5.1f} MB\n"
            
            if 'memory_leaks' in results['memory']:
                leak_summary = results['memory']['memory_leaks']['summary']
                report += f"\nMemory Leak Analysis:\n"
                report += f"  • Total Growth: {leak_summary['total_growth']:5.1f} MB\n"
                report += f"  • Growth Rate:  {leak_summary['growth_rate']:5.1f} MB/iteration\n"
        
        # API performance
        if 'api' in results:
            report += f"\n🌐 API PERFORMANCE\n{'=' * 30}\n"
            
            if 'endpoint_performance' in results['api']:
                report += "Endpoint Response Times:\n"
                for endpoint, metrics in results['api']['endpoint_performance'].items():
                    rps = metrics['requests_per_second']
                    report += f"  • {endpoint:15s}: {metrics['avg_response_time']:6.3f}s ({rps:6.1f} req/s)\n"
        
        # Performance recommendations
        report += f"\n💡 PERFORMANCE RECOMMENDATIONS\n{'=' * 30}\n"
        
        recommendations = self.generate_recommendations(results)
        for rec in recommendations:
            report += f"• {rec}\n"
        
        report += f"\n{'=' * 60}\nBenchmark completed successfully! 🎉\n"
        
        return report
    
    def generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        # Database recommendations
        if 'database' in results:
            db_results = results['database']
            
            # Check insertion performance
            if 'insert_performance' in db_results:
                largest_test = max(db_results['insert_performance'].keys())
                rate = db_results['insert_performance'][largest_test]['rate']
                
                if rate < 100:  # articles per second
                    recommendations.append("Consider database optimization: add indexes, use bulk operations")
                
            # Check query performance
            if 'query_performance' in db_results:
                for query, metrics in db_results['query_performance'].items():
                    if metrics['avg_time'] > 1.0:  # seconds
                        recommendations.append(f"Optimize {query} query: consider adding indexes or caching")
        
        # Memory recommendations
        if 'memory' in results:
            memory_results = results['memory']
            
            if 'memory_leaks' in memory_results:
                growth_rate = memory_results['memory_leaks']['summary']['growth_rate']
                if growth_rate > 5:  # MB per iteration
                    recommendations.append("Potential memory leak detected: review object lifecycle management")
            
            # Check peak memory usage
            if 'scraping_memory' in memory_results:
                for op, metrics in memory_results['scraping_memory'].items():
                    if metrics['increase'] > 100:  # MB
                        recommendations.append(f"High memory usage in {op}: consider processing in batches")
        
        # API recommendations
        if 'api' in results:
            api_results = results['api']
            
            if 'endpoint_performance' in api_results:
                for endpoint, metrics in api_results['endpoint_performance'].items():
                    if metrics['avg_response_time'] > 2.0:  # seconds
                        recommendations.append(f"Slow API endpoint {endpoint}: consider caching or optimization")
                    
                    if metrics['success_rate'] < 0.95:  # 95%
                        recommendations.append(f"Low success rate for {endpoint}: check error handling")
        
        # Scraping recommendations
        if 'scraping' in results:
            scraping_results = results['scraping']
            
            if 'summarization_performance' in scraping_results:
                for length, metrics in scraping_results['summarization_performance'].items():
                    if metrics['rate'] < 1000:  # chars per second
                        recommendations.append("Slow summarization: consider using faster algorithms or GPU acceleration")
        
        # General recommendations
        if not recommendations:
            recommendations.append("System performance is within acceptable ranges")
        
        recommendations.extend([
            "Monitor performance regularly with automated benchmarks",
            "Consider horizontal scaling if handling >1000 requests/hour",
            "Implement caching for frequently accessed data",
            "Regular database maintenance and optimization"
        ])
        
        return recommendations
    
    def run_full_benchmark(self) -> Dict[str, Any]:
        """Run complete performance benchmark suite"""
        print("🚀 STARTING COMPREHENSIVE PERFORMANCE BENCHMARK")
        print("=" * 60)
        
        if not AGENT_AVAILABLE:
            print("❌ News agent not available for benchmarking")
            return {}
        
        original_cwd = self.setup_test_environment()
        
        try:
            all_results = {}
            
            # Run all benchmark tests
            all_results['database'] = self.benchmark_database_operations()
            all_results['scraping'] = self.benchmark_scraping_performance()
            all_results['memory'] = self.benchmark_memory_usage()
            
            # API benchmarking (optional, requires running server)
            try:
                all_results['api'] = self.benchmark_api_performance()
            except Exception as e:
                print(f"⚠️ API benchmarking skipped: {e}")
            
            # Generate and save report
            report = self.generate_performance_report(all_results)
            
            # Save results
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Save detailed results as JSON
            with open(f'benchmark_results_{timestamp}.json', 'w') as f:
                json.dump(all_results, f, indent=2, default=str)
            
            # Save human-readable report
            with open(f'benchmark_report_{timestamp}.txt', 'w') as f:
                f.write(report)
            
            print("\n" + "=" * 60)
            print("📊 BENCHMARK COMPLETED")
            print("=" * 60)
            print(f"Results saved to: benchmark_results_{timestamp}.json")
            print(f"Report saved to: benchmark_report_{timestamp}.txt")
            print("\n" + report)
            
            return all_results
            
        finally:
            self.cleanup_test_environment(original_cwd)

def main():
    """Run performance benchmarks"""
    print("🧪 NEWS AGENT PERFORMANCE BENCHMARK SUITE")
    print("=" * 50)
    
    # Check requirements
    try:
        import matplotlib.pyplot as plt
        import psutil
        import memory_profiler
        BENCHMARK_DEPS_AVAILABLE = True
    except ImportError:
        print("❌ Benchmark dependencies missing")
        print("📥 Install with: pip install matplotlib psutil memory-profiler")
        BENCHMARK_DEPS_AVAILABLE = False
    
    if not BENCHMARK_DEPS_AVAILABLE:
        print("⚠️ Running basic benchmarks only...")
    
    # Run benchmarks
    benchmark = PerformanceBenchmark()
    
    try:
        results = benchmark.run_full_benchmark()
        
        if results:
            print("🎉 Benchmark suite completed successfully!")
            
            # Quick summary
            if 'database' in results and 'insert_performance' in results['database']:
                largest_test = max(results['database']['insert_performance'].keys())
                rate = results['database']['insert_performance'][largest_test]['rate']
                print(f"📊 Database performance: {rate:.1f} articles/second")
            
            if 'memory' in results and 'baseline_memory' in results['memory']:
                baseline = results['memory']['baseline_memory']['initial']
                print(f"🧠 Memory baseline: {baseline:.1f} MB")
            
            return True
        else:
            print("❌ Benchmark failed to complete")
            return False
            
    except Exception as e:
        print(f"❌ Benchmark error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
