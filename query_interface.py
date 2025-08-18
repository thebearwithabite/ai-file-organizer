#!/usr/bin/env python3
"""
Natural Language Query Interface for Local LLM Librarian
Provides intelligent file search with natural language understanding
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict

from content_extractor import ContentExtractor
from classification_engine import FileClassificationEngine
from staging_monitor import StagingMonitor

@dataclass
class QueryResult:
    """Result of a natural language query"""
    file_path: str
    filename: str
    relevance_score: float
    matching_content: str
    file_category: str
    last_modified: datetime
    file_size: int
    confidence: float
    reasoning: List[str]

class QueryProcessor:
    """
    Processes natural language queries and returns intelligent results
    Combines semantic search, file classification, and temporal analysis
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "Documents"
        
        # Initialize components
        self.content_extractor = ContentExtractor(base_dir)
        self.classifier = FileClassificationEngine(base_dir)
        self.staging_monitor = StagingMonitor(base_dir)
        
        # Query patterns and entity extraction
        self.entity_patterns = self._init_entity_patterns()
        self.temporal_patterns = self._init_temporal_patterns()
    
    def _init_entity_patterns(self) -> Dict[str, List[str]]:
        """Initialize entity recognition patterns"""
        return {
            'people': [
                r'finn\s*wolfhard?', r'stranger\s*things', r'netflix',
                r'refinery', r'artist\s*management', r'mnt'
            ],
            'projects': [
                r'papers\s*that\s*dream', r'podcast', r'episode',
                r'stranger\s*things', r'netflix', r'refinery'
            ],
            'document_types': [
                r'contract', r'agreement', r'script', r'audio',
                r'payment', r'report', r'invoice', r'tax',
                r'notebook', r'code', r'development'
            ],
            'file_types': [
                r'pdf', r'docx?', r'pages', r'mp3', r'wav', r'audio',
                r'image', r'photo', r'video', r'code', r'python', r'jupyter'
            ]
        }
    
    def _init_temporal_patterns(self) -> Dict[str, str]:
        """Initialize temporal expression patterns"""
        return {
            r'today|this\s+day': 'today',
            r'yesterday': 'yesterday', 
            r'this\s+week': 'this_week',
            r'last\s+week': 'last_week',
            r'this\s+month': 'this_month',
            r'last\s+month': 'last_month',
            r'this\s+year': 'this_year',
            r'last\s+year': 'last_year',
            r'recent|recently': 'recent',
            r'(\d{4})': 'year',  # Specific year
            r'(january|february|march|april|may|june|july|august|september|october|november|december)': 'month',
            r'(\d{1,2}\/\d{1,2}\/\d{4})': 'date'  # MM/DD/YYYY
        }
    
    def parse_query(self, query: str) -> Dict[str, any]:
        """Parse natural language query into structured components"""
        query_lower = query.lower()
        
        parsed = {
            'original_query': query,
            'intent': self._detect_intent(query_lower),
            'entities': self._extract_entities(query_lower),
            'temporal': self._extract_temporal(query_lower),
            'keywords': self._extract_keywords(query_lower),
            'search_terms': []
        }
        
        # Generate search terms from entities and keywords
        for entity_type, entities in parsed['entities'].items():
            parsed['search_terms'].extend(entities)
        parsed['search_terms'].extend(parsed['keywords'])
        
        return parsed
    
    def _detect_intent(self, query: str) -> str:
        """Detect the primary intent of the query"""
        intents = {
            'find': [r'find', r'search', r'show', r'get', r'where', r'locate'],
            'list': [r'list', r'all', r'everything', r'show me all'],
            'recent': [r'recent', r'latest', r'new', r'updated'],
            'related': [r'related', r'similar', r'connected', r'about'],
            'temporal': [r'when', r'date', r'time', r'ago', r'last', r'this'],
            'category': [r'type', r'kind', r'category', r'files']
        }
        
        for intent, patterns in intents.items():
            if any(re.search(pattern, query) for pattern in patterns):
                return intent
        
        return 'find'  # Default intent
    
    def _extract_entities(self, query: str) -> Dict[str, List[str]]:
        """Extract named entities from query"""
        entities = defaultdict(list)
        
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, query, re.IGNORECASE)
                if matches:
                    entities[entity_type].extend(matches)
        
        return dict(entities)
    
    def _extract_temporal(self, query: str) -> Dict[str, any]:
        """Extract temporal information from query"""
        temporal = {'type': None, 'value': None, 'date_range': None}
        
        for pattern, temporal_type in self.temporal_patterns.items():
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                temporal['type'] = temporal_type
                temporal['value'] = match.group(0)
                temporal['date_range'] = self._convert_to_date_range(temporal_type, match.group(0))
                break
        
        return temporal
    
    def _convert_to_date_range(self, temporal_type: str, value: str) -> Tuple[datetime, datetime]:
        """Convert temporal expressions to date ranges"""
        now = datetime.now()
        
        if temporal_type == 'today':
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        elif temporal_type == 'yesterday':
            end = now.replace(hour=0, minute=0, second=0, microsecond=0)
            start = end - timedelta(days=1)
        elif temporal_type == 'this_week':
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7)
        elif temporal_type == 'last_week':
            end = now - timedelta(days=now.weekday())
            end = end.replace(hour=0, minute=0, second=0, microsecond=0)
            start = end - timedelta(days=7)
        elif temporal_type == 'this_month':
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if now.month == 12:
                end = now.replace(year=now.year + 1, month=1, day=1)
            else:
                end = now.replace(month=now.month + 1, day=1)
        elif temporal_type == 'last_month':
            if now.month == 1:
                end = now.replace(year=now.year - 1, month=12, day=1)
                start = now.replace(year=now.year - 1, month=11, day=1)
            else:
                end = now.replace(month=now.month, day=1)
                start = now.replace(month=now.month - 1, day=1)
        elif temporal_type == 'recent':
            start = now - timedelta(days=7)  # Last week
            end = now
        elif temporal_type == 'year' and value.isdigit():
            year = int(value)
            start = datetime(year, 1, 1)
            end = datetime(year + 1, 1, 1)
        else:
            # Default to recent if can't parse
            start = now - timedelta(days=30)
            end = now
        
        return start, end
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract meaningful keywords from query"""
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'can', 'about', 'find', 'search',
            'show', 'get', 'me', 'my', 'i', 'you', 'all', 'any', 'some'
        }
        
        # Extract words, remove punctuation
        words = re.findall(r'\b\w+\b', query.lower())
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        return keywords
    
    def search(self, query: str, limit: int = 10) -> List[QueryResult]:
        """Perform intelligent search based on natural language query"""
        # Parse the query
        parsed = self.parse_query(query)
        
        # Multi-stage search strategy
        results = []
        
        # Stage 1: Direct content search
        if parsed['search_terms']:
            content_results = self._search_content(parsed, limit * 2)
            results.extend(content_results)
        
        # Stage 2: Filename-based search
        filename_results = self._search_filenames(parsed, limit)
        results.extend(filename_results)
        
        # Stage 3: Temporal filtering
        if parsed['temporal']['type']:
            results = self._apply_temporal_filter(results, parsed['temporal'])
        
        # Stage 4: Entity-based boosting
        results = self._boost_entity_matches(results, parsed['entities'])
        
        # Deduplicate and sort by relevance
        unique_results = self._deduplicate_results(results)
        sorted_results = sorted(unique_results, key=lambda x: x.relevance_score, reverse=True)
        
        return sorted_results[:limit]
    
    def _search_content(self, parsed: Dict, limit: int) -> List[QueryResult]:
        """Search within file contents"""
        results = []
        
        # Create search query for FTS
        search_query = ' OR '.join(parsed['search_terms'][:5])  # Limit terms for FTS
        
        try:
            content_matches = self.content_extractor.search_content(search_query, limit)
            
            for match in content_matches:
                file_path = Path(match['file_path'])
                if not file_path.exists():
                    continue
                
                stat = file_path.stat()
                
                result = QueryResult(
                    file_path=str(file_path),
                    filename=file_path.name,
                    relevance_score=0.8,  # High for content matches
                    matching_content=match['snippet'],
                    file_category=self._classify_file_quickly(file_path),
                    last_modified=datetime.fromtimestamp(stat.st_mtime),
                    file_size=stat.st_size,
                    confidence=0.8,
                    reasoning=['Content match', f"Found in: {match['snippet'][:100]}..."]
                )
                
                results.append(result)
                
        except Exception as e:
            print(f"Content search error: {e}")
        
        return results
    
    def _search_filenames(self, parsed: Dict, limit: int) -> List[QueryResult]:
        """Search based on filenames and paths"""
        results = []
        
        # Search in common locations
        search_locations = [
            self.base_dir / "01_ACTIVE_PROJECTS",
            self.base_dir / "02_MEDIA_ASSETS", 
            self.base_dir / "03_ARCHIVE_REFERENCE",
            Path.home() / "Desktop",
            Path.home() / "Downloads"
        ]
        
        for location in search_locations:
            if not location.exists():
                continue
                
            for file_path in location.rglob('*'):
                if not file_path.is_file() or len(results) >= limit:
                    continue
                
                filename_lower = file_path.name.lower()
                path_lower = str(file_path).lower()
                
                # Check if any search terms match filename or path
                matches = 0
                matching_terms = []
                
                for term in parsed['search_terms']:
                    if term.lower() in filename_lower or term.lower() in path_lower:
                        matches += 1
                        matching_terms.append(term)
                
                if matches > 0:
                    stat = file_path.stat()
                    relevance = min(matches / len(parsed['search_terms']), 1.0) * 0.6
                    
                    result = QueryResult(
                        file_path=str(file_path),
                        filename=file_path.name,
                        relevance_score=relevance,
                        matching_content=f"Filename matches: {', '.join(matching_terms)}",
                        file_category=self._classify_file_quickly(file_path),
                        last_modified=datetime.fromtimestamp(stat.st_mtime),
                        file_size=stat.st_size,
                        confidence=0.6,
                        reasoning=['Filename match', f"Terms found: {', '.join(matching_terms)}"]
                    )
                    
                    results.append(result)
        
        return results
    
    def _classify_file_quickly(self, file_path: Path) -> str:
        """Quick file classification for search results"""
        try:
            classification = self.classifier.classify_file(file_path)
            return classification.category
        except:
            # Fallback to extension-based classification
            ext = file_path.suffix.lower()
            if ext in ['.pdf', '.docx', '.pages']:
                return 'document'
            elif ext in ['.mp3', '.wav', '.aiff', '.m4a']:
                return 'audio'
            elif ext in ['.jpg', '.jpeg', '.png', '.gif']:
                return 'image'
            elif ext in ['.py', '.js', '.html', '.ipynb']:
                return 'code'
            else:
                return 'unknown'
    
    def _apply_temporal_filter(self, results: List[QueryResult], temporal: Dict) -> List[QueryResult]:
        """Filter results based on temporal criteria"""
        if not temporal['date_range']:
            return results
        
        start_date, end_date = temporal['date_range']
        filtered = []
        
        for result in results:
            if start_date <= result.last_modified <= end_date:
                # Boost relevance for temporal matches
                result.relevance_score += 0.1
                result.reasoning.append(f"Modified {temporal['type']}")
                filtered.append(result)
        
        return filtered if filtered else results  # Return original if no matches
    
    def _boost_entity_matches(self, results: List[QueryResult], entities: Dict[str, List[str]]) -> List[QueryResult]:
        """Boost relevance for entity matches"""
        for result in results:
            filename_lower = result.filename.lower()
            path_lower = result.file_path.lower()
            content_lower = result.matching_content.lower()
            
            entity_boost = 0
            matched_entities = []
            
            for entity_type, entity_list in entities.items():
                for entity in entity_list:
                    if (entity.lower() in filename_lower or 
                        entity.lower() in path_lower or 
                        entity.lower() in content_lower):
                        entity_boost += 0.15
                        matched_entities.append(f"{entity_type}:{entity}")
            
            if entity_boost > 0:
                result.relevance_score += min(entity_boost, 0.3)  # Cap boost
                result.reasoning.append(f"Entity matches: {', '.join(matched_entities)}")
        
        return results
    
    def _deduplicate_results(self, results: List[QueryResult]) -> List[QueryResult]:
        """Remove duplicate results, keeping highest relevance"""
        seen_paths = {}
        
        for result in results:
            path = result.file_path
            if path not in seen_paths or result.relevance_score > seen_paths[path].relevance_score:
                seen_paths[path] = result
        
        return list(seen_paths.values())
    
    def get_quick_suggestions(self, partial_query: str) -> List[str]:
        """Get quick search suggestions based on partial query"""
        suggestions = []
        
        # Common search patterns
        common_searches = [
            "Find Finn Wolfhard contracts",
            "Show me recent audio files",
            "Scripts from last month",
            "Financial documents from 2024", 
            "Development projects",
            "Papers That Dream episodes",
            "Refinery payment reports",
            "Stranger Things files",
            "Recent notebooks"
        ]
        
        partial_lower = partial_query.lower()
        
        # Filter suggestions that match partial query
        for search in common_searches:
            if partial_lower in search.lower():
                suggestions.append(search)
        
        return suggestions[:5]

class LocalLibrarian:
    """
    Main interface for the Local LLM Librarian system
    Combines all components for intelligent file management and search
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "Documents"
        self.query_processor = QueryProcessor(base_dir)
        
    def search(self, query: str, limit: int = 10) -> List[QueryResult]:
        """Main search interface"""
        return self.query_processor.search(query, limit)
    
    def get_suggestions(self, partial_query: str) -> List[str]:
        """Get search suggestions"""
        return self.query_processor.get_quick_suggestions(partial_query)
    
    def get_system_status(self) -> Dict[str, any]:
        """Get system status and statistics"""
        content_stats = self.query_processor.content_extractor.get_extraction_stats()
        staging_stats = self.query_processor.staging_monitor.get_staging_stats()
        
        return {
            'content_extraction': content_stats,
            'staging_system': staging_stats,
            'last_updated': datetime.now().isoformat()
        }

def test_query_interface():
    """Test the natural language query interface"""
    print("🧪 Testing Natural Language Query Interface")
    print("-" * 40)
    
    # Initialize librarian
    librarian = LocalLibrarian()
    
    # Test queries
    test_queries = [
        "Find Finn Wolfhard contracts",
        "Show me recent audio files",
        "Financial documents from 2024",
        "Development projects",
        "Files about Refinery"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        results = librarian.search(query, limit=3)
        
        if results:
            print(f"  Found {len(results)} results:")
            for i, result in enumerate(results, 1):
                print(f"    [{i}] {result.filename}")
                print(f"        📊 Relevance: {result.relevance_score:.2f}")
                print(f"        📂 Category: {result.file_category}")
                print(f"        💭 Reasoning: {', '.join(result.reasoning[:2])}")
                print(f"        🔍 Content: {result.matching_content[:100]}...")
        else:
            print("  No results found")
    
    # Test system status
    print(f"\n📊 System Status:")
    status = librarian.get_system_status()
    
    content_stats = status['content_extraction']
    print(f"  Content Index: {content_stats['total_files']} files, {content_stats['success_rate']:.1f}% success")
    
    staging_stats = status['staging_system']
    print(f"  Staging Monitor: {staging_stats['total_active_files']} active files")
    
    print(f"\n✅ Query interface test completed!")

if __name__ == "__main__":
    test_query_interface()