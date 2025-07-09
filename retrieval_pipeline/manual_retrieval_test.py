"""
Manual testing script for NewsletterRetriever.
Run this to test the retriever with actual data.
"""

import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from retriever import NewsletterRetriever
from settings import Settings


def test_basic_retrieval():
    """Test basic retrieval functionality."""
    print("🔍 Testing NewsletterRetriever...")
    
    try:
        retriever = NewsletterRetriever()
        print("✅ NewsletterRetriever initialized successfully")
        
        # Test queries
        test_queries = [
            "How can the democrats defeat trump",
            "How can the democrats stop the big beautiful bill",
            "American politics analysis",
            "How will trumps big beautiful affect the U.S. deficit"
        ]
        
        for query in test_queries:
            print(f"\n📋 Testing query: '{query}'")
            
            try:
                results = retriever.retrieve(query, top_k=3)
                print(f"✅ Found {len(results)} results")
                
                for i, chunk in enumerate(results, 1):
                    print(f"  {i}. Score: {chunk.score:.3f}")
                    print(f"     Content: {chunk.content[:100]}...")
                    print(f"     Metadata: {chunk.metadata}")
                    
            except Exception as e:
                print(f"❌ Error retrieving for '{query}': {e}")
                
    except Exception as e:
        print(f"❌ Failed to initialize NewsletterRetriever: {e}")
        return False
    
    return True


def test_filtered_retrieval():
    """Test retrieval with filters."""
    print("\n🔍 Testing filtered retrieval...")
    
    try:
        retriever = NewsletterRetriever()
        
        # Example filters - adjust based on your metadata structure
        filters = {
            "source": "newsletter_name",  # Adjust field name
            # "date": {"$gte": "2024-01-01"}  # Example date filter
        }
        
        results = retriever.retrieve(
            "artificial intelligence",
            top_k=5,
            filters=filters
        )
        
        print(f"✅ Filtered search returned {len(results)} results")
        
        for i, chunk in enumerate(results, 1):
            print(f"  {i}. Score: {chunk.score:.3f}")
            print(f"     Metadata: {chunk.metadata}")
            
    except Exception as e:
        print(f"❌ Error in filtered retrieval: {e}")


def test_edge_cases():
    """Test edge cases and error conditions."""
    print("\n🔍 Testing edge cases...")
    
    retriever = NewsletterRetriever()
    
    # Test empty query
    try:
        results = retriever.retrieve("", top_k=1)
        print(f"✅ Empty query handled: {len(results)} results")
    except Exception as e:
        print(f"❌ Empty query error: {e}")
    
    # Test very long query
    try:
        long_query = "artificial intelligence " * 50
        results = retriever.retrieve(long_query, top_k=1)
        print(f"✅ Long query handled: {len(results)} results")
    except Exception as e:
        print(f"❌ Long query error: {e}")
    
    # Test high top_k
    try:
        results = retriever.retrieve("test", top_k=100)
        print(f"✅ High top_k handled: {len(results)} results")
    except Exception as e:
        print(f"❌ High top_k error: {e}")


def check_environment():
    """Check if environment is properly configured."""
    print("🔧 Checking environment...")
    
    required_env_vars = [
        "OPENAI_API_KEY",
        # Add other required env vars
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        return False
    
    print("✅ Environment variables OK")
    
    # Check settings
    try:
        print(f"  - Qdrant URL: {Settings.QDRANT_URL}")
        print(f"  - Collection: {Settings.QDRANT_COLLECTION}")
        print(f"  - Embedding Provider: {Settings.EMBEDDING_PROVIDER}")
        print(f"  - Embedding Model: {Settings.EMBEDDING_MODEL}")
        print(f"  - Embedding Dim: {Settings.EMBEDDING_DIM}")
        print("✅ Settings loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Settings error: {e}")
        return False


def main():
    """Run all manual tests."""
    print("🚀 Starting manual tests for NewsletterRetriever")
    print("=" * 50)
    
    if not check_environment():
        print("❌ Environment check failed. Please fix configuration.")
        return
    
    print("\n" + "=" * 50)
    test_basic_retrieval()
    
    print("\n" + "=" * 50)
    test_filtered_retrieval()
    
    print("\n" + "=" * 50)
    test_edge_cases()
    
    print("\n" + "=" * 50)
    print("🎉 Manual testing completed!")


if __name__ == "__main__":
    main()