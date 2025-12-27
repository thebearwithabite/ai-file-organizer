#!/usr/bin/env python3
"""
Local Metadata Store - High-Performance SQLite Database
Implements the local metadata storage system for the hybrid cloud architecture

Features:
- SQLite database with WAL mode for performance
- Complete file metadata tracking
- Vector embeddings storage
- Cache management
- ACID transactions
- Full-text search capabilities
- Automatic indexing and optimization

Database Schema:
- files: Core file metadata
- classifications: AI classification results  
- embeddings: Vector embeddings for semantic search
- cache_policy: Smart caching decisions
- sync_log: Change tracking for synchronization

Usage:
    store = LocalMetadataStore()
    file_id = store.add_file(metadata_dict)
    files = store.search_files("contract", category="business")
    
Created by: RT Max
"""

import shutil
import sqlite3
import json
import time
import hashlib
import logging
import threading
from gdrive_integration import get_metadata_root, ensure_safe_local_path
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import numpy as np
import pickle
import gzip

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class FileMetadata:
    """Complete file metadata structure"""
    file_id: str
    google_drive_id: str
    file_path: str
    file_name: str
    size_bytes: int
    content_hash: Optional[str]
    mime_type: str
    modified_time: datetime
    created_time: datetime
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    is_cached: bool = False
    cache_priority: float = 0.0
    
    # Classification data
    category: Optional[str] = None
    subcategory: Optional[str] = None
    confidence: float = 0.0
    tags: List[str] = None
    people: List[str] = None
    projects: List[str] = None
    
    # Sync metadata
    sync_status: str = "pending"  # pending, synced, conflict
    last_sync: Optional[datetime] = None

@dataclass
class EmbeddingChunk:
    """Vector embedding chunk for semantic search"""
    file_id: str
    chunk_index: int
    chunk_text: str
    embedding: np.ndarray
    chunk_hash: str

class LocalMetadataStoreError(Exception):
    """Custom exception for metadata store errors"""
    pass

class LocalMetadataStore:
    """
    High-Performance Local Metadata Store
    
    Provides fast, reliable local storage for file metadata with
    full-text search, vector embeddings, and intelligent caching.
    """
    
    # Database schema version for migrations
    SCHEMA_VERSION = 1
    
    # Default configuration
    DEFAULT_CONFIG = {
        'max_cache_size_mb': 500,
        'embedding_compression': True,
        'auto_vacuum': True,
        'wal_checkpoint_interval': 1000
    }
    
    def __init__(self, 
                 db_path: Optional[Path] = None,
                 config: Optional[Dict] = None):
        """
        Initialize the local metadata store
        
        Args:
            db_path: Path to SQLite database file
            config: Configuration dictionary
        """
        
        # Set up paths
        self.metadata_root = get_metadata_root()
        self.metadata_root.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path or (self.metadata_root / 'databases' / 'metadata.db')
        # Enforce local storage if no explicit path provided (or even if it is)
        self.db_path = ensure_safe_local_path(self.db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        
        # Connection management
        self._local = threading.local()
        self._connection_lock = threading.Lock()
        
        # Performance tracking
        self._query_count = 0
        self._last_optimization = None
        
        # Initialize database
        self._initialize_database()
        
        logger.info(f"📊 LocalMetadataStore initialized")
        logger.info(f"   💾 Database: {self.db_path}")
        logger.info(f"   📏 Size: {self._get_db_size_mb():.1f} MB")
        logger.info(f"   📁 Files tracked: {self.get_total_file_count()}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0,  # 30 second timeout
                isolation_level=None  # Autocommit mode
            )
            
            # Enable WAL mode for better concurrency
            self._local.connection.execute("PRAGMA journal_mode=WAL")
            self._local.connection.execute("PRAGMA synchronous=NORMAL")  
            self._local.connection.execute("PRAGMA cache_size=10000")
            self._local.connection.execute("PRAGMA temp_store=MEMORY")
            self._local.connection.execute("PRAGMA mmap_size=XXXXXXXXX")  # 256MB
            
            # Enable foreign keys
            self._local.connection.execute("PRAGMA foreign_keys=ON")
            
            # Set row factory for easier data access
            self._local.connection.row_factory = sqlite3.Row
        
        return self._local.connection
    
    @contextmanager
    def _get_cursor(self):
        """Get database cursor with automatic cleanup"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
            self._query_count += 1
            
            # Periodic optimization
            if self._query_count % self.config['wal_checkpoint_interval'] == 0:
                self._optimize_database()
    
    def _initialize_database(self):
        """Initialize database schema and indexes"""
        
        try:
            with self._get_cursor() as cursor:
                # Create schema version table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS schema_info (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Check schema version
                cursor.execute("SELECT value FROM schema_info WHERE key = 'version'")
                result = cursor.fetchone()
                
                if result is None:
                    # New database - create all tables
                    self._create_tables(cursor)
                    self._create_indexes(cursor)
                    cursor.execute(
                        "INSERT INTO schema_info (key, value) VALUES ('version', ?)",
                        (str(self.SCHEMA_VERSION),)
                    )
                    logger.info("🆕 Created new database schema")
                elif int(result[0]) < self.SCHEMA_VERSION:
                    # Migration needed
                    self._migrate_database(cursor, int(result[0]))
                
                logger.info("✅ Database initialization complete")
                
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise LocalMetadataStoreError(f"Database initialization failed: {e}")
    
    def _create_tables(self, cursor: sqlite3.Cursor):
        """Create all database tables"""
        
        # Core files table
        cursor.execute("""
            CREATE TABLE files (
                file_id TEXT PRIMARY KEY,
                google_drive_id TEXT UNIQUE,
                file_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                content_hash TEXT,
                mime_type TEXT,
                modified_time TIMESTAMP NOT NULL,
                created_time TIMESTAMP NOT NULL,
                last_accessed TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                is_cached BOOLEAN DEFAULT FALSE,
                cache_priority REAL DEFAULT 0.0,
                sync_status TEXT DEFAULT 'pending',
                last_sync TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Classifications table
        cursor.execute("""
            CREATE TABLE classifications (
                file_id TEXT PRIMARY KEY REFERENCES files(file_id) ON DELETE CASCADE,
                category TEXT,
                subcategory TEXT,
                confidence REAL DEFAULT 0.0,
                reasoning TEXT,
                tags JSON,
                people JSON,
                projects JSON,
                classification_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                classifier_version TEXT
            )
        """)
        
        # Vector embeddings table
        cursor.execute("""
            CREATE TABLE embeddings (
                file_id TEXT REFERENCES files(file_id) ON DELETE CASCADE,
                chunk_index INTEGER,
                chunk_text TEXT,
                embedding BLOB,
                chunk_hash TEXT,
                embedding_model TEXT DEFAULT 'sentence-transformers',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (file_id, chunk_index)
            )
        """)
        
        # Cache policy table
        cursor.execute("""
            CREATE TABLE cache_policy (
                file_id TEXT PRIMARY KEY REFERENCES files(file_id) ON DELETE CASCADE,
                priority_score REAL DEFAULT 0.0,
                last_cache_decision TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                eviction_weight REAL DEFAULT 1.0,
                cache_reason TEXT,
                auto_cache BOOLEAN DEFAULT TRUE
            )
        """)
        
        # Synchronization log
        cursor.execute("""
            CREATE TABLE sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT REFERENCES files(file_id),
                operation TEXT NOT NULL,  -- insert, update, delete, conflict
                status TEXT NOT NULL,     -- pending, success, error
                error_message TEXT,
                sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                retry_count INTEGER DEFAULT 0
            )
        """)
        
        # Search optimization - FTS virtual table
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
                file_id,
                file_name,
                file_path,
                content,
                tags,
                people,
                projects
            )
        """)
        
        logger.info("📋 Database tables created")
    
    def _create_indexes(self, cursor: sqlite3.Cursor):
        """Create database indexes for performance"""
        
        indexes = [
            # Files table indexes
            "CREATE INDEX IF NOT EXISTS idx_files_path ON files(file_path)",
            "CREATE INDEX IF NOT EXISTS idx_files_name ON files(file_name)",
            "CREATE INDEX IF NOT EXISTS idx_files_modified ON files(modified_time DESC)",
            "CREATE INDEX IF NOT EXISTS idx_files_accessed ON files(last_accessed DESC)",
            "CREATE INDEX IF NOT EXISTS idx_files_cached ON files(is_cached)",
            "CREATE INDEX IF NOT EXISTS idx_files_sync_status ON files(sync_status)",
            "CREATE INDEX IF NOT EXISTS idx_files_size ON files(size_bytes)",
            
            # Classifications indexes
            "CREATE INDEX IF NOT EXISTS idx_classifications_category ON classifications(category)",
            "CREATE INDEX IF NOT EXISTS idx_classifications_subcategory ON classifications(subcategory)",
            "CREATE INDEX IF NOT EXISTS idx_classifications_confidence ON classifications(confidence DESC)",
            
            # Cache policy indexes
            "CREATE INDEX IF NOT EXISTS idx_cache_priority ON cache_policy(priority_score DESC)",
            "CREATE INDEX IF NOT EXISTS idx_cache_decision ON cache_policy(last_cache_decision DESC)",
            
            # Sync log indexes
            "CREATE INDEX IF NOT EXISTS idx_sync_log_status ON sync_log(status)",
            "CREATE INDEX IF NOT EXISTS idx_sync_log_time ON sync_log(sync_time DESC)",
            
            # Composite indexes
            "CREATE INDEX IF NOT EXISTS idx_files_category_modified ON files(modified_time DESC)",
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        logger.info("📈 Database indexes created")
    
    # CRUD Operations
    
    def add_file(self, metadata: Dict[str, Any]) -> str:
        """
        Add new file metadata to the store
        
        Args:
            metadata: File metadata dictionary
            
        Returns:
            str: Generated file_id
        """
        
        try:
            # Generate file ID if not provided
            file_id = metadata.get('file_id')
            if not file_id:
                file_id = self._generate_file_id(
                    metadata['file_path'], 
                    metadata.get('content_hash', '')
                )
            
            with self._get_cursor() as cursor:
                # Insert into files table
                cursor.execute("""
                    INSERT OR REPLACE INTO files (
                        file_id, google_drive_id, file_path, file_name,
                        size_bytes, content_hash, mime_type,
                        modified_time, created_time, last_accessed,
                        access_count, is_cached, cache_priority,
                        sync_status, last_sync
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    file_id,
                    metadata.get('google_drive_id'),
                    metadata['file_path'],
                    metadata['file_name'],
                    metadata['size_bytes'],
                    metadata.get('content_hash'),
                    metadata.get('mime_type', 'application/octet-stream'),
                    metadata.get('modified_time', datetime.now()),
                    metadata.get('created_time', datetime.now()),
                    metadata.get('last_accessed'),
                    metadata.get('access_count', 0),
                    metadata.get('is_cached', False),
                    metadata.get('cache_priority', 0.0),
                    metadata.get('sync_status', 'pending'),
                    metadata.get('last_sync')
                ))
                
                # Add classification if provided
                if any(key in metadata for key in ['category', 'subcategory', 'tags', 'people', 'projects']):
                    self._add_classification(cursor, file_id, metadata)
                
                # Add to FTS index
                cursor.execute("""
                    INSERT OR REPLACE INTO files_fts (
                        file_id, file_name, file_path, content, tags, people, projects
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    file_id,
                    metadata['file_name'],
                    metadata['file_path'],
                    metadata.get('content', ''),
                    json.dumps(metadata.get('tags', [])),
                    json.dumps(metadata.get('people', [])),
                    json.dumps(metadata.get('projects', []))
                ))
                
                # Log sync operation
                cursor.execute("""
                    INSERT INTO sync_log (file_id, operation, status) 
                    VALUES (?, 'insert', 'pending')
                """, (file_id,))
                
            logger.debug(f"📄 Added file: {metadata['file_name']} ({file_id})")
            return file_id
            
        except Exception as e:
            logger.error(f"❌ Failed to add file: {e}")
            raise LocalMetadataStoreError(f"Failed to add file: {e}")
    
    def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get file metadata by ID
        
        Args:
            file_id: File identifier
            
        Returns:
            dict: File metadata or None if not found
        """
        
        try:
            with self._get_cursor() as cursor:
                # Get file data
                cursor.execute("""
                    SELECT * FROM files WHERE file_id = ?
                """, (file_id,))
                
                file_row = cursor.fetchone()
                if not file_row:
                    return None
                
                # Convert to dict
                file_data = dict(file_row)
                
                # Get classification data
                cursor.execute("""
                    SELECT * FROM classifications WHERE file_id = ?
                """, (file_id,))
                
                classification_row = cursor.fetchone()
                if classification_row:
                    classification_data = dict(classification_row)
                    # Parse JSON fields
                    for json_field in ['tags', 'people', 'projects']:
                        if classification_data.get(json_field):
                            classification_data[json_field] = json.loads(classification_data[json_field])
                    
                    file_data.update(classification_data)
                
                return file_data
                
        except Exception as e:
            logger.error(f"❌ Failed to get file {file_id}: {e}")
            return None
    
    def update_file(self, file_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update file metadata
        
        Args:
            file_id: File identifier
            updates: Dictionary of fields to update
            
        Returns:
            bool: True if successful
        """
        
        try:
            with self._get_cursor() as cursor:
                # Build dynamic update query
                file_fields = []
                file_values = []
                
                for field, value in updates.items():
                    if field in ['file_path', 'file_name', 'size_bytes', 'content_hash', 
                                'mime_type', 'modified_time', 'last_accessed', 'access_count',
                                'is_cached', 'cache_priority', 'sync_status', 'last_sync']:
                        file_fields.append(f"{field} = ?")
                        file_values.append(value)
                
                if file_fields:
                    file_values.append(file_id)
                    cursor.execute(f"""
                        UPDATE files SET {', '.join(file_fields)}, updated_at = CURRENT_TIMESTAMP
                        WHERE file_id = ?
                    """, file_values)
                
                # Update classification if provided
                classification_fields = {}
                for field in ['category', 'subcategory', 'confidence', 'reasoning', 'tags', 'people', 'projects']:
                    if field in updates:
                        classification_fields[field] = updates[field]
                
                if classification_fields:
                    self._update_classification(cursor, file_id, classification_fields)
                
                # Log sync operation
                cursor.execute("""
                    INSERT INTO sync_log (file_id, operation, status) 
                    VALUES (?, 'update', 'pending')
                """, (file_id,))
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to update file {file_id}: {e}")
            return False
    
    def delete_file(self, file_id: str) -> bool:
        """
        Delete file metadata
        
        Args:
            file_id: File identifier
            
        Returns:
            bool: True if successful
        """
        
        try:
            with self._get_cursor() as cursor:
                # Delete from main table (cascades to other tables)
                cursor.execute("DELETE FROM files WHERE file_id = ?", (file_id,))
                
                # Delete from FTS index
                cursor.execute("DELETE FROM files_fts WHERE file_id = ?", (file_id,))
                
                # Log sync operation
                cursor.execute("""
                    INSERT INTO sync_log (file_id, operation, status) 
                    VALUES (?, 'delete', 'pending')
                """, (file_id,))
                
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"❌ Failed to delete file {file_id}: {e}")
            return False
    
    # Search and Query Operations
    
    def search_files(self, 
                    query: str = None,
                    category: str = None,
                    subcategory: str = None,
                    tags: List[str] = None,
                    people: List[str] = None,
                    projects: List[str] = None,
                    min_confidence: float = None,
                    is_cached: bool = None,
                    limit: int = 100,
                    offset: int = 0) -> List[Dict[str, Any]]:
        """
        Search files with multiple criteria
        
        Args:
            query: Text search query
            category: File category filter
            subcategory: File subcategory filter
            tags: Tag filters (ANY match)
            people: People filters (ANY match)
            projects: Project filters (ANY match)
            min_confidence: Minimum classification confidence
            is_cached: Filter by cache status
            limit: Maximum results
            offset: Result offset for pagination
            
        Returns:
            list: Matching file metadata dictionaries
        """
        
        try:
            with self._get_cursor() as cursor:
                # Build query conditions
                conditions = []
                params = []
                
                if query:
                    # Use FTS for text search
                    conditions.append("""
                        files.file_id IN (
                            SELECT file_id FROM files_fts 
                            WHERE files_fts MATCH ?
                        )
                    """)
                    params.append(query)
                
                if category:
                    conditions.append("classifications.category = ?")
                    params.append(category)
                
                if subcategory:
                    conditions.append("classifications.subcategory = ?")
                    params.append(subcategory)
                
                if min_confidence is not None:
                    conditions.append("classifications.confidence >= ?")
                    params.append(min_confidence)
                
                if is_cached is not None:
                    conditions.append("files.is_cached = ?")
                    params.append(is_cached)
                
                # JSON array searches for tags, people, projects
                if tags:
                    tag_conditions = []
                    for tag in tags:
                        tag_conditions.append("JSON_EXTRACT(classifications.tags, '$') LIKE ?")
                        params.append(f'%"{tag}"%')
                    conditions.append(f"({' OR '.join(tag_conditions)})")
                
                if people:
                    people_conditions = []
                    for person in people:
                        people_conditions.append("JSON_EXTRACT(classifications.people, '$') LIKE ?")
                        params.append(f'%"{person}"%')
                    conditions.append(f"({' OR '.join(people_conditions)})")
                
                if projects:
                    project_conditions = []
                    for project in projects:
                        project_conditions.append("JSON_EXTRACT(classifications.projects, '$') LIKE ?")
                        params.append(f'%"{project}"%')
                    conditions.append(f"({' OR '.join(project_conditions)})")
                
                # Build final query
                where_clause = ""
                if conditions:
                    where_clause = "WHERE " + " AND ".join(conditions)
                
                query_sql = f"""
                    SELECT files.*, classifications.*
                    FROM files
                    LEFT JOIN classifications ON files.file_id = classifications.file_id
                    {where_clause}
                    ORDER BY files.modified_time DESC, files.access_count DESC
                    LIMIT ? OFFSET ?
                """
                
                params.extend([limit, offset])
                cursor.execute(query_sql, params)
                
                # Convert results
                results = []
                for row in cursor.fetchall():
                    file_data = dict(row)
                    
                    # Parse JSON fields
                    for json_field in ['tags', 'people', 'projects']:
                        if file_data.get(json_field):
                            file_data[json_field] = json.loads(file_data[json_field])
                    
                    results.append(file_data)
                
                logger.debug(f"🔍 Search returned {len(results)} results")
                return results
                
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return []
    
    def get_files_by_category(self, category: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get files by category, ordered by relevance"""
        
        return self.search_files(
            category=category,
            limit=limit
        )
    
    def get_recently_accessed_files(self, days: int = 7, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recently accessed files"""
        
        try:
            with self._get_cursor() as cursor:
                cursor.execute("""
                    SELECT files.*, classifications.*
                    FROM files
                    LEFT JOIN classifications ON files.file_id = classifications.file_id
                    WHERE files.last_accessed >= datetime('now', '-{} days')
                    ORDER BY files.last_accessed DESC, files.access_count DESC
                    LIMIT ?
                """.format(days), (limit,))
                
                results = []
                for row in cursor.fetchall():
                    file_data = dict(row)
                    
                    # Parse JSON fields
                    for json_field in ['tags', 'people', 'projects']:
                        if file_data.get(json_field):
                            file_data[json_field] = json.loads(file_data[json_field])
                    
                    results.append(file_data)
                
                return results
                
        except Exception as e:
            logger.error(f"❌ Failed to get recent files: {e}")
            return []
    
    def get_cached_files(self) -> List[Dict[str, Any]]:
        """Get all cached files with their metadata"""
        
        return self.search_files(is_cached=True, limit=1000)
    
    # Vector Embedding Operations
    
    def add_embedding(self, file_id: str, chunk_index: int, 
                     chunk_text: str, embedding: np.ndarray) -> bool:
        """
        Add vector embedding for semantic search
        
        Args:
            file_id: File identifier
            chunk_index: Chunk sequence number
            chunk_text: Original text content
            embedding: Vector embedding array
            
        Returns:
            bool: True if successful
        """
        
        try:
            # Create chunk hash for deduplication
            chunk_hash = hashlib.md5(chunk_text.encode()).hexdigest()
            
            # Compress embedding if enabled
            if self.config['embedding_compression']:
                embedding_data = gzip.compress(pickle.dumps(embedding))
            else:
                embedding_data = pickle.dumps(embedding)
            
            with self._get_cursor() as cursor:
                cursor.execute("""
                    INSERT OR REPLACE INTO embeddings (
                        file_id, chunk_index, chunk_text, embedding, chunk_hash
                    ) VALUES (?, ?, ?, ?, ?)
                """, (file_id, chunk_index, chunk_text, embedding_data, chunk_hash))
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to add embedding: {e}")
            return False
    
    def get_embeddings(self, file_id: str) -> List[Tuple[int, str, np.ndarray]]:
        """
        Get all embeddings for a file
        
        Args:
            file_id: File identifier
            
        Returns:
            list: Tuples of (chunk_index, chunk_text, embedding)
        """
        
        try:
            with self._get_cursor() as cursor:
                cursor.execute("""
                    SELECT chunk_index, chunk_text, embedding 
                    FROM embeddings 
                    WHERE file_id = ?
                    ORDER BY chunk_index
                """, (file_id,))
                
                results = []
                for row in cursor.fetchall():
                    chunk_index, chunk_text, embedding_data = row
                    
                    # Decompress embedding
                    if self.config['embedding_compression']:
                        embedding = pickle.loads(gzip.decompress(embedding_data))
                    else:
                        embedding = pickle.loads(embedding_data)
                    
                    results.append((chunk_index, chunk_text, embedding))
                
                return results
                
        except Exception as e:
            logger.error(f"❌ Failed to get embeddings: {e}")
            return []
    
    def delete_embeddings(self, file_id: str) -> bool:
        """Delete all embeddings for a file"""
        
        try:
            with self._get_cursor() as cursor:
                cursor.execute("DELETE FROM embeddings WHERE file_id = ?", (file_id,))
                return True
        except Exception as e:
            logger.error(f"❌ Failed to delete embeddings: {e}")
            return False
    
    # Cache Management Operations
    
    def update_cache_policy(self, file_id: str, priority_score: float, reason: str = "") -> bool:
        """Update cache policy for a file"""
        
        try:
            with self._get_cursor() as cursor:
                cursor.execute("""
                    INSERT OR REPLACE INTO cache_policy (
                        file_id, priority_score, last_cache_decision, cache_reason
                    ) VALUES (?, ?, CURRENT_TIMESTAMP, ?)
                """, (file_id, priority_score, reason))
                return True
        except Exception as e:
            logger.error(f"❌ Failed to update cache policy: {e}")
            return False
    
    def get_cache_candidates(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get files that should be cached based on policy"""
        
        try:
            with self._get_cursor() as cursor:
                cursor.execute("""
                    SELECT files.*, cache_policy.priority_score, cache_policy.cache_reason
                    FROM files
                    JOIN cache_policy ON files.file_id = cache_policy.file_id
                    WHERE files.is_cached = FALSE
                    ORDER BY cache_policy.priority_score DESC
                    LIMIT ?
                """, (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"❌ Failed to get cache candidates: {e}")
            return []
    
    def get_eviction_candidates(self, target_size_mb: float) -> List[Dict[str, Any]]:
        """Get files that should be evicted from cache"""
        
        try:
            with self._get_cursor() as cursor:
                cursor.execute("""
                    SELECT files.*, cache_policy.priority_score, cache_policy.eviction_weight
                    FROM files
                    LEFT JOIN cache_policy ON files.file_id = cache_policy.file_id
                    WHERE files.is_cached = TRUE
                    ORDER BY 
                        COALESCE(cache_policy.priority_score, 0.0) ASC,
                        files.last_accessed ASC,
                        files.access_count ASC
                """)
                
                candidates = []
                total_size = 0.0
                
                for row in cursor.fetchall():
                    file_data = dict(row)
                    size_mb = file_data['size_bytes'] / (1024 * 1024)
                    candidates.append(file_data)
                    total_size += size_mb
                    
                    if total_size >= target_size_mb:
                        break
                
                return candidates
                
        except Exception as e:
            logger.error(f"❌ Failed to get eviction candidates: {e}")
            return []
    
    # Statistics and Monitoring
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        
        try:
            with self._get_cursor() as cursor:
                stats = {}
                
                # File counts
                cursor.execute("SELECT COUNT(*) FROM files")
                stats['total_files'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM files WHERE is_cached = TRUE")
                stats['cached_files'] = cursor.fetchone()[0]
                
                # Storage stats
                cursor.execute("SELECT SUM(size_bytes) FROM files")
                result = cursor.fetchone()[0]
                stats['total_size_bytes'] = result or 0
                
                cursor.execute("SELECT SUM(size_bytes) FROM files WHERE is_cached = TRUE")
                result = cursor.fetchone()[0]
                stats['cached_size_bytes'] = result or 0
                
                # Classification stats
                cursor.execute("SELECT category, COUNT(*) FROM classifications GROUP BY category")
                stats['categories'] = dict(cursor.fetchall())
                
                # Database stats
                stats['db_size_mb'] = self._get_db_size_mb()
                stats['query_count'] = self._query_count
                stats['last_optimization'] = self._last_optimization
                
                return stats
                
        except Exception as e:
            logger.error(f"❌ Failed to get statistics: {e}")
            return {}
    
    def get_total_file_count(self) -> int:
        """Get total number of files in database"""
        
        try:
            with self._get_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM files")
                return cursor.fetchone()[0]
        except:
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive metadata store statistics"""
        
        try:
            with self._get_cursor() as cursor:
                # File counts
                cursor.execute("SELECT COUNT(*) FROM files")
                total_files = cursor.fetchone()[0]
                
                # Total size
                cursor.execute("SELECT COALESCE(SUM(size_bytes), 0) FROM files")
                total_size_bytes = cursor.fetchone()[0]
                
                # Cache statistics  
                cursor.execute("SELECT COUNT(*) FROM files WHERE is_cached = 1")
                cached_files = cursor.fetchone()[0]
                
                # Classification statistics
                cursor.execute("SELECT COUNT(*) FROM classifications")
                classified_files = cursor.fetchone()[0]
                
                return {
                    'total_files': total_files,
                    'total_size_bytes': total_size_bytes,
                    'total_size_mb': total_size_bytes / (1024 * 1024),
                    'cached_files': cached_files,
                    'classified_files': classified_files,
                    'db_size_mb': self._get_db_size_mb(),
                    'schema_version': self.SCHEMA_VERSION
                }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                'total_files': 0,
                'total_size_bytes': 0,
                'total_size_mb': 0.0,
                'cached_files': 0,
                'classified_files': 0,
                'db_size_mb': 0.0,
                'schema_version': self.SCHEMA_VERSION
            }
    
    # Utility Methods
    
    def _generate_file_id(self, file_path: str, content_hash: str = "") -> str:
        """Generate unique file ID from path and content"""
        
        combined = f"{file_path}:{content_hash}:{datetime.now().isoformat()}"
        return hashlib.sha256(combined.encode()).hexdigest()[:32]
    
    def _get_db_size_mb(self) -> float:
        """Get database file size in MB"""
        
        db_path = Path(self.db_path) if isinstance(self.db_path, str) else self.db_path
        if db_path.exists():
            return db_path.stat().st_size / (1024 * 1024)
        return 0.0
    
    def _add_classification(self, cursor: sqlite3.Cursor, file_id: str, metadata: Dict[str, Any]):
        """Add classification data for a file"""
        
        cursor.execute("""
            INSERT OR REPLACE INTO classifications (
                file_id, category, subcategory, confidence, reasoning,
                tags, people, projects
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            file_id,
            metadata.get('category'),
            metadata.get('subcategory'),
            metadata.get('confidence', 0.0),
            metadata.get('reasoning', ''),
            json.dumps(metadata.get('tags', [])),
            json.dumps(metadata.get('people', [])),
            json.dumps(metadata.get('projects', []))
        ))
    
    def _update_classification(self, cursor: sqlite3.Cursor, file_id: str, updates: Dict[str, Any]):
        """Update classification data for a file"""
        
        # Convert lists to JSON for storage
        json_fields = {}
        for field in ['tags', 'people', 'projects']:
            if field in updates and isinstance(updates[field], list):
                json_fields[field] = json.dumps(updates[field])
            elif field in updates:
                json_fields[field] = updates[field]
        
        # Build update query
        fields = []
        values = []
        
        for field, value in {**updates, **json_fields}.items():
            if field in ['category', 'subcategory', 'confidence', 'reasoning', 'tags', 'people', 'projects']:
                fields.append(f"{field} = ?")
                values.append(value)
        
        if fields:
            values.append(file_id)
            cursor.execute(f"""
                INSERT OR REPLACE INTO classifications (
                    file_id, {', '.join(field.split(' = ')[0] for field in fields)}
                ) VALUES (?, {', '.join(['?'] * len(fields))})
            """, [file_id] + [updates.get(field.split(' = ')[0]) for field in fields])
    
    def _optimize_database(self):
        """Perform database optimization"""
        
        try:
            with self._get_cursor() as cursor:
                # Analyze tables for query optimization
                cursor.execute("ANALYZE")
                
                # WAL checkpoint
                cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                
                # Vacuum if auto_vacuum is enabled
                if self.config['auto_vacuum']:
                    cursor.execute("PRAGMA auto_vacuum = INCREMENTAL")
                    cursor.execute("PRAGMA incremental_vacuum")
                
                self._last_optimization = datetime.now()
                logger.debug("🔧 Database optimization completed")
                
        except Exception as e:
            logger.warning(f"⚠️  Database optimization failed: {e}")
    
    def _migrate_database(self, cursor: sqlite3.Cursor, from_version: int):
        """Migrate database schema to newer version"""
        
        logger.info(f"🔄 Migrating database from version {from_version} to {self.SCHEMA_VERSION}")
        
        # Add migration logic here as schema evolves
        # For now, just update version
        cursor.execute(
            "UPDATE schema_info SET value = ? WHERE key = 'version'",
            (str(self.SCHEMA_VERSION),)
        )
    
    def close(self):
        """Close database connections"""
        
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            delattr(self._local, 'connection')

def main():
    """Test the local metadata store"""
    
    print("🗄️  Local Metadata Store Test")
    print("=" * 50)
    
    # Initialize store
    store = LocalMetadataStore()
    
    # Test data
    test_file = {
        'google_drive_id': 'test_123',
        'file_path': 'documents/contracts/test_contract.pdf',
        'file_name': 'test_contract.pdf',
        'size_bytes': 1024 * 1024,  # 1MB
        'content_hash': 'abc123',
        'mime_type': 'application/pdf',
        'modified_time': datetime.now(),
        'created_time': datetime.now(),
        'category': 'business',
        'subcategory': 'contracts',
        'confidence': 0.95,
        'tags': ['contract', 'business', 'legal'],
        'people': ['client_name'],
        'projects': ['business_operations']
    }
    
    try:
        # Test CRUD operations
        print("📄 Testing CRUD operations...")
        
        # Create
        file_id = store.add_file(test_file)
        print(f"   ✅ Added file: {file_id}")
        
        # Read
        retrieved = store.get_file(file_id)
        if retrieved:
            print(f"   ✅ Retrieved file: {retrieved['file_name']}")
        
        # Update
        updated = store.update_file(file_id, {'access_count': 5})
        if updated:
            print(f"   ✅ Updated file access count")
        
        # Search
        results = store.search_files(query="contract", category="business")
        print(f"   ✅ Search found {len(results)} results")
        
        # Statistics
        stats = store.get_statistics()
        print(f"\n📊 Database Statistics:")
        print(f"   Total files: {stats['total_files']}")
        print(f"   Cached files: {stats['cached_files']}")
        print(f"   Database size: {stats['db_size_mb']:.1f} MB")
        print(f"   Categories: {stats.get('categories', {})}")
        
        # Test vector embedding
        print(f"\n🧠 Testing vector embeddings...")
        dummy_embedding = np.random.rand(384)  # Typical sentence transformer size
        store.add_embedding(file_id, 0, "Test contract content", dummy_embedding)
        embeddings = store.get_embeddings(file_id)
        print(f"   ✅ Added and retrieved {len(embeddings)} embeddings")
        
        print(f"\n✅ All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    finally:
        store.close()

if __name__ == "__main__":
    main()