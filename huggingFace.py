#!/usr/bin/env python3
"""
RAG Introduction - Building on Your Tavily Agent
Step-by-step introduction to Retrieval-Augmented Generation
"""

import os
import requests
import json
import time
from datetime import datetime
from typing import List, Dict, Any
import re

# Set your API key
os.environ["TAVILY_API_KEY"] = "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"

# ===== STEP 1: Simple Document Storage =====

class SimpleDocumentStore:
    """Simple in-memory document storage (RAG Step 1)"""
    
    def __init__(self):
        self.documents = {}
        self.doc_id_counter = 0
        
        # Add some sample documents
        self.add_sample_documents()
    
    def add_document(self, title: str, content: str) -> str:
        """Add a document to the store"""
        doc_id = f"doc_{self.doc_id_counter}"
        self.documents[doc_id] = {
            "id": doc_id,
            "title": title,
            "content": content,
            "added_date": datetime.now().isoformat()
        }
        self.doc_id_counter += 1
        return doc_id
    
    def add_sample_documents(self):
        """Add some sample documents for testing"""
        samples = [
            {
                "title": "Python Basics Guide",
                "content": "Python is a high-level programming language. It supports object-oriented programming and has dynamic typing. Python is great for beginners because of its simple syntax. Key features include: easy to read syntax, extensive standard library, cross-platform compatibility, and strong community support."
            },
            {
                "title": "Machine Learning Overview", 
                "content": "Machine Learning is a subset of artificial intelligence that enables computers to learn from data without explicit programming. Main types include supervised learning (with labeled data), unsupervised learning (finding patterns), and reinforcement learning (learning through rewards). Popular libraries include scikit-learn, TensorFlow, and PyTorch."
            },
            {
                "title": "Web Development with Python",
                "content": "Python offers several frameworks for web development. Django is a full-featured framework with ORM, admin interface, and security features. Flask is lightweight and flexible. FastAPI is modern and fast, with automatic API documentation. For frontend, you can use templates or build APIs for JavaScript frameworks."
            },
            {
                "title": "Company Policy: Remote Work",
                "content": "Our company supports flexible remote work arrangements. Employees can work from home up to 3 days per week. Core hours are 10 AM to 3 PM in your local timezone. All meetings should be scheduled during core hours when possible. Use Slack for quick communication and email for formal correspondence."
            }
        ]
        
        for doc in samples:
            self.add_document(doc["title"], doc["content"])
    
    def simple_search(self, query: str, max_results: int = 3) -> List[Dict]:
        """Simple keyword-based document search"""
        query_words = query.lower().split()
        results = []
        
        for doc_id, doc in self.documents.items():
            # Simple scoring: count matching words
            content_lower = (doc["title"] + " " + doc["content"]).lower()
            score = sum(1 for word in query_words if word in content_lower)
            
            if score > 0:
                results.append({
                    "doc_id": doc_id,
                    "title": doc["title"],
                    "content": doc["content"],
                    "score": score
                })
        
        # Sort by score and return top results
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:max_results]
    
    def get_all_documents(self) -> List[Dict]:
        """Get all documents"""
        return list(self.documents.values())

# ===== STEP 2: Enhanced Agent with Document Search =====

class RAGAgent:
    """Agent with both web search (Tavily) and document search (RAG)"""
    
    def __init__(self):
        self.name = "RAG-Enhanced Agent"
        self.document_store = SimpleDocumentStore()
        self.conversation_history = []
        
        # Tools now include document search
        self.tools = {
            "web_search": self.web_search,
            "doc_search": self.document_search,
            "add_document": self.add_document,
            "list_documents": self.list_documents,
            "help": self.show_help
        }
    
    def web_search(self, query: str) -> str:
        """Your existing Tavily web search"""
        try:
            api_key = os.getenv("TAVILY_API_KEY")
            url = "https://api.tavily.com/search"
            
            payload = {
                "api_key": api_key,
                "query": query,
                "max_results": 3
            }
            
            print(f"🌐 Web searching: {query}")
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return self.format_web_results(result)
            else:
                return f"❌ Web search failed: {response.status_code}"
                
        except Exception as e:
            return f"❌ Web search error: {e}"
    
    def document_search(self, query: str) -> str:
        """Search through local documents (RAG)"""
        print(f"📚 Document searching: {query}")
        
        results = self.document_store.simple_search(query)
        
        if not results:
            return "📭 No relevant documents found in knowledge base."
        
        formatted = f"📚 Found {len(results)} relevant documents:\n\n"
        
        for i, doc in enumerate(results, 1):
            formatted += f"{i}. 📄 **{doc['title']}** (Score: {doc['score']})\n"
            # Show relevant excerpt
            content = doc['content']
            if len(content) > 200:
                content = content[:200] + "..."
            formatted += f"   📝 {content}\n\n"
        
        return formatted
    
    def add_document(self, args: str) -> str:
        """Add a new document to the knowledge base"""
        parts = args.split(' | ', 1)  # Use | as separator between title and content
        
        if len(parts) != 2:
            return "❌ Usage: /add Title | Content goes here..."
        
        title, content = parts
        doc_id = self.document_store.add_document(title.strip(), content.strip())
        
        return f"✅ Document added with ID: {doc_id}\n   Title: {title}"
    
    def list_documents(self, args: str = "") -> str:
        """List all documents in the knowledge base"""
        docs = self.document_store.get_all_documents()
        
        if not docs:
            return "📭 No documents in knowledge base."
        
        formatted = f"📚 Knowledge Base ({len(docs)} documents):\n\n"
        
        for i, doc in enumerate(docs, 1):
            formatted += f"{i}. 📄 {doc['title']} (ID: {doc['id']})\n"
            content_preview = doc['content'][:100] + "..."
            formatted += f"   📝 {content_preview}\n\n"
        
        return formatted
    
    def format_web_results(self, result: Dict) -> str:
        """Format web search results"""
        results = result.get('results', [])
        
        if not results:
            return "❌ No web results found"
        
        formatted = f"🌐 Web search results ({len(results)}):\n\n"
        
        for i, item in enumerate(results, 1):
            title = item.get('title', 'No title')
            url_link = item.get('url', 'No URL')
            content = item.get('content', '')[:150] + "..."
            
            formatted += f"{i}. 🔗 {title}\n"
            formatted += f"   📝 {content}\n"
            formatted += f"   🌐 {url_link}\n\n"
        
        return formatted
    
    def show_help(self, args: str = "") -> str:
        """Show help with new RAG commands"""
        help_text = """
🤖 RAG-Enhanced Agent - Commands:

🌐 WEB SEARCH:
  /web <query>         - Search the internet with Tavily
  
📚 DOCUMENT SEARCH (RAG):
  /docs <query>        - Search your knowledge base
  /add <title> | <content> - Add document to knowledge base
  /list                - List all documents
  
🎯 SMART SEARCH:
  /both <query>        - Search both web and documents
  /compare <query>     - Compare web vs document results
  
📱 GENERAL:
  /help                - Show this help
  /quit                - Exit

💡 EXAMPLES:
  /docs python basics
  /add Python Tips | Use list comprehensions for cleaner code
  /both machine learning
  /web latest AI news
  /compare React vs Vue

🧠 The agent now has RAG capabilities - it can search your personal 
   knowledge base AND the web, giving you the best of both worlds!
        """
        return help_text
    
    def smart_search(self, query: str, search_type: str = "auto") -> str:
        """Intelligent search that decides between web, docs, or both"""
        
        if search_type == "both":
            # Search both web and documents
            web_results = self.web_search(query)
            doc_results = self.document_search(query)
            
            return f"🔍 **COMBINED SEARCH RESULTS**\n\n{doc_results}\n{'-'*50}\n\n{web_results}"
        
        elif search_type == "compare":
            # Compare results from both sources
            print("🔍 Comparing web vs document results...")
            web_results = self.web_search(query)
            doc_results = self.document_search(query)
            
            comparison = f"📊 **COMPARISON SEARCH**: {query}\n\n"
            comparison += f"📚 **FROM YOUR KNOWLEDGE BASE:**\n{doc_results}\n"
            comparison += f"🌐 **FROM THE WEB:**\n{web_results}\n"
            comparison += f"💡 **INSIGHT:** Use documents for internal/personal info, web for latest/external info."
            
            return comparison
        
        else:
            # Auto-decide based on query content
            query_lower = query.lower()
            
            # Keywords that suggest document search
            doc_keywords = ["policy", "internal", "company", "guide", "our", "my", "personal"]
            # Keywords that suggest web search  
            web_keywords = ["latest", "news", "current", "2025", "recent", "trending"]
            
            if any(keyword in query_lower for keyword in doc_keywords):
                return f"🧠 Auto-selected: Document search\n\n" + self.document_search(query)
            elif any(keyword in query_lower for keyword in web_keywords):
                return f"🧠 Auto-selected: Web search\n\n" + self.web_search(query)
            else:
                # Default: search both
                return f"🧠 Auto-selected: Combined search\n\n" + self.smart_search(query, "both")
    
    def process_command(self, user_input: str) -> str:
        """Process commands with new RAG features"""
        if user_input.startswith('/'):
            parts = user_input[1:].split(maxsplit=1)
            command = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            if command in ["quit", "exit"]:
                return "QUIT"
            elif command == "help":
                return self.show_help()
            elif command == "web":
                return self.web_search(args) if args else "❌ Provide search query"
            elif command == "docs":
                return self.document_search(args) if args else "❌ Provide search query"
            elif command == "add":
                return self.add_document(args) if args else "❌ Usage: /add Title | Content"
            elif command == "list":
                return self.list_documents()
            elif command == "both":
                return self.smart_search(args, "both") if args else "❌ Provide search query"
            elif command == "compare":
                return self.smart_search(args, "compare") if args else "❌ Provide search query"
            else:
                return f"❌ Unknown command. Type /help for available commands."
        
        return None
    
    def run(self, query: str) -> str:
        """Main processing with smart search decision"""
        return self.smart_search(query, "auto")

# ===== DEMO FUNCTION =====

def demo_rag_agent():
    """Demo the RAG-enhanced agent"""
    print("\n🚀 RAG-Enhanced Agent Demo")
    print("=" * 35)
    print("🧠 Now with Document Search + Web Search!")
    print("📚 Pre-loaded with sample documents")
    print("💡 Type /help for all commands")
    
    agent = RAGAgent()
    
    # Show sample searches
    print(f"\n🤖 {agent.name}: Hello! I now have RAG capabilities!")
    print("    I can search both your documents AND the web.")
    print("    Let me show you what's in my knowledge base:")
    
    print(f"\n📚 {agent.list_documents()}")
    
    print("💡 Try these commands:")
    print("  /docs python          (search documents)")
    print("  /web latest AI news    (search web)")
    print("  /both machine learning (search both)")
    print("  /add My Note | This is my personal note")
    
    while True:
        try:
            user_input = input(f"\n👤 You: ").strip()
            
            if not user_input:
                continue
            
            print("🤖 Agent: 🤔 Processing...")
            time.sleep(0.3)
            
            # Process command or run smart search
            command_result = agent.process_command(user_input)
            
            if command_result == "QUIT":
                print("👋 Goodbye! Your documents are saved in memory.")
                break
            elif command_result:
                response = command_result
            else:
                # Use smart search for natural queries
                response = agent.run(user_input)
            
            print(f"\r🤖 Agent: {response}")
                
        except KeyboardInterrupt:
            print(f"\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

# ===== SIMPLE RAG CONCEPTS DEMO =====

def explain_rag_concepts():
    """Explain RAG concepts step by step"""
    print("\n📖 RAG (Retrieval-Augmented Generation) Explained")
    print("=" * 55)
    
    concepts = [
        {
            "concept": "What is RAG?",
            "explanation": "RAG combines retrieval (finding relevant documents) with generation (creating responses). Instead of just generating from training data, the AI first retrieves relevant information from your documents, then generates a response based on that retrieved content."
        },
        {
            "concept": "Why use RAG?", 
            "explanation": "1. Access to private/current data 2. Reduces hallucination 3. Provides source citations 4. Updates knowledge without retraining 5. Domain-specific expertise"
        },
        {
            "concept": "RAG vs Web Search",
            "explanation": "Web Search: Public internet data, real-time, broad topics\nRAG: Your private documents, controlled data, domain-specific knowledge\nBest approach: Use both together!"
        },
        {
            "concept": "Next Steps",
            "explanation": "We started simple with keyword search. Next we can add: 1. Vector embeddings 2. Similarity search 3. Document chunking 4. Multiple file formats 5. Advanced retrieval strategies"
        }
    ]
    
    for i, item in enumerate(concepts, 1):
        print(f"\n{i}. 🎯 {item['concept']}")
        print(f"   {item['explanation']}")
        input("   Press Enter to continue...")

if __name__ == "__main__":
    print("🚀 RAG Introduction for Your Tavily Agent")
    print("=" * 45)
    print("1. Interactive RAG Agent Demo")
    print("2. RAG Concepts Explanation")
    
    choice = input("\nChoose (1 or 2): ").strip()
    
    if choice == "1":
        demo_rag_agent()
    elif choice == "2":
        explain_rag_concepts()
        print("\nNow try option 1 to see RAG in action!")
    else:
        print("Starting RAG agent demo...")
        demo_rag_agent()