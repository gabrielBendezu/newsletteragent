from typing import List
from rag_chunk import RAGChunk

def query_rag_system(question: str, top_k: int = 5) -> List[RAGChunk]:
    ...