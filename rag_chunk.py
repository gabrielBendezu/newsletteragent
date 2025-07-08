from typing import TypedDict, List, Optional

class RAGChunk(TypedDict):
    id: str
    content: str
    headline: str
    author: str
    sourceUrl: str
    publishedAt: str  # or datetime if we parse it upstream
    tags: Optional[List[str]]