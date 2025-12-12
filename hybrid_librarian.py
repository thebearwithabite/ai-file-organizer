#!/usr/bin/env python3
"""
Enhanced Hybrid Librarian - Semantic Search + Metadata
Combines your existing system with semantic embeddings for intelligent content understanding
"""

import sqlite3
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import json
import hashlib

try:
    # from sentence_transformers import SentenceTransformer
    # EMBEDDINGS_AVAILABLE = True
    EMBEDDINGS_AVAILABLE = False
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("⚠️  Install sentence-transformers for semantic search: pip install sentence-transformers")

from query_interface import QueryProcessor, QueryResult
from content_extractor import ContentExtractor
from classification_engine import FileClassificationEngine
from gdrive_integration import get_ai_organizer_root

@dataclass
class EnhancedQueryResult:
    """Enhanced result with semantic similarity"""
    file_path: str
    filename: str
    relevance_score: float
    semantic_score: float
    matching_content: str
    file_category: str
    tags: List[str]
    last_modified: datetime
    file_size: int
    reasoning: List[str]
    content_summary: str = ""
    key_concepts: List[str] = None

class HybridLibrarian:
    """
    Enhanced librarian combining:
    1. Your existing keyword/metadata search (fast)
    2. Semantic embeddings (smart content understanding)
    3. Intelligent query routing (choose best approach)
    """
    
    def __init__(self, base_dir: str = None):
        # Use Google Drive integration as primary storage root
        self.base_dir = Path(base_dir) if base_dir else get_ai_organizer_root()
        
        # Initialize your existing components
        self.query_processor = QueryProcessor(str(self.base_dir))
        self.content_extractor = ContentExtractor(str(self.base_dir))
        self.classifier = FileClassificationEngine(str(self.base_dir))
        
        # Semantic search setup
        self.embeddings_db_path = self.base_dir / "embeddings.db"
        self.model = None
        if EMBEDDINGS_AVAILABLE:
            self._init_semantic_search()
        
        # Query intelligence
        self.query_stats = {}
        self._load_query_patterns()
    
    def _init_semantic_search(self):
        """Initialize semantic search components"""
        try:
            # Use a lightweight, fast model for local processing
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            print("✅ Semantic search initialized")
        except Exception as e:
            print(f"⚠️  Could not load embedding model: {e}")
            self.model = None
        
        # Create embeddings database
        self._init_embeddings_db()
    
    def _init_embeddings_db(self):
        """Create database for storing embeddings"""
        with sqlite3.connect(self.embeddings_db_path) as conn:
            # File-level embeddings (legacy/summary)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_embeddings (
                    file_path TEXT PRIMARY KEY,
                    content_hash TEXT,
                    embedding BLOB,
                    content_summary TEXT,
                    key_concepts TEXT,
                    indexed_date TIMESTAMP,
                    file_size INTEGER,
                    last_modified TIMESTAMP
                )
            """)
            
            # Chunk-level embeddings (new)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    file_path TEXT,
                    chunk_index INTEGER,
                    chunk_type TEXT,
                    content TEXT,
                    embedding BLOB,
                    metadata TEXT,
                    FOREIGN KEY(file_path) REFERENCES file_embeddings(file_path)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS query_cache (
                    query_hash TEXT PRIMARY KEY,
                    query_text TEXT,
                    query_embedding BLOB,
                    result_paths TEXT,
                    timestamp TIMESTAMP
                )
            """)

    def _load_query_patterns(self):
        """Load patterns for intelligent query routing"""
        # Define what types of queries work best with each approach
        self.query_patterns = {
            'semantic_queries': [
                'about', 'related to', 'similar', 'discusses', 'mentions',
                'themes', 'concepts', 'ideas', 'meaning', 'content'
            ],
            'metadata_queries': [
                'created', 'modified', 'date', 'size', 'type', 'extension',
                'folder', 'path', 'recent', 'latest', 'yesterday'
            ],
            'entity_queries': [
                'Client Name', 'TV Show', 'refinery', 'Creative Project',
                'contract', 'agreement', 'payment', 'invoice'
            ]
        }
    
    def search(self, query: str, search_mode: str = "auto", limit: int = 10) -> List[EnhancedQueryResult]:
        """
        Intelligent search that chooses the best approach
        
        search_mode options:
        - "auto": Automatically choose best approach
        - "fast": Metadata/keyword only
        - "semantic": Semantic search only  
        - "hybrid": Combine both approaches
        """
        
        if search_mode == "auto":
            search_mode = self._determine_search_strategy(query)
        
        if search_mode == "fast":
            return self._fast_search(query, limit)
        elif search_mode == "semantic" and self.model:
            return self._semantic_search(query, limit)
        elif search_mode == "hybrid":
            return self._hybrid_search(query, limit)
        else:
            # Fallback to existing system
            return self._fast_search(query, limit)
    
    def _determine_search_strategy(self, query: str) -> str:
        """Intelligently choose search strategy based on query"""
        query_lower = query.lower()
        
        # Count semantic indicators
        semantic_score = sum(1 for pattern in self.query_patterns['semantic_queries'] 
                           if pattern in query_lower)
        
        # Count metadata indicators  
        metadata_score = sum(1 for pattern in self.query_patterns['metadata_queries']
                           if pattern in query_lower)
        
        # Count entity indicators
        entity_score = sum(1 for pattern in self.query_patterns['entity_queries']
                         if pattern in query_lower)
        
        # Decision logic
        if semantic_score > 0 and self.model:
            return "semantic"
        elif metadata_score > semantic_score:
            return "fast"
        elif entity_score > 0:
            return "fast"  # Your existing system handles entities well
        elif len(query.split()) > 5 and self.model:
            return "semantic"  # Long queries often need semantic understanding
        else:
            return "fast"
    
    def _fast_search(self, query: str, limit: int) -> List[EnhancedQueryResult]:
        """Use your existing fast search system"""
        results = self.query_processor.search(query, limit)
        
        # Convert to enhanced results
        enhanced_results = []
        for result in results:
            # Try to get tags from classification
            try:
                file_path = Path(result.file_path)
                classification = self.classifier.classify_file(file_path)
                tags = classification.tags if hasattr(classification, 'tags') else []
            except:
                tags = []
            
            enhanced = EnhancedQueryResult(
                file_path=result.file_path,
                filename=result.filename,
                relevance_score=result.relevance_score,
                semantic_score=0.0,  # No semantic analysis in fast mode
                matching_content=result.matching_content,
                file_category=result.file_category,
                tags=tags,
                last_modified=result.last_modified,
                file_size=result.file_size,
                reasoning=result.reasoning,
                content_summary="",
                key_concepts=[]
            )
            enhanced_results.append(enhanced)
        
        return enhanced_results

    def _hybrid_search(self, query: str, limit: int) -> List[EnhancedQueryResult]:
        """Combine fast search + semantic search for best results"""
        # Get fast results (your existing system)
        fast_results = self._fast_search(query, limit)
        
        # Get semantic results if available
        semantic_results = []
        if self.model:
            semantic_results = self._semantic_search(query, limit)
        
        # Combine and deduplicate
        all_results = {}
        
        # Add fast results with boosted scores for exact matches
        for result in fast_results:
            result.relevance_score *= 1.2  # Boost exact keyword matches
            all_results[result.file_path] = result
        
        # Add semantic results, merging with existing
        for result in semantic_results:
            if result.file_path in all_results:
                # Merge: take best of both scores
                existing = all_results[result.file_path]
                existing.semantic_score = result.semantic_score
                existing.relevance_score = max(existing.relevance_score, result.relevance_score)
                existing.content_summary = result.content_summary
                existing.key_concepts = result.key_concepts
                existing.reasoning.extend(result.reasoning)
            else:
                all_results[result.file_path] = result
        
        # Sort by combined relevance
        final_results = list(all_results.values())
        final_results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return final_results[:limit]
            
    def index_file_for_semantic_search(self, file_path: Path) -> bool:
        """Index a file for semantic search using Smart Chunking"""
        if not self.model:
            return False
        
        try:
            # Extract content
            extraction_result = self.content_extractor.extract_content(file_path)
            if not extraction_result['success']:
                return False
            
            content = extraction_result['text']
            if len(content.strip()) < 50:  # Skip very short content
                return False
            
            # 1. File-Level Indexing (Summary)
            # Generate summary and key concepts
            summary = self._generate_content_summary(content)
            key_concepts = self._extract_key_concepts(content)
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            # Generate file-level embedding (from summary + concepts)
            file_context = f"{summary}\nKey Concepts: {', '.join(key_concepts)}"
            file_embedding = self.model.encode(file_context)
            
            with sqlite3.connect(self.embeddings_db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO file_embeddings 
                    (file_path, content_hash, embedding, content_summary, key_concepts, 
                     indexed_date, file_size, last_modified)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(file_path),
                    content_hash,
                    file_embedding.tobytes(),
                    summary,
                    json.dumps(key_concepts),
                    datetime.now().isoformat(),
                    file_path.stat().st_size,
                    datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                ))
                
                # 2. Chunk-Level Indexing
                # Clear existing chunks for this file
                conn.execute("DELETE FROM file_chunks WHERE file_path = ?", (str(file_path),))
                
                # Use SmartChunker
                from chunking_utils import SmartChunker
                chunker = SmartChunker()
                chunks = chunker.chunk_document(content, str(file_path))
                
                for chunk in chunks:
                    chunk_embedding = self.model.encode(chunk.content)
                    
                    conn.execute("""
                        INSERT INTO file_chunks 
                        (chunk_id, file_path, chunk_index, chunk_type, content, embedding, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        chunk.chunk_id,
                        str(file_path),
                        chunk.chunk_index,
                        chunk.chunk_type,
                        chunk.content,
                        chunk_embedding.tobytes(),
                        json.dumps(chunk.metadata)
                    ))
            
            return True
            
        except Exception as e:
            print(f"Failed to index {file_path}: {e}")
            return False

    def _semantic_search(self, query: str, limit: int) -> List[EnhancedQueryResult]:
        """Semantic search using embeddings (Chunks + File Level)"""
        if not self.model:
            print("⚠️  Semantic search not available, falling back to fast search")
            return self._fast_search(query, limit)
        
        # Generate query embedding
        query_embedding = self.model.encode(query)
        
        results = []
        seen_files = set()
        
        with sqlite3.connect(self.embeddings_db_path) as conn:
            # Search Chunks First (More precise)
            cursor = conn.execute("""
                SELECT c.file_path, c.content, c.embedding, c.chunk_type, f.content_summary, f.key_concepts, f.last_modified, f.file_size
                FROM file_chunks c
                JOIN file_embeddings f ON c.file_path = f.file_path
                WHERE c.embedding IS NOT NULL
            """)
            
            chunk_matches = []
            for row in cursor.fetchall():
                file_path, content, embedding_blob, chunk_type, summary, concepts, modified, size = row
                
                if embedding_blob:
                    chunk_embedding = np.frombuffer(embedding_blob, dtype=np.float32)
                    similarity = np.dot(query_embedding, chunk_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding)
                    )
                    
                    if similarity > 0.3:
                        chunk_matches.append({
                            'file_path': file_path,
                            'similarity': similarity,
                            'content': content,
                            'chunk_type': chunk_type,
                            'summary': summary,
                            'concepts': concepts,
                            'modified': modified,
                            'size': size
                        })
            
            # Sort matches
            chunk_matches.sort(key=lambda x: x['similarity'], reverse=True)
            
            for match in chunk_matches:
                if match['file_path'] in seen_files:
                    continue
                    
                # Get file classification for tags
                try:
                    classification = self.classifier.classify_file(Path(match['file_path']))
                    tags = classification.tags if hasattr(classification, 'tags') else []
                    category = classification.category if hasattr(classification, 'category') else 'unknown'
                except:
                    tags = []
                    category = 'unknown'
                
                result = EnhancedQueryResult(
                    file_path=match['file_path'],
                    filename=Path(match['file_path']).name,
                    relevance_score=match['similarity'] * 100,
                    semantic_score=match['similarity'],
                    matching_content=match['content'][:200] + "..." if len(match['content']) > 200 else match['content'],
                    file_category=category,
                    tags=tags,
                    last_modified=datetime.fromisoformat(match['modified']) if match['modified'] else datetime.now(),
                    file_size=match['size'] or 0,
                    reasoning=[f"Semantic similarity: {match['similarity']:.1%}", f"Matched chunk: {match['chunk_type']}"],
                    content_summary=match['summary'] or "",
                    key_concepts=json.loads(match['concepts']) if match['concepts'] else []
                )
                results.append(result)
                seen_files.add(match['file_path'])
                
                if len(results) >= limit:
                    break
        
        return results
    
    def _generate_content_summary(self, content: str) -> str:
        """Generate a summary of file content"""
        # Simple extractive summary - take first meaningful sentences
        sentences = content.split('. ')
        meaningful_sentences = [s for s in sentences if len(s.split()) > 5]
        
        if meaningful_sentences:
            return '. '.join(meaningful_sentences[:3]) + '.'
        else:
            return content[:300] + "..." if len(content) > 300 else content
    
    def _extract_key_concepts(self, content: str) -> List[str]:
        """Extract key concepts from content"""
        # Simple keyword extraction based on your domain
        concepts = []
        content_lower = content.lower()
        
        # Entertainment industry terms
        entertainment_terms = [
            'Client Name', 'TV Show', 'netflix', 'actor', 'contract',
            'agreement', 'series', 'episode', 'production', 'casting'
        ]
        
        # Creative terms  
        creative_terms = [
            'podcast', 'episode', 'script', 'audio', 'story', 'narrative',
            'Creative Project', 'ai', 'research', 'consciousness'
        ]
        
        # Business terms
        business_terms = [
            'refinery', 'management', 'payment', 'commission', 'invoice',
            'financial', 'tax', 'business', 'legal'
        ]
        
        all_terms = entertainment_terms + creative_terms + business_terms
        
        for term in all_terms:
            if term in content_lower:
                concepts.append(term)
        
        return list(set(concepts))  # Remove duplicates
    
    def get_search_suggestions(self, partial_query: str) -> List[str]:
        """Enhanced search suggestions based on content and patterns"""
        suggestions = []
        
        # Your existing suggestions
        existing_suggestions = self.query_processor.get_suggestions(partial_query)
        suggestions.extend(existing_suggestions)
        
        # Add semantic-based suggestions
        if self.model and len(partial_query) > 3:
            # Look for semantically similar indexed content
            with sqlite3.connect(self.embeddings_db_path) as conn:
                cursor = conn.execute("""
                    SELECT DISTINCT key_concepts FROM file_embeddings 
                    WHERE key_concepts IS NOT NULL
                """)
                
                for (concepts_json,) in cursor.fetchall():
                    if concepts_json:
                        concepts = json.loads(concepts_json)
                        for concept in concepts:
                            if partial_query.lower() in concept.lower():
                                suggestions.append(f"Find files about {concept}")
        
        return list(set(suggestions))[:10]  # Deduplicate and limit
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get enhanced system statistics"""
        stats = {
            'semantic_search_available': self.model is not None,
            'files_indexed_semantically': 0,
            'total_chunks': 0,
            'embedding_model': 'all-MiniLM-L6-v2' if self.model else None
        }
        
        if self.embeddings_db_path.exists():
            with sqlite3.connect(self.embeddings_db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM file_embeddings")
                stats['files_indexed_semantically'] = cursor.fetchone()[0]
                
                # Check for chunks table
                try:
                    cursor = conn.execute("SELECT COUNT(*) FROM file_chunks")
                    stats['total_chunks'] = cursor.fetchone()[0]
                except:
                    pass
        
        return stats

def test_hybrid_librarian():
    """Test the enhanced librarian"""
    print("🧪 Testing Enhanced Hybrid Librarian")
    print("-" * 50)
    
    librarian = HybridLibrarian()
    
    # Test queries that demonstrate different capabilities
    test_queries = [
        "Find Client Name contracts",  # Should use fast search (entities)
        "Documents about AI consciousness",  # Should use semantic search
        "Files created last week",  # Should use fast search (metadata)
        "Content similar to attention mechanisms"  # Should use semantic search
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        
        # Show which strategy would be chosen
        strategy = librarian._determine_search_strategy(query)
        print(f"Strategy: {strategy}")
        
        # Run the search
        results = librarian.search(query, search_mode="auto", limit=3)
        
        if results:
            print(f"Found {len(results)} results:")
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result.filename}")
                print(f"     Relevance: {result.relevance_score:.1f}%")
                if result.semantic_score > 0:
                    print(f"     Semantic: {result.semantic_score:.1%}")
                print(f"     Tags: {', '.join(result.tags[:3]) if result.tags else 'None'}")
        else:
            print("  No results found")
    
    # Show system stats
    stats = librarian.get_system_stats()
    print(f"\n📊 System Stats:")
    print(f"  Semantic search: {'✅' if stats['semantic_search_available'] else '❌'}")
    print(f"  Files indexed: {stats['files_indexed_semantically']}")

if __name__ == "__main__":
    test_hybrid_librarian()