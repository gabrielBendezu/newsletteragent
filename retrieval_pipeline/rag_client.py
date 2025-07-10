from typing import List

from typing import List, Optional
from .retriever import NewsletterRetriever
from models import RAGChunk
import logging

logger = logging.getLogger(__name__)

# Global instance (created once, reused)
_retriever: Optional[NewsletterRetriever] = None

def get_retriever() -> NewsletterRetriever:
    """Get or create the retriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = NewsletterRetriever()
    return _retriever

def query_rag_system(
    user_query: str, 
    top_k: int = 5, 
    newsletter_filter: Optional[str] = None
) -> List[RAGChunk]:
    """
    Query the RAG system for relevant newsletter content.
    
    Args:
        user_query: The user's search query
        top_k: Number of chunks to return
        newsletter_filter: Optional filter by newsletter name
        
    Returns:
        List of RAGChunk objects with relevant content
    """
    try:
        retriever = get_retriever()
        
        # Build filters if needed
        filters = {}
        if newsletter_filter:
            filters["newsletter_name"] = newsletter_filter
        
        chunks = retriever.retrieve(
            query=user_query,
            top_k=top_k,
            filters=filters
        )
        
        logger.info(f"Retrieved {len(chunks)} chunks for query: {user_query}")
        return chunks
        
    except Exception as e:
        logger.error(f"Error in query_rag_system: {e}")
        raise