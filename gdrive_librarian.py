#!/usr/bin/env python3
"""
Google Drive Librarian - Complete Hybrid Cloud/Local Search System
Seamlessly integrates local metadata search with Google Drive streaming and background sync

This replaces the missing gdrive_librarian.py with a complete implementation that:
- Provides unified search across local and cloud files
- Integrates with background sync service
- Handles file streaming on-demand
- Maintains ADHD-friendly user experience
- Offers intelligent caching and conflict resolution

Usage:
    librarian = GoogleDriveLibrarian()
    results = librarian.search("Client Name contracts")
    file_path = librarian.get_file_content(file_id)

Created by: RT Max for AI File Organizer v3.0
"""

import os
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import logging
from gdrive_integration import get_ai_organizer_root

# Google API imports
try:
    from googleapiclient.errors import HttpError
except ImportError as e:
    print("❌ Google API libraries not installed.")
    print("Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    raise e

from google_drive_auth import GoogleDriveAuth
from local_metadata_store import LocalMetadataStore, FileMetadata
from gdrive_streamer import GoogleDriveStreamer, StreamingProgress
from background_sync_service import BackgroundSyncService, ConflictResolution
from hybrid_librarian import HybridLibrarian, EnhancedQueryResult

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SearchScope(Enum):
    """Search scope options"""
    LOCAL_ONLY = "local_only"
    CLOUD_ONLY = "cloud_only"
    HYBRID = "hybrid"
    AUTO = "auto"

class FileAvailability(Enum):
    """File availability status"""
    LOCAL_CACHED = "local_cached"
    CLOUD_STREAMABLE = "cloud_streamable"
    DOWNLOADING = "downloading"
    UNAVAILABLE = "unavailable"

@dataclass
class CloudSearchResult:
    """Enhanced search result with cloud capabilities"""
    file_id: str
    filename: str
    relevance_score: float
    matching_content: str
    file_category: str
    last_modified: datetime
    file_size: int
    availability: FileAvailability
    local_path: Optional[str] = None
    drive_path: Optional[str] = None
    can_stream: bool = True
    cache_score: float = 0.0
    sync_status: str = "synced"
    reasoning: List[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.reasoning is None:
            self.reasoning = []
        if self.tags is None:
            self.tags = []

class GoogleDriveLibrarian:
    """
    Complete Google Drive Librarian System
    
    Provides unified search and file access across local and cloud storage
    with intelligent caching, background sync, and ADHD-friendly features.
    
    Key Features:
    - Unified search across local metadata and Google Drive
    - On-demand file streaming and caching
    - Background synchronization
    - Intelligent conflict resolution
    - ADHD-friendly progressive disclosure
    - Seamless local/cloud file access
    """
    
    def __init__(self, 
                 config_dir: Path = None,
                 cache_size_gb: float = 5.0,
                 auto_sync: bool = True,
                 sync_interval: int = 300):
        """
        Initialize Google Drive Librarian
        
        Args:
            config_dir: Configuration directory
            cache_size_gb: Maximum cache size in GB
            auto_sync: Enable automatic background synchronization
            sync_interval: Sync interval in seconds
        """
        
        # Set up configuration
        if config_dir is None:
            config_dir = Path.home() / ".ai_organizer_config"
        config_dir.mkdir(exist_ok=True)
        self.config_dir = config_dir
        
        # Initialize core components
        logger.info("🔧 Initializing Google Drive Librarian...")
        
        # Authentication
        self.auth_service = GoogleDriveAuth(
            config_dir=config_dir
        )
        
        # Metadata store
        self.metadata_store = LocalMetadataStore(
            db_path=config_dir / "file_metadata.db"
        )
        
        # File streamer
        cache_dir = config_dir / "file_cache"
        self.streamer = GoogleDriveStreamer(
            auth_service=self.auth_service,
            metadata_store=self.metadata_store,
            cache_dir=cache_dir,
            cache_size_gb=cache_size_gb
        )
        
        # Hybrid search (local + semantic) - LAZY LOADED
        # Don't initialize HybridLibrarian here - it loads heavy SentenceTransformer model
        self._hybrid_librarian = None
        self._hybrid_librarian_base_dir = str(get_ai_organizer_root())
        
        # Background sync service
        self.sync_service = None
        if auto_sync:
            self.sync_service = BackgroundSyncService(
                auth_service=self.auth_service,
                metadata_store=self.metadata_store,
                streamer=self.streamer,
                sync_interval=sync_interval
            )
        
        # Configuration
        self.config_file = config_dir / "librarian_config.json"
        self.config = self._load_config()
        
        # State
        self._authenticated = False
        self._cached_auth_info = None  # Cache for auth info
        self._last_drive_scan: Optional[datetime] = None
        self._drive_file_cache: Dict[str, Dict] = {}
        
        logger.info("✅ Google Drive Librarian created (components initialized)")
        logger.info(f"   📁 Config: {config_dir}")
        logger.info(f"   💾 Cache: {cache_size_gb}GB")
        logger.info(f"   🔄 Auto-sync: {auto_sync}")
        logger.info("   🚀 HybridLibrarian (semantic search) will load on first use")

    @property
    def hybrid_librarian(self):
        """Lazy load HybridLibrarian with SentenceTransformer model"""
        if self._hybrid_librarian is None:
            logger.info("🔍 Loading HybridLibrarian (semantic search) for first time...")
            self._hybrid_librarian = HybridLibrarian(
                base_dir=self._hybrid_librarian_base_dir
            )
            logger.info("✅ HybridLibrarian loaded successfully")
        return self._hybrid_librarian
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        
        default_config = {
            'version': '3.0',
            'search_preferences': {
                'default_scope': SearchScope.HYBRID.value,
                'max_results': 50,
                'enable_semantic_search': True,
                'auto_download_threshold_mb': 10
            },
            'sync_preferences': {
                'conflict_resolution': ConflictResolution.NEWER_WINS.value,
                'auto_resolve_conflicts': True,
                'sync_file_types': [
                    'application/pdf',
                    'text/',
                    'application/vnd.openxmlformats-officedocument'
                ]
            },
            'adhd_features': {
                'progressive_disclosure': True,
                'simple_questions': True,
                'immediate_feedback': True,
                'confidence_threshold': 85
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults
                    for section, values in default_config.items():
                        if section not in loaded_config:
                            loaded_config[section] = values
                        elif isinstance(values, dict):
                            for key, default_value in values.items():
                                if key not in loaded_config[section]:
                                    loaded_config[section][key] = default_value
                    return loaded_config
            except Exception as e:
                logger.warning(f"⚠️  Could not load config: {e}")
        
        # Save default config
        self._save_config(default_config)
        return default_config
    
    def _save_config(self, config: Dict[str, Any]):
        """Save configuration to file"""
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Could not save config: {e}")
    
    def initialize(self) -> bool:
        """
        Initialize the librarian system
        
        Returns:
            bool: True if initialization successful
        """
        
        try:
            logger.info("🚀 Initializing Google Drive Librarian System...")
            
            # Step 1: Authenticate
            logger.info("   🔐 Authenticating...")
            auth_result = self.auth_service.test_authentication()
            if not auth_result['success']:
                logger.error(f"❌ Authentication failed: {auth_result}")
                return False
            
            self._authenticated = True
            self._cached_auth_info = auth_result
            self._auth_cache_time = datetime.now()
            logger.info(f"   ✅ Authenticated as: {auth_result['user_name']}")
            
            # Step 2: Initialize metadata store
            logger.info("   📊 Initializing metadata store...")
            metadata_stats = self.metadata_store.get_stats()
            logger.info(f"   📁 Local files indexed: {metadata_stats['total_files']}")
            
            # Step 3: Start background sync if enabled
            if self.sync_service:
                logger.info("   🔄 Starting background sync...")
                if self.sync_service.start_background_sync():
                    logger.info("   ✅ Background sync started")
                else:
                    logger.warning("   ⚠️  Background sync failed to start")
            
            # Step 4: Initial Drive scan (lightweight)
            logger.info("   🔍 Performing initial Drive scan...")
            self._scan_drive_metadata()
            
            logger.info("✅ Google Drive Librarian fully initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            return False
    
    def search(self, 
               query: str, 
               scope: SearchScope = SearchScope.AUTO,
               limit: int = None,
               file_types: List[str] = None,
               date_range: Tuple[datetime, datetime] = None) -> List[CloudSearchResult]:
        """
        Unified search across local and cloud storage
        
        Args:
            query: Search query
            scope: Search scope (local, cloud, hybrid, auto)
            limit: Maximum results to return
            file_types: Filter by file types/extensions
            date_range: Filter by date range (start, end)
            
        Returns:
            List of CloudSearchResult objects
        """
        
        if not self._authenticated:
            logger.warning("⚠️  Not authenticated - searching local files only")
            scope = SearchScope.LOCAL_ONLY
        
        if limit is None:
            limit = self.config['search_preferences']['max_results']
        
        logger.info(f"🔍 Searching: '{query}' (scope: {scope.value}, limit: {limit})")
        
        results = []
        
        try:
            if scope == SearchScope.AUTO:
                scope = self._determine_search_scope(query)
                logger.info(f"   🎯 Auto-selected scope: {scope.value}")
            
            # Local search (always include for hybrid and local-only)
            if scope in [SearchScope.LOCAL_ONLY, SearchScope.HYBRID]:
                local_results = self._search_local(query, limit)
                results.extend(local_results)
                logger.info(f"   📁 Local results: {len(local_results)}")
            
            # Cloud search
            if scope in [SearchScope.CLOUD_ONLY, SearchScope.HYBRID] and self._authenticated:
                cloud_results = self._search_drive(query, limit)
                results.extend(cloud_results)
                logger.info(f"   ☁️  Cloud results: {len(cloud_results)}")
            
            # Deduplicate and merge results
            results = self._merge_and_deduplicate_results(results)
            
            # Apply filters
            if file_types:
                results = self._filter_by_file_types(results, file_types)
            
            if date_range:
                results = self._filter_by_date_range(results, date_range)
            
            # Sort by relevance
            results.sort(key=lambda x: x.relevance_score, reverse=True)
            
            # Limit results
            results = results[:limit]
            
            # Enhance with availability information
            results = self._enhance_with_availability(results)
            
            logger.info(f"✅ Search complete: {len(results)} results")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return []
    
    def _determine_search_scope(self, query: str) -> SearchScope:
        """Intelligently determine search scope based on query"""
        
        query_lower = query.lower()
        
        # Patterns that suggest cloud search
        cloud_patterns = [
            'recent', 'latest', 'new', 'shared', 'collaborative',
            'drive', 'google', 'sync', 'uploaded'
        ]
        
        # Patterns that suggest local search
        local_patterns = [
            'cached', 'offline', 'local', 'downloaded',
            'my computer', 'this machine'
        ]
        
        cloud_score = sum(1 for pattern in cloud_patterns if pattern in query_lower)
        local_score = sum(1 for pattern in local_patterns if pattern in query_lower)
        
        if cloud_score > local_score:
            return SearchScope.CLOUD_ONLY
        elif local_score > cloud_score:
            return SearchScope.LOCAL_ONLY
        else:
            return SearchScope.HYBRID
    
    def _search_local(self, query: str, limit: int) -> List[CloudSearchResult]:
        """Search local metadata and cached files"""
        
        # Use hybrid librarian for local search
        hybrid_results = self.hybrid_librarian.search(query, search_mode="auto", limit=limit)
        
        # Convert to CloudSearchResult
        cloud_results = []
        for result in hybrid_results:
            # Determine availability
            availability = FileAvailability.LOCAL_CACHED
            if not result.file_path or not Path(result.file_path).exists():
                availability = FileAvailability.UNAVAILABLE
            
            cloud_result = CloudSearchResult(
                file_id=result.file_path,  # Use file path as ID for local files
                filename=result.filename,
                relevance_score=result.relevance_score,
                matching_content=result.matching_content,
                file_category=result.file_category,
                last_modified=result.last_modified,
                file_size=result.file_size,
                availability=availability,
                local_path=result.file_path,
                reasoning=result.reasoning,
                tags=result.tags,
                sync_status="local"
            )
            cloud_results.append(cloud_result)
        
        return cloud_results
    
    def _search_drive(self, query: str, limit: int) -> List[CloudSearchResult]:
        """Search Google Drive files"""
        
        try:
            service = self.auth_service.get_authenticated_service()
            
            # Build Drive API search query
            drive_query = f"name contains '{query}' or fullText contains '{query}'"
            
            # Execute search
            results = service.files().list(
                q=drive_query,
                pageSize=min(limit, 100),
                fields='files(id,name,size,mimeType,modifiedTime,parents,owners,description)',
                orderBy='modifiedTime desc'
            ).execute()
            
            drive_files = results.get('files', [])
            
            # Convert to CloudSearchResult
            cloud_results = []
            for drive_file in drive_files:
                
                # Calculate relevance score (simple text matching for now)
                relevance_score = self._calculate_drive_relevance(query, drive_file)
                
                # Check local availability
                file_id = drive_file['id']
                cached_path = self.streamer.cache_manager.get_cached_file_path(file_id)
                availability = FileAvailability.LOCAL_CACHED if cached_path else FileAvailability.CLOUD_STREAMABLE
                
                # Get modified time
                modified_time = datetime.fromisoformat(
                    drive_file.get('modifiedTime', datetime.now().isoformat()).replace('Z', '+00:00')
                )
                
                cloud_result = CloudSearchResult(
                    file_id=file_id,
                    filename=drive_file.get('name', 'Unknown'),
                    relevance_score=relevance_score,
                    matching_content=drive_file.get('description', '')[:200],
                    file_category=self._categorize_drive_file(drive_file),
                    last_modified=modified_time,
                    file_size=int(drive_file.get('size', 0)),
                    availability=availability,
                    local_path=str(cached_path) if cached_path else None,
                    drive_path=f"drive:///{file_id}",
                    reasoning=[f"Drive search match: {query}"],
                    tags=[],
                    sync_status="cloud"
                )
                cloud_results.append(cloud_result)
            
            return cloud_results
            
        except Exception as e:
            logger.error(f"❌ Drive search failed: {e}")
            return []
    
    def _calculate_drive_relevance(self, query: str, drive_file: Dict) -> float:
        """Calculate relevance score for Drive file"""
        
        query_lower = query.lower()
        filename = drive_file.get('name', '').lower()
        description = drive_file.get('description', '').lower()
        
        score = 0.0
        
        # Exact filename match
        if query_lower == filename:
            score += 100
        elif query_lower in filename:
            score += 50
        
        # Filename word matches
        query_words = query_lower.split()
        filename_words = filename.split()
        
        for query_word in query_words:
            for filename_word in filename_words:
                if query_word in filename_word:
                    score += 10
        
        # Description matches
        if query_lower in description:
            score += 20
        
        # File type relevance
        mime_type = drive_file.get('mimeType', '')
        if 'document' in mime_type or 'pdf' in mime_type:
            score += 5  # Boost text documents
        
        return min(score, 100.0)  # Cap at 100
    
    def _categorize_drive_file(self, drive_file: Dict) -> str:
        """Categorize Drive file based on metadata"""
        
        mime_type = drive_file.get('mimeType', '')
        filename = drive_file.get('name', '').lower()
        
        # Document types
        if any(doc_type in mime_type for doc_type in [
            'document', 'pdf', 'text', 'rtf'
        ]):
            return 'document'
        
        # Spreadsheet types
        if 'spreadsheet' in mime_type or filename.endswith(('.xlsx', '.csv')):
            return 'spreadsheet'
        
        # Presentation types
        if 'presentation' in mime_type or filename.endswith('.pptx'):
            return 'presentation'
        
        # Media types
        if mime_type.startswith('image/'):
            return 'image'
        elif mime_type.startswith('video/'):
            return 'video'
        elif mime_type.startswith('audio/'):
            return 'audio'
        
        return 'unknown'
    
    def _merge_and_deduplicate_results(self, results: List[CloudSearchResult]) -> List[CloudSearchResult]:
        """Merge and deduplicate search results"""
        
        # Use filename and size for deduplication
        seen = {}
        merged_results = []
        
        for result in results:
            # Create key for deduplication
            key = f"{result.filename}_{result.file_size}"
            
            if key not in seen:
                seen[key] = result
                merged_results.append(result)
            else:
                # Merge information from duplicate
                existing = seen[key]
                
                # Prefer result with higher relevance score
                if result.relevance_score > existing.relevance_score:
                    existing.relevance_score = result.relevance_score
                    existing.matching_content = result.matching_content
                
                # Merge reasoning
                existing.reasoning.extend(result.reasoning)
                
                # Update availability if better
                if (result.availability == FileAvailability.LOCAL_CACHED and 
                    existing.availability == FileAvailability.CLOUD_STREAMABLE):
                    existing.availability = result.availability
                    existing.local_path = result.local_path
        
        return merged_results
    
    def _filter_by_file_types(self, results: List[CloudSearchResult], file_types: List[str]) -> List[CloudSearchResult]:
        """Filter results by file types"""
        
        filtered = []
        for result in results:
            filename_lower = result.filename.lower()
            if any(filename_lower.endswith(f'.{ft.lower()}') or ft.lower() in filename_lower 
                  for ft in file_types):
                filtered.append(result)
        
        return filtered
    
    def _filter_by_date_range(self, results: List[CloudSearchResult], date_range: Tuple[datetime, datetime]) -> List[CloudSearchResult]:
        """Filter results by date range"""
        
        start_date, end_date = date_range
        return [r for r in results if start_date <= r.last_modified <= end_date]
    
    def _enhance_with_availability(self, results: List[CloudSearchResult]) -> List[CloudSearchResult]:
        """Enhance results with current availability information"""
        
        for result in results:
            # Check if file is being downloaded
            if self.streamer.get_streaming_status().get(result.file_id):
                result.availability = FileAvailability.DOWNLOADING
            
            # Update cache scores for cached files
            if result.availability == FileAvailability.LOCAL_CACHED and result.file_id in self.streamer.cache_manager.cache_metadata:
                cached_file = self.streamer.cache_manager.cache_metadata[result.file_id]
                result.cache_score = self.streamer.cache_manager.calculate_cache_score(cached_file)
        
        return results
    
    def get_file_content(self, 
                        file_id: str, 
                        ensure_local: bool = False,
                        progress_callback = None) -> Optional[Union[str, bytes]]:
        """
        Get file content (streaming or cached)
        
        Args:
            file_id: File identifier
            ensure_local: Force download to local storage
            progress_callback: Callback for download progress
            
        Returns:
            File content as string or bytes
        """
        
        try:
            logger.info(f"📖 Getting content for file: {file_id}")
            
            # Check if file is available locally
            if not ensure_local:
                cached_path = self.streamer.cache_manager.get_cached_file_path(file_id)
                if cached_path:
                    logger.info(f"   📁 Reading from cache: {cached_path.name}")
                    with open(cached_path, 'rb') as f:
                        content = f.read()
                    
                    # Try to decode as text for common file types
                    if cached_path.suffix.lower() in ['.txt', '.md', '.py', '.js', '.json', '.xml']:
                        try:
                            return content.decode('utf-8')
                        except UnicodeDecodeError:
                            pass
                    
                    return content
            
            # Download/stream from Drive
            logger.info(f"   ☁️  Streaming from Drive...")
            local_path = self.streamer.ensure_file_available(file_id, force_download=ensure_local)
            
            with open(local_path, 'rb') as f:
                content = f.read()
            
            # Try to decode as text for common file types
            if local_path.suffix.lower() in ['.txt', '.md', '.py', '.js', '.json', '.xml']:
                try:
                    return content.decode('utf-8')
                except UnicodeDecodeError:
                    pass
            
            return content
            
        except Exception as e:
            logger.error(f"❌ Error getting file content: {e}")
            return None
    
    def ensure_file_available(self, file_id: str) -> Optional[Path]:
        """Ensure file is available locally and return path"""
        
        try:
            return self.streamer.ensure_file_available(file_id)
        except Exception as e:
            logger.error(f"❌ Error ensuring file availability: {e}")
            return None
    
    def _scan_drive_metadata(self):
        """Perform lightweight scan of Drive metadata"""
        
        try:
            service = self.auth_service.get_authenticated_service()
            
            # Get recent files for quick overview
            results = service.files().list(
                pageSize=100,
                fields='files(id,name,size,mimeType,modifiedTime,parents)',
                orderBy='modifiedTime desc'
            ).execute()
            
            files = results.get('files', [])
            
            # Cache metadata
            for drive_file in files:
                self._drive_file_cache[drive_file['id']] = drive_file
            
            self._last_drive_scan = datetime.now()
            logger.info(f"   📊 Scanned {len(files)} recent Drive files")
            
        except Exception as e:
            logger.warning(f"⚠️  Drive metadata scan failed: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        
        status = {
            'authenticated': self._authenticated,
            'last_drive_scan': self._last_drive_scan.isoformat() if self._last_drive_scan else None,
            'config': self.config,
            'components': {}
        }
        
        # Authentication status
        # Authentication status
        if self._authenticated:
            # Use cached auth info if available and fresh (TTL 5 minutes)
            should_refresh = True
            if self._cached_auth_info and hasattr(self, '_auth_cache_time') and self._auth_cache_time:
                age = datetime.now() - self._auth_cache_time
                if age < timedelta(minutes=5):
                    should_refresh = False
                    auth_test = self._cached_auth_info

            if should_refresh:
                # Refresh cache
                try:
                     auth_test = self.auth_service.test_authentication()
                     if auth_test.get('success'):
                         self._cached_auth_info = auth_test
                         self._auth_cache_time = datetime.now()
                except Exception as e:
                     logger.warning(f"Status check auth failed: {e}")
                     # Keep old cache if refresh failed, or empty if none
                     auth_test = self._cached_auth_info if self._cached_auth_info else {}

            status['auth_info'] = {
                'user_name': auth_test.get('user_name', 'Unknown'),
                'user_email': auth_test.get('user_email', 'Unknown'),
                'storage_quota_gb': auth_test.get('total_storage_gb', 0),
                'storage_used_gb': auth_test.get('used_storage_gb', 0)
            }
        
        # Metadata store status
        metadata_stats = self.metadata_store.get_stats()
        status['components']['metadata_store'] = metadata_stats
        
        # Cache status
        cache_size = self.streamer.cache_manager.get_cache_size()
        status['components']['cache'] = {
            'size_mb': cache_size / (1024 * 1024),
            'max_size_mb': self.streamer.cache_manager.max_cache_size_bytes / (1024 * 1024),
            'files_cached': len(self.streamer.cache_manager.cache_metadata),
            'cache_dir': str(self.streamer.cache_manager.cache_dir)
        }
        
        # Sync service status
        if self.sync_service:
            status['components']['sync_service'] = self.sync_service.get_sync_status()
        
        # Active streaming status
        streaming_status = self.streamer.get_streaming_status()
        status['components']['streaming'] = {
            'active_streams': len(streaming_status),
            'stream_details': streaming_status
        }
        
        return status
    
    def cleanup(self):
        """Clean up resources and stop services"""
        
        logger.info("🧹 Cleaning up Google Drive Librarian...")
        
        # Stop sync service
        if self.sync_service and self.sync_service.is_running:
            self.sync_service.stop_background_sync()
        
        # Clear cache if requested
        # (This would be configurable in a real implementation)
        
        # Save configuration
        self._save_config(self.config)
        
        logger.info("✅ Cleanup complete")

def test_gdrive_librarian():
    """Test the complete Google Drive Librarian"""
    
    print("🔍 Testing Google Drive Librarian")
    print("=" * 50)
    
    try:
        # Initialize librarian
        librarian = GoogleDriveLibrarian(
            cache_size_gb=1.0,  # Small cache for testing
            auto_sync=False,    # Disable auto-sync for testing
            sync_interval=60
        )
        
        # Initialize system
        if not librarian.initialize():
            print("❌ Failed to initialize librarian")
            return
        
        print("✅ Librarian initialized successfully")
        
        # Test search functionality
        test_queries = [
            "contract",
            "Creative Project",
            "document",
            "recent files"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Testing search: '{query}'")
            
            results = librarian.search(
                query=query,
                scope=SearchScope.AUTO,
                limit=5
            )
            
            print(f"   📊 Found {len(results)} results")
            
            for i, result in enumerate(results, 1):
                print(f"   {i}. {result.filename}")
                print(f"      💯 Relevance: {result.relevance_score:.1f}%")
                print(f"      📁 Availability: {result.availability.value}")
                print(f"      📅 Modified: {result.last_modified.strftime('%Y-%m-%d %H:%M')}")
                if result.local_path:
                    print(f"      💾 Local: {Path(result.local_path).name}")
        
        # Test system status
        print(f"\n📊 System Status:")
        status = librarian.get_system_status()
        print(f"   🔐 Authenticated: {status['authenticated']}")
        if status['authenticated']:
            print(f"   👤 User: {status['auth_info']['user_name']}")
            print(f"   💾 Storage: {status['auth_info']['storage_used_gb']:.1f}GB used")
        
        print(f"   🗄️  Cache: {status['components']['cache']['files_cached']} files, "
              f"{status['components']['cache']['size_mb']:.1f}MB")
        
        print(f"   📊 Metadata: {status['components']['metadata_store']['total_files']} files indexed")
        
        # Cleanup
        librarian.cleanup()
        
        print(f"\n✅ Google Drive Librarian test complete!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gdrive_librarian()