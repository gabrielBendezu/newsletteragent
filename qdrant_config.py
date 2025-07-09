from dataclasses import dataclass
from haystack.utils import Secret

@dataclass
class QdrantConfig:
    """Configuration for Qdrant connection"""
    url: str = "https://07d9c379-addb-4c4c-a4c6-5a6834c9f9aa.eu-central-1-0.aws.cloud.qdrant.io"
    api_key: Secret = Secret.from_env_var("QDRANT_API_KEY")
    collection_name: str = "newsletter_articles"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536  