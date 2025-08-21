#!/usr/bin/env python3
"""
Scrub personal information from files before public release
"""

import re
from pathlib import Path

def scrub_file(file_path: Path):
    """Remove personal information from a file"""
    
    if not file_path.exists() or file_path.suffix not in ['.py', '.md']:
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace personal names and companies
        replacements = {
            # Personal names
            r'User': 'User',
            r'user': 'user', 
            r'/Users/user/': '/Users/user/',
            
            # Entertainment industry specifics
            r'Client Name': 'Client Name',
            r'ClientName': 'ClientName',
            r'Client': 'Client',
            r'Client': 'CLIENT',
            r'TV Show': 'TV Show',
            r'Management Company': 'Management Company',
            r'MGMT': 'MGMT',  # Keep as project code but generic
            
            # Creative projects
            r'Creative Project': 'Creative Project',
            r'PROJ': 'PROJ',  # Keep as project code but generic
            r'Creative Work': 'Creative Work',
            r'PROJ2': 'PROJ2',
            
            # Specific file examples that contain personal info
            r'SAMPLE_AGREEMENT_2016': 'SAMPLE_AGREEMENT_2016',
            r'SAMPLE_AGREEMENT_2018': 'SAMPLE_AGREEMENT_2018',
            r'client_contract_06.pdf': 'client_contract_06.pdf',
            r'SAMPLE_COMMISSIONS': 'SAMPLE_COMMISSIONS',
            
            # Email addresses (if any)
            r'rt@papersthatdream\.com': 'user@example.com',
            
            # Keep directory structure generic but functional
            r'Documents/AI_ORGANIZER_BASE': 'Documents/AI_ORGANIZER_BASE',
            r'Documents/TEMP_PROCESSING': 'Documents/TEMP_PROCESSING',
        }
        
        # Apply replacements
        for pattern, replacement in replacements.items():
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
        
        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Scrubbed: {file_path.name}")
            return True
        else:
            print(f"⏭️  No changes: {file_path.name}")
            return False
            
    except Exception as e:
        print(f"❌ Error scrubbing {file_path}: {e}")
        return False

def main():
    """Scrub all files in the project"""
    
    print("🧹 Scrubbing Personal Information")
    print("=" * 40)
    
    project_dir = Path("/Users/user/Github/ai-file-organizer")
    
    # Find all Python and Markdown files
    files_to_scrub = []
    for pattern in ['*.py', '*.md']:
        files_to_scrub.extend(project_dir.glob(pattern))
    
    print(f"📄 Found {len(files_to_scrub)} files to check")
    print()
    
    scrubbed_count = 0
    for file_path in files_to_scrub:
        if scrub_file(file_path):
            scrubbed_count += 1
    
    print(f"\n🎉 Scrubbing complete!")
    print(f"   Files modified: {scrubbed_count}")
    print(f"   Files checked: {len(files_to_scrub)}")
    print()
    print("✅ Ready for public release")

if __name__ == "__main__":
    main()