import os

class Settings:
    """Centralized settings management."""
    
    # Embedding settings
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai") # ???
    EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))
    EMBEDDING_KEY = os.getenv("OPENAI_API_KEY", "")
    
    # Qdrant settings
    QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
    QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "newsletters")
    