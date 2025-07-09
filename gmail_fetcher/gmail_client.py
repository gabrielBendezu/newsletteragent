"""
Manual Gmail Newsletter Fetcher
Polls Gmail for newsletter emails and extracts content + metadata
"""

import os
import json
import base64
import re
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/gmail.read']

@dataclass
class NewsletterEmail:
    """Structure for newsletter email data"""
    message_id: str
    thread_id: str
    subject: str
    sender: str
    sender_name: str
    recipient: str
    date: str
    timestamp: int
    content_plain: str
    content_html: str
    newsletter_name: str
    article_urls: List[str]
    labels: List[str]
    snippet: str
    
    def to_dict(self) -> Dict:
        return asdict(self)


class GmailNewsletterFetcher:
    def __init__(self, credentials_file: str = 'credentials.json', token_file: str = 'token.json'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.authenticate()
    
    def authenticate(self):
        """Authenticate with Gmail API"""
        creds = None
        
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)
        print("✓ Successfully authenticated with Gmail API")
    
    def get_newsletter_messages(self, query: str = None, max_results: int = 50) -> List[str]:
        """
        Get message IDs for newsletter emails
        
        Args:
            query: Gmail search query (default searches for common newsletter patterns)
            max_results: Maximum number of messages to fetch
        """
        if query is None:
            # Default query for newsletters - customize based on your subscriptions
            query = (
                'from:substack.com OR from:newsletter OR from:noreply '
                'OR subject:newsletter OR from:medium.com OR from:substackcdn.com'
            )
        
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            print(f"✓ Found {len(messages)} newsletter messages")
            return [msg['id'] for msg in messages]
            
        except HttpError as error:
            print(f"❌ Error fetching messages: {error}")
            return []
        
    def mark_as_read(self, message_ids: List[str]):
        """Mark the given message IDs as read by removing the UNREAD label"""
        for msg_id in message_ids:
            try:
                self.service.users().messages().modify(
                    userId='me',
                    id=msg_id,
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
                print(f"✓ Marked message {msg_id} as read")
            except HttpError as error:
                print(f"❌ Failed to mark message {msg_id} as read: {error}")
    
    def get_message_content(self, message_id: str) -> Optional[NewsletterEmail]:
        """Extract content and metadata from a single message"""
        try:
            message = self.service.users().messages().get(
                userId='me', 
                id=message_id, 
                format='full'
            ).execute()
            
            return self._parse_message(message)
            
        except HttpError as error:
            print(f"❌ Error fetching message {message_id}: {error}")
            return None
    
    def _parse_message(self, message: Dict) -> NewsletterEmail:
        """Parse Gmail message into NewsletterEmail object"""
        headers = {h['name']: h['value'] for h in message['payload']['headers']}
        
        # Extract basic metadata
        subject = headers.get('Subject', 'No Subject')
        sender = headers.get('From', 'Unknown')
        recipient = headers.get('To', 'Unknown')
        date_str = headers.get('Date', '')
        
        # Parse sender name and email
        sender_name, sender_email = self._parse_sender(sender)
        
        # Get timestamp
        timestamp = int(message.get('internalDate', 0)) // 1000
        
        # Extract content
        content_plain, content_html = self._extract_content(message['payload'])
        
        # Extract URLs from content
        article_urls = self._extract_urls(content_html or content_plain)
        
        # Determine newsletter name
        newsletter_name = self._determine_newsletter_name(sender_email, subject)
        
        # Get labels
        labels = [label for label in message.get('labelIds', []) if not label.startswith('Label_')]
        
        return NewsletterEmail(
            message_id=message['id'],
            thread_id=message['threadId'],
            subject=subject,
            sender=sender_email,
            sender_name=sender_name,
            recipient=recipient,
            date=date_str,
            timestamp=timestamp,
            content_plain=content_plain,
            content_html=content_html,
            newsletter_name=newsletter_name,
            article_urls=article_urls,
            labels=labels,
            snippet=message.get('snippet', '')
        )
    
    def _parse_sender(self, sender: str) -> tuple:
        """Parse sender into name and email"""
        if '<' in sender and '>' in sender:
            # Format: "Name <email@domain.com>"
            name = sender.split('<')[0].strip().strip('"')
            email = sender.split('<')[1].split('>')[0].strip()
        else:
            # Just email address
            name = sender
            email = sender
        
        return name, email
    
    def _extract_content(self, payload: Dict) -> tuple:
        """Extract plain text and HTML content from message payload"""
        content_plain = ""
        content_html = ""
        
        def extract_from_part(part):
            nonlocal content_plain, content_html
            
            if part.get('mimeType') == 'text/plain':
                data = part.get('body', {}).get('data', '')
                if data:
                    content_plain += base64.urlsafe_b64decode(data).decode('utf-8')
            
            elif part.get('mimeType') == 'text/html':
                data = part.get('body', {}).get('data', '')
                if data:
                    content_html += base64.urlsafe_b64decode(data).decode('utf-8')
            
            # Handle multipart messages
            if 'parts' in part:
                for subpart in part['parts']:
                    extract_from_part(subpart)
        
        extract_from_part(payload)
        
        return content_plain, content_html
    
    def _extract_urls(self, content: str) -> List[str]:
        """Extract URLs from email content"""
        if not content:
            return []
        
        # Basic URL regex
        url_pattern = r'https?://[^\s<>"{\|}\\^`\[\]]+'
        urls = re.findall(url_pattern, content)
        
        # Remove duplicates and common tracking URLs
        unique_urls = []
        skip_domains = ['unsubscribe', 'tracking', 'pixel', 'open.substack.com']
        
        for url in set(urls):
            if not any(domain in url.lower() for domain in skip_domains):
                unique_urls.append(url)
        
        return unique_urls[:10]  # Limit to first 10 URLs
    
    def _determine_newsletter_name(self, sender_email: str, subject: str) -> str:
        """Determine newsletter name from sender or subject"""
        # Custom mapping - expand this based on your subscriptions
        newsletter_mapping = {
            'substack.com': 'Substack Newsletter',
            'medium.com': 'Medium',
            'techcrunch.com': 'TechCrunch',
            'hackernewsletter.com': 'Hacker News',
            'morningbrew.com': 'Morning Brew',
            'thehustle.co': 'The Hustle',
        }
        
        # Check if sender domain matches known newsletters
        for domain, name in newsletter_mapping.items():
            if domain in sender_email.lower():
                return name
        
        # Extract from subject if possible
        if 'newsletter' in subject.lower():
            return subject.split('newsletter')[0].strip()
        
        # Default to sender domain
        try:
            domain = sender_email.split('@')[1]
            return domain.replace('.com', '').replace('.', ' ').title()
        except:
            return sender_email
    
    def fetch_newsletters(self, query: str = None, max_results: int = 50) -> List[NewsletterEmail]:
        """Main method to fetch and parse newsletter emails"""
        print(f"🔍 Fetching newsletters...")
        
        # Get message IDs
        message_ids = self.get_newsletter_messages(query, max_results)
        
        if not message_ids:
            print("No messages found")
            return []
        
        newsletters = []
        
        for i, message_id in enumerate(message_ids):
            print(f"📧 Processing message {i+1}/{len(message_ids)}: {message_id}")
            
            newsletter = self.get_message_content(message_id)
            if newsletter:
                newsletters.append(newsletter)
        
        if newsletters:
            self.mark_as_read([n.message_id for n in newsletters])
        
        print(f"✓ Successfully processed {len(newsletters)} newsletter emails")
        return newsletters
    
    def save_to_json(self, newsletters: List[NewsletterEmail], filename: str = 'newsletters.json'):
        """Save newsletters to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump([newsletter.to_dict() for newsletter in newsletters], f, indent=2, ensure_ascii=False)
        
        print(f"✓ Saved {len(newsletters)} newsletters to {filename}")


def main():
    fetcher = GmailNewsletterFetcher()
    
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