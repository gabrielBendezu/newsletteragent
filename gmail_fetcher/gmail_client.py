"""
Manual Gmail Newsletter Fetcher
Polls Gmail for newsletter emails and extracts content + metadata
"""

import os
import json
import base64
import re
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from newsletter import NewsletterEmail
from email_parser import parse_gmail_message

SCOPES = ['https://www.googleapis.com/auth/gmail.read']
    
def get_gmail_service(credentials_file='credentials.json', token_file='token.json'):
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

class GmailClient:
    def __init__(self, service):
        self.service = service

    def list_message_ids(self, query: str, max_results: int = 50) -> List[str]:
        try:
            response = self.service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
            return [msg['id'] for msg in response.get('messages', [])]
        except HttpError as e:
            print(f"Error fetching messages: {e}")
            return []

    def get_message(self, message_id: str) -> Optional[NewsletterEmail]:
        try:
            message = self.service.users().messages().get(userId='me', id=message_id, format='full').execute()
            return parse_gmail_message(message)
        except HttpError as e:
            print(f"Error getting message {message_id}: {e}")
            return None

    def mark_as_read(self, message_ids: List[str]):
        for msg_id in message_ids:
            try:
                self.service.users().messages().modify(
                    userId='me',
                    id=msg_id,
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
            except HttpError as e:
                print(f"Error marking message {msg_id} as read: {e}")

def main():
    # Test puts emails into the newsletters.json
    service = get_gmail_service
    fetcher = GmailClient(service)
    
    # Examples:
    # query = "from:substack.com newer_than:7d"  # Last 7 days from Substack
    # query = "subject:newsletter newer_than:3d"  # Last 3 days with "newsletter" in subject
    # query = None  # Use default query
    
    # query = "newer_than:7d"  # Last 7 days
    query = (
        'is:unread AND (from:substack.com OR from:newsletter OR from:noreply '
        'OR subject:newsletter OR from:medium.com OR from:substackcdn.com)'
    )
    
    newsletters = fetcher.fetch_newsletters(query=query, max_results=20)
    
    if newsletters:
        # Save to JSON
        fetcher.save_to_json(newsletters)
        
        # Print summary
        print("\n" + "="*50)
        print("SUMMARY")
        print("="*50)
        
        for newsletter in newsletters:
            print(f"📧 {newsletter.newsletter_name}")
            print(f"   Subject: {newsletter.subject}")
            print(f"   From: {newsletter.sender_name}")
            print(f"   Date: {newsletter.date}")
            print(f"   URLs: {len(newsletter.article_urls)}")
            print(f"   Content: {len(newsletter.content_plain)} chars (plain), {len(newsletter.content_html)} chars (html)")
            print()


if __name__ == "__main__":
    main()