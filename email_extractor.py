#!/usr/bin/env python3
"""
Email Content Extractor for macOS Mail
Handles .emlx files and .mbox directories
"""

import os
import re
import email
import email.header
import quopri
import base64
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import sqlite3
import plistlib

class EmailExtractor:
    """Extract content from macOS Mail emails"""
    
    def __init__(self):
        self.mail_dir = Path.home() / "Library" / "Mail"
        self.supported_extensions = {'.emlx', '.eml'}
    
    def extract_email_content(self, email_path: Path) -> Dict:
        """Extract content from an email file"""
        if not email_path.exists():
            return {'success': False, 'error': 'File not found'}
        
        try:
            if email_path.suffix == '.emlx':
                return self._extract_emlx(email_path)
            elif email_path.suffix == '.eml':
                return self._extract_eml(email_path)
            else:
                return {'success': False, 'error': 'Unsupported email format'}
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _extract_emlx(self, emlx_path: Path) -> Dict:
        """Extract content from macOS .emlx files"""
        try:
            with open(emlx_path, 'rb') as f:
                # .emlx files start with a line containing the message size
                first_line = f.readline().decode('utf-8', errors='ignore').strip()
                
                # The rest is the raw email message
                raw_email = f.read()
            
            # Parse the email
            return self._parse_raw_email(raw_email, emlx_path)
        
        except Exception as e:
            return {'success': False, 'error': f'EMLX parsing error: {e}'}
    
    def _extract_eml(self, eml_path: Path) -> Dict:
        """Extract content from standard .eml files"""
        try:
            with open(eml_path, 'rb') as f:
                raw_email = f.read()
            
            return self._parse_raw_email(raw_email, eml_path)
        
        except Exception as e:
            return {'success': False, 'error': f'EML parsing error: {e}'}
    
    def _parse_raw_email(self, raw_email: bytes, file_path: Path) -> Dict:
        """Parse raw email bytes into structured data"""
        try:
            # Parse with email library
            msg = email.message_from_bytes(raw_email)
            
            # Extract headers
            subject = self._decode_header(msg.get('Subject', ''))
            from_addr = self._decode_header(msg.get('From', ''))
            to_addr = self._decode_header(msg.get('To', ''))
            cc_addr = self._decode_header(msg.get('Cc', ''))
            date_str = msg.get('Date', '')
            message_id = msg.get('Message-ID', '')
            
            # Parse date
            email_date = None
            if date_str:
                try:
                    email_date = email.utils.parsedate_to_datetime(date_str)
                except:
                    pass
            
            # Extract body content
            text_content = ""
            html_content = ""
            attachments = []
            
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get('Content-Disposition', ''))
                    
                    # Skip attachments for now, focus on text content
                    if 'attachment' in content_disposition:
                        filename = part.get_filename()
                        if filename:
                            attachments.append(filename)
                        continue
                    
                    if content_type == 'text/plain':
                        try:
                            payload = part.get_payload(decode=True)
                            if payload:
                                text_content += payload.decode('utf-8', errors='ignore')
                        except:
                            pass
                    
                    elif content_type == 'text/html':
                        try:
                            payload = part.get_payload(decode=True)
                            if payload:
                                html_content += payload.decode('utf-8', errors='ignore')
                        except:
                            pass
            else:
                # Single part message
                content_type = msg.get_content_type()
                if content_type == 'text/plain':
                    try:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            text_content = payload.decode('utf-8', errors='ignore')
                    except:
                        pass
            
            # Clean up text content
            if html_content and not text_content:
                # Convert HTML to text if no plain text available
                text_content = self._html_to_text(html_content)
            
            # Create searchable text
            searchable_text = f"{subject}\\n\\n"
            searchable_text += f"From: {from_addr}\\n"
            searchable_text += f"To: {to_addr}\\n"
            if cc_addr:
                searchable_text += f"CC: {cc_addr}\\n"
            searchable_text += f"\\n{text_content}"
            
            return {
                'success': True,
                'text': searchable_text,
                'subject': subject,
                'from': from_addr,
                'to': to_addr,
                'cc': cc_addr,
                'date': email_date,
                'message_id': message_id,
                'attachments': attachments,
                'file_path': str(file_path),
                'word_count': len(searchable_text.split()),
                'content_type': 'email'
            }
        
        except Exception as e:
            return {'success': False, 'error': f'Email parsing error: {e}'}
    
    def _decode_header(self, header_value: str) -> str:
        """Decode email headers that might be encoded"""
        if not header_value:
            return ""
        
        try:
            decoded_parts = email.header.decode_header(header_value)
            decoded_string = ""
            
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_string += part.decode(encoding, errors='ignore')
                    else:
                        decoded_string += part.decode('utf-8', errors='ignore')
                else:
                    decoded_string += part
            
            return decoded_string.strip()
        
        except Exception:
            return header_value
    
    def _html_to_text(self, html_content: str) -> str:
        """Basic HTML to text conversion"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_content)
        
        # Decode HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        
        # Clean up whitespace
        text = re.sub(r'\\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def find_all_emails(self, limit: int = 1000) -> List[Path]:
        """Find all email files in the Mail directory"""
        email_files = []
        
        if not self.mail_dir.exists():
            return email_files
        
        try:
            # Find .emlx files
            for emlx_file in self.mail_dir.rglob('*.emlx'):
                # Skip partial files and junk
                if 'partial.emlx' not in str(emlx_file) and 'Junk.mbox' not in str(emlx_file):
                    email_files.append(emlx_file)
                    if len(email_files) >= limit:
                        break
        
        except Exception as e:
            print(f"Error scanning mail directory: {e}")
        
        return email_files
    
    def get_recent_emails(self, days: int = 365, limit: int = 500) -> List[Path]:
        """Get recent email files"""
        all_emails = self.find_all_emails(limit * 2)  # Get more to filter by date
        recent_emails = []
        
        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        for email_path in all_emails:
            try:
                if email_path.stat().st_mtime > cutoff_time:
                    recent_emails.append(email_path)
                    if len(recent_emails) >= limit:
                        break
            except:
                continue
        
        # If we don't have enough recent emails, just get the first few
        if len(recent_emails) < 5:
            recent_emails = all_emails[:limit]
        
        # Sort by modification time (most recent first)
        recent_emails.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        return recent_emails

def test_email_extraction():
    """Test email extraction"""
    print("🧪 Testing Email Extraction")
    print("-" * 40)
    
    extractor = EmailExtractor()
    
    # Find some recent emails
    recent_emails = extractor.get_recent_emails(days=7, limit=5)
    
    if not recent_emails:
        print("❌ No recent emails found")
        return
    
    print(f"📧 Found {len(recent_emails)} recent emails")
    
    for i, email_path in enumerate(recent_emails, 1):
        print(f"\\n📩 Email {i}: {email_path.name}")
        
        result = extractor.extract_email_content(email_path)
        
        if result['success']:
            print(f"   ✅ Extracted successfully")
            print(f"   📝 Subject: {result['subject'][:60]}...")
            print(f"   👤 From: {result['from'][:50]}...")
            print(f"   📅 Date: {result['date']}")
            print(f"   📊 Word count: {result['word_count']}")
            print(f"   🔍 Preview: {result['text'][:100]}...")
        else:
            print(f"   ❌ Failed: {result['error']}")

if __name__ == "__main__":
    test_email_extraction()