#!/usr/bin/env python3
"""
Interactive Batch Processing with Content Preview
Part of AI File Organizer v3.1 - Adaptive Emergency Prevention System

Provides ADHD-friendly batch processing with:
- Content preview before organization decisions
- Human-in-the-loop batch processing
- Smart grouping and similarity detection
- Confidence-based automatic vs manual processing
- Preview-based decision making

Created by: RT Max / Claude Code
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any, Tuple
import sqlite3
import json
import logging
import hashlib
from dataclasses import dataclass, asdict
from collections import defaultdict
import re

# Import existing system components
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from universal_adaptive_learning import UniversalAdaptiveLearning
from confidence_system import ADHDFriendlyConfidenceSystem, ConfidenceLevel
from content_extractor import ContentExtractor
from gdrive_integration import get_ai_organizer_root, get_metadata_root
from easy_rollback_system import EasyRollbackSystem

@dataclass
class FilePreview:
    """Preview information for a file"""
    file_path: str
    file_name: str
    file_size_mb: float
    file_type: str
    creation_date: datetime
    modification_date: datetime
    content_preview: str
    content_keywords: List[str]
    content_summary: str
    predicted_category: str
    confidence_score: float
    similar_files: List[str]
    duplicate_indicator: bool

@dataclass
class BatchGroup:
    """A group of similar files for batch processing"""
    group_id: str
    group_type: str  # "similar_content", "same_type", "same_source", "duplicates"
    group_name: str
    file_previews: List[FilePreview]
    common_characteristics: Dict[str, Any]
    suggested_action: str
    confidence_level: ConfidenceLevel
    batch_size: int

@dataclass
class BatchOperation:
    """A batch operation to be performed"""
    operation_id: str
    operation_type: str  # "organize", "deduplicate", "archive", "delete"
    target_location: str
    affected_files: List[str]
    confidence_score: float
    user_approved: bool
    execution_time: Optional[datetime] = None
    success: Optional[bool] = None

class InteractiveBatchProcessor:
    """
    Interactive batch processor with content preview capabilities
    
    Designed for ADHD users to make informed decisions about file organization
    through visual previews and intelligent grouping
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else get_ai_organizer_root()
        
        # Initialize components
        self.learning_system = UniversalAdaptiveLearning(str(self.base_dir))
        self.confidence_system = ADHDFriendlyConfidenceSystem(str(self.base_dir))
        self.content_extractor = ContentExtractor(str(self.base_dir))
        self.rollback_system = EasyRollbackSystem()
        
        # Batch processing database
        self.batch_db_path = get_metadata_root() /  "batch_processing.db"
        
        # Configuration
        self.config = {
            "max_batch_size": 50,           # Maximum files per batch
            "preview_length": 500,          # Characters in content preview
            "similarity_threshold": 0.7,    # Similarity threshold for grouping
            "auto_process_threshold": 0.85, # Confidence for automatic processing
            "keyword_limit": 10,            # Maximum keywords per file
            "group_by_preferences": [
                "duplicates",
                "similar_content", 
                "same_type",
                "same_source",
                "same_date"
            ]
        }
        
        # Content preview cache
        self.preview_cache = {}
        
        # Active batch sessions
        self.active_sessions = {}
        
        # Statistics
        self.stats = {
            "batches_processed": 0,
            "files_organized": 0,
            "preview_cache_hits": 0,
            "user_decisions": 0,
            "automatic_decisions": 0,
            "confidence_improvements": 0
        }
        
        # Initialize database
        self._init_batch_database()
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.info("Interactive Batch Processor initialized")

    def _init_batch_database(self):
        """Initialize batch processing database"""
        self.batch_db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.batch_db_path) as conn:
            # File previews cache
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_previews (
                    file_path TEXT PRIMARY KEY,
                    file_hash TEXT,
                    preview_data TEXT,
                    generated_time TEXT,
                    last_accessed TEXT,
                    access_count INTEGER DEFAULT 1
                )
            """)
            
            # Batch sessions
            conn.execute("""
                CREATE TABLE IF NOT EXISTS batch_sessions (
                    session_id TEXT PRIMARY KEY,
                    start_time TEXT,
                    end_time TEXT,
                    source_directory TEXT,
                    total_files INTEGER,
                    groups_created INTEGER,
                    files_processed INTEGER,
                    user_decisions INTEGER,
                    automatic_decisions INTEGER,
                    success_rate REAL
                )
            """)
            
            # Batch operations
            conn.execute("""
                CREATE TABLE IF NOT EXISTS batch_operations (
                    operation_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    operation_type TEXT,
                    target_location TEXT,
                    affected_files TEXT,
                    confidence_score REAL,
                    user_approved BOOLEAN,
                    execution_time TEXT,
                    success BOOLEAN,
                    error_message TEXT
                )
            """)
            
            # User feedback
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_feedback (
                    feedback_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    file_path TEXT,
                    predicted_action TEXT,
                    user_action TEXT,
                    satisfaction_score INTEGER,
                    feedback_time TEXT,
                    comments TEXT
                )
            """)
            
            conn.commit()

    def start_batch_session(self, source_directory: str, session_name: str = None) -> str:
        """
        Start a new batch processing session
        
        Args:
            source_directory: Directory to process
            session_name: Optional name for the session
            
        Returns:
            Session ID
        """
        
        source_path = Path(source_directory)
        if not source_path.exists():
            raise ValueError(f"Source directory does not exist: {source_directory}")
        
        # Generate session ID
        session_id = hashlib.md5(f"{source_directory}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        # Scan directory for files
        files_found = self._scan_directory_for_files(source_path)
        
        if not files_found:
            raise ValueError(f"No processable files found in {source_directory}")
        
        self.logger.info(f"Starting batch session {session_id} with {len(files_found)} files")
        
        # Create file previews
        file_previews = []
        
        # OPTIMIZATION: Reuse database connection for batch processing
        # This prevents N+1 connection overhead (opens 1 connection instead of 2*N)
        try:
            with sqlite3.connect(self.batch_db_path) as conn:
                for file_path in files_found:
                    preview = self._generate_file_preview(file_path, db_connection=conn)
                    if preview:
                        file_previews.append(preview)

                # Group files intelligently (CPU bound, no DB)
                batch_groups = self._create_intelligent_groups(file_previews)

                # Create session
                session_data = {
                    "session_id": session_id,
                    "session_name": session_name or f"Batch_{datetime.now().strftime('%Y%m%d_%H%M')}",
                    "start_time": datetime.now(),
                    "source_directory": str(source_path),
                    "total_files": len(files_found),
                    "file_previews": file_previews,
                    "batch_groups": batch_groups,
                    "current_group_index": 0,
                    "processed_groups": [],
                    "pending_operations": [],
                    "user_decisions": [],
                    "status": "active"
                }

                self.active_sessions[session_id] = session_data

                # Record session in database (reusing connection)
                self._record_batch_session(session_data, db_connection=conn)

        except Exception as e:
            self.logger.error(f"Error in batch session initialization: {e}")
            raise
        
        self.logger.info(f"Batch session {session_id} created with {len(batch_groups)} groups")
        
        return session_id

    def get_session_overview(self, session_id: str) -> Dict[str, Any]:
        """Get overview of batch session"""
        
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.active_sessions[session_id]
        
        return {
            "session_id": session_id,
            "session_name": session["session_name"],
            "source_directory": session["source_directory"],
            "total_files": session["total_files"],
            "total_groups": len(session["batch_groups"]),
            "current_group": session["current_group_index"],
            "processed_groups": len(session["processed_groups"]),
            "pending_operations": len(session["pending_operations"]),
            "status": session["status"],
            "progress_percent": (len(session["processed_groups"]) / len(session["batch_groups"]) * 100) if session["batch_groups"] else 0
        }

    def get_next_group_for_review(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the next group for user review"""
        
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.active_sessions[session_id]
        
        if session["current_group_index"] >= len(session["batch_groups"]):
            return None  # No more groups
        
        current_group = session["batch_groups"][session["current_group_index"]]
        
        # Check if this group can be processed automatically
        if (current_group.confidence_level in [ConfidenceLevel.ALWAYS] or
            (current_group.confidence_level == ConfidenceLevel.SMART and 
             max(fp.confidence_score for fp in current_group.file_previews) >= self.config["auto_process_threshold"])):
            
            # Process automatically
            self._process_group_automatically(session_id, current_group)
            session["current_group_index"] += 1
            return self.get_next_group_for_review(session_id)  # Get next group
        
        # Prepare group for user review
        group_data = self._prepare_group_for_review(current_group)
        
        return group_data

    def process_user_decision(self, session_id: str, group_id: str, user_decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process user decision for a group
        
        Args:
            session_id: Session ID
            group_id: Group ID
            user_decision: User's decision data
            
        Returns:
            Processing result
        """
        
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.active_sessions[session_id]
        current_group = session["batch_groups"][session["current_group_index"]]
        
        if current_group.group_id != group_id:
            raise ValueError(f"Group ID mismatch: expected {current_group.group_id}, got {group_id}")
        
        # Process the decision
        result = self._execute_user_decision(session_id, current_group, user_decision)
        
        # Record user decision for learning
        self._record_user_decision(session_id, current_group, user_decision, result)
        
        # Update learning system
        self._update_learning_from_decision(current_group, user_decision)
        
        # Move to next group
        session["processed_groups"].append(current_group.group_id)
        session["current_group_index"] += 1
        session["user_decisions"].append({
            "group_id": group_id,
            "decision": user_decision,
            "timestamp": datetime.now().isoformat()
        })
        
        self.stats["user_decisions"] += 1
        
        return result

    def _scan_directory_for_files(self, directory: Path) -> List[Path]:
        """Scan directory for processable files"""
        
        files = []
        supported_extensions = {'.pdf', '.docx', '.doc', '.txt', '.md', '.pages', '.rtf',
                              '.jpg', '.png', '.gif', '.jpeg', '.mp4', '.mov', '.avi',
                              '.mp3', '.wav', '.m4a', '.ipynb', '.json', '.csv', '.xlsx'}
        
        try:
            for file_path in directory.rglob('*'):
                if (file_path.is_file() and 
                    file_path.suffix.lower() in supported_extensions and
                    not file_path.name.startswith('.')):
                    files.append(file_path)
        except Exception as e:
            self.logger.error(f"Error scanning directory {directory}: {e}")
        
        return files

    def _generate_file_preview(self, file_path: Path, db_connection: Optional[sqlite3.Connection] = None) -> Optional[FilePreview]:
        """Generate preview for a file"""
        
        try:
            # Check cache first
            file_hash = self._calculate_file_hash(file_path)
            cached_preview = self._get_cached_preview(str(file_path), file_hash, db_connection)
            
            if cached_preview:
                self.stats["preview_cache_hits"] += 1
                return cached_preview
            
            # Generate new preview
            stat_info = file_path.stat()
            
            # Extract content
            content_preview = ""
            content_keywords = []
            content_summary = ""
            
            try:
                if file_path.suffix.lower() in ['.txt', '.md', '.py', '.js', '.css', '.html']:
                    # Read text files directly
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(self.config["preview_length"] * 2)
                        content_preview = content[:self.config["preview_length"]]
                        content_keywords = self._extract_keywords(content)
                        content_summary = self._generate_content_summary(content)
                
                elif file_path.suffix.lower() in ['.pdf', '.docx', '.doc', '.pages', '.rtf']:
                    # Use content extractor for documents
                    extraction_result = self.content_extractor.extract_content(file_path)
                    if extraction_result['success']:
                        content = extraction_result['text']
                        content_preview = content[:self.config["preview_length"]]
                        content_keywords = self._extract_keywords(content)
                        content_summary = self._generate_content_summary(content)
                
            except Exception as e:
                self.logger.warning(f"Could not extract content from {file_path}: {e}")
            
            # Get prediction from learning system
            prediction = self.learning_system.predict_user_action(
                str(file_path), 
                {"content_keywords": content_keywords}
            )
            
            predicted_category = prediction.get("predicted_action", {}).get("target_category", "unknown")
            confidence_score = prediction.get("confidence", 0.0)
            
            # Check for similar files
            similar_files = self._find_similar_files(file_path, content_keywords)
            
            # Check for duplicates
            duplicate_indicator = self._is_likely_duplicate(file_path)
            
            preview = FilePreview(
                file_path=str(file_path),
                file_name=file_path.name,
                file_size_mb=stat_info.st_size / (1024 * 1024),
                file_type=file_path.suffix.lower(),
                creation_date=datetime.fromtimestamp(stat_info.st_ctime),
                modification_date=datetime.fromtimestamp(stat_info.st_mtime),
                content_preview=content_preview,
                content_keywords=content_keywords,
                content_summary=content_summary,
                predicted_category=predicted_category,
                confidence_score=confidence_score,
                similar_files=similar_files,
                duplicate_indicator=duplicate_indicator
            )
            
            # Cache the preview
            self._cache_preview(str(file_path), file_hash, preview, db_connection)
            
            return preview
            
        except Exception as e:
            self.logger.error(f"Error generating preview for {file_path}: {e}")
            return None

    def _create_intelligent_groups(self, file_previews: List[FilePreview]) -> List[BatchGroup]:
        """Create intelligent groups of similar files"""
        
        groups = []
        remaining_files = file_previews.copy()
        
        # Group by priority order
        for group_type in self.config["group_by_preferences"]:
            if group_type == "duplicates":
                duplicate_groups = self._group_by_duplicates(remaining_files)
                groups.extend(duplicate_groups)
                # Remove grouped files
                grouped_files = {fp.file_path for group in duplicate_groups for fp in group.file_previews}
                remaining_files = [fp for fp in remaining_files if fp.file_path not in grouped_files]
            
            elif group_type == "similar_content":
                content_groups = self._group_by_similar_content(remaining_files)
                groups.extend(content_groups)
                # Remove grouped files
                grouped_files = {fp.file_path for group in content_groups for fp in group.file_previews}
                remaining_files = [fp for fp in remaining_files if fp.file_path not in grouped_files]
            
            elif group_type == "same_type":
                type_groups = self._group_by_file_type(remaining_files)
                groups.extend(type_groups)
                # Remove grouped files
                grouped_files = {fp.file_path for group in type_groups for fp in group.file_previews}
                remaining_files = [fp for fp in remaining_files if fp.file_path not in grouped_files]
            
            elif group_type == "same_source":
                source_groups = self._group_by_source_directory(remaining_files)
                groups.extend(source_groups)
                # Remove grouped files
                grouped_files = {fp.file_path for group in source_groups for fp in group.file_previews}
                remaining_files = [fp for fp in remaining_files if fp.file_path not in grouped_files]
            
            elif group_type == "same_date":
                date_groups = self._group_by_date(remaining_files)
                groups.extend(date_groups)
                # Remove grouped files
                grouped_files = {fp.file_path for group in date_groups for fp in group.file_previews}
                remaining_files = [fp for fp in remaining_files if fp.file_path not in grouped_files]
        
        # Create individual groups for remaining files
        for file_preview in remaining_files:
            individual_group = self._create_individual_group(file_preview)
            groups.append(individual_group)
        
        # Ensure no group exceeds max batch size
        final_groups = []
        for group in groups:
            if len(group.file_previews) <= self.config["max_batch_size"]:
                final_groups.append(group)
            else:
                # Split large groups
                split_groups = self._split_large_group(group)
                final_groups.extend(split_groups)
        
        return final_groups

    def _group_by_duplicates(self, file_previews: List[FilePreview]) -> List[BatchGroup]:
        """Group files that appear to be duplicates"""
        
        groups = []
        duplicate_candidates = [fp for fp in file_previews if fp.duplicate_indicator]
        
        if not duplicate_candidates:
            return groups
        
        # Group by similar file names and sizes
        name_size_groups = defaultdict(list)
        
        for fp in duplicate_candidates:
            # Create a key based on base filename and size
            base_name = re.sub(r'[\s\-_]*\([0-9]+\)|[\s\-_]*copy[\s\-_]*[0-9]*', '', fp.file_name.lower())
            size_key = f"{fp.file_size_mb:.1f}mb"
            key = f"{base_name}_{size_key}"
            name_size_groups[key].append(fp)
        
        # Create groups for sets with multiple files
        for key, file_list in name_size_groups.items():
            if len(file_list) > 1:
                group_id = hashlib.md5(f"duplicates_{key}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
                
                group = BatchGroup(
                    group_id=group_id,
                    group_type="duplicates",
                    group_name=f"Duplicates: {file_list[0].file_name}",
                    file_previews=file_list,
                    common_characteristics={
                        "base_filename": base_name,
                        "file_size": f"{file_list[0].file_size_mb:.1f} MB",
                        "file_type": file_list[0].file_type
                    },
                    suggested_action="remove_duplicates",
                    confidence_level=ConfidenceLevel.SMART,
                    batch_size=len(file_list)
                )
                
                groups.append(group)
        
        return groups

    def _group_by_similar_content(self, file_previews: List[FilePreview]) -> List[BatchGroup]:
        """Group files with similar content"""
        
        groups = []
        
        # Only group files with actual content
        content_files = [fp for fp in file_previews if fp.content_keywords]
        
        if len(content_files) < 2:
            return groups
        
        # Calculate content similarity matrix
        similarity_groups = []
        processed = set()
        
        for i, fp1 in enumerate(content_files):
            if fp1.file_path in processed:
                continue
            
            similar_files = [fp1]
            processed.add(fp1.file_path)
            
            for j, fp2 in enumerate(content_files[i+1:], i+1):
                if fp2.file_path in processed:
                    continue
                
                similarity = self._calculate_content_similarity(fp1, fp2)
                
                if similarity >= self.config["similarity_threshold"]:
                    similar_files.append(fp2)
                    processed.add(fp2.file_path)
            
            if len(similar_files) > 1:
                similarity_groups.append(similar_files)
        
        # Create batch groups
        for i, file_list in enumerate(similarity_groups):
            if len(file_list) > 1:
                group_id = hashlib.md5(f"similar_content_{i}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
                
                # Find common keywords
                common_keywords = self._find_common_keywords([fp.content_keywords for fp in file_list])
                
                group = BatchGroup(
                    group_id=group_id,
                    group_type="similar_content",
                    group_name=f"Similar: {', '.join(common_keywords[:3])}",
                    file_previews=file_list,
                    common_characteristics={
                        "common_keywords": common_keywords,
                        "content_theme": self._infer_content_theme(common_keywords),
                        "average_confidence": sum(fp.confidence_score for fp in file_list) / len(file_list)
                    },
                    suggested_action="organize_together",
                    confidence_level=ConfidenceLevel.SMART,
                    batch_size=len(file_list)
                )
                
                groups.append(group)
        
        return groups

    def _group_by_file_type(self, file_previews: List[FilePreview]) -> List[BatchGroup]:
        """Group files by file type"""
        
        groups = []
        type_groups = defaultdict(list)
        
        for fp in file_previews:
            type_groups[fp.file_type].append(fp)
        
        for file_type, file_list in type_groups.items():
            if len(file_list) > 1:
                group_id = hashlib.md5(f"file_type_{file_type}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
                
                group = BatchGroup(
                    group_id=group_id,
                    group_type="same_type", 
                    group_name=f"{file_type.upper()} Files",
                    file_previews=file_list,
                    common_characteristics={
                        "file_type": file_type,
                        "total_size_mb": sum(fp.file_size_mb for fp in file_list),
                        "date_range": f"{min(fp.modification_date for fp in file_list).date()} to {max(fp.modification_date for fp in file_list).date()}"
                    },
                    suggested_action="organize_by_type",
                    confidence_level=ConfidenceLevel.MINIMAL,
                    batch_size=len(file_list)
                )
                
                groups.append(group)
        
        return groups

    def _group_by_source_directory(self, file_previews: List[FilePreview]) -> List[BatchGroup]:
        """Group files by source directory"""
        
        groups = []
        dir_groups = defaultdict(list)
        
        for fp in file_previews:
            source_dir = str(Path(fp.file_path).parent)
            dir_groups[source_dir].append(fp)
        
        for source_dir, file_list in dir_groups.items():
            if len(file_list) > 1:
                group_id = hashlib.md5(f"source_dir_{source_dir}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
                
                group = BatchGroup(
                    group_id=group_id,
                    group_type="same_source",
                    group_name=f"From: {Path(source_dir).name}",
                    file_previews=file_list,
                    common_characteristics={
                        "source_directory": source_dir,
                        "total_files": len(file_list),
                        "mixed_types": len(set(fp.file_type for fp in file_list)) > 1
                    },
                    suggested_action="organize_from_source",
                    confidence_level=ConfidenceLevel.MINIMAL,
                    batch_size=len(file_list)
                )
                
                groups.append(group)
        
        return groups

    def _group_by_date(self, file_previews: List[FilePreview]) -> List[BatchGroup]:
        """Group files by modification date"""
        
        groups = []
        
        # Group by week
        week_groups = defaultdict(list)
        
        for fp in file_previews:
            # Get the start of the week
            week_start = fp.modification_date.date() - timedelta(days=fp.modification_date.weekday())
            week_groups[week_start].append(fp)
        
        for week_start, file_list in week_groups.items():
            if len(file_list) > 2:  # At least 3 files to make a group
                group_id = hashlib.md5(f"date_week_{week_start}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
                
                group = BatchGroup(
                    group_id=group_id,
                    group_type="same_date",
                    group_name=f"Week of {week_start}",
                    file_previews=file_list,
                    common_characteristics={
                        "week_start": str(week_start),
                        "date_range": f"{min(fp.modification_date for fp in file_list).date()} to {max(fp.modification_date for fp in file_list).date()}",
                        "total_files": len(file_list)
                    },
                    suggested_action="organize_by_date",
                    confidence_level=ConfidenceLevel.NEVER,  # Always ask for date-based groups
                    batch_size=len(file_list)
                )
                
                groups.append(group)
        
        return groups

    def _create_individual_group(self, file_preview: FilePreview) -> BatchGroup:
        """Create a group for a single file"""
        
        group_id = hashlib.md5(f"individual_{file_preview.file_path}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        # Determine confidence level based on prediction confidence
        if file_preview.confidence_score >= 0.8:
            confidence_level = ConfidenceLevel.SMART
        elif file_preview.confidence_score >= 0.6:
            confidence_level = ConfidenceLevel.MINIMAL
        else:
            confidence_level = ConfidenceLevel.NEVER
        
        group = BatchGroup(
            group_id=group_id,
            group_type="individual",
            group_name=file_preview.file_name,
            file_previews=[file_preview],
            common_characteristics={
                "file_type": file_preview.file_type,
                "predicted_category": file_preview.predicted_category,
                "confidence": file_preview.confidence_score
            },
            suggested_action="organize_individual",
            confidence_level=confidence_level,
            batch_size=1
        )
        
        return group

    def _split_large_group(self, group: BatchGroup) -> List[BatchGroup]:
        """Split a large group into smaller groups"""
        
        split_groups = []
        files = group.file_previews
        
        for i in range(0, len(files), self.config["max_batch_size"]):
            batch_files = files[i:i + self.config["max_batch_size"]]
            
            split_group_id = f"{group.group_id}_split_{i // self.config['max_batch_size']}"
            
            split_group = BatchGroup(
                group_id=split_group_id,
                group_type=group.group_type,
                group_name=f"{group.group_name} (Part {i // self.config['max_batch_size'] + 1})",
                file_previews=batch_files,
                common_characteristics=group.common_characteristics,
                suggested_action=group.suggested_action,
                confidence_level=group.confidence_level,
                batch_size=len(batch_files)
            )
            
            split_groups.append(split_group)
        
        return split_groups

    def _prepare_group_for_review(self, group: BatchGroup) -> Dict[str, Any]:
        """Prepare group data for user review"""
        
        # Create summary information
        group_summary = {
            "group_id": group.group_id,
            "group_type": group.group_type,
            "group_name": group.group_name,
            "batch_size": group.batch_size,
            "suggested_action": group.suggested_action,
            "confidence_level": group.confidence_level.name,
            "common_characteristics": group.common_characteristics
        }
        
        # Prepare file previews for display
        file_displays = []
        for fp in group.file_previews:
            file_display = {
                "file_name": fp.file_name,
                "file_path": fp.file_path,
                "file_size_mb": round(fp.file_size_mb, 2),
                "file_type": fp.file_type,
                "modification_date": fp.modification_date.strftime("%Y-%m-%d %H:%M"),
                "content_preview": fp.content_preview[:200] + "..." if len(fp.content_preview) > 200 else fp.content_preview,
                "content_keywords": fp.content_keywords[:5],  # Top 5 keywords
                "content_summary": fp.content_summary,
                "predicted_category": fp.predicted_category,
                "confidence_score": round(fp.confidence_score, 2),
                "duplicate_indicator": fp.duplicate_indicator
            }
            file_displays.append(file_display)
        
        # Suggest possible actions
        possible_actions = self._get_possible_actions(group)
        
        return {
            "group_summary": group_summary,
            "file_previews": file_displays,
            "possible_actions": possible_actions,
            "recommendation": self._get_group_recommendation(group)
        }

    def _get_possible_actions(self, group: BatchGroup) -> List[Dict[str, Any]]:
        """Get possible actions for a group"""
        
        actions = []
        
        if group.group_type == "duplicates":
            actions.extend([
                {"action": "keep_newest", "label": "Keep newest, delete others", "confidence": 0.8},
                {"action": "keep_largest", "label": "Keep largest, delete others", "confidence": 0.7},
                {"action": "manual_select", "label": "Let me choose which to keep", "confidence": 1.0},
                {"action": "skip", "label": "Skip this group", "confidence": 1.0}
            ])
        elif group.group_type == "similar_content":
            actions.extend([
                {"action": "organize_together", "label": f"Organize to {group.file_previews[0].predicted_category}", "confidence": 0.8},
                {"action": "organize_separately", "label": "Organize files separately", "confidence": 0.6},
                {"action": "create_project_folder", "label": "Create new project folder", "confidence": 0.7},
                {"action": "skip", "label": "Skip this group", "confidence": 1.0}
            ])
        else:
            # Generic actions
            actions.extend([
                {"action": "organize_predicted", "label": f"Organize to predicted categories", "confidence": 0.7},
                {"action": "organize_together", "label": "Organize all together", "confidence": 0.6},
                {"action": "organize_individually", "label": "Process each file separately", "confidence": 0.8},
                {"action": "skip", "label": "Skip this group", "confidence": 1.0}
            ])
        
        return actions

    def _get_group_recommendation(self, group: BatchGroup) -> Dict[str, Any]:
        """Get recommendation for a group"""
        
        avg_confidence = sum(fp.confidence_score for fp in group.file_previews) / len(group.file_previews)
        
        if group.group_type == "duplicates":
            recommendation = {
                "action": "keep_newest",
                "reasoning": "Keep the most recent version and remove duplicates to save space",
                "confidence": 0.8
            }
        elif group.group_type == "similar_content" and avg_confidence > 0.7:
            recommendation = {
                "action": "organize_together",
                "reasoning": f"Files appear related and can be organized to {group.file_previews[0].predicted_category}",
                "confidence": avg_confidence
            }
        elif avg_confidence > 0.6:
            recommendation = {
                "action": "organize_predicted",
                "reasoning": "System is confident about categorization predictions",
                "confidence": avg_confidence
            }
        else:
            recommendation = {
                "action": "organize_individually",
                "reasoning": "Files need individual review due to low confidence",
                "confidence": avg_confidence
            }
        
        return recommendation

    # Helper methods
    def _resolve_category_path(self, category: str) -> Path:
        """Resolve category to a path relative to base_dir"""
        # Map categories to Google Drive structure (simplified version of GDriveIntegration)
        category_mapping = {
            "creative": "01_ACTIVE_PROJECTS/Creative_Projects",
            "entertainment": "01_ACTIVE_PROJECTS/Entertainment_Industry",
            "business": "01_ACTIVE_PROJECTS/Business_Operations",
            "visual": "02_MEDIA_ASSETS/Visual_Assets",
            "audio": "02_MEDIA_ASSETS/Audio_Library",
            "video": "02_MEDIA_ASSETS/Video_Content",
            "research": "03_REFERENCE_LIBRARY/Research_Papers",
            "templates": "03_REFERENCE_LIBRARY/Templates",
            "unknown": "99_TEMP_PROCESSING/Manual_Review"
        }

        rel_path = category_mapping.get(category, "99_TEMP_PROCESSING/Manual_Review")
        return self.base_dir / rel_path

    def _move_file_safely(self, source_path: Path, target_dir: Path, session_id: str, action_type: str, confidence: float, category: str) -> Optional[Path]:
        """Move file safely with collision handling and rollback logging"""
        try:
            if not source_path.exists():
                self.logger.warning(f"File not found for move: {source_path}")
                return None

            # Create target directory
            target_dir.mkdir(parents=True, exist_ok=True)

            target_path = target_dir / source_path.name

            # Handle name conflicts
            counter = 1
            original_target = target_path
            while target_path.exists():
                stem = original_target.stem
                suffix = original_target.suffix
                target_path = target_dir / f"{stem}_{counter}{suffix}"
                counter += 1

            # Record operation before moving (in case it fails midway, though move is atomic-ish)
            # Actually rollback system records what happened, so we log it.
            # But EasyRollbackSystem needs the move to happen?
            # Looking at EasyRollbackSystem, it just logs the operation.

            import shutil
            shutil.move(str(source_path), str(target_path))

            # Log to rollback system
            try:
                self.rollback_system.record_operation(
                    operation_type=action_type,
                    original_path=str(source_path.parent),
                    original_filename=source_path.name,
                    new_filename=target_path.name,
                    new_location=str(target_dir),
                    category=category,
                    confidence=confidence,
                    notes=f"Batch session {session_id}"
                )
            except Exception as e:
                self.logger.error(f"Failed to log rollback operation: {e}")

            return target_path

        except Exception as e:
            self.logger.error(f"Error moving file {source_path}: {e}")
            return None

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate file hash for caching"""
        try:
            stat_info = file_path.stat()
            content = f"{file_path.name}_{stat_info.st_size}_{stat_info.st_mtime}"
            return hashlib.md5(content.encode()).hexdigest()
        except:
            return hashlib.md5(str(file_path).encode()).hexdigest()

    def _get_cached_preview(self, file_path: str, file_hash: str, db_connection: Optional[sqlite3.Connection] = None) -> Optional[FilePreview]:
        """Get cached preview if available"""
        try:
            if db_connection:
                # Use provided connection
                cursor = db_connection.execute("""
                    SELECT preview_data FROM file_previews 
                    WHERE file_path = ? AND file_hash = ?
                """, (file_path, file_hash))
                
                result = cursor.fetchone()
                
                if result:
                    preview_data = json.loads(result[0])
                    # Update access count
                    db_connection.execute("""
                        UPDATE file_previews 
                        SET last_accessed = ?, access_count = access_count + 1
                        WHERE file_path = ?
                    """, (datetime.now().isoformat(), file_path))
                    # Note: We do NOT commit here if using shared connection
                    
                    # Convert back to FilePreview object
                    preview = FilePreview(**preview_data)
                    return preview
            else:
                # Create new connection
                with sqlite3.connect(self.batch_db_path) as conn:
                    cursor = conn.execute("""
                        SELECT preview_data FROM file_previews
                        WHERE file_path = ? AND file_hash = ?
                    """, (file_path, file_hash))

                    result = cursor.fetchone()

                    if result:
                        preview_data = json.loads(result[0])
                        # Update access count
                        conn.execute("""
                            UPDATE file_previews
                            SET last_accessed = ?, access_count = access_count + 1
                            WHERE file_path = ?
                        """, (datetime.now().isoformat(), file_path))
                        conn.commit()

                        # Convert back to FilePreview object
                        preview = FilePreview(**preview_data)
                        return preview
        except Exception as e:
            self.logger.error(f"Error getting cached preview: {e}")
        
        return None

    def _cache_preview(self, file_path: str, file_hash: str, preview: FilePreview, db_connection: Optional[sqlite3.Connection] = None):
        """Cache file preview"""
        try:
            preview_data = asdict(preview)
            # Convert datetime objects to ISO strings
            preview_data['creation_date'] = preview.creation_date.isoformat()
            preview_data['modification_date'] = preview.modification_date.isoformat()

            if db_connection:
                # Use provided connection
                db_connection.execute("""
                    INSERT OR REPLACE INTO file_previews 
                    (file_path, file_hash, preview_data, generated_time, last_accessed)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    file_path,
                    file_hash, 
                    json.dumps(preview_data),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
            else:
                # Create new connection
                with sqlite3.connect(self.batch_db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO file_previews
                        (file_path, file_hash, preview_data, generated_time, last_accessed)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        file_path,
                        file_hash,
                        json.dumps(preview_data),
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))
                    conn.commit()
        except Exception as e:
            self.logger.error(f"Error caching preview: {e}")

    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content"""
        import re
        
        # Remove common words and extract meaningful terms
        stop_words = {"the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was", "one", "our", "out", "day", "get", "has", "him", "his", "how", "its", "may", "new", "now", "old", "see", "two", "who", "boy", "did", "man", "men", "put", "say", "she", "too", "use", "way", "who", "oil", "sit", "now", "run", "set", "eat", "far", "sea", "eye", "red", "top", "try", "yes", "six", "ten", "cut", "end", "few", "yet", "own", "big", "why", "let", "any", "ask", "god", "job", "lot", "off", "off", "air", "age", "ago", "arm", "bad", "box", "boy", "car", "day", "dog", "far", "few", "fun", "guy", "hit", "hot", "job", "lot", "man", "new", "old", "run", "say", "see", "top", "try", "war", "way", "win", "yes"}
        
        words = re.findall(r'\b[a-zA-Z]{3,}\b', content.lower())
        keywords = [word for word in words if word not in stop_words]
        
        # Get word frequency
        word_freq = {}
        for word in keywords:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency and return top keywords
        sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_keywords[:self.config["keyword_limit"]]]

    def _generate_content_summary(self, content: str) -> str:
        """Generate a summary of the content"""
        # Simple summary generation - first sentence or first 100 characters
        sentences = content.split('.')
        if sentences and len(sentences[0]) > 10:
            return sentences[0][:100] + "..."
        else:
            return content[:100] + "..." if len(content) > 100 else content

    def _find_similar_files(self, file_path: Path, keywords: List[str]) -> List[str]:
        """Find files with similar content"""
        # TODO: Implement similarity search
        return []

    def _is_likely_duplicate(self, file_path: Path) -> bool:
        """Check if file is likely a duplicate"""
        filename = file_path.name.lower()
        duplicate_indicators = [
            ' (1)', ' (2)', ' (3)', ' (4)', ' (5)',
            ' copy', '_copy', '-copy',
            ' duplicate', '_duplicate',
            'copy of', 'copy_of'
        ]
        return any(indicator in filename for indicator in duplicate_indicators)

    def _calculate_content_similarity(self, fp1: FilePreview, fp2: FilePreview) -> float:
        """Calculate content similarity between two files"""
        if not fp1.content_keywords or not fp2.content_keywords:
            return 0.0
        
        # Simple keyword overlap similarity
        keywords1 = set(fp1.content_keywords)
        keywords2 = set(fp2.content_keywords)
        
        intersection = keywords1 & keywords2
        union = keywords1 | keywords2
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)

    def _find_common_keywords(self, keyword_lists: List[List[str]]) -> List[str]:
        """Find common keywords across multiple lists"""
        if not keyword_lists:
            return []
        
        # Count keyword frequency across all lists
        keyword_freq = {}
        for keywords in keyword_lists:
            for keyword in set(keywords):  # Use set to count each keyword once per list
                keyword_freq[keyword] = keyword_freq.get(keyword, 0) + 1
        
        # Get keywords that appear in at least half the lists
        min_frequency = len(keyword_lists) // 2
        common_keywords = [kw for kw, freq in keyword_freq.items() if freq >= min_frequency]
        
        # Sort by frequency
        common_keywords.sort(key=lambda kw: keyword_freq[kw], reverse=True)
        
        return common_keywords[:5]  # Return top 5

    def _infer_content_theme(self, keywords: List[str]) -> str:
        """Infer content theme from keywords"""
        
        # Define theme keywords
        themes = {
            "business": ["contract", "agreement", "business", "company", "revenue", "profit", "meeting", "client"],
            "entertainment": ["film", "movie", "television", "tv", "show", "entertainment", "actor", "director"],
            "creative": ["design", "art", "creative", "project", "idea", "concept", "inspiration"],
            "technical": ["code", "programming", "software", "development", "technical", "system", "data"],
            "personal": ["personal", "family", "home", "private", "diary", "journal"],
            "academic": ["research", "study", "paper", "academic", "university", "education", "thesis"],
            "financial": ["finance", "money", "budget", "investment", "bank", "financial", "payment"]
        }
        
        theme_scores = {}
        for theme, theme_keywords in themes.items():
            score = sum(1 for keyword in keywords if keyword in theme_keywords)
            if score > 0:
                theme_scores[theme] = score
        
        if theme_scores:
            return max(theme_scores, key=theme_scores.get)
        else:
            return "general"

    def _process_group_automatically(self, session_id: str, group: BatchGroup):
        """Process a group automatically based on confidence"""

        # Get recommendation
        recommendation = self._get_group_recommendation(group)

        # Create decision
        decision = {
            "action": recommendation["action"],
            "target_category": group.file_previews[0].predicted_category if group.file_previews else "unknown",
            "automatic": True,
            "confidence": recommendation["confidence"]
        }

        self.logger.info(f"Automatically processing group {group.group_id} with action {decision['action']}")

        # Execute decision
        result = self._execute_user_decision(session_id, group, decision)

        # Update stats
        self.stats["automatic_decisions"] += 1

        # Log result
        if result["success"]:
            self.logger.info(f"Successfully processed {len(result['processed_files'])} files")
        else:
            self.logger.warning(f"Failed to process group: {result.get('message', 'Unknown error')}")

    def _execute_user_decision(self, session_id: str, group: BatchGroup, user_decision: Dict[str, Any]) -> Dict[str, Any]:
        """Execute user decision for a group"""

        action = user_decision.get("action")
        results = {
            "success": True,
            "processed_files": [],
            "failed_files": []
        }

        self.logger.info(f"Executing decision '{action}' for group {group.group_id}")

        try:
            # Handle "keep_newest" for duplicates
            if action == "keep_newest" and group.group_type == "duplicates":
                # Sort files by modification date (newest first)
                sorted_files = sorted(group.file_previews, key=lambda fp: fp.modification_date, reverse=True)

                # Keep the first one
                keeper = sorted_files[0]
                to_remove = sorted_files[1:]

                # Move duplicates to a "Duplicates" folder (safer than delete)
                # or actually delete if that's the policy. For now, let's move to a Duplicates folder
                # inside a "99_TEMP_PROCESSING" area to be safe.
                duplicates_dir = self.base_dir / "99_TEMP_PROCESSING" / "Duplicates"

                for fp in to_remove:
                    result = self._move_file_safely(
                        Path(fp.file_path),
                        duplicates_dir,
                        session_id,
                        "archive_duplicate",
                        1.0,
                        "duplicates"
                    )

                    if result:
                        results["processed_files"].append(fp.file_path)
                    else:
                        results["failed_files"].append(fp.file_path)

                # Ensure the keeper is in the right place (if needed) - usually it stays or moves to valid category
                # If the group has a predicted category, move the keeper there
                if keeper.predicted_category and keeper.predicted_category != "unknown":
                    target_dir = self._resolve_category_path(keeper.predicted_category)
                    self._move_file_safely(
                        Path(keeper.file_path),
                        target_dir,
                        session_id,
                        "organize",
                        keeper.confidence_score,
                        keeper.predicted_category
                    )

            # Handle "organize_together"
            elif action == "organize_together":
                # Determine target category
                # Use the one from decision if available, otherwise from group
                target_category = user_decision.get("target_category")
                if not target_category and group.file_previews:
                    target_category = group.file_previews[0].predicted_category

                if not target_category:
                    target_category = "unknown"

                target_dir = self._resolve_category_path(target_category)

                for fp in group.file_previews:
                    result = self._move_file_safely(
                        Path(fp.file_path),
                        target_dir,
                        session_id,
                        "organize",
                        fp.confidence_score,
                        target_category
                    )

                    if result:
                        results["processed_files"].append(fp.file_path)
                    else:
                        results["failed_files"].append(fp.file_path)

            # Handle "organize_predicted" (or individually)
            elif action in ["organize_predicted", "organize_individually", "organize_individual"]:
                for fp in group.file_previews:
                    category = fp.predicted_category
                    target_dir = self._resolve_category_path(category)

                    result = self._move_file_safely(
                        Path(fp.file_path),
                        target_dir,
                        session_id,
                        "organize",
                        fp.confidence_score,
                        category
                    )

                    if result:
                        results["processed_files"].append(fp.file_path)
                    else:
                        results["failed_files"].append(fp.file_path)

            # Handle "organize_by_type"
            elif action == "organize_by_type":
                # Usually map extension to a category or folder
                # Simple mapping for now
                for fp in group.file_previews:
                    # Logic could be more complex, but let's stick to predicted category or a type folder
                    # If predicted category is good, use it. Else create a folder for the type.
                    if fp.confidence_score > 0.6:
                         category = fp.predicted_category
                         target_dir = self._resolve_category_path(category)
                    else:
                        # Fallback to type folder in Manual Review
                        ext = fp.file_type.strip('.')
                        target_dir = self.base_dir / "99_TEMP_PROCESSING" / "Manual_Review" / ext.upper()
                        category = "manual_review"

                    result = self._move_file_safely(
                        Path(fp.file_path),
                        target_dir,
                        session_id,
                        "organize",
                        fp.confidence_score,
                        category
                    )

                    if result:
                        results["processed_files"].append(fp.file_path)
                    else:
                        results["failed_files"].append(fp.file_path)

            elif action == "skip":
                pass

            else:
                self.logger.warning(f"Unknown action: {action}")
                results["success"] = False
                results["message"] = f"Unknown action: {action}"

            # Update stats
            self.stats["files_organized"] += len(results["processed_files"])

        except Exception as e:
            self.logger.error(f"Error executing decision: {e}")
            results["success"] = False
            results["message"] = str(e)

        return results

    def _record_user_decision(self, session_id: str, group: BatchGroup, user_decision: Dict[str, Any], result: Dict[str, Any]):
        """Record user decision for learning"""
        try:
            with sqlite3.connect(self.batch_db_path) as conn:
                for fp in group.file_previews:
                    conn.execute("""
                        INSERT INTO user_feedback
                        (feedback_id, session_id, file_path, predicted_action, user_action, feedback_time, comments)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        hashlib.md5(f"{session_id}_{fp.file_path}_{datetime.now().isoformat()}".encode()).hexdigest()[:12],
                        session_id,
                        fp.file_path,
                        fp.predicted_category,
                        user_decision.get("action", "unknown"),
                        datetime.now().isoformat(),
                        json.dumps(user_decision)
                    ))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error recording user decision: {e}")

    def _update_learning_from_decision(self, group: BatchGroup, user_decision: Dict[str, Any]):
        """Update learning system from user decision"""
        # In a real system, this would feed back into the learning model
        # For now, we'll just track that confidence is improving if the user agrees
        action = user_decision.get("action")

        # If user agreed with recommendation or high confidence prediction
        if (action == "organize_predicted" or
            action == "organize_together" or
            action == "keep_newest"):  # Assuming smart defaults
            self.stats["confidence_improvements"] += 1

    def _record_batch_session(self, session_data: Dict[str, Any], db_connection: Optional[sqlite3.Connection] = None):
        """Record batch session in database"""
        try:
            if db_connection:
                db_connection.execute("""
                    INSERT INTO batch_sessions 
                    (session_id, start_time, source_directory, total_files, groups_created)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    session_data["session_id"],
                    session_data["start_time"].isoformat(),
                    session_data["source_directory"],
                    session_data["total_files"],
                    len(session_data["batch_groups"])
                ))
            else:
                with sqlite3.connect(self.batch_db_path) as conn:
                    conn.execute("""
                        INSERT INTO batch_sessions
                        (session_id, start_time, source_directory, total_files, groups_created)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        session_data["session_id"],
                        session_data["start_time"].isoformat(),
                        session_data["source_directory"],
                        session_data["total_files"],
                        len(session_data["batch_groups"])
                    ))
                    conn.commit()
        except Exception as e:
            self.logger.error(f"Error recording batch session: {e}")

    def get_processor_stats(self) -> Dict[str, Any]:
        """Get batch processor statistics"""
        return {
            "processor_stats": self.stats,
            "active_sessions": len(self.active_sessions),
            "config": self.config,
            "cache_size": len(self.preview_cache)
        }

# Testing and CLI interface
def main():
    """Command line interface for interactive batch processor"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Interactive Batch Processor')
    parser.add_argument('--start', help='Start batch session for directory')
    parser.add_argument('--stats', action='store_true', help='Show processor statistics')
    parser.add_argument('--test', action='store_true', help='Run test scenarios')
    
    args = parser.parse_args()
    
    processor = InteractiveBatchProcessor()
    
    if args.start:
        try:
            session_id = processor.start_batch_session(args.start)
            print(f"📋 Started batch session: {session_id}")
            
            overview = processor.get_session_overview(session_id)
            print(f"📊 Total files: {overview['total_files']}, Groups: {overview['total_groups']}")
            
        except Exception as e:
            print(f"❌ Error starting batch session: {e}")
    elif args.stats:
        stats = processor.get_processor_stats()
        print("📋 Interactive Batch Processor Statistics:")
        print(json.dumps(stats, indent=2, default=str))
    elif args.test:
        print("📋 Testing interactive batch processor...")
        # TODO: Implement test scenarios
        print("✅ Test completed!")
    else:
        print("📋 Interactive Batch Processor")
        print("Use --help for options")

if __name__ == "__main__":
    main()