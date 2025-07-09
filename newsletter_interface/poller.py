""" Calls the gmail client every 20 minutes or so, orchestrates everything with parsing and embedding and pushing to qdrant """

from newsletter_interface.gmail_client import get_gmail_service, GmailClient
from newsletter_interface.embedder import embed  
from newsletter_interface.qdrant_uploader import store_newsletters
from newsletter_interface.newsletter import NewsletterEmail

from typing import List

def fetch_unread_newsletters(service) -> List[NewsletterEmail]:
    client = GmailClient(service)
    query = (
        'is:unread AND (from:substack.com OR from:newsletter OR from:noreply '
        'OR subject:newsletter OR from:medium.com OR from:substackcdn.com)'
    )
    message_ids = client.list_message_ids(query=query, max_results=50)
    newsletters = [client.get_message(mid) for mid in message_ids]
    newsletters = [n for n in newsletters if n is not None]
    #client.mark_as_read([n.message_id for n in newsletters])
    
    return newsletters

def test_fetch_unread_newsletters(service):
    """Test and log the subjects of unread newsletter emails fetched."""
    newsletters = fetch_unread_newsletters(service)
    
    if not newsletters:
        print("No unread newsletters found.")
        return

    print(f"Fetched {len(newsletters)} unread newsletters:")
    # for idx, email in enumerate(newsletters, start=1):
    #     subject = getattr(email, 'subject', '(No Subject)')
    #     print(f"{idx}. {subject}")
    # for newsletter in newsletters:
    #     print(f"Subject: {newsletter.subject}") 
    #     print(f"From: {newsletter.sender}")
    #     print(f"Newsletter: {newsletter.newsletter_name}")
    #     print(f"URL: {newsletter.primary_url}")
    #     print("-" * 50)
    # print(newsletters[1].subject)
    # print(newsletters[1].content_plain)

def run_ingestion_pipeline():
    """Main orchestrator."""
    service = get_gmail_service()
    newsletters = fetch_unread_newsletters(service)
    # test_fetch_unread_newsletters(service)
    if newsletters:
        store_newsletters(newsletters)
    else:
        print("No new newsletters to process.")

if __name__ == "__main__":
    run_ingestion_pipeline()