"""Parses emails"""
import base64
import re
from typing import Dict, Tuple, List
from newsletter import NewsletterEmail

def parse_sender(sender: str) -> Tuple[str, str]:
    if '<' in sender and '>' in sender:
        name = sender.split('<')[0].strip().strip('"')
        email = sender.split('<')[1].split('>')[0].strip()
    else:
        name = sender
        email = sender
    return name, email

def extract_content(payload: Dict) -> Tuple[str, str]:
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
        if 'parts' in part:
            for subpart in part['parts']:
                extract_from_part(subpart)
    extract_from_part(payload)
    return content_plain, content_html

def extract_urls(content: str) -> List[str]:
    if not content:
        return []
    url_pattern = r'https?://[^\s<>"{\|}\\^`$begin:math:display$$end:math:display$]+'
    urls = re.findall(url_pattern, content)
    skip_domains = ['unsubscribe', 'tracking', 'pixel', 'open.substack.com']
    unique_urls = [url for url in set(urls) if not any(d in url.lower() for d in skip_domains)]
    return unique_urls[:10]

def determine_newsletter_name(sender_email: str, subject: str) -> str:
    mapping = {
        'substack.com': 'Substack Newsletter',
        'medium.com': 'Medium',
        'techcrunch.com': 'TechCrunch',
        'hackernewsletter.com': 'Hacker News',
        'morningbrew.com': 'Morning Brew',
        'thehustle.co': 'The Hustle',
    }
    for domain, name in mapping.items():
        if domain in sender_email.lower():
            return name
    if 'newsletter' in subject.lower():
        return subject.split('newsletter')[0].strip()
    try:
        domain = sender_email.split('@')[1]
        return domain.replace('.com', '').replace('.', ' ').title()
    except:
        return sender_email

def parse_gmail_message(message: Dict) -> NewsletterEmail:
    headers = {h['name']: h['value'] for h in message['payload']['headers']}
    subject = headers.get('Subject', 'No Subject')
    sender = headers.get('From', 'Unknown')
    recipient = headers.get('To', 'Unknown')
    date_str = headers.get('Date', '')
    sender_name, sender_email = parse_sender(sender)
    timestamp = int(message.get('internalDate', 0)) // 1000
    content_plain, content_html = extract_content(message['payload'])
    article_urls = extract_urls(content_html or content_plain)
    newsletter_name = determine_newsletter_name(sender_email, subject)
    labels = [l for l in message.get('labelIds', []) if not l.startswith('Label_')]
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