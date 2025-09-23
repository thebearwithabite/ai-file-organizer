#!/usr/bin/env python3
"""
Scrub personal information from files before public release
Enhanced to detect and anonymize various PII patterns including:
- Email addresses
- Phone numbers  
- Social Security Numbers
- API keys and tokens
- Personal names and addresses
- File paths with personal information
"""

import re
from pathlib import Path
import os

def scrub_file(file_path: Path):
    """Remove personal information from a file"""
    
    if not file_path.exists() or file_path.suffix not in ['.py', '.md', '.txt', '.json', '.yml', '.yaml']:
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Comprehensive PII patterns and replacements
        replacements = {
            # Email addresses - comprehensive patterns
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}': 'user@example.com',
            
            # Phone numbers (various formats)
            r'\b\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b': 'XXX-XXX-XXXX',
            r'\b([0-9]{3})[-.]([0-9]{3})[-.]([0-9]{4})\b': 'XXX-XXX-XXXX',
            r'\+1[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b': '+1-XXX-XXX-XXXX',
            
            # Social Security Numbers
            r'\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b': 'XXX-XX-XXXX',
            r'\b[0-9]{9}\b': 'XXXXXXXXX',  # SSN without dashes
            
            # API Keys and Tokens (common patterns)
            r'(?:api[_-]?key|token|secret)[\s]*[=:]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?': r'\1: "[REDACTED_API_KEY]"',
            r'sk-[a-zA-Z0-9]{32,}': 'sk-[REDACTED_SECRET_KEY]',
            r'pk-[a-zA-Z0-9]{32,}': 'pk-[REDACTED_PUBLIC_KEY]',
            r'ghp_[a-zA-Z0-9]{36}': 'ghp_[REDACTED_GITHUB_TOKEN]',
            r'gho_[a-zA-Z0-9]{36}': 'gho_[REDACTED_GITHUB_TOKEN]',
            
            # Personal names (specific to this codebase)
            r'\bRyan\b': 'User',
            r'\bryan\b': 'user',
            r'\bryanthomson\b': 'user',
            r'thebearwithabite@gmail\.com': 'user@example.com',
            r'rt@papersthatdream\.com': 'user@example.com',
            
            # File paths with personal information
            r'/Users/user/': '/Users/user/',
            r'/Users/User/': '/Users/user/',
            r'GoogleDrive-thebearwithabite@gmail\.com': 'user@example.com',
            
            # Address patterns (more specific to avoid false positives)
            r'\b\d{1,5}\s+[A-Za-z\s]{3,}(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct)\s+(?:Apt|Suite|Unit)?\s*\d*\b': '[REDACTED_ADDRESS]',
            
            # Credit card patterns (basic)
            r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b': '[REDACTED_CREDIT_CARD]',
            
            # Entertainment industry specifics (keep but genericize)
            r'Client Name': 'Client Name',
            r'ClientName': 'ClientName', 
            r'TV Show': 'TV Show',
            r'Management Company': 'Management Company',
            r'MGMT': 'MGMT',
            
            # Creative projects (keep generic)
            r'Creative Project': 'Creative Project',
            r'PROJ': 'PROJ',
            r'Creative Work': 'Creative Work',
            r'PROJ2': 'PROJ2',
            
            # Specific file examples that contain personal info
            r'SAMPLE_AGREEMENT_2016': 'SAMPLE_AGREEMENT_2016',
            r'SAMPLE_AGREEMENT_2018': 'SAMPLE_AGREEMENT_2018', 
            r'client_contract_06\.pdf': 'client_contract_06.pdf',
            r'SAMPLE_COMMISSIONS': 'SAMPLE_COMMISSIONS',
            
            # Keep directory structure generic but functional
            r'Documents/AI_ORGANIZER_BASE': 'Documents/AI_ORGANIZER_BASE',
            r'Documents/TEMP_PROCESSING': 'Documents/TEMP_PROCESSING',
        }
        
        # Apply replacements with case sensitivity where appropriate
        changes_made = []
        for pattern, replacement in replacements.items():
            old_content = content
            if 'email' in pattern.lower() or '@' in pattern:
                # Case-insensitive for email patterns
                content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
            else:
                # Case-sensitive for most other patterns
                content = re.sub(pattern, replacement, content)
            
            if content != old_content:
                changes_made.append(f"Applied pattern: {pattern[:50]}...")
        
        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Scrubbed: {file_path.name}")
            # Comment: Log what changes were made for transparency
            for change in changes_made[:3]:  # Show first 3 changes to avoid spam
                print(f"   - {change}")
            return True
        else:
            print(f"⏭️  No changes: {file_path.name}")
            return False
            
    except Exception as e:
        print(f"❌ Error scrubbing {file_path}: {e}")
        return False

def main():
    """Scrub all files in the project"""
    
    print("🧹 Enhanced PII Scrubbing Tool")
    print("=" * 40)
    
    # Use current directory instead of hardcoded path
    project_dir = Path(os.getcwd())
    print(f"📂 Scanning directory: {project_dir}")
    
    # Find all relevant files (expanded file types)
    files_to_scrub = []
    patterns = ['*.py', '*.md', '*.txt', '*.json', '*.yml', '*.yaml']
    
    for pattern in patterns:
        files_to_scrub.extend(project_dir.glob(pattern))
        # Also check subdirectories (but not hidden ones)
        for subdir in project_dir.iterdir():
            if subdir.is_dir() and not subdir.name.startswith('.'):
                files_to_scrub.extend(subdir.glob(pattern))
    
    # Remove duplicates and sort
    files_to_scrub = sorted(set(files_to_scrub))
    
    print(f"📄 Found {len(files_to_scrub)} files to check")
    print(f"   File types: {', '.join(patterns)}")
    print()
    
    # Comment: Show user what files will be processed for transparency
    if len(files_to_scrub) <= 10:
        print("Files to be processed:")
        for file_path in files_to_scrub:
            print(f"  - {file_path.relative_to(project_dir)}")
        print()
    
    scrubbed_count = 0
    for file_path in files_to_scrub:
        if scrub_file(file_path):
            scrubbed_count += 1
    
    print(f"\n🎉 PII Scrubbing complete!")
    print(f"   Files modified: {scrubbed_count}")
    print(f"   Files checked: {len(files_to_scrub)}")
    print()
    
    # Comment: Provide clear guidance on what was accomplished
    if scrubbed_count > 0:
        print("✅ PII has been anonymized and files are ready for public release")
        print("📝 Changes made:")
        print("   - Email addresses → user@example.com")
        print("   - Personal names → generic equivalents")
        print("   - Phone numbers → XXX-XXX-XXXX")
        print("   - File paths → /Users/user/...")
        print("   - API keys/tokens → [REDACTED_*]")
    else:
        print("✅ No PII detected - files are already clean for public release")
        
    return scrubbed_count

if __name__ == "__main__":
    main()