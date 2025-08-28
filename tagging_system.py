#!/usr/bin/env python3
"""
Comprehensive Tagging System with Auto-Tagging for AI File Organizer
Generates meaningful tags from content and enables tag-based file discovery
ADHD-friendly design with smart suggestions and cross-referencing
"""

import sys
import os
import sqlite3
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from collections import Counter, defaultdict
import hashlib

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from content_extractor import ContentExtractor

@dataclass
class TaggedFile:
    """Represents a file with its tags"""
    file_path: Path
    auto_tags: List[str]
    user_tags: List[str]
    confidence_scores: Dict[str, float]
    tag_sources: Dict[str, str]  # tag -> source (content, filename, user, etc.)
    last_tagged: datetime
    file_hash: str

@dataclass
class TagSuggestion:
    """Represents a suggested tag with reasoning"""
    tag: str
    confidence: float
    source: str
    reasoning: str
    similar_files: List[Path]

class ComprehensiveTaggingSystem:
    """
    Advanced tagging system that automatically generates meaningful tags
    and enables intelligent file discovery through tag relationships
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "Documents" / "AI_ORGANIZER_BASE"
        self.tagging_dir = self.base_dir / "04_METADATA_SYSTEM" / "tagging_system"
        self.tagging_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize content extractor
        self.content_extractor = ContentExtractor(str(self.base_dir))
        
        # Database for tagging system
        self.db_path = self.tagging_dir / "tagging_system.db"
        self._init_tagging_db()
        
        # Tag extraction patterns
        self.tag_patterns = {
            # People and Characters (more selective)
            'people': {
                'patterns': [
                    r'\b(Client Name|Client Name|User|Alex|Maya|Torres|Dr\. Chen)\b',
                    r'\b(Mr\.|Ms\.|Dr\.|Prof\.) [A-Z][a-z]+\b',  # Only with titles
                ],
                'weight': 0.8,
                'prefix': 'person:'
            },
            
            # Organizations and Companies
            'organizations': {
                'patterns': [
                    r'\b(Netflix|SAG-AFTRA|Management Company|Refinery|Apple|Google|Sony|Warner|Disney)\b',
                    r'\b([A-Z][a-z]+ (Inc|LLC|Corp|Company|Studios|Entertainment))\b',
                ],
                'weight': 0.7,
                'prefix': 'org:'
            },
            
            # Projects and Shows
            'projects': {
                'patterns': [
                    r'\b(TV Show|Creative Project|Papers That Dream|Stranger Things)\b',
                    r'\b(Season \d+|Episode \d+|Chapter \d+)\b',
                    r'\bProject [A-Z][a-z]+',
                ],
                'weight': 0.9,
                'prefix': 'project:'
            },
            
            # Legal and Business Terms
            'business': {
                'patterns': [
                    r'\b(contract|agreement|deal memo|NDA|exclusive|commission|payment|invoice)\b',
                    r'\b(royalty|residual|advance|option|rights|license)\b',
                    r'\b(deadline|milestone|deliverable|scope of work)\b',
                ],
                'weight': 0.6,
                'prefix': 'business:'
            },
            
            # Creative Content
            'creative': {
                'patterns': [
                    r'\b(script|screenplay|treatment|pitch|outline|character|dialogue)\b',
                    r'\b(scene|act|fade in|fade out|interior|exterior)\b',
                    r'\b(draft|revision|final|shooting|production)\b',
                ],
                'weight': 0.7,
                'prefix': 'creative:'
            },
            
            # Technical Terms
            'technical': {
                'patterns': [
                    r'\b(AI|artificial intelligence|machine learning|neural network|algorithm)\b',
                    r'\b(code|programming|development|software|API|database)\b',
                    r'\b(automation|workflow|system|process|integration)\b',
                ],
                'weight': 0.6,
                'prefix': 'tech:'
            },
            
            # Dates and Time
            'temporal': {
                'patterns': [
                    r'\b(2024|2025|2026)\b',
                    r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\b',
                    r'\b(Q1|Q2|Q3|Q4|quarter|annual|monthly|weekly)\b',
                ],
                'weight': 0.4,
                'prefix': 'time:'
            },
            
            # Content Types
            'content_type': {
                'patterns': [
                    r'\b(meeting|interview|presentation|report|memo|notes)\b',
                    r'\b(email|correspondence|communication|discussion)\b',
                    r'\b(research|analysis|summary|review|feedback)\b',
                ],
                'weight': 0.5,
                'prefix': 'type:'
            }
        }
        
        # Filename-based tag extraction
        self.filename_patterns = {
            'file_types': {
                'contract': r'(contract|agreement|deal)',
                'script': r'(script|screenplay|treatment)',
                'invoice': r'(invoice|payment|bill)',
                'meeting': r'(meeting|notes|minutes)',
                'draft': r'(draft|v\d+|version)',
                'final': r'(final|approved|signed)'
            },
            'projects': {
                'stranger_things': r'(stranger|things|netflix|hawkins)',
                'creative_project': r'(creative.project|podcast|consciousness)',
                'client_work': r'(client|management|talent)',
                'personal': r'(personal|private|own)'
            }
        }
        
        # Stop words to avoid as tags
        self.stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above',
            'below', 'between', 'among', 'this', 'that', 'these', 'those', 'a', 'an', 'is',
            'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
            'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'shall'
        }
    
    def _init_tagging_db(self):
        """Initialize SQLite database for tagging system"""
        with sqlite3.connect(self.db_path) as conn:
            # File tags table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT,
                    file_name TEXT,
                    file_extension TEXT,
                    file_hash TEXT,
                    auto_tags TEXT,  -- JSON array
                    user_tags TEXT,  -- JSON array
                    confidence_scores TEXT,  -- JSON object
                    tag_sources TEXT,  -- JSON object
                    last_tagged TEXT,
                    created_date TEXT,
                    UNIQUE(file_path)
                )
            """)
            
            # Tag relationships table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tag_relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tag1 TEXT,
                    tag2 TEXT,
                    co_occurrence_count INTEGER,
                    relationship_strength REAL,
                    last_updated TEXT,
                    UNIQUE(tag1, tag2)
                )
            """)
            
            # Tag statistics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tag_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tag TEXT UNIQUE,
                    usage_count INTEGER,
                    file_count INTEGER,
                    category TEXT,
                    average_confidence REAL,
                    first_seen TEXT,
                    last_seen TEXT
                )
            """)
            
            # Tag aliases table (for similar tags)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tag_aliases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    canonical_tag TEXT,
                    alias_tag TEXT,
                    similarity_score REAL,
                    created_date TEXT,
                    UNIQUE(canonical_tag, alias_tag)
                )
            """)
            
            conn.commit()
    
    def extract_tags_from_content(self, content: str, file_path: Path) -> Tuple[List[str], Dict[str, float], Dict[str, str]]:
        """Extract tags from file content using pattern matching"""
        
        tags = []
        confidence_scores = {}
        tag_sources = {}
        
        content_lower = content.lower()
        
        # Extract using predefined patterns
        for category, config in self.tag_patterns.items():
            patterns = config['patterns']
            weight = config['weight']
            prefix = config.get('prefix', '')
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]  # Take first group if tuple
                    
                    # Clean up the match
                    tag = match.strip().lower()
                    
                    # Skip stop words and very short tags
                    if tag in self.stop_words or len(tag) < 2:
                        continue
                    
                    # Apply prefix if specified
                    if prefix and not tag.startswith(prefix):
                        final_tag = f"{prefix}{tag}"
                    else:
                        final_tag = tag
                    
                    tags.append(final_tag)
                    confidence_scores[final_tag] = weight
                    tag_sources[final_tag] = f"content_{category}"
        
        # Extract from filename
        filename_tags, filename_confidences, filename_sources = self.extract_tags_from_filename(file_path)
        tags.extend(filename_tags)
        confidence_scores.update(filename_confidences)
        tag_sources.update(filename_sources)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_tags = []
        for tag in tags:
            if tag not in seen:
                unique_tags.append(tag)
                seen.add(tag)
        
        return unique_tags, confidence_scores, tag_sources
    
    def extract_tags_from_filename(self, file_path: Path) -> Tuple[List[str], Dict[str, float], Dict[str, str]]:
        """Extract tags from filename patterns"""
        
        tags = []
        confidence_scores = {}
        tag_sources = {}
        
        filename_lower = file_path.name.lower()
        
        # Check filename patterns
        for category, patterns in self.filename_patterns.items():
            for tag_name, pattern in patterns.items():
                if re.search(pattern, filename_lower):
                    tags.append(tag_name)
                    confidence_scores[tag_name] = 0.8
                    tag_sources[tag_name] = f"filename_{category}"
        
        # Extract date from filename
        date_patterns = [
            r'(\d{4}[-_]\d{2}[-_]\d{2})',  # 2025-08-22 or 2025_08_22
            r'(\d{2}[-_]\d{2}[-_]\d{4})',  # 08-22-2025 or 08_22_2025
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, filename_lower)
            for match in matches:
                # Normalize date format
                date_tag = match.replace('_', '-')
                tags.append(f"date:{date_tag}")
                confidence_scores[f"date:{date_tag}"] = 0.6
                tag_sources[f"date:{date_tag}"] = "filename_date"
        
        # Extract version numbers
        version_pattern = r'v(\d+)|version[_\s]*(\d+)'
        version_matches = re.findall(version_pattern, filename_lower)
        for match in version_matches:
            version_num = match[0] or match[1]
            if version_num:
                version_tag = f"version:{version_num}"
                tags.append(version_tag)
                confidence_scores[version_tag] = 0.7
                tag_sources[version_tag] = "filename_version"
        
        return tags, confidence_scores, tag_sources
    
    def generate_contextual_tags(self, content: str, existing_tags: List[str]) -> List[str]:
        """Generate additional contextual tags based on content and existing tags"""
        
        contextual_tags = []
        content_lower = content.lower()
        
        # Industry-specific context
        if any(tag in ['netflix', 'sag-aftra', 'contract', 'agreement'] for tag in existing_tags):
            if 'exclusive' in content_lower:
                contextual_tags.append('exclusive_deal')
            if 'commission' in content_lower:
                contextual_tags.append('commission_based')
            if 'residual' in content_lower:
                contextual_tags.append('residual_payments')
        
        # Creative context
        if any(tag in ['script', 'screenplay', 'creative'] for tag in existing_tags):
            if 'character' in content_lower:
                contextual_tags.append('character_development')
            if 'scene' in content_lower:
                contextual_tags.append('scene_work')
            if 'dialogue' in content_lower:
                contextual_tags.append('dialogue_heavy')
        
        # AI/Tech context
        if any(tag in ['ai', 'artificial_intelligence', 'tech:'] for tag in existing_tags):
            if 'consciousness' in content_lower:
                contextual_tags.append('ai_consciousness')
            if 'automation' in content_lower:
                contextual_tags.append('automation_focus')
            if 'algorithm' in content_lower:
                contextual_tags.append('algorithmic')
        
        # Business context
        if any(tag in ['business:', 'invoice', 'payment'] for tag in existing_tags):
            if 'tax' in content_lower:
                contextual_tags.append('tax_related')
            if 'quarterly' in content_lower:
                contextual_tags.append('quarterly_report')
            if 'annual' in content_lower:
                contextual_tags.append('annual_document')
        
        return contextual_tags
    
    def tag_file(self, file_path: Path, user_tags: List[str] = None) -> TaggedFile:
        """Comprehensively tag a single file"""
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Extract content
        content_result = self.content_extractor.extract_content(file_path)
        content = content_result.get('text', '') if content_result.get('success') else ''
        
        # Extract auto tags
        auto_tags, confidence_scores, tag_sources = self.extract_tags_from_content(content, file_path)
        
        # Generate contextual tags
        contextual_tags = self.generate_contextual_tags(content, auto_tags)
        auto_tags.extend(contextual_tags)
        
        # Add contextual tag confidences
        for ctx_tag in contextual_tags:
            confidence_scores[ctx_tag] = 0.6
            tag_sources[ctx_tag] = "contextual"
        
        # Merge with user tags
        user_tags = user_tags or []
        for user_tag in user_tags:
            confidence_scores[user_tag] = 1.0
            tag_sources[user_tag] = "user"
        
        # Calculate file hash
        file_hash = self._calculate_file_hash(file_path)
        
        # Create tagged file object
        tagged_file = TaggedFile(
            file_path=file_path,
            auto_tags=auto_tags,
            user_tags=user_tags,
            confidence_scores=confidence_scores,
            tag_sources=tag_sources,
            last_tagged=datetime.now(),
            file_hash=file_hash
        )
        
        return tagged_file
    
    def save_tagged_file(self, tagged_file: TaggedFile) -> bool:
        """Save tagged file to database"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO file_tags
                    (file_path, file_name, file_extension, file_hash, auto_tags, user_tags,
                     confidence_scores, tag_sources, last_tagged, created_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(tagged_file.file_path),
                    tagged_file.file_path.name,
                    tagged_file.file_path.suffix.lower(),
                    tagged_file.file_hash,
                    json.dumps(tagged_file.auto_tags),
                    json.dumps(tagged_file.user_tags),
                    json.dumps(tagged_file.confidence_scores),
                    json.dumps(tagged_file.tag_sources),
                    tagged_file.last_tagged.isoformat(),
                    datetime.now().isoformat()
                ))
                conn.commit()
            
            # Update tag relationships and statistics
            self._update_tag_relationships(tagged_file)
            self._update_tag_statistics(tagged_file)
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving tagged file: {e}")
            return False
    
    def _update_tag_relationships(self, tagged_file: TaggedFile):
        """Update co-occurrence relationships between tags"""
        
        all_tags = tagged_file.auto_tags + tagged_file.user_tags
        
        with sqlite3.connect(self.db_path) as conn:
            # Update co-occurrence counts for all tag pairs
            for i, tag1 in enumerate(all_tags):
                for tag2 in all_tags[i+1:]:
                    # Ensure consistent ordering
                    if tag1 > tag2:
                        tag1, tag2 = tag2, tag1
                    
                    # Update or insert relationship
                    conn.execute("""
                        INSERT OR REPLACE INTO tag_relationships
                        (tag1, tag2, co_occurrence_count, relationship_strength, last_updated)
                        VALUES (?, ?, 
                               COALESCE((SELECT co_occurrence_count FROM tag_relationships 
                                       WHERE tag1=? AND tag2=?), 0) + 1,
                               COALESCE((SELECT relationship_strength FROM tag_relationships 
                                       WHERE tag1=? AND tag2=?), 0) + 0.1,
                               ?)
                    """, (tag1, tag2, tag1, tag2, tag1, tag2, datetime.now().isoformat()))
            
            conn.commit()
    
    def _update_tag_statistics(self, tagged_file: TaggedFile):
        """Update usage statistics for tags"""
        
        all_tags = tagged_file.auto_tags + tagged_file.user_tags
        
        with sqlite3.connect(self.db_path) as conn:
            for tag in all_tags:
                confidence = tagged_file.confidence_scores.get(tag, 0.5)
                
                conn.execute("""
                    INSERT OR REPLACE INTO tag_statistics
                    (tag, usage_count, file_count, category, average_confidence, first_seen, last_seen)
                    VALUES (?, 
                           COALESCE((SELECT usage_count FROM tag_statistics WHERE tag=?), 0) + 1,
                           COALESCE((SELECT file_count FROM tag_statistics WHERE tag=?), 0) + 1,
                           ?,
                           (COALESCE((SELECT average_confidence FROM tag_statistics WHERE tag=?), 0) + ?) / 2,
                           COALESCE((SELECT first_seen FROM tag_statistics WHERE tag=?), ?),
                           ?)
                """, (tag, tag, tag, 
                     self._get_tag_category(tag), 
                     tag, confidence, 
                     tag, datetime.now().isoformat(),
                     datetime.now().isoformat()))
            
            conn.commit()
    
    def _get_tag_category(self, tag: str) -> str:
        """Determine category of a tag based on prefix or content"""
        
        if ':' in tag:
            return tag.split(':', 1)[0]
        
        # Check content-based categories
        for category, config in self.tag_patterns.items():
            patterns = config.get('patterns', [])
            for pattern in patterns:
                if re.search(pattern.replace(r'\b', ''), tag, re.IGNORECASE):
                    return category
        
        return 'general'
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate file hash for change detection"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except:
            return ""
    
    def find_files_by_tags(self, tags: List[str], match_all: bool = False, 
                          limit: int = 50) -> List[Dict]:
        """Find files that match specified tags"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM file_tags")
            columns = [desc[0] for desc in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                file_data = dict(zip(columns, row))
                
                file_auto_tags = json.loads(file_data['auto_tags'])
                file_user_tags = json.loads(file_data['user_tags'])
                all_file_tags = file_auto_tags + file_user_tags
                
                # Check tag matching
                if match_all:
                    # All specified tags must be present
                    if all(tag in all_file_tags for tag in tags):
                        file_data['matching_tags'] = tags
                        file_data['all_tags'] = all_file_tags
                        results.append(file_data)
                else:
                    # Any specified tag must be present
                    matching_tags = [tag for tag in tags if tag in all_file_tags]
                    if matching_tags:
                        file_data['matching_tags'] = matching_tags
                        file_data['all_tags'] = all_file_tags
                        results.append(file_data)
            
            # Sort by number of matching tags (descending)
            results.sort(key=lambda x: len(x['matching_tags']), reverse=True)
            
            return results[:limit]
    
    def suggest_tags(self, file_path: Path, content: str = None) -> List[TagSuggestion]:
        """Suggest tags for a file based on similar files and patterns"""
        
        suggestions = []
        
        if not content:
            content_result = self.content_extractor.extract_content(file_path)
            content = content_result.get('text', '') if content_result.get('success') else ''
        
        # Get existing tags for this file
        existing_tags = self.get_file_tags(file_path)
        existing_tag_names = existing_tags.get('auto_tags', []) + existing_tags.get('user_tags', [])
        
        # Find similar files by extension and name patterns
        similar_files = self._find_similar_files(file_path)
        
        # Analyze tags from similar files
        if similar_files:
            tag_frequency = Counter()
            
            for similar_file in similar_files:
                similar_tags = self.get_file_tags(Path(similar_file['file_path']))
                if similar_tags:
                    all_tags = similar_tags.get('auto_tags', []) + similar_tags.get('user_tags', [])
                    for tag in all_tags:
                        if tag not in existing_tag_names:
                            tag_frequency[tag] += 1
            
            # Create suggestions from frequent tags
            for tag, frequency in tag_frequency.most_common(10):
                confidence = min(frequency / len(similar_files), 1.0)
                
                suggestions.append(TagSuggestion(
                    tag=tag,
                    confidence=confidence,
                    source="similar_files",
                    reasoning=f"Found in {frequency} similar files",
                    similar_files=[Path(f['file_path']) for f in similar_files[:3]]
                ))
        
        # Add pattern-based suggestions
        potential_tags, confidences, sources = self.extract_tags_from_content(content, file_path)
        
        for tag in potential_tags:
            if tag not in existing_tag_names:
                suggestions.append(TagSuggestion(
                    tag=tag,
                    confidence=confidences.get(tag, 0.5),
                    source=sources.get(tag, "pattern_matching"),
                    reasoning=f"Detected from {sources.get(tag, 'content')}",
                    similar_files=[]
                ))
        
        # Sort by confidence
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        
        return suggestions[:20]  # Top 20 suggestions
    
    def _find_similar_files(self, file_path: Path) -> List[Dict]:
        """Find files similar to the given file"""
        
        similar_files = []
        file_ext = file_path.suffix.lower()
        filename_lower = file_path.name.lower()
        
        with sqlite3.connect(self.db_path) as conn:
            # Find files with same extension
            cursor = conn.execute("""
                SELECT * FROM file_tags WHERE file_extension = ? AND file_path != ?
                ORDER BY last_tagged DESC LIMIT 10
            """, (file_ext, str(file_path)))
            
            columns = [desc[0] for desc in cursor.description]
            
            for row in cursor.fetchall():
                file_data = dict(zip(columns, row))
                similar_files.append(file_data)
        
        return similar_files
    
    def get_file_tags(self, file_path: Path) -> Optional[Dict]:
        """Get all tags for a specific file"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM file_tags WHERE file_path = ?
            """, (str(file_path),))
            
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                file_data = dict(zip(columns, row))
                
                # Parse JSON fields
                file_data['auto_tags'] = json.loads(file_data['auto_tags'])
                file_data['user_tags'] = json.loads(file_data['user_tags'])
                file_data['confidence_scores'] = json.loads(file_data['confidence_scores'])
                file_data['tag_sources'] = json.loads(file_data['tag_sources'])
                
                return file_data
        
        return None
    
    def get_tag_statistics(self) -> Dict[str, Any]:
        """Get comprehensive tag usage statistics"""
        
        with sqlite3.connect(self.db_path) as conn:
            # Most used tags
            cursor = conn.execute("""
                SELECT tag, usage_count, file_count, category, average_confidence
                FROM tag_statistics 
                ORDER BY usage_count DESC 
                LIMIT 50
            """)
            
            most_used = [dict(zip([desc[0] for desc in cursor.description], row)) 
                        for row in cursor.fetchall()]
            
            # Tag categories distribution
            cursor = conn.execute("""
                SELECT category, COUNT(*) as count, SUM(usage_count) as total_usage
                FROM tag_statistics 
                GROUP BY category 
                ORDER BY total_usage DESC
            """)
            
            categories = [dict(zip([desc[0] for desc in cursor.description], row)) 
                         for row in cursor.fetchall()]
            
            # Recent activity
            cursor = conn.execute("""
                SELECT COUNT(*) as total_files, 
                       COUNT(DISTINCT file_path) as unique_files
                FROM file_tags
                WHERE last_tagged > datetime('now', '-7 days')
            """)
            
            recent_activity = cursor.fetchone()
            
            return {
                'most_used_tags': most_used,
                'category_distribution': categories,
                'recent_activity': {
                    'files_tagged_last_week': recent_activity[0],
                    'unique_files_tagged': recent_activity[1]
                },
                'total_tags': len(most_used),
                'generated_at': datetime.now().isoformat()
            }

def test_tagging_system():
    """Test the comprehensive tagging system"""
    
    print("🧪 Testing Comprehensive Tagging System")
    print("=" * 60)
    
    tagger = ComprehensiveTaggingSystem()
    
    # Find test files
    test_dirs = [
        Path("/Users/user/Github/ai-file-organizer"),
        Path.home() / "Downloads",
        Path.home() / "Desktop"
    ]
    
    test_files = []
    for test_dir in test_dirs:
        if test_dir.exists():
            files = [f for f in test_dir.glob("*.md") if f.is_file()][:2]
            test_files.extend(files)
            if len(test_files) >= 3:
                break
    
    if not test_files:
        print("❌ No test files found")
        return
    
    print(f"📁 Testing with {len(test_files)} files")
    
    for i, test_file in enumerate(test_files, 1):
        print(f"\n📄 [{i}] Tagging: {test_file.name}")
        
        try:
            # Tag the file
            tagged_file = tagger.tag_file(test_file)
            
            print(f"   🏷️  Auto tags ({len(tagged_file.auto_tags)}): {', '.join(tagged_file.auto_tags[:5])}")
            
            if len(tagged_file.auto_tags) > 5:
                print(f"      ... and {len(tagged_file.auto_tags) - 5} more")
            
            # Show top confidence scores
            top_confident = sorted(tagged_file.confidence_scores.items(), 
                                 key=lambda x: x[1], reverse=True)[:3]
            print(f"   🎯 Top confident: {', '.join([f'{tag}({score:.1%})' for tag, score in top_confident])}")
            
            # Save to database
            success = tagger.save_tagged_file(tagged_file)
            print(f"   💾 Saved: {'✅' if success else '❌'}")
            
            # Test tag suggestions
            suggestions = tagger.suggest_tags(test_file)
            if suggestions:
                print(f"   💡 Suggestions: {', '.join([s.tag for s in suggestions[:3]])}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Test file search by tags
    print(f"\n🔍 Testing tag-based search:")
    
    # Search for files with common tags
    common_tags = ['project:', 'creative:', 'tech:']
    
    for tag in common_tags:
        results = tagger.find_files_by_tags([tag], match_all=False, limit=3)
        if results:
            print(f"   🏷️  '{tag}': Found {len(results)} files")
            for result in results[:2]:
                file_name = Path(result['file_path']).name
                matching = ', '.join(result['matching_tags'])
                print(f"      📄 {file_name} (tags: {matching})")
    
    # Show statistics
    print(f"\n📊 Tag Statistics:")
    stats = tagger.get_tag_statistics()
    
    print(f"   Total unique tags: {stats['total_tags']}")
    print(f"   Files tagged this week: {stats['recent_activity']['files_tagged_last_week']}")
    
    if stats['most_used_tags']:
        print(f"   Most used tags:")
        for tag_info in stats['most_used_tags'][:5]:
            print(f"      {tag_info['tag']}: {tag_info['usage_count']} uses")
    
    print(f"\n✅ Tagging system test completed!")

if __name__ == "__main__":
    test_tagging_system()