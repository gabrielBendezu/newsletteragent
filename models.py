from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class RAGChunk:
    content: str
    metadata: Dict[str, Any]
    score: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'content': self.content,
            'metadata': self.metadata,
            'score': self.score
        }
    

# class RAGChunk(TypedDict):
#     id: str
#     content: str
#     primay_url: str
#     subject: str
#     author: str
#     date: str  # or datetime if we parse it upstream
