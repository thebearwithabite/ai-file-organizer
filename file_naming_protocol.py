#!/usr/bin/env python3
"""
File Naming Protocol for User's AI File Organizer
Implements YYYY-MM-DD_PROJECT_CLIENT_CONTENT-TYPE_vN naming convention
"""

import re
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class FileNamingComponents:
    """Components for the enhanced filename"""
    date: str  # YYYY-MM-DD
    project: str  # MGMT, ST, PROJ, etc.
    client: str  # ClientName, Netflix, etc.
    content_type: str  # Management-Agreement, Script, etc.
    version: str  # v1, v2, etc.
    extension: str  # .pdf, .docx, etc.

class FileNamingProtocol:
    """
    Handles intelligent file renaming using User's naming protocol
    Format: YYYY-MM-DD_PROJECT_CLIENT_CONTENT-TYPE_vN.ext
    """
    
    def __init__(self):
        # Project code mappings
        self.project_codes = {
            # Entertainment Management
            "Management Company": "MGMT",
            "refinery": "MGMT",
            "management": "MGMT",
            
            # Shows/Productions
            "TV Show": "ST",
            "hell of a summer": "HOAS",
            "it": "IT",
            "ghostbusters": "GB",
            
            # Creative Projects
            "Creative Project": "PROJ",
            "Creative Work": "PROJ2",
            "papers": "PROJ",
            
            # Business
            "development": "DEV",
            "firebase": "DEV",
            "ai organizer": "DEV",
            
            # Default fallbacks
            "entertainment": "ENT",
            "business": "BUS",
            "creative": "CRE"
        }
        
        # Client/Person mappings
        self.client_codes = {
            "Client Name": "ClientName",
            "finn": "ClientName", 
            "Client": "ClientName",
            "netflix": "Netflix",
            "Management Company": "RefineryAM",
            "internal": "Internal",
            "personal": "Personal",
            "User": "user",
            "business contacts": "BusinessContacts",
            "unknown": "General"
        }
        
        # Content type mappings
        self.content_types = {
            # Contracts & Legal
            "management agreement": "Management-Agreement",
            "agreement": "Agreement",
            "contract": "Contract",
            "start slip": "Start-Slip",
            "payroll docs": "Payroll-Docs",
            "tax return": "Tax-Return",
            "commission": "Commission-Report",
            "invoice": "Invoice",
            
            # Creative Content
            "script": "Script",
            "screenplay": "Screenplay",
            "episode": "Episode-Script",
            "research": "Research-Paper",
            "notes": "Notes",
            
            # Business Documents
            "report": "Report",
            "financial": "Financial-Report",
            "spreadsheet": "Spreadsheet",
            "presentation": "Presentation",
            
            # Technical
            "deployment plan": "Deployment-Plan",
            "documentation": "Documentation",
            "specification": "Specification",
            
            # General
            "document": "Document",
            "file": "Document",
            "untitled": "Document"
        }
        
        # Date extraction patterns
        self.date_patterns = [
            r'(\d{4})-(\d{2})-(\d{2})',  # 2025-08-20
            r'(\d{4})(\d{2})(\d{2})',    # 20250820
            r'(\d{2})-(\d{2})-(\d{4})',  # 08-20-2025
            r'(\d{2})(\d{2})(\d{4})',    # 08202025
            r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})',  # 8/20/25 or 8-20-2025
        ]
    
    def generate_enhanced_filename(self, original_path: Path, classification_result: Dict, extraction_result: Dict = None) -> str:
        """
        Generate enhanced filename using User's protocol
        
        Args:
            original_path: Original file path
            classification_result: AI classification result
            extraction_result: Content extraction result (optional)
            
        Returns:
            Enhanced filename string
        """
        
        # Extract components
        components = self._extract_naming_components(
            original_path, 
            classification_result, 
            extraction_result
        )
        
        # Build filename
        enhanced_name = f"{components.date}_{components.project}_{components.client}_{components.content_type}_{components.version}{components.extension}"
        
        return enhanced_name
    
    def _extract_naming_components(self, original_path: Path, classification_result: Dict, extraction_result: Dict = None) -> FileNamingComponents:
        """Extract all components for filename"""
        
        original_name = original_path.stem.lower()
        content = extraction_result.get('text', '') if extraction_result else ''
        
        # 1. Extract Date
        date = self._extract_date(original_path, content)
        
        # 2. Extract Project
        project = self._extract_project(original_name, content, classification_result)
        
        # 3. Extract Client
        client = self._extract_client(original_name, content, classification_result)
        
        # 4. Extract Content Type
        content_type = self._extract_content_type(original_name, content, classification_result)
        
        # 5. Extract Version
        version = self._extract_version(original_name)
        
        return FileNamingComponents(
            date=date,
            project=project,
            client=client,
            content_type=content_type,
            version=version,
            extension=original_path.suffix
        )
    
    def _extract_date(self, original_path: Path, content: str) -> str:
        """Extract or infer date for filename"""
        
        # Try to find date in filename
        filename = original_path.name
        for pattern in self.date_patterns:
            match = re.search(pattern, filename)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    # Handle different date formats
                    if len(groups[0]) == 4:  # YYYY-MM-DD format
                        year, month, day = groups
                    else:  # MM-DD-YYYY format
                        month, day, year = groups
                        if len(year) == 2:
                            year = f"20{year}"
                    
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        # Try to find date in content
        if content:
            for pattern in self.date_patterns:
                match = re.search(pattern, content)
                if match:
                    groups = match.groups()
                    if len(groups) == 3:
                        if len(groups[0]) == 4:
                            year, month, day = groups
                        else:
                            month, day, year = groups
                            if len(year) == 2:
                                year = f"20{year}"
                        
                        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        # Use file modification date as fallback
        try:
            mtime = datetime.fromtimestamp(original_path.stat().st_mtime)
            return mtime.strftime("%Y-%m-%d")
        except:
            # Final fallback to today
            return datetime.now().strftime("%Y-%m-%d")
    
    def _extract_project(self, filename: str, content: str, classification: Dict) -> str:
        """Extract project code"""
        
        # Check filename for project indicators
        for project_name, code in self.project_codes.items():
            if project_name in filename or project_name in content.lower():
                return code
        
        # Check classification category
        category = classification.get('category', '').lower()
        if 'entertainment' in category:
            return "ENT"
        elif 'business' in category:
            return "BUS"
        elif 'creative' in category:
            return "CRE"
        elif 'development' in category:
            return "DEV"
        
        # Default fallback
        return "GEN"
    
    def _extract_client(self, filename: str, content: str, classification: Dict) -> str:
        """Extract client/person code"""
        
        # Check people from classification
        people = classification.get('people', [])
        if people:
            person = people[0].lower().replace('_', ' ')
            for client_name, code in self.client_codes.items():
                if client_name in person:
                    return code
        
        # Check filename and content
        text_to_check = f"{filename} {content.lower()}"
        for client_name, code in self.client_codes.items():
            if client_name in text_to_check:
                return code
        
        # Default fallback
        return "General"
    
    def _extract_content_type(self, filename: str, content: str, classification: Dict) -> str:
        """Extract content type"""
        
        # Check filename for content type indicators
        text_to_check = f"{filename} {content.lower()}"
        
        for content_name, content_type in self.content_types.items():
            if content_name in text_to_check:
                return content_type
        
        # Check classification tags
        tags = classification.get('tags', [])
        for tag in tags:
            tag_lower = tag.lower()
            for content_name, content_type in self.content_types.items():
                if content_name in tag_lower:
                    return content_type
        
        # Fallback based on category
        category = classification.get('category', '').lower()
        if 'contract' in category or 'agreement' in category:
            return "Agreement"
        elif 'financial' in category:
            return "Financial-Report"
        elif 'creative' in category:
            return "Creative-Document"
        
        return "Document"
    
    def _extract_version(self, filename: str) -> str:
        """Extract or assign version number"""
        
        # Look for existing version patterns
        version_patterns = [
            r'v(\d+)',           # v1, v2, etc.
            r'version\s*(\d+)',  # version 1, version2
            r'\(v?(\d+)\)',      # (1), (v1)
            r'_(\d+)$',          # ending with _1, _2
        ]
        
        for pattern in version_patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                version_num = match.group(1)
                return f"v{version_num}"
        
        # Default to v1
        return "v1"
    
    def handle_filename_collision(self, target_path: Path, enhanced_filename: str) -> str:
        """Handle filename collisions by incrementing version"""
        
        name_parts = enhanced_filename.split('_')
        if len(name_parts) >= 5:
            # Extract current version
            version_with_ext = name_parts[-1]  # "v1.pdf"
            extension = Path(version_with_ext).suffix
            current_version = Path(version_with_ext).stem  # "v1"
            
            # Find available version number
            counter = 1
            if current_version.startswith('v'):
                try:
                    counter = int(current_version[1:]) + 1
                except:
                    counter = 2
            
            while True:
                # Build new filename with incremented version
                new_version = f"v{counter}"
                new_name_parts = name_parts[:-1] + [f"{new_version}{extension}"]
                new_filename = "_".join(new_name_parts)
                
                if not (target_path.parent / new_filename).exists():
                    return new_filename
                
                counter += 1
                
                # Safety valve
                if counter > 99:
                    import uuid
                    unique_id = str(uuid.uuid4())[:8]
                    new_name_parts = name_parts[:-1] + [f"v{counter}_{unique_id}{extension}"]
                    return "_".join(new_name_parts)
        
        # Fallback for malformed filenames
        stem = Path(enhanced_filename).stem
        extension = Path(enhanced_filename).suffix
        counter = 2
        
        while True:
            new_filename = f"{stem}_v{counter}{extension}"
            if not (target_path.parent / new_filename).exists():
                return new_filename
            counter += 1
            
            if counter > 99:
                import uuid
                unique_id = str(uuid.uuid4())[:8]
                return f"{stem}_{unique_id}{extension}"
    
    def preview_renaming(self, original_path: Path, classification_result: Dict, extraction_result: Dict = None) -> Dict:
        """Preview what the filename would become"""
        
        enhanced_name = self.generate_enhanced_filename(
            original_path, 
            classification_result, 
            extraction_result
        )
        
        return {
            'original_name': original_path.name,
            'enhanced_name': enhanced_name,
            'components': self._extract_naming_components(original_path, classification_result, extraction_result),
            'size_difference': len(enhanced_name) - len(original_path.name),
            'is_meaningful_change': enhanced_name.lower() != original_path.name.lower()
        }

def test_naming_protocol():
    """Test the naming protocol with sample files"""
    print("🧪 Testing File Naming Protocol")
    print("=" * 50)
    
    protocol = FileNamingProtocol()
    
    # Test cases based on User's actual files
    test_cases = [
        {
            'filename': 'SAMPLE_AGREEMENT_2016.pdf',
            'classification': {
                'category': 'entertainment_industry',
                'people': ['business_contacts'],
                'tags': ['entertainment_industry', 'business_contacts', '2016']
            }
        },
        {
            'filename': 'client_contract_06.pdf',
            'classification': {
                'category': 'entertainment_industry', 
                'people': ['finn_Client'],
                'tags': ['entertainment_industry', 'finn_Client']
            }
        },
        {
            'filename': 'SAMPLE_COMMISSIONS - Jan 2021.pdf',
            'classification': {
                'category': 'business',
                'people': [],
                'tags': ['business', 'commission', '2020', '2021']
            }
        },
        {
            'filename': 'Firebase Deployment Plan for AudioAI Organizer SaaS.pdf',
            'classification': {
                'category': 'development',
                'people': [],
                'tags': ['development', 'firebase', 'ai']
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📄 Test Case {i}:")
        
        original_path = Path(f"/test/{test_case['filename']}")
        preview = protocol.preview_renaming(original_path, test_case['classification'])
        
        print(f"   Original: {preview['original_name']}")
        print(f"   Enhanced: {preview['enhanced_name']}")
        print(f"   Components:")
        components = preview['components']
        print(f"     Date: {components.date}")
        print(f"     Project: {components.project}")
        print(f"     Client: {components.client}")
        print(f"     Content: {components.content_type}")
        print(f"     Version: {components.version}")
        
        if preview['is_meaningful_change']:
            print(f"   ✅ Meaningful improvement")
        else:
            print(f"   ⚠️  Minimal change")

if __name__ == "__main__":
    test_naming_protocol()