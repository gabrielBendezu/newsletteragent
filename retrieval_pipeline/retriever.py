from haystack import Pipeline
from haystack.components.embedders import OpenAITextEmbedder, SentenceTransformersTextEmbedder
from haystack_integrations.components.retrievers.qdrant import QdrantHybridRetriever
from haystack.utils import Secret
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore

from typing import List, Dict, Any, Optional
from settings import Settings 
from ..models import RAGChunk


class NewsletterRetriever:
    """Handles newsletter retrieval using Haystack."""
    
    def __init__(self):
        self.document_store = self._create_document_store()
        self.pipeline = self._create_retrieval_pipeline()
    
    def _create_document_store(self) -> QdrantDocumentStore:
        """Create the Qdrant document store."""
        return QdrantDocumentStore(
            url=Settings.QDRANT_URL,
            api_key=Secret.from_env_var("OPENAI_API_KEY"),
            index=Settings.QDRANT_COLLECTION,
            embedding_dim=Settings.EMBEDDING_DIM,
            return_embedding=True,
            similarity="cosine"
        )
    
    def _create_text_embedder(self):
        """Create embedder for query text (must match document embedder)."""
        if Settings.EMBEDDING_PROVIDER == "openai":
            return OpenAITextEmbedder(
                model=Settings.EMBEDDING_MODEL,
                api_key=Secret.from_env_var("OPENAI_API_KEY")
            )
        elif Settings.EMBEDDING_PROVIDER == "sentence-transformers":
            return SentenceTransformersTextEmbedder(
                model=Settings.EMBEDDING_MODEL
            )
        else:
            raise ValueError(f"Unsupported embedding provider: {Settings.EMBEDDING_PROVIDER}")
    
    def _create_retrieval_pipeline(self) -> Pipeline:
        """Create the retrieval pipeline."""
        text_embedder = self._create_text_embedder()
        retriever = QdrantHybridRetriever(
            document_store=self.document_store,
            top_k=10  # Adjust based on your needs
        )
        
        pipeline = Pipeline()
        pipeline.add_component("embedder", text_embedder)
        pipeline.add_component("retriever", retriever)
        
        pipeline.connect("embedder.embedding", "retriever.query_embedding")
        
        return pipeline
    
    def retrieve(self, query: str, top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[RAGChunk]:
        """Retrieve relevant documents for a query."""
        result = self.pipeline.run({
            "embedder": {"text": query},
            "retriever": {
                "top_k": top_k,
                "filters": filters or {}
            }
        })
        
        documents = result["retriever"]["documents"]
        
        # Convert to RAGChunk objects
        chunks = []
        for doc in documents:
            chunks.append(RAGChunk(
                content=doc.content,
                metadata=doc.meta,
                score=doc.score if hasattr(doc, 'score') else 0.0
            ))
        
        return chunks