"""
Newsletter RAG Orchestration Script
Combines Gmail fetching, embedding, and Qdrant storage into a single workflow
"""

import argparse
import json
import sys
from datetime import datetime
from typing import List, Dict

# Import our custom modules
from rag_pipeline.qdrant_storage import NewsletterQdrantStorage, QdrantConfig

class NewsletterRAGOrchestrator:
    def __init__(self, 
                 gmail_credentials: str = 'credentials.json',
                 gmail_token: str = 'token.json',
                 qdrant_config: QdrantConfig = None):
        """
        Initialize the orchestrator
        
        Args:
            gmail_credentials: Path to Gmail API credentials
            gmail_token: Path to Gmail OAuth token
            qdrant_config: Qdrant configuration
        """
        self.gmail_fetcher = GmailNewsletterFetcher(gmail_credentials, gmail_token)
        self.qdrant_storage = NewsletterQdrantStorage(qdrant_config)
        
        print("🚀 Newsletter RAG Orchestrator initialized")
    
    def full_pipeline(self, 
                     gmail_query: str = None,
                     max_results: int = 50,
                     save_json: bool = True,
                     json_filename: str = None,
                     skip_existing: bool = True) -> Dict:
        """
        Run the complete pipeline: fetch -> embed -> store
        
        Args:
            gmail_query: Gmail search query
            max_results: Maximum emails to fetch
            save_json: Whether to save intermediate JSON
            json_filename: Custom JSON filename
            skip_existing: Skip newsletters already in Qdrant
            
        Returns:
            Dictionary with pipeline statistics
        """
        print("🔄 Starting full newsletter RAG pipeline...")
        
        # Step 1: Fetch newsletters from Gmail
        print("\n" + "="*50)
        print("STEP 1: FETCHING NEWSLETTERS FROM GMAIL")
        print("="*50)
        
        newsletters = self.gmail_fetcher.fetch_newsletters(gmail_query, max_results)
        
        if not newsletters:
            print("❌ No newsletters fetched. Pipeline stopped.")
            return {
                "fetched": 0,
                "stored": 0,
                "skipped": 0,
                "errors": 0,
                "success": False
            }
        
        # Step 2: Save to JSON (optional)
        if save_json:
            if json_filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                json_filename = f"newsletters_{timestamp}.json"
            
            self.gmail_fetcher.save_to_json(newsletters, json_filename)
        
        # Step 3: Store in Qdrant
        print("\n" + "="*50)
        print("STEP 2: STORING IN QDRANT VECTOR DATABASE")
        print("="*50)
        
        # Convert NewsletterEmail objects to dictionaries
        newsletter_dicts = [newsletter.to_dict() for newsletter in newsletters]
        
        storage_stats = self.qdrant_storage.store_newsletters(newsletter_dicts, skip_existing)
        
        # Step 4: Final summary
        print("\n" + "="*50)
        print("PIPELINE COMPLETE - SUMMARY")
        print("="*50)
        
        final_stats = {
            "fetched": len(newsletters),
            "stored": storage_stats["stored"],
            "skipped": storage_stats["skipped"],
            "errors": storage_stats["errors"],
            "success": storage_stats["stored"] > 0 or storage_stats["skipped"] > 0
        }
        
        print(f"📧 Newsletters fetched: {final_stats['fetched']}")
        print(f"💾 Newsletters stored: {final_stats['stored']}")
        print(f"⏭️  Newsletters skipped: {final_stats['skipped']}")
        print(f"❌ Errors: {final_stats['errors']}")
        
        if save_json:
            print(f"📄 JSON saved to: {json_filename}")
        
        return final_stats
    
    def search_newsletters(self, query: str, filters: Dict = None, top_k: int = 5) -> List[Dict]:
        """Search newsletters with optional filters"""
        return self.qdrant_storage.search_newsletters(query, filters, top_k)
    
    def get_stats(self) -> Dict:
        """Get comprehensive statistics"""
        return self.qdrant_storage.get_collection_stats()
    
    def interactive_search(self):
        """Interactive search interface"""
        print("\n🔍 Interactive Newsletter Search")
        print("Type 'quit' to exit, 'stats' for statistics")
        print("-" * 40)
        
        while True:
            query = input("\nEnter search query: ").strip()
            
            if query.lower() == 'quit':
                break
            elif query.lower() == 'stats':
                stats = self.get_stats()
                print(f"\n📊 Collection Statistics:")
                print(f"Total documents: {stats.get('total_documents', 0)}")
                if 'newsletter_distribution' in stats:
                    print("Newsletter distribution:")
                    for newsletter, count in stats['newsletter_distribution'].items():
                        print(f"  {newsletter}: {count}")
                continue
            elif not query:
                continue
            
            results = self.search_newsletters(query, top_k=3)
            
            if not results:
                print("No results found.")
                continue
            
            print(f"\n📄 Found {len(results)} results:")
            print("-" * 40)
            
            for i, result in enumerate(results, 1):
                metadata = result['metadata']
                print(f"\n{i}. {metadata['newsletter_name']}")
                print(f"   Subject: {metadata['subject']}")
                print(f"   Date: {metadata['date']}")
                print(f"   Score: {result['score']:.3f}")
                
                if metadata.get('primary_url'):
                    print(f"   URL: {metadata['primary_url']}")
                
                print(f"   Preview: {result['content'][:200]}...")
    
    def update_from_json(self, json_filename: str, skip_existing: bool = True) -> Dict:
        """Update Qdrant from existing JSON file"""
        try:
            with open(json_filename, 'r', encoding='utf-8') as f:
                newsletters = json.load(f)
            
            print(f"📄 Loaded {len(newsletters)} newsletters from {json_filename}")
            
            stats = self.qdrant_storage.store_newsletters(newsletters, skip_existing)
            
            print(f"✅ Update complete:")
            print(f"   Stored: {stats['stored']}")
            print(f"   Skipped: {stats['skipped']}")
            print(f"   Errors: {stats['errors']}")
            
            return stats
            
        except FileNotFoundError:
            print(f"❌ File not found: {json_filename}")
            return {"error": "File not found"}
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON: {e}")
            return {"error": "Invalid JSON"}


def main():
    """Main function with command-line interface"""
    parser = argparse.ArgumentParser(description='Newsletter RAG Pipeline')
    parser.add_argument('--mode', choices=['full', 'search', 'update', 'stats'], 
                       default='full', help='Operation mode')
    parser.add_argument('--query', type=str, help='Gmail search query')
    parser.add_argument('--max-results', type=int, default=50, 
                       help='Maximum emails to fetch')
    parser.add_argument('--no-json', action='store_true', 
                       help='Skip saving JSON file')
    parser.add_argument('--json-file', type=str, 
                       help='JSON filename for update mode')
    parser.add_argument('--search-query', type=str, 
                       help='Search query for search mode')
    parser.add_argument('--qdrant-url', type=str, default='http://localhost:6333',
                       help='Qdrant URL')
    parser.add_argument('--qdrant-api-key', type=str,
                       help='Qdrant API key (for cloud)')
    parser.add_argument('--collection-name', type=str, default='newsletter_articles',
                       help='Qdrant collection name')
    
    args = parser.parse_args()
    
    # Setup Qdrant configuration
    qdrant_config = QdrantConfig(
        url=args.qdrant_url,
        api_key=args.qdrant_api_key,
        collection_name=args.collection_name
    )
    
    # Initialize orchestrator
    try:
        orchestrator = NewsletterRAGOrchestrator(qdrant_config=qdrant_config)
    except Exception as e:
        print(f"❌ Error initializing orchestrator: {e}")
        sys.exit(1)
    
    # Run based on mode
    if args.mode == 'full':
        # Full pipeline
        gmail_query = args.query or "newer_than:7d"
        print(f"🎯 Gmail query: {gmail_query}")
        
        stats = orchestrator.full_pipeline(
            gmail_query=gmail_query,
            max_results=args.max_results,
            save_json=not args.no_json
        )
        
        if stats['success']:
            print("\n✅ Pipeline completed successfully!")
            
            # Ask if user wants to try searching
            try:
                response = input("\nWould you like to try searching? (y/n): ").strip().lower()
                if response == 'y':
                    orchestrator.interactive_search()
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
        else:
            print("\n❌ Pipeline failed!")
            sys.exit(1)
    
    elif args.mode == 'search':
        # Search mode
        if args.search_query:
            results = orchestrator.search_newsletters(args.search_query)
            
            for i, result in enumerate(results, 1):
                metadata = result['metadata']
                print(f"\n{i}. {metadata['newsletter_name']}")
                print(f"   Subject: {metadata['subject']}")
                print(f"   Score: {result['score']:.3f}")
                print(f"   Preview: {result['content'][:200]}...")
        else:
            # Interactive search
            orchestrator.interactive_search()
    
    elif args.mode == 'update':
        # Update from JSON
        if not args.json_file:
            print("❌ --json-file required for update mode")
            sys.exit(1)
        
        orchestrator.update_from_json(args.json_file)
    
    elif args.mode == 'stats':
        # Show statistics
        stats = orchestrator.get_stats()
        print("\n📊 Collection Statistics:")
        print(f"Total documents: {stats.get('total_documents', 0)}")
        
        if 'newsletter_distribution' in stats:
            print("\nNewsletter distribution:")
            for newsletter, count in stats['newsletter_distribution'].items():
                print(f"  {newsletter}: {count}")
        
        if 'date_range' in stats:
            date_range = stats['date_range']
            print(f"\nDate range:")
            print(f"  Earliest: {date_range.get('earliest', 'Unknown')}")
            print(f"  Latest: {date_range.get('latest', 'Unknown')}")


if __name__ == "__main__":
    main()