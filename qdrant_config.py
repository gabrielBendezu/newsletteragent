from dataclasses import dataclass
from haystack.utils import Secret
from dotenv import load_dotenv
import os

load_dotenv()

@dataclass
class QdrantConfig:
    """Configuration for Qdrant connection"""
    url: str = os.getenv("QDRANT_URL", "")
    api_key: Secret = Secret.from_env_var("QDRANT_API_KEY")
    collection_name: str = "newsletter_articles"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536  