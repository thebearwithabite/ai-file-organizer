"""
MetadataService - The Unified Metadata Engine
Part of AI File Organizer v3.5 - Phase 4 Implementation

This service serves as the central source of truth for all file metadata, 
consolidating fragmented SQLite databases and providing a bridge to 
cloud synchronization (Supabase).

Rules:
1. Databases must remain in ~/Documents/AI_METADATA_SYSTEM/databases
2. Fail-fast on unsafe paths.
3. Every major metadata change triggers a JSON sidecar export for backup.
"""

import os
import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from gdrive_integration import get_metadata_root, ensure_safe_local_path

class MetadataService:
    def __init__(self, db_name: str = "unified_metadata.db"):
        self.logger = logging.getLogger(__name__)
        
        # Enforce Rule #5 - Strict local storage
        metadata_root = get_metadata_root()
        db_dir = metadata_root / "databases"
        db_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = ensure_safe_local_path(db_dir / db_name)
        
        # Initialize tables
        self._init_db()
        
    def _init_db(self):
        """Initialize the unified database schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 1. Main File Metadata Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS file_metadata (
                        file_id TEXT PRIMARY KEY,
                        file_path TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        category TEXT,
                        mood TEXT,
                        confidence REAL,
                        tags TEXT, -- JSON string
                        transcript TEXT,
                        metadata_json TEXT, -- All extended attributes
                        last_analyzed TIMESTAMP,
                        sync_status TEXT DEFAULT 'pending'
                    )
                """)
                
                # 2. User Interaction Queue
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS interaction_queue (
                        interaction_id TEXT PRIMARY KEY,
                        file_path TEXT NOT NULL,
                        question TEXT NOT NULL,
                        options TEXT, -- JSON string of suggested actions
                        context TEXT, -- Why was this queued?
                        status TEXT DEFAULT 'pending', -- pending, resolved, dismissed
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        resolved_at TIMESTAMP
                    )
                """)
                
                # 3. Global Patterns (Consolidated from Adaptive Learning)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS learned_patterns (
                        pattern_key TEXT PRIMARY KEY,
                        pattern_type TEXT, -- 'extension', 'keyword', 'path'
                        target_category TEXT,
                        weight REAL,
                        hit_count INTEGER DEFAULT 0,
                        last_hit TIMESTAMP
                    )
                """)
                
                # 4. VEO Sessions (Scripts, Shot Lists, Generated Keyframes)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS veo_sessions (
                        session_id TEXT PRIMARY KEY,
                        session_name TEXT NOT NULL,
                        script_path TEXT,
                        shot_list_json TEXT, -- JSON string of shots
                        assets_json TEXT, -- JSON string of detected assets
                        status TEXT DEFAULT 'active', -- active, archived, completed
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.commit()
                self.logger.info(f"✅ Unified Metadata Engine initialized at {self.db_path}")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize MetadataService: {e}")
            raise

    def upsert_file_metadata(self, file_path: Union[str, Path], metadata: Dict[str, Any]):
        """Save or update metadata for a file and trigger JSON backup"""
        path_obj = Path(file_path)
        file_id = self._generate_file_id(path_obj)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO file_metadata (
                        file_id, file_path, filename, category, mood, 
                        confidence, tags, transcript, metadata_json, last_analyzed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(file_id) DO UPDATE SET
                        category=excluded.category,
                        mood=excluded.mood,
                        confidence=excluded.confidence,
                        tags=excluded.tags,
                        transcript=excluded.transcript,
                        metadata_json=excluded.metadata_json,
                        last_analyzed=excluded.last_analyzed,
                        sync_status='pending'
                """, (
                    file_id,
                    str(path_obj),
                    path_obj.name,
                    metadata.get('category'),
                    metadata.get('mood'),
                    metadata.get('confidence', 0.0),
                    json.dumps(metadata.get('tags', [])),
                    metadata.get('transcript'),
                    json.dumps(metadata),
                    datetime.now().isoformat()
                ))
                conn.commit()
            
            # Export JSON sidecar as backup (Truth in DB, Backup on Disk)
            self._export_json_sidecar(path_obj, metadata)
            
        except Exception as e:
            self.logger.error(f"Failed to upsert metadata for {path_obj.name}: {e}")

    def queue_interaction(self, file_path: Path, question: str, options: List[str], context: str = ""):
        """Add a manual review task to the queue"""
        interaction_id = f"int_{int(datetime.now().timestamp())}_{file_path.stem[:10]}"
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO interaction_queue (
                        interaction_id, file_path, question, options, context
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    interaction_id,
                    str(file_path),
                    question,
                    json.dumps(options),
                    context
                ))
                conn.commit()
                self.logger.info(f"📋 Queued interaction: {interaction_id} for {file_path.name}")
        except Exception as e:
            self.logger.error(f"Failed to queue interaction: {e}")

    def _generate_file_id(self, file_path: Path) -> str:
        """Generate a consistent ID based on path or inode"""
        # Simple path-based ID for now. Later we can use hashes for deduplication.
        import hashlib
        return hashlib.md5(str(file_path.resolve()).encode()).hexdigest()

    def _export_json_sidecar(self, file_path: Path, metadata: Dict[str, Any]):
        """Write a .meta.json sidecar to the same directory for external portability"""
        try:
            sidecar_path = file_path.with_suffix(file_path.suffix + ".meta.json")
            # Don't overwrite if it's already there and perfectly identical? 
            # (Simplistic overwrite for now for consistency)
            with open(sidecar_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
             self.logger.warning(f"Could not export JSON sidecar for {file_path.name}: {e}")

    def get_pending_interactions(self) -> List[Dict[str, Any]]:
        """Get all pending user review tasks"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM interaction_queue WHERE status = 'pending' ORDER BY created_at DESC")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Error fetching interactions: {e}")
            return []

    def upsert_veo_session(self, session_id: str, session_data: Dict[str, Any]):
        """Create or update a VEO creative session"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO veo_sessions (
                        session_id, session_name, script_path, shot_list_json, assets_json, status, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        session_name=excluded.session_name,
                        script_path=excluded.script_path,
                        shot_list_json=excluded.shot_list_json,
                        assets_json=excluded.assets_json,
                        status=excluded.status,
                        last_updated=excluded.last_updated
                """, (
                    session_id,
                    session_data.get('session_name', 'Untitled Session'),
                    session_data.get('script_path'),
                    json.dumps(session_data.get('shot_list', [])),
                    json.dumps(session_data.get('assets', [])),
                    session_data.get('status', 'active'),
                    datetime.now().isoformat()
                ))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to upsert VEO session {session_id}: {e}")

    def get_veo_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a VEO session by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM veo_sessions WHERE session_id = ?", (session_id,))
                row = cursor.fetchone()
                if row:
                    session = dict(row)
                    session['shot_list'] = json.loads(session.pop('shot_list_json', '[]'))
                    session['assets'] = json.loads(session.pop('assets_json', '[]'))
                    return session
                return None
        except Exception as e:
            self.logger.error(f"Error fetching VEO session {session_id}: {e}")
            return None
