"""loads openai embedding model to embed stuff"""
 
# Doesn't know from where anything comes from or where it goes

from typing import List

from newsletter_interface.newsletter import NewsletterEmail

def embed(newsletters: List[NewsletterEmail]):
    ...