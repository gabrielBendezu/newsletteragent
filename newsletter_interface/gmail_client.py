import os
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from newsletter_interface.newsletter import NewsletterEmail
from newsletter_interface.email_parser import parse_gmail_raw_message

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
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
        """Get a single message by ID and return as NewsletterEmail."""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='raw'
            ).execute()
            return parse_gmail_raw_message(message)
        except HttpError as e:
            print(f"Error getting message {message_id}: {e}")
            return None

    def get_messages(self, query: str, max_results: int = 50) -> List[NewsletterEmail]:
        """Get multiple messages based on search query."""
        message_ids = self.list_message_ids(query, max_results)
        messages = []
        
        for msg_id in message_ids:
            message = self.get_message(msg_id)
            if message:
                messages.append(message)
        
        return messages

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
