import base64
from email import policy
from email.parser import BytesParser
import re
from typing import Dict, Tuple, List
from newsletter_interface.newsletter import NewsletterEmail

def parse_sender(sender: str) -> Tuple[str, str]:
    """Parse sender string to extract name and email."""
    if '<' in sender and '>' in sender:
        name = sender.split('<')[0].strip().strip('"')
        email = sender.split('<')[1].split('>')[0].strip()
    else:
        name = sender
        email = sender
    return name, email

def extract_urls(content: str) -> List[str]:
    """Extract URLs from email content, filtering out tracking/unsubscribe links."""
    if not content:
        return []
    url_pattern = r'https?://[^\s<>"{\|}\\^`\[\]]+' 
    urls = re.findall(url_pattern, content)
    skip_domains = ['unsubscribe', 'tracking', 'pixel', 'open.substack.com']
    unique_urls = [url for url in set(urls) if not any(d in url.lower() for d in skip_domains)]
    return unique_urls[:10]

def extract_primary_url(content_html: str, content_plain: str, sender_email: str) -> str:
    """Extract the primary/canonical URL from newsletter content."""
    content = content_html or content_plain
    if not content:
        return ""
    
    # Look for canonical URL in HTML meta tags first
    if content_html:
        canonical_match = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', content_html, re.IGNORECASE)
        if canonical_match:
            return canonical_match.group(1)
    
    # Platform-specific URL extraction patterns
    url_pattern = r'https?://[^\s<>"{\|}\\^`\[\]]+'
    urls = re.findall(url_pattern, content)
    
    # Skip tracking/utility URLs
    skip_domains = ['unsubscribe', 'tracking', 'pixel', 'open.substack.com', 'mailchi.mp', 
                   'constantcontact.com', 'campaign-archive.com', 'us-east-1.amazonaws.com']
    
    # Platform-specific primary URL detection
    domain_patterns = {
        'substack.com': r'https://[^/]+\.substack\.com/p/[^?\s<>"]+',
        'medium.com': r'https://[^/]*medium\.com/[^?\s<>"]+',
        'substackcdn.com': r'https://[^/]+\.substack\.com/p/[^?\s<>"]+',  # Sometimes referenced in content
        'beehiiv.com': r'https://[^/]+\.beehiiv\.com/p/[^?\s<>"]+',
        'convertkit.com': r'https://[^/]+\.ck\.page/[^?\s<>"]+',
        'ghost.org': r'https://[^/]+/[^?\s<>"]+',
        'mailerlite.com': r'https://[^/]+\.mailerlite\.com/[^?\s<>"]+',
    }
    
    # Try to find platform-specific primary URL
    for domain, pattern in domain_patterns.items():
        if domain in sender_email.lower():
            matches = re.findall(pattern, content)
            if matches:
                return matches[0]
    
    # Look for common newsletter URL patterns
    newsletter_patterns = [
        r'https://[^/]+\.substack\.com/p/[^?\s<>"]+',
        r'https://[^/]*medium\.com/@[^/]+/[^?\s<>"]+',
        r'https://[^/]*medium\.com/[^/]+/[^?\s<>"]+',
        r'https://[^/]+\.beehiiv\.com/p/[^?\s<>"]+',
        r'https://[^/]+\.ghost\.io/[^?\s<>"]+',
        r'https://[^/]+\.ck\.page/[^?\s<>"]+',
    ]
    
    for pattern in newsletter_patterns:
        matches = re.findall(pattern, content)
        if matches:
            return matches[0]
    
    # Look for "View in browser" or "Read online" links
    if content_html:
        browser_patterns = [
            r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>.*?(?:view.*?browser|read.*?online|view.*?web|open.*?browser)',
            r'<a[^>]+>.*?(?:view.*?browser|read.*?online|view.*?web|open.*?browser).*?</a>[^<]*href=["\']([^"\']+)["\']',
        ]
        
        for pattern in browser_patterns:
            matches = re.findall(pattern, content_html, re.IGNORECASE | re.DOTALL)
            if matches:
                url = matches[0] if isinstance(matches[0], str) else matches[0][0]
                if not any(skip in url.lower() for skip in skip_domains):
                    return url
    
    # Fallback: return first non-tracking URL
    for url in urls:
        if not any(skip in url.lower() for skip in skip_domains):
            # Skip social media and common utility URLs
            if not any(social in url.lower() for social in ['twitter.com', 'facebook.com', 'linkedin.com', 'instagram.com']):
                return url
    
    return ""

def determine_newsletter_name(sender_email: str, subject: str) -> str:
    """Determine newsletter name from sender email and subject."""
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
    
def parse_gmail_raw_message(raw_message: Dict) -> NewsletterEmail:
    """Parse Gmail raw message format to NewsletterEmail object."""
    try:
        # Decode the raw message
        raw_data = base64.urlsafe_b64decode(raw_message['raw'].encode('UTF-8'))
        msg = BytesParser(policy=policy.default).parsebytes(raw_data)

        # Extract basic headers
        subject = msg.get('subject') or 'No Subject'
        sender = msg.get('from') or 'Unknown'
        date = msg.get('date') or ''
        sender_name, sender_email = parse_sender(sender)
        timestamp = int(raw_message.get('internalDate', 0)) // 1000

        # Extract content
        content_plain = ''
        content_html = ''
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                try:
                    # Only process text parts, skip multipart containers
                    if content_type in ['text/plain', 'text/html']:
                        payload = part.get_payload(decode=True)
                        if payload and isinstance(payload, bytes):
                            charset = part.get_content_charset('utf-8')
                            decoded_payload = payload.decode(charset, errors='replace')
                            
                            if content_type == 'text/plain':
                                content_plain += decoded_payload
                            elif content_type == 'text/html':
                                content_html += decoded_payload
                except Exception as e:
                    print(f"Error decoding part: {e}")
                    continue
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload and isinstance(payload, bytes):
                    charset = msg.get_content_charset('utf-8')
                    decoded_payload = payload.decode(charset, errors='replace')
                    
                    if msg.get_content_type() == 'text/plain':
                        content_plain = decoded_payload
                    elif msg.get_content_type() == 'text/html':
                        content_html = decoded_payload
            except Exception as e:
                print(f"Error decoding message: {e}")

        # Extract URLs and determine newsletter name
        primary_url = extract_primary_url(content_html, content_plain, sender_email)
        article_urls = extract_urls(content_html or content_plain)
        newsletter_name = determine_newsletter_name(sender_email, subject)

        return NewsletterEmail(
            message_id=raw_message['id'],
            subject=subject,
            sender=sender_email,
            date=date,
            timestamp=timestamp,
            content_plain=content_plain,
            newsletter_name=newsletter_name,
            primary_url=primary_url,
            snippet=raw_message.get('snippet', '')
        )
        
    except Exception as e:
        print(f"Error parsing message {raw_message.get('id', 'unknown')}: {e}")
        # Return a minimal valid object in case of parsing errors
        return NewsletterEmail(
            message_id=raw_message.get('id', 'unknown'),
            subject='Parse Error',
            sender='unknown',
            date='',
            timestamp=0,
            content_plain='',
            newsletter_name='Unknown',
            primary_url='',
            snippet=raw_message.get('snippet', '')
        )