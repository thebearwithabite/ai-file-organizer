#!/usr/bin/env python3
"""
Google Drive File Streaming System
On-demand file streaming with intelligent caching and memory-efficient processing

Features:
- Chunked downloads for large files
- Range requests for partial file access
- Memory-efficient streaming without full downloads
- Smart caching with usage patterns
- ADHD-friendly progress indicators
- Seamless local/cloud file access

Usage:
    streamer = GoogleDriveStreamer(auth_service)
    content = streamer.stream_file_content(drive_file_id)
    local_path = streamer.ensure_file_available(drive_file_id)

Created by: RT Max for AI File Organizer v3.0
"""

import os
import io
import time
import hashlib
import threading
from pathlib import Path
from typing import Optional, Dict, Any, BinaryIO, Iterator, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import logging

# Google API imports
try:
    from googleapiclient.http import MediaIoBaseDownload
    from googleapiclient.errors import HttpError
    import requests
except ImportError as e:
    print("❌ Required libraries not installed.")
    print("Run: pip install google-api-python-client requests")
    raise e

from google_drive_auth import GoogleDriveAuth, GoogleDriveAuthError
from local_metadata_store import LocalMetadataStore

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class StreamingProgress:
    """Track streaming progress for ADHD-friendly feedback"""
    file_id: str
    filename: str
    total_bytes: int
    downloaded_bytes: int
    start_time: datetime
    estimated_remaining: Optional[float] = None
    
    @property
    def progress_percent(self) -> float:
        if self.total_bytes == 0:
            return 0.0
        return (self.downloaded_bytes / self.total_bytes) * 100
    
    @property
    def download_speed_mbps(self) -> float:
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if elapsed == 0:
            return 0.0
        mb_downloaded = self.downloaded_bytes / (1024 * 1024)
        return mb_downloaded / elapsed

@dataclass
class CachedFile:
    """Information about a cached file"""
    file_id: str
    local_path: Path
    cache_time: datetime
    access_count: int
    last_access: datetime
    file_size: int
    drive_modified: datetime
    cache_score: float = 0.0
    
class SmartCacheManager:
    """
    Intelligent caching system for frequently accessed files
    
    Features:
    - Usage pattern analysis
    - Automatic cache eviction based on scores
    - File modification tracking
    - Memory-efficient cache management
    """
    
    def __init__(self, cache_dir: Path, max_cache_size_gb: float = 5.0):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_cache_size_bytes = max_cache_size_gb * 1024 * 1024 * 1024
        
        # Cache metadata
        self.cache_db_path = cache_dir / "cache_metadata.json"
        self.cache_metadata: Dict[str, CachedFile] = {}
        self.cache_lock = threading.Lock()
        
        self._load_cache_metadata()
        
        logger.info(f"🗄️  Smart cache initialized: {cache_dir} (max: {max_cache_size_gb}GB)")
    
    def _load_cache_metadata(self):
        """Load cache metadata from disk"""
        if self.cache_db_path.exists():
            try:
                with open(self.cache_db_path, 'r') as f:
                    data = json.load(f)
                
                # Convert to CachedFile objects
                for file_id, item_data in data.items():
                    self.cache_metadata[file_id] = CachedFile(
                        file_id=item_data['file_id'],
                        local_path=Path(item_data['local_path']),
                        cache_time=datetime.fromisoformat(item_data['cache_time']),
                        access_count=item_data.get('access_count', 1),
                        last_access=datetime.fromisoformat(item_data['last_access']),
                        file_size=item_data['file_size'],
                        drive_modified=datetime.fromisoformat(item_data['drive_modified']),
                        cache_score=item_data.get('cache_score', 0.0)
                    )
                
                logger.info(f"📚 Loaded {len(self.cache_metadata)} cached files")
                
            except Exception as e:
                logger.warning(f"⚠️  Could not load cache metadata: {e}")
                self.cache_metadata = {}
    
    def _save_cache_metadata(self):
        """Save cache metadata to disk"""
        try:
            # Convert to serializable format
            data = {}
            for file_id, cached_file in self.cache_metadata.items():
                data[file_id] = {
                    'file_id': cached_file.file_id,
                    'local_path': str(cached_file.local_path),
                    'cache_time': cached_file.cache_time.isoformat(),
                    'access_count': cached_file.access_count,
                    'last_access': cached_file.last_access.isoformat(),
                    'file_size': cached_file.file_size,
                    'drive_modified': cached_file.drive_modified.isoformat(),
                    'cache_score': cached_file.cache_score
                }
            
            with open(self.cache_db_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"❌ Could not save cache metadata: {e}")
    
    def calculate_cache_score(self, cached_file: CachedFile) -> float:
        """
        Calculate cache score based on usage patterns
        
        Higher scores = keep in cache longer
        Lower scores = evict sooner
        
        Factors:
        - Access frequency (higher = better)
        - Recency (more recent = better)
        - File size (smaller files score higher)
        - File age in cache (established files score higher)
        """
        now = datetime.now()
        
        # Access frequency score (0-40 points)
        days_in_cache = max(1, (now - cached_file.cache_time).days)
        access_frequency = cached_file.access_count / days_in_cache
        frequency_score = min(40, access_frequency * 10)
        
        # Recency score (0-30 points)
        hours_since_access = (now - cached_file.last_access).total_seconds() / 3600
        if hours_since_access < 1:
            recency_score = 30
        elif hours_since_access < 24:
            recency_score = 25
        elif hours_since_access < 168:  # 1 week
            recency_score = 15
        else:
            recency_score = 5
        
        # Size score (0-20 points) - prefer smaller files
        size_mb = cached_file.file_size / (1024 * 1024)
        if size_mb < 10:
            size_score = 20
        elif size_mb < 100:
            size_score = 15
        elif size_mb < 500:
            size_score = 10
        else:
            size_score = 5
        
        # Stability score (0-10 points) - files cached longer are more established
        days_cached = (now - cached_file.cache_time).days
        if days_cached > 30:
            stability_score = 10
        elif days_cached > 7:
            stability_score = 7
        elif days_cached > 1:
            stability_score = 4
        else:
            stability_score = 1
        
        total_score = frequency_score + recency_score + size_score + stability_score
        cached_file.cache_score = total_score
        
        return total_score
    
    def should_cache_file(self, file_size: int, mime_type: str = "") -> bool:
        """Determine if a file should be cached"""
        
        # Don't cache very large files (> 500MB)
        if file_size > 500 * 1024 * 1024:
            return False
        
        # Always cache small files (< 10MB)
        if file_size < 10 * 1024 * 1024:
            return True
        
        # Cache certain file types
        cache_friendly_types = [
            'application/pdf',
            'text/',
            'application/vnd.openxmlformats-officedocument',
            'application/vnd.oasis.opendocument'
        ]
        
        if any(mime_type.startswith(t) for t in cache_friendly_types):
            return True
        
        # Check available cache space
        current_size = self.get_cache_size()
        if current_size + file_size > self.max_cache_size_bytes * 0.8:  # 80% threshold
            return False
        
        return True
    
    def get_cached_file_path(self, file_id: str) -> Optional[Path]:
        """Get cached file path if available and valid"""
        
        with self.cache_lock:
            if file_id not in self.cache_metadata:
                return None
            
            cached_file = self.cache_metadata[file_id]
            
            # Check if file still exists
            if not cached_file.local_path.exists():
                logger.warning(f"🗑️  Cached file missing, removing from metadata: {cached_file.local_path}")
                del self.cache_metadata[file_id]
                self._save_cache_metadata()
                return None
            
            # Update access info
            cached_file.access_count += 1
            cached_file.last_access = datetime.now()
            self._save_cache_metadata()
            
            return cached_file.local_path
    
    def add_to_cache(self, file_id: str, content: bytes, drive_metadata: Dict) -> Path:
        """Add file to cache"""
        
        # Generate cache file path
        filename = drive_metadata.get('name', f'file_{file_id}')
        # Sanitize filename
        safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '.', '-', '_')).strip()
        cache_path = self.cache_dir / f"{file_id}_{safe_filename}"
        
        # Write content to cache
        with open(cache_path, 'wb') as f:
            f.write(content)
        
        # Add to metadata
        with self.cache_lock:
            modified_time = datetime.fromisoformat(drive_metadata.get('modifiedTime', datetime.now().isoformat()).replace('Z', '+00:00'))
            
            cached_file = CachedFile(
                file_id=file_id,
                local_path=cache_path,
                cache_time=datetime.now(),
                access_count=1,
                last_access=datetime.now(),
                file_size=len(content),
                drive_modified=modified_time
            )
            
            self.cache_metadata[file_id] = cached_file
            self._save_cache_metadata()
        
        logger.info(f"📁 Cached file: {safe_filename} ({len(content) / 1024:.1f}KB)")
        return cache_path
    
    def get_cache_size(self) -> int:
        """Get current cache size in bytes"""
        total_size = 0
        for cached_file in self.cache_metadata.values():
            if cached_file.local_path.exists():
                total_size += cached_file.file_size
            else:
                # Clean up missing files
                logger.warning(f"🧹 Cleaning up missing cache file: {cached_file.local_path}")
        
        return total_size
    
    def evict_cache_intelligently(self, target_free_bytes: int):
        """Intelligently evict cached files to free space"""
        
        logger.info(f"🧹 Starting intelligent cache eviction (target: {target_free_bytes / 1024 / 1024:.1f}MB)")
        
        with self.cache_lock:
            # Calculate cache scores for all files
            for cached_file in self.cache_metadata.values():
                self.calculate_cache_score(cached_file)
            
            # Sort by cache score (lowest first = evict first)
            files_to_consider = sorted(
                self.cache_metadata.values(), 
                key=lambda x: x.cache_score
            )
            
            freed_bytes = 0
            files_evicted = 0
            
            for cached_file in files_to_consider:
                if freed_bytes >= target_free_bytes:
                    break
                
                # Remove file
                if cached_file.local_path.exists():
                    try:
                        cached_file.local_path.unlink()
                        freed_bytes += cached_file.file_size
                        files_evicted += 1
                        logger.info(f"🗑️  Evicted: {cached_file.local_path.name} (score: {cached_file.cache_score:.1f})")
                    except Exception as e:
                        logger.error(f"❌ Could not evict {cached_file.local_path}: {e}")
                
                # Remove from metadata
                del self.cache_metadata[cached_file.file_id]
            
            self._save_cache_metadata()
            
        logger.info(f"✅ Cache eviction complete: {files_evicted} files, {freed_bytes / 1024 / 1024:.1f}MB freed")

class GoogleDriveStreamer:
    """
    Google Drive File Streaming System
    
    Provides on-demand file streaming with intelligent caching,
    memory-efficient processing, and seamless local/cloud access.
    """
    
    def __init__(self, 
                 auth_service: GoogleDriveAuth,
                 metadata_store: LocalMetadataStore,
                 cache_dir: Path = None,
                 cache_size_gb: float = 5.0):
        """
        Initialize Google Drive Streamer
        
        Args:
            auth_service: Authenticated Google Drive service
            metadata_store: Local metadata store
            cache_dir: Directory for caching files
            cache_size_gb: Maximum cache size in GB
        """
        
        self.auth_service = auth_service
        self.metadata_store = metadata_store
        self.drive_service = None
        
        # Set up caching
        if cache_dir is None:
            cache_dir = Path.home() / ".ai_organizer_cache" / "drive_files"
        self.cache_manager = SmartCacheManager(cache_dir, cache_size_gb)
        
        # Streaming state
        self.active_streams: Dict[str, StreamingProgress] = {}
        self.stream_lock = threading.Lock()
        
        logger.info(f"🌊 GoogleDriveStreamer initialized")
        logger.info(f"   📁 Cache dir: {cache_dir}")
        logger.info(f"   💾 Max cache: {cache_size_gb}GB")
    
    def _get_drive_service(self):
        """Get authenticated Google Drive service"""
        if not self.drive_service:
            self.drive_service = self.auth_service.get_authenticated_service()
        return self.drive_service
    
    def stream_file_content(self, 
                           file_id: str, 
                           chunk_size: int = 1024 * 1024,
                           start_byte: int = 0,
                           end_byte: Optional[int] = None) -> Iterator[bytes]:
        """
        Stream file content in chunks without full download
        
        Args:
            file_id: Google Drive file ID
            chunk_size: Size of chunks to stream (default 1MB)
            start_byte: Starting byte position (for range requests)
            end_byte: Ending byte position (optional)
            
        Yields:
            bytes: File content chunks
        """
        
        try:
            service = self._get_drive_service()
            
            # Get file metadata
            file_metadata = service.files().get(fileId=file_id, fields='name,size,mimeType,modifiedTime').execute()
            file_size = int(file_metadata.get('size', 0))
            filename = file_metadata.get('name', f'file_{file_id}')
            
            # Set up progress tracking
            progress = StreamingProgress(
                file_id=file_id,
                filename=filename,
                total_bytes=file_size,
                downloaded_bytes=start_byte,
                start_time=datetime.now()
            )
            
            with self.stream_lock:
                self.active_streams[file_id] = progress
            
            logger.info(f"🌊 Starting stream: {filename} ({file_size / 1024 / 1024:.1f}MB)")
            
            # Create download request
            request = service.files().get_media(fileId=file_id)
            
            # Set up range request if specified
            if start_byte > 0 or end_byte is not None:
                end_pos = end_byte if end_byte is not None else file_size - 1
                request.headers['Range'] = f'bytes={start_byte}-{end_pos}'
            
            # Stream the content
            downloaded = 0
            with io.BytesIO() as buffer:
                downloader = MediaIoBaseDownload(buffer, request, chunksize=chunk_size)
                done = False
                
                while not done:
                    status, done = downloader.next_chunk()
                    
                    # Get chunk data
                    buffer.seek(downloaded)
                    chunk_data = buffer.read()
                    
                    if chunk_data:
                        downloaded += len(chunk_data)
                        progress.downloaded_bytes = start_byte + downloaded
                        
                        # ADHD-friendly progress update
                        if downloaded % (chunk_size * 5) == 0:  # Every 5 chunks
                            logger.info(f"   📊 {filename}: {progress.progress_percent:.1f}% "
                                       f"({progress.download_speed_mbps:.1f}MB/s)")
                        
                        yield chunk_data
            
            logger.info(f"✅ Stream complete: {filename}")
            
        except HttpError as e:
            logger.error(f"❌ HTTP error streaming {file_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error streaming {file_id}: {e}")
            raise
        finally:
            # Clean up progress tracking
            with self.stream_lock:
                if file_id in self.active_streams:
                    del self.active_streams[file_id]
    
    def ensure_file_available(self, file_id: str, force_download: bool = False) -> Path:
        """
        Ensure file is available locally (from cache or download)
        
        Args:
            file_id: Google Drive file ID
            force_download: Force re-download even if cached
            
        Returns:
            Path: Local file path
        """
        
        # Check cache first (unless forced download)
        if not force_download:
            cached_path = self.cache_manager.get_cached_file_path(file_id)
            if cached_path:
                logger.info(f"📁 File available from cache: {cached_path.name}")
                return cached_path
        
        # Download file
        return self._download_and_cache_file(file_id)
    
    def _download_and_cache_file(self, file_id: str) -> Path:
        """Download file and add to cache if appropriate"""
        
        try:
            service = self._get_drive_service()
            
            # Get file metadata
            file_metadata = service.files().get(
                fileId=file_id, 
                fields='name,size,mimeType,modifiedTime'
            ).execute()
            
            file_size = int(file_metadata.get('size', 0))
            filename = file_metadata.get('name', f'file_{file_id}')
            mime_type = file_metadata.get('mimeType', '')
            
            logger.info(f"⬇️  Downloading: {filename} ({file_size / 1024 / 1024:.1f}MB)")
            
            # Check if we should cache this file
            should_cache = self.cache_manager.should_cache_file(file_size, mime_type)
            
            if should_cache:
                # Make room in cache if needed
                current_cache_size = self.cache_manager.get_cache_size()
                if current_cache_size + file_size > self.cache_manager.max_cache_size_bytes:
                    target_free = file_size + (self.cache_manager.max_cache_size_bytes * 0.2)  # 20% buffer
                    self.cache_manager.evict_cache_intelligently(target_free)
            
            # Download content
            content = b''
            for chunk in self.stream_file_content(file_id):
                content += chunk
            
            if should_cache:
                # Add to cache
                cache_path = self.cache_manager.add_to_cache(file_id, content, file_metadata)
                return cache_path
            else:
                # Save to temp location
                temp_dir = Path.home() / ".ai_organizer_temp"
                temp_dir.mkdir(exist_ok=True)
                
                safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '.', '-', '_')).strip()
                temp_path = temp_dir / f"temp_{file_id}_{safe_filename}"
                
                with open(temp_path, 'wb') as f:
                    f.write(content)
                
                logger.info(f"💾 File saved to temp: {temp_path}")
                return temp_path
                
        except Exception as e:
            logger.error(f"❌ Error downloading file {file_id}: {e}")
            raise
    
    def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """Get comprehensive file information"""
        
        try:
            service = self._get_drive_service()
            
            # Get file metadata from Drive
            drive_metadata = service.files().get(
                fileId=file_id,
                fields='id,name,size,mimeType,modifiedTime,createdTime,parents,owners'
            ).execute()
            
            # Check if file is cached
            cached_path = self.cache_manager.get_cached_file_path(file_id)
            is_cached = cached_path is not None
            
            # Get local metadata if available
            local_metadata = self.metadata_store.get_file_metadata(file_id)
            
            file_info = {
                'drive_metadata': drive_metadata,
                'local_metadata': local_metadata,
                'is_cached': is_cached,
                'cached_path': str(cached_path) if cached_path else None,
                'file_size_mb': int(drive_metadata.get('size', 0)) / (1024 * 1024),
                'can_stream': True,
                'last_checked': datetime.now().isoformat()
            }
            
            return file_info
            
        except Exception as e:
            logger.error(f"❌ Error getting file info for {file_id}: {e}")
            return {'error': str(e)}
    
    def get_streaming_status(self) -> Dict[str, Dict]:
        """Get status of all active streams"""
        
        with self.stream_lock:
            status = {}
            for file_id, progress in self.active_streams.items():
                status[file_id] = {
                    'filename': progress.filename,
                    'progress_percent': progress.progress_percent,
                    'downloaded_mb': progress.downloaded_bytes / (1024 * 1024),
                    'total_mb': progress.total_bytes / (1024 * 1024),
                    'speed_mbps': progress.download_speed_mbps,
                    'elapsed_seconds': (datetime.now() - progress.start_time).total_seconds()
                }
            
            return status
    
    def clear_cache(self, older_than_days: int = 30):
        """Clear cached files older than specified days"""
        
        cutoff_date = datetime.now() - timedelta(days=older_than_days)
        files_to_remove = []
        
        with self.cache_manager.cache_lock:
            for file_id, cached_file in self.cache_manager.cache_metadata.items():
                if cached_file.last_access < cutoff_date:
                    files_to_remove.append(file_id)
        
        for file_id in files_to_remove:
            cached_file = self.cache_manager.cache_metadata[file_id]
            if cached_file.local_path.exists():
                cached_file.local_path.unlink()
            del self.cache_manager.cache_metadata[file_id]
        
        if files_to_remove:
            self.cache_manager._save_cache_metadata()
            logger.info(f"🧹 Cleared {len(files_to_remove)} old cached files")

def test_gdrive_streamer():
    """Test the Google Drive Streamer"""
    
    print("🌊 Testing Google Drive Streamer")
    print("=" * 50)
    
    try:
        # Initialize components
        auth = GoogleDriveAuth()
        metadata_store = LocalMetadataStore()
        streamer = GoogleDriveStreamer(auth, metadata_store)
        
        # Test authentication
        test_results = auth.test_authentication()
        if not test_results['success']:
            print(f"❌ Authentication failed: {test_results}")
            return
        
        print(f"✅ Authenticated as: {test_results['user_name']}")
        print(f"   💾 Drive storage: {test_results['free_storage_gb']:.1f}GB free")
        
        # Get a test file (first file in Drive)
        service = auth.get_authenticated_service()
        results = service.files().list(pageSize=1).execute()
        files = results.get('files', [])
        
        if not files:
            print("📂 No files found in Google Drive for testing")
            return
        
        test_file = files[0]
        file_id = test_file['id']
        filename = test_file['name']
        
        print(f"\n🧪 Testing with file: {filename}")
        
        # Test file info
        file_info = streamer.get_file_info(file_id)
        print(f"   📊 File size: {file_info['file_size_mb']:.2f}MB")
        print(f"   🗄️  Cached: {file_info['is_cached']}")
        
        # Test ensuring file availability
        print(f"\n⬇️  Ensuring file availability...")
        local_path = streamer.ensure_file_available(file_id)
        print(f"   ✅ File available at: {local_path}")
        
        # Test cache status
        cache_size = streamer.cache_manager.get_cache_size()
        print(f"\n📁 Cache status:")
        print(f"   💾 Current size: {cache_size / 1024 / 1024:.1f}MB")
        print(f"   📈 Files cached: {len(streamer.cache_manager.cache_metadata)}")
        
        print(f"\n✅ Google Drive Streamer test complete!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gdrive_streamer()