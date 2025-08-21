#!/usr/bin/env python3
"""
Vector-Powered Librarian with Smart Chunking
Enhanced semantic search using ChromaDB for full document understanding
"""

import re
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("⚠️  Install ChromaDB for enhanced vector search: pip install chromadb")

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("⚠️  Install sentence-transformers: pip install sentence-transformers")

from hybrid_librarian import HybridLibrarian, EnhancedQueryResult
from content_extractor import ContentExtractor
from classification_engine import FileClassificationEngine
from email_extractor import EmailExtractor

@dataclass
class DocumentChunk:
    """Represents a chunk of a document for vector indexing"""
    chunk_id: str
    file_path: str
    chunk_index: int
    content: str
    chunk_type: str  # 'header', 'body', 'conclusion', 'metadata'
    metadata: Dict[str, Any]

class SmartChunker:
    """
    Intelligent document chunking for your specific file types
    Understands entertainment contracts, scripts, business docs
    """
    
    def __init__(self):
        # Contract section patterns
        self.contract_patterns = {
            'header': [r'agreement', r'contract', r'parties', r'whereas'],
            'compensation': [r'payment', r'salary', r'fee', r'compensation', r'royalty'],
            'terms': [r'term', r'duration', r'period', r'expiry', r'termination'],
            'exclusivity': [r'exclusiv', r'non-compete', r'restriction', r'limitation'],
            'rights': [r'rights', r'license', r'permission', r'usage', r'territory'],
            'obligations': [r'shall', r'must', r'required', r'responsible', r'duty']
        }
        
        # Creative content patterns
        self.creative_patterns = {
            'scene': [r'scene \d+', r'act \d+', r'chapter \d+'],
            'dialogue': [r':', r'said', r'spoke', r'replied'],
            'action': [r'fade in', r'cut to', r'sound', r'music'],
            'character': [r'character', r'protagonist', r'narrator']
        }
        
        # Business document patterns
        self.business_patterns = {
            'financial': [r'revenue', r'profit', r'loss', r'tax', r'expense'],
            'legal': [r'liability', r'indemnify', r'breach', r'default'],
            'operational': [r'procedure', r'process', r'workflow', r'responsibility']
        }
        
        # Email patterns
        self.email_patterns = {
            'meeting': [r'meeting', r'schedule', r'calendar', r'appointment'],
            'business': [r'contract', r'deal', r'agreement', r'negotiation'],
            'personal': [r'thank you', r'thanks', r'regards', r'best'],
            'urgent': [r'urgent', r'asap', r'immediate', r'deadline'],
            'creative': [r'script', r'project', r'creative', r'production']
        }
    
    def chunk_document(self, content: str, file_path: str, max_chunk_size: int = 200) -> List[DocumentChunk]:
        """Smart chunking based on document type and content structure"""
        chunks = []
        file_type = self._detect_file_type(content, file_path)
        
        if file_type == 'contract':
            chunks = self._chunk_contract(content, file_path, max_chunk_size)
        elif file_type == 'script':
            chunks = self._chunk_script(content, file_path, max_chunk_size)
        elif file_type == 'business':
            chunks = self._chunk_business_doc(content, file_path, max_chunk_size)
        elif file_type == 'email':
            chunks = self._chunk_email(content, file_path, max_chunk_size)
        else:
            chunks = self._chunk_generic(content, file_path, max_chunk_size)
        
        return chunks
    
    def _detect_file_type(self, content: str, file_path: str) -> str:
        """Detect document type for appropriate chunking strategy"""
        content_lower = content.lower()
        filename = Path(file_path).name.lower()
        
        # Check for contract indicators
        contract_indicators = ['agreement', 'contract', 'whereas', 'party', 'consideration']
        if any(indicator in content_lower for indicator in contract_indicators):
            return 'contract'
        
        # Check for script indicators
        script_indicators = ['scene', 'fade in', 'cut to', 'dialogue', 'character']
        if any(indicator in content_lower for indicator in script_indicators):
            return 'script'
        
        # Check for business document indicators
        business_indicators = ['revenue', 'financial', 'invoice', 'payment', 'commission']
        if any(indicator in content_lower for indicator in business_indicators):
            return 'business'
        
        # Check for email indicators
        if 'from:' in content_lower and 'to:' in content_lower:
            return 'email'
        
        return 'generic'
    
    def _chunk_contract(self, content: str, file_path: str, max_chunk_size: int) -> List[DocumentChunk]:
        """Chunk entertainment contracts by logical sections"""
        chunks = []
        
        # Split into paragraphs first
        paragraphs = content.split('\n\n')
        current_chunk = ""
        current_type = "body"
        chunk_index = 0
        
        for para in paragraphs:
            para_lower = para.lower()
            
            # Determine chunk type based on content
            chunk_type = "body"  # default
            for section, patterns in self.contract_patterns.items():
                if any(pattern in para_lower for pattern in patterns):
                    chunk_type = section
                    break
            
            # If adding this paragraph would exceed size, create chunk
            if len(current_chunk.split()) + len(para.split()) > max_chunk_size:
                if current_chunk.strip():
                    chunks.append(DocumentChunk(
                        chunk_id=f"{hashlib.md5(file_path.encode()).hexdigest()[:8]}_{chunk_index}",
                        file_path=file_path,
                        chunk_index=chunk_index,
                        content=current_chunk.strip(),
                        chunk_type=current_type,
                        metadata={'section': current_type, 'doc_type': 'contract'}
                    ))
                    chunk_index += 1
                
                current_chunk = para
                current_type = chunk_type
            else:
                current_chunk += "\n\n" + para
                if chunk_type != "body":  # Priority to more specific types
                    current_type = chunk_type
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(DocumentChunk(
                chunk_id=f"{hashlib.md5(file_path.encode()).hexdigest()[:8]}_{chunk_index}",
                file_path=file_path,
                chunk_index=chunk_index,
                content=current_chunk.strip(),
                chunk_type=current_type,
                metadata={'section': current_type, 'doc_type': 'contract'}
            ))
        
        return chunks
    
    def _chunk_script(self, content: str, file_path: str, max_chunk_size: int) -> List[DocumentChunk]:
        """Chunk scripts by scenes/sections"""
        chunks = []
        
        # Try to split by scene markers
        scene_splits = re.split(r'(SCENE \d+|ACT \d+|FADE IN|CUT TO)', content, flags=re.IGNORECASE)
        
        current_chunk = ""
        chunk_index = 0
        
        for i, section in enumerate(scene_splits):
            if len(current_chunk.split()) + len(section.split()) > max_chunk_size:
                if current_chunk.strip():
                    chunks.append(DocumentChunk(
                        chunk_id=f"{hashlib.md5(file_path.encode()).hexdigest()[:8]}_{chunk_index}",
                        file_path=file_path,
                        chunk_index=chunk_index,
                        content=current_chunk.strip(),
                        chunk_type="scene",
                        metadata={'doc_type': 'script', 'scene_number': chunk_index}
                    ))
                    chunk_index += 1
                current_chunk = section
            else:
                current_chunk += section
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(DocumentChunk(
                chunk_id=f"{hashlib.md5(file_path.encode()).hexdigest()[:8]}_{chunk_index}",
                file_path=file_path,
                chunk_index=chunk_index,
                content=current_chunk.strip(),
                chunk_type="scene",
                metadata={'doc_type': 'script', 'scene_number': chunk_index}
            ))
        
        return chunks
    
    def _chunk_business_doc(self, content: str, file_path: str, max_chunk_size: int) -> List[DocumentChunk]:
        """Chunk business documents by topics"""
        chunks = []
        
        # Split by sections/headers
        lines = content.split('\n')
        current_chunk = ""
        current_type = "general"
        chunk_index = 0
        
        for line in lines:
            line_lower = line.lower()
            
            # Detect section type
            section_type = "general"
            for section, patterns in self.business_patterns.items():
                if any(pattern in line_lower for pattern in patterns):
                    section_type = section
                    break
            
            # Check if we need to create a new chunk
            if len(current_chunk.split()) + len(line.split()) > max_chunk_size:
                if current_chunk.strip():
                    chunks.append(DocumentChunk(
                        chunk_id=f"{hashlib.md5(file_path.encode()).hexdigest()[:8]}_{chunk_index}",
                        file_path=file_path,
                        chunk_index=chunk_index,
                        content=current_chunk.strip(),
                        chunk_type=current_type,
                        metadata={'section': current_type, 'doc_type': 'business'}
                    ))
                    chunk_index += 1
                current_chunk = line
                current_type = section_type
            else:
                current_chunk += "\n" + line
                if section_type != "general":
                    current_type = section_type
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(DocumentChunk(
                chunk_id=f"{hashlib.md5(file_path.encode()).hexdigest()[:8]}_{chunk_index}",
                file_path=file_path,
                chunk_index=chunk_index,
                content=current_chunk.strip(),
                chunk_type=current_type,
                metadata={'section': current_type, 'doc_type': 'business'}
            ))
        
        return chunks
    
    def _chunk_email(self, content: str, file_path: str, max_chunk_size: int) -> List[DocumentChunk]:
        """Chunk emails by headers and content sections"""
        chunks = []
        
        # Split email into header and body sections
        lines = content.split('\n')
        header_section = ""
        body_section = ""
        in_body = False
        
        for line in lines:
            if not in_body and (line.startswith('From:') or line.startswith('To:') or line.startswith('Subject:')):
                header_section += line + '\n'
            elif line.strip() == "" and not in_body:
                in_body = True
            elif in_body:
                body_section += line + '\n'
        
        chunk_index = 0
        
        # Create header chunk
        if header_section.strip():
            chunks.append(DocumentChunk(
                chunk_id=f"{hashlib.md5(file_path.encode()).hexdigest()[:8]}_{chunk_index}",
                file_path=file_path,
                chunk_index=chunk_index,
                content=header_section.strip(),
                chunk_type="header",
                metadata={'section': 'header', 'doc_type': 'email'}
            ))
            chunk_index += 1
        
        # Chunk body by email patterns
        if body_section.strip():
            body_lower = body_section.lower()
            
            # Determine email type
            email_type = "general"
            for section, patterns in self.email_patterns.items():
                if any(pattern in body_lower for pattern in patterns):
                    email_type = section
                    break
            
            # Split body into chunks
            words = body_section.split()
            for i in range(0, len(words), max_chunk_size):
                chunk_words = words[i:i + max_chunk_size]
                chunk_content = ' '.join(chunk_words)
                
                chunks.append(DocumentChunk(
                    chunk_id=f"{hashlib.md5(file_path.encode()).hexdigest()[:8]}_{chunk_index}",
                    file_path=file_path,
                    chunk_index=chunk_index,
                    content=chunk_content,
                    chunk_type=email_type,
                    metadata={'section': email_type, 'doc_type': 'email'}
                ))
                chunk_index += 1
        
        return chunks
    
    def _chunk_generic(self, content: str, file_path: str, max_chunk_size: int) -> List[DocumentChunk]:
        """Generic chunking for other document types"""
        chunks = []
        words = content.split()
        
        for i in range(0, len(words), max_chunk_size):
            chunk_words = words[i:i + max_chunk_size]
            chunk_content = ' '.join(chunk_words)
            
            chunk = DocumentChunk(
                chunk_id=f"{hashlib.md5(file_path.encode()).hexdigest()[:8]}_{i // max_chunk_size}",
                file_path=file_path,
                chunk_index=i // max_chunk_size,
                content=chunk_content,
                chunk_type="content",
                metadata={'doc_type': 'generic', 'word_offset': i}
            )
            chunks.append(chunk)
        
        return chunks

class VectorLibrarian:
    """
    Vector-powered librarian using ChromaDB for advanced semantic search
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "Documents"
        
        # Initialize existing components
        self.content_extractor = ContentExtractor(str(self.base_dir))
        self.classifier = FileClassificationEngine(str(self.base_dir))
        self.chunker = SmartChunker()
        self.email_extractor = EmailExtractor()
        
        # Vector database setup
        self.chroma_client = None
        self.collection = None
        
        if CHROMADB_AVAILABLE and EMBEDDINGS_AVAILABLE:
            self._init_vector_db()
        else:
            print("⚠️  Vector search not available. Install: pip install chromadb sentence-transformers")
    
    def _init_vector_db(self):
        """Initialize ChromaDB for vector storage"""
        try:
            # Create persistent ChromaDB client
            db_path = str(self.base_dir / "04_METADATA_SYSTEM" / "vector_db")
            
            self.chroma_client = chromadb.PersistentClient(
                path=db_path,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get or create collection for file chunks
            self.collection = self.chroma_client.get_or_create_collection(
                name="file_chunks",
                metadata={"description": "Ryan's intelligent file organization system"}
            )
            
            print("✅ Vector database initialized")
            
        except Exception as e:
            print(f"⚠️  Could not initialize vector database: {e}")
            self.chroma_client = None
            self.collection = None
    
    def index_file_with_chunks(self, file_path: Path) -> bool:
        """Index a file using smart chunking for full content coverage"""
        if not self.collection:
            return False
        
        try:
            # Extract full content - handle emails specially
            if file_path.suffix == '.emlx':
                extraction_result = self.email_extractor.extract_email_content(file_path)
            else:
                extraction_result = self.content_extractor.extract_content(file_path)
            
            if not extraction_result['success']:
                return False
            
            content = extraction_result['text']
            if len(content.strip()) < 50:
                return False
            
            # Smart chunking
            chunks = self.chunker.chunk_document(content, str(file_path))
            
            if not chunks:
                return False
            
            # Prepare data for ChromaDB
            chunk_ids = []
            chunk_contents = []
            chunk_metadatas = []
            
            for chunk in chunks:
                # Get file classification for metadata
                try:
                    classification = self.classifier.classify_file(file_path)
                    tags = classification.tags if hasattr(classification, 'tags') else []
                    category = classification.category if hasattr(classification, 'category') else 'unknown'
                except:
                    tags = []
                    category = 'unknown'
                
                # Enhanced metadata
                metadata = {
                    'file_path': str(file_path),
                    'filename': file_path.name,
                    'chunk_index': chunk.chunk_index,
                    'chunk_type': chunk.chunk_type,
                    'file_category': category,
                    'tags': ','.join(tags),
                    'file_size': file_path.stat().st_size,
                    'last_modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                    'indexed_at': datetime.now().isoformat(),
                    **chunk.metadata
                }
                
                # Add email-specific metadata
                if file_path.suffix == '.emlx' and hasattr(extraction_result, 'get'):
                    metadata.update({
                        'email_subject': extraction_result.get('subject', ''),
                        'email_from': extraction_result.get('from', ''),
                        'email_to': extraction_result.get('to', ''),
                        'email_date': extraction_result.get('date', '').isoformat() if extraction_result.get('date') else ''
                    })
                
                chunk_ids.append(chunk.chunk_id)
                chunk_contents.append(chunk.content)
                chunk_metadatas.append(metadata)
            
            # Add to ChromaDB
            self.collection.add(
                ids=chunk_ids,
                documents=chunk_contents,
                metadatas=chunk_metadatas
            )
            
            print(f"✅ Indexed {len(chunks)} chunks from {file_path.name}")
            return True
            
        except Exception as e:
            print(f"Failed to index {file_path}: {e}")
            return False
    
    def index_document(self, file_path: Path, content: str) -> bool:
        """Index a document with provided content (for background monitor)"""
        try:
            # Use the existing index_file method with content
            chunks = self.chunker.chunk_document(content, str(file_path))
            
            if not chunks:
                print(f"No content to index for {file_path.name}")
                return False
            
            # Process chunks similar to index_file
            chunk_ids = []
            chunk_contents = []
            chunk_metadatas = []
            
            for chunk in chunks:
                # Extract key information for tags
                words = chunk.content.lower().split()
                important_words = [w for w in words if len(w) > 3 and w.isalpha()]
                tags = important_words[:10]  # Top 10 meaningful words
                
                metadata = {
                    'file_path': str(file_path),
                    'file_name': file_path.name,
                    'chunk_index': chunk.chunk_index,
                    'chunk_type': chunk.chunk_type,
                    'tags': ','.join(tags),
                    'file_size': file_path.stat().st_size if file_path.exists() else 0,
                    'last_modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat() if file_path.exists() else datetime.now().isoformat(),
                    'indexed_at': datetime.now().isoformat(),
                    **chunk.metadata
                }
                
                chunk_ids.append(chunk.chunk_id)
                chunk_contents.append(chunk.content)
                chunk_metadatas.append(metadata)
            
            # Add to ChromaDB
            self.collection.add(
                ids=chunk_ids,
                documents=chunk_contents,
                metadatas=chunk_metadatas
            )
            
            print(f"✅ Indexed {len(chunks)} chunks from {file_path.name}")
            return True
            
        except Exception as e:
            print(f"Failed to index document {file_path}: {e}")
            return False
    
    def index_email(self, file_path: Path, email_data: dict) -> bool:
        """Index email content (for background monitor)"""
        try:
            if not email_data.get('success', False):
                return False
            
            # Combine email parts for chunking
            email_content = ""
            if email_data.get('headers'):
                email_content += f"Subject: {email_data['headers'].get('subject', '')}\n"
                email_content += f"From: {email_data['headers'].get('from', '')}\n"
                email_content += f"To: {email_data['headers'].get('to', '')}\n"
                email_content += f"Date: {email_data['headers'].get('date', '')}\n\n"
            
            if email_data.get('body'):
                email_content += email_data['body']
            
            # Chunk the email content
            chunks = self.chunker._chunk_email(email_content, str(file_path), 500)
            
            if not chunks:
                print(f"No email content to index for {file_path.name}")
                return False
            
            # Process email chunks
            chunk_ids = []
            chunk_contents = []
            chunk_metadatas = []
            
            for chunk in chunks:
                metadata = {
                    'file_path': str(file_path),
                    'file_name': file_path.name,
                    'chunk_index': chunk.chunk_index,
                    'chunk_type': chunk.chunk_type,
                    'file_size': file_path.stat().st_size if file_path.exists() else 0,
                    'last_modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat() if file_path.exists() else datetime.now().isoformat(),
                    'indexed_at': datetime.now().isoformat(),
                    'content_type': 'email',
                    **chunk.metadata
                }
                
                # Add email-specific metadata
                if email_data.get('headers'):
                    metadata.update({
                        'email_subject': email_data['headers'].get('subject', ''),
                        'email_from': email_data['headers'].get('from', ''),
                        'email_to': email_data['headers'].get('to', ''),
                        'email_date': str(email_data['headers'].get('date', ''))
                    })
                
                chunk_ids.append(chunk.chunk_id)
                chunk_contents.append(chunk.content)
                chunk_metadatas.append(metadata)
            
            # Add to ChromaDB
            self.collection.add(
                ids=chunk_ids,
                documents=chunk_contents,
                metadatas=chunk_metadatas
            )
            
            print(f"✅ Indexed email {len(chunks)} chunks from {file_path.name}")
            return True
            
        except Exception as e:
            print(f"Failed to index email {file_path}: {e}")
            return False
    
    def vector_search(self, query: str, limit: int = 10, filter_metadata: Dict = None) -> List[EnhancedQueryResult]:
        """Advanced vector search with optional metadata filtering"""
        if not self.collection:
            return []
        
        try:
            # Build where clause for filtering
            where_clause = {}
            if filter_metadata:
                where_clause.update(filter_metadata)
            
            # Query ChromaDB
            results = self.collection.query(
                query_texts=[query],
                n_results=limit * 2,  # Get more to account for deduplication
                where=where_clause if where_clause else None,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Convert to EnhancedQueryResult
            enhanced_results = []
            seen_files = set()
            
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0], 
                results['distances'][0]
            )):
                file_path = metadata['file_path']
                
                # Calculate relevance score (distance -> similarity)
                similarity = 1 - distance  # ChromaDB uses L2 distance
                relevance_score = similarity * 100
                
                # Create enhanced result
                result = EnhancedQueryResult(
                    file_path=file_path,
                    filename=metadata['filename'],
                    relevance_score=relevance_score,
                    semantic_score=similarity,
                    matching_content=doc[:200] + "..." if len(doc) > 200 else doc,
                    file_category=metadata.get('file_category', 'unknown'),
                    tags=metadata.get('tags', '').split(',') if metadata.get('tags') else [],
                    last_modified=datetime.fromisoformat(metadata['last_modified']),
                    file_size=metadata.get('file_size', 0),
                    reasoning=[
                        f"Vector similarity: {similarity:.1%}",
                        f"Chunk type: {metadata.get('chunk_type', 'unknown')}",
                        f"Section: {metadata.get('section', 'N/A')}"
                    ],
                    content_summary=doc[:300] + "..." if len(doc) > 300 else doc,
                    key_concepts=metadata.get('tags', '').split(',') if metadata.get('tags') else []
                )
                
                enhanced_results.append(result)
                seen_files.add(file_path)
                
                if len(enhanced_results) >= limit:
                    break
            
            return enhanced_results
            
        except Exception as e:
            print(f"Vector search failed: {e}")
            return []
    
    def get_similar_documents(self, file_path: str, limit: int = 5) -> List[EnhancedQueryResult]:
        """Find documents similar to a given file"""
        if not self.collection:
            return []
        
        try:
            # Get a chunk from the target file
            results = self.collection.get(
                where={"file_path": file_path},
                limit=1,
                include=['documents']
            )
            
            if not results['documents']:
                return []
            
            # Use the first chunk as query
            sample_content = results['documents'][0]
            
            # Find similar content
            return self.vector_search(
                sample_content, 
                limit=limit,
                filter_metadata={"file_path": {"$ne": file_path}}  # Exclude the original file
            )
            
        except Exception as e:
            print(f"Similar document search failed: {e}")
            return []
    
    def index_recent_emails(self, days: int = 30, limit: int = 100) -> Dict[str, int]:
        """Index recent emails for semantic search"""
        if not self.collection:
            return {"error": "Vector database not available"}
        
        print(f"📧 Finding recent emails from last {days} days...")
        email_files = self.email_extractor.get_recent_emails(days=days, limit=limit)
        
        if not email_files:
            return {"emails_found": 0, "emails_indexed": 0}
        
        print(f"Found {len(email_files)} email files to index")
        
        indexed_count = 0
        failed_count = 0
        
        for email_path in email_files:
            try:
                success = self.index_file_with_chunks(email_path)
                if success:
                    indexed_count += 1
                    print(f"   ✅ {email_path.name}")
                else:
                    failed_count += 1
                    print(f"   ⚠️ {email_path.name} (failed)")
            except Exception as e:
                failed_count += 1
                print(f"   ❌ {email_path.name} (error: {e})")
        
        return {
            "emails_found": len(email_files),
            "emails_indexed": indexed_count,
            "emails_failed": failed_count
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector database statistics"""
        if not self.collection:
            return {"vector_db_available": False}
        
        try:
            count = self.collection.count()
            return {
                "vector_db_available": True,
                "total_chunks": count,
                "database_type": "ChromaDB",
                "chunking_enabled": True
            }
        except:
            return {"vector_db_available": False}

def test_vector_librarian():
    """Test the vector-powered librarian"""
    print("🧪 Testing Vector-Powered Librarian with Smart Chunking")
    print("-" * 60)
    
    librarian = VectorLibrarian()
    
    if not librarian.collection:
        print("❌ Vector database not available")
        return
    
    # Test queries
    test_queries = [
        "entertainment contracts with exclusivity clauses",
        "payment terms in actor agreements", 
        "creative scripts about AI consciousness",
        "financial commission structures"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Vector Search: '{query}'")
        results = librarian.vector_search(query, limit=3)
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result.filename}")
                print(f"     Semantic Score: {result.semantic_score:.1%}")
                print(f"     Chunk Type: {result.reasoning[1] if len(result.reasoning) > 1 else 'N/A'}")
                print(f"     Content: {result.matching_content[:100]}...")
        else:
            print("  No results found")
    
    # Show stats
    stats = librarian.get_stats()
    print(f"\n📊 Vector Database Stats:")
    print(f"  Available: {'✅' if stats['vector_db_available'] else '❌'}")
    if stats.get('total_chunks'):
        print(f"  Total chunks indexed: {stats['total_chunks']}")

if __name__ == "__main__":
    test_vector_librarian()