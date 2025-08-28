#!/usr/bin/env python3
"""
Custom Category System for AI File Organizer
Allows users to create and train custom file categories beyond the default set
Based on AudioAI custom category patterns but for document organization
"""

import sys
import os
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import re

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from content_extractor import ContentExtractor

class CustomCategoryManager:
    """
    Manages custom user-defined categories and training examples
    Like AudioAI but for document classification and organization
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "Documents" / "AI_ORGANIZER_BASE"
        self.categories_dir = self.base_dir / "04_METADATA_SYSTEM" / "custom_categories"
        self.categories_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize content extractor
        self.content_extractor = ContentExtractor(str(self.base_dir))
        
        # Database for custom categories
        self.db_path = self.categories_dir / "custom_categories.db"
        self._init_categories_db()
        
        # Load built-in category templates
        self.default_categories = self._load_default_categories()
    
    def _init_categories_db(self):
        """Initialize SQLite database for custom categories"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS custom_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_name TEXT UNIQUE,
                    display_name TEXT,
                    description TEXT,
                    parent_category TEXT,
                    keywords TEXT,  -- JSON array of keywords
                    patterns TEXT,  -- JSON array of regex patterns
                    file_types TEXT,  -- JSON array of supported file types
                    created_date TEXT,
                    updated_date TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    usage_count INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS training_examples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_name TEXT,
                    example_file_path TEXT,
                    content_sample TEXT,
                    keywords_found TEXT,  -- JSON array
                    confidence_score REAL,
                    added_date TEXT,
                    added_by TEXT,  -- 'user' or 'system'
                    is_positive_example BOOLEAN DEFAULT 1,
                    FOREIGN KEY (category_name) REFERENCES custom_categories (category_name)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS category_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_name TEXT,
                    rule_type TEXT,  -- 'keyword', 'pattern', 'file_extension', 'content_length'
                    rule_value TEXT,
                    weight REAL DEFAULT 1.0,
                    created_date TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (category_name) REFERENCES custom_categories (category_name)
                )
            """)
            
            conn.commit()
    
    def _load_default_categories(self) -> Dict[str, Dict]:
        """Load built-in category templates that users can customize"""
        return {
            'entertainment_contracts': {
                'display_name': 'Entertainment Contracts',
                'description': 'SAG-AFTRA agreements, talent contracts, management deals',
                'keywords': ['sag-aftra', 'contract', 'agreement', 'talent', 'management', 'exclusive', 'commission'],
                'patterns': [r'sag.aftra', r'exclusive.{1,50}management', r'commission.{1,20}percent'],
                'file_types': ['.pdf', '.docx', '.doc']
            },
            'creative_scripts': {
                'display_name': 'Creative Scripts',
                'description': 'TV scripts, film screenplays, creative writing',
                'keywords': ['int.', 'ext.', 'fade in', 'fade out', 'character', 'dialogue', 'scene'],
                'patterns': [r'INT\.|EXT\.', r'FADE IN:', r'FADE OUT:', r'[A-Z]{2,}\s*\n'],
                'file_types': ['.pdf', '.txt', '.fountain', '.fdx']
            },
            'business_invoices': {
                'display_name': 'Business Invoices',
                'description': 'Client invoices, commission statements, payment records',
                'keywords': ['invoice', 'payment', 'commission', 'due date', 'amount', 'bill to', 'remit to'],
                'patterns': [r'invoice.{1,20}\d+', r'due.{1,10}\d{1,2}\/\d{1,2}\/\d{4}', r'\$[\d,]+\.\d{2}'],
                'file_types': ['.pdf', '.xlsx', '.csv']
            },
            'ai_research': {
                'display_name': 'AI Research Papers',
                'description': 'Academic papers, AI research, consciousness studies',
                'keywords': ['abstract', 'artificial intelligence', 'machine learning', 'neural network', 'consciousness'],
                'patterns': [r'abstract', r'introduction', r'methodology', r'results', r'conclusion', r'arxiv:\d+'],
                'file_types': ['.pdf', '.tex', '.md']
            },
            'email_archives': {
                'display_name': 'Important Emails',
                'description': 'Business correspondence, project discussions, client communications',
                'keywords': ['from:', 'to:', 'subject:', 're:', 'fwd:', 'meeting', 'project'],
                'patterns': [r'from:.*@.*\.', r'subject:.*', r'meeting.{1,30}(tomorrow|today|monday|tuesday)'],
                'file_types': ['.emlx', '.eml', '.msg']
            }
        }
    
    def create_custom_category(self, category_name: str, display_name: str, 
                             description: str, keywords: List[str] = None,
                             patterns: List[str] = None, file_types: List[str] = None,
                             parent_category: str = None) -> bool:
        """Create a new custom category"""
        
        try:
            # Validate category name
            if not re.match(r'^[a-z][a-z0-9_]*$', category_name):
                raise ValueError("Category name must be lowercase, start with letter, use only letters, numbers, and underscores")
            
            # Prepare data
            keywords = keywords or []
            patterns = patterns or []
            file_types = file_types or ['.pdf', '.docx', '.txt']
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO custom_categories 
                    (category_name, display_name, description, parent_category, 
                     keywords, patterns, file_types, created_date, updated_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    category_name, display_name, description, parent_category,
                    json.dumps(keywords), json.dumps(patterns), json.dumps(file_types),
                    datetime.now().isoformat(), datetime.now().isoformat()
                ))
                conn.commit()
            
            print(f"✅ Created custom category: {display_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error creating category: {e}")
            return False
    
    def add_training_example(self, category_name: str, file_path: str, 
                           is_positive: bool = True) -> bool:
        """Add a training example for a custom category"""
        
        try:
            # Extract content from file
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise FileNotFoundError(f"Training file not found: {file_path}")
            
            # Extract content
            content_result = self.content_extractor.extract_content(file_path_obj)
            
            if not content_result['success']:
                raise ValueError(f"Could not extract content from {file_path}")
            
            content = content_result['text'][:2000]  # First 2000 chars for analysis
            
            # Find keywords in content
            category_info = self.get_category_info(category_name)
            if not category_info:
                raise ValueError(f"Category {category_name} not found")
            
            keywords_found = []
            category_keywords = json.loads(category_info['keywords'])
            
            for keyword in category_keywords:
                if keyword.lower() in content.lower():
                    keywords_found.append(keyword)
            
            # Calculate confidence based on keyword matches
            confidence = len(keywords_found) / max(len(category_keywords), 1) if category_keywords else 0.5
            
            # Save training example
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO training_examples
                    (category_name, example_file_path, content_sample, keywords_found,
                     confidence_score, added_date, added_by, is_positive_example)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    category_name, file_path, content, json.dumps(keywords_found),
                    confidence, datetime.now().isoformat(), 'user', is_positive
                ))
                conn.commit()
            
            print(f"✅ Added training example for {category_name}")
            print(f"   Keywords found: {keywords_found}")
            print(f"   Confidence: {confidence:.1%}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error adding training example: {e}")
            return False
    
    def classify_with_custom_categories(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Classify a file using custom categories"""
        
        try:
            # Extract content
            content_result = self.content_extractor.extract_content(file_path)
            if not content_result['success']:
                return None
            
            content = content_result['text']
            if not content:
                return None
            
            content_lower = content.lower()
            
            # Get all active custom categories
            categories = self.list_categories(active_only=True)
            
            best_match = None
            best_score = 0.0
            
            for category in categories:
                score = self._calculate_category_score(content_lower, category, file_path.suffix.lower())
                
                if score > best_score:
                    best_score = score
                    best_match = category
            
            if best_match and best_score > 0.3:  # Minimum confidence threshold
                # Update usage count
                self._increment_usage_count(best_match['category_name'])
                
                return {
                    'category': best_match['category_name'],
                    'display_name': best_match['display_name'],
                    'confidence': best_score,
                    'source': 'custom_categories'
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Error in custom classification: {e}")
            return None
    
    def _calculate_category_score(self, content_lower: str, category: Dict, file_extension: str) -> float:
        """Calculate how well content matches a category"""
        
        score = 0.0
        
        # File type matching (20% weight)
        file_types = json.loads(category['file_types'])
        if file_extension in file_types:
            score += 0.2
        
        # Keyword matching (50% weight)
        keywords = json.loads(category['keywords'])
        if keywords:
            keyword_matches = sum(1 for keyword in keywords if keyword.lower() in content_lower)
            keyword_score = keyword_matches / len(keywords)
            score += keyword_score * 0.5
        
        # Pattern matching (30% weight)
        patterns = json.loads(category['patterns'])
        if patterns:
            pattern_matches = 0
            for pattern in patterns:
                try:
                    if re.search(pattern, content_lower, re.IGNORECASE):
                        pattern_matches += 1
                except re.error:
                    continue  # Skip invalid patterns
            
            if patterns:
                pattern_score = pattern_matches / len(patterns)
                score += pattern_score * 0.3
        
        return min(score, 1.0)  # Cap at 100%
    
    def _increment_usage_count(self, category_name: str):
        """Increment usage count for a category"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE custom_categories 
                SET usage_count = usage_count + 1, updated_date = ?
                WHERE category_name = ?
            """, (datetime.now().isoformat(), category_name))
            conn.commit()
    
    def get_category_info(self, category_name: str) -> Optional[Dict]:
        """Get detailed information about a custom category"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM custom_categories WHERE category_name = ?
            """, (category_name,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
    
    def list_categories(self, active_only: bool = True) -> List[Dict]:
        """List all custom categories"""
        
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT * FROM custom_categories"
            if active_only:
                query += " WHERE is_active = 1"
            query += " ORDER BY usage_count DESC, display_name"
            
            cursor = conn.execute(query)
            columns = [desc[0] for desc in cursor.description]
            
            categories = []
            for row in cursor.fetchall():
                category = dict(zip(columns, row))
                categories.append(category)
            
            return categories
    
    def get_training_examples(self, category_name: str) -> List[Dict]:
        """Get training examples for a category"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM training_examples 
                WHERE category_name = ?
                ORDER BY added_date DESC
            """, (category_name,))
            
            columns = [desc[0] for desc in cursor.description]
            examples = []
            
            for row in cursor.fetchall():
                example = dict(zip(columns, row))
                examples.append(example)
            
            return examples
    
    def update_category(self, category_name: str, **updates) -> bool:
        """Update an existing custom category"""
        
        try:
            allowed_fields = ['display_name', 'description', 'parent_category', 'keywords', 'patterns', 'file_types']
            
            update_fields = []
            update_values = []
            
            for field, value in updates.items():
                if field in allowed_fields:
                    if field in ['keywords', 'patterns', 'file_types'] and isinstance(value, list):
                        value = json.dumps(value)
                    update_fields.append(f"{field} = ?")
                    update_values.append(value)
            
            if not update_fields:
                return False
            
            update_fields.append("updated_date = ?")
            update_values.append(datetime.now().isoformat())
            update_values.append(category_name)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(f"""
                    UPDATE custom_categories 
                    SET {', '.join(update_fields)}
                    WHERE category_name = ?
                """, update_values)
                conn.commit()
            
            print(f"✅ Updated category: {category_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error updating category: {e}")
            return False
    
    def delete_category(self, category_name: str, confirm: bool = False) -> bool:
        """Delete a custom category and its training examples"""
        
        if not confirm:
            print(f"⚠️  Use confirm=True to actually delete category {category_name}")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Delete training examples first
                conn.execute("DELETE FROM training_examples WHERE category_name = ?", (category_name,))
                
                # Delete category rules
                conn.execute("DELETE FROM category_rules WHERE category_name = ?", (category_name,))
                
                # Delete category
                conn.execute("DELETE FROM custom_categories WHERE category_name = ?", (category_name,))
                
                conn.commit()
            
            print(f"✅ Deleted category: {category_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error deleting category: {e}")
            return False
    
    def install_default_categories(self) -> int:
        """Install built-in category templates"""
        
        installed = 0
        
        for category_key, template in self.default_categories.items():
            success = self.create_custom_category(
                category_name=category_key,
                display_name=template['display_name'],
                description=template['description'],
                keywords=template['keywords'],
                patterns=template['patterns'],
                file_types=template['file_types']
            )
            
            if success:
                installed += 1
        
        print(f"✅ Installed {installed} default categories")
        return installed

def test_custom_categories():
    """Test the custom category system"""
    
    print("🧪 Testing Custom Category System")
    print("=" * 50)
    
    manager = CustomCategoryManager()
    
    # Install default categories
    print("📦 Installing default categories...")
    installed = manager.install_default_categories()
    
    # List categories
    print(f"\n📊 Current categories:")
    categories = manager.list_categories()
    
    for category in categories:
        print(f"   {category['display_name']} ({category['category_name']})")
        print(f"      Keywords: {json.loads(category['keywords'])[:3]}...")  # Show first 3
    
    # Test classification on a sample file
    test_files = [
        Path.home() / "Downloads",
        Path.home() / "Desktop", 
        Path.home() / "Documents"
    ]
    
    for test_dir in test_files:
        if test_dir.exists():
            sample_files = [f for f in test_dir.iterdir() 
                           if f.is_file() and f.suffix.lower() in ['.pdf', '.txt', '.md']]
            
            if sample_files:
                test_file = sample_files[0]
                print(f"\n🔍 Testing classification on: {test_file.name}")
                
                result = manager.classify_with_custom_categories(test_file)
                
                if result:
                    print(f"   ✅ Classified as: {result['display_name']}")
                    print(f"   🎯 Confidence: {result['confidence']:.1%}")
                else:
                    print(f"   ❌ No custom category match found")
                break

if __name__ == "__main__":
    test_custom_categories()