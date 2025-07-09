"""Inserts and updates vectors in qdrant, can be the one who tags with metadata"""

from typing import List

from newsletter_interface.newsletter import NewsletterEmail


def store_newsletters(newsletters: List[NewsletterEmail]):
    ...


# embedded_newsletter = embed(newsletters)     # List[Dict] with 'id', 'vector', 'metadata'