from dataclasses import dataclass, asdict
from typing import List, Dict

@dataclass
class NewsletterEmail:
    message_id: str
    subject: str
    sender: str
    date: str
    timestamp: int
    content_plain: str
    newsletter_name: str
    primary_url: str
    snippet: str
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
# Comprehensive:
# @dataclass
# class NewsletterEmail:
#     message_id: str
#     thread_id: str
#     subject: str
#     sender: str
#     sender_name: str
#     recipient: str
#     date: str
#     timestamp: int
#     content_plain: str
#     content_html: str
#     newsletter_name: str
#     article_urls: List[str]
#     labels: List[str]
#     snippet: str
    
#     def to_dict(self) -> Dict:
#         return asdict(self)