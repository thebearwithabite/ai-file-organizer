"""
MetadataGenerator - Compatibility Shim for AI File Organizer v3.5
Routes legacy MetadataGenerator calls to the modern MetadataService and UnifiedClassificationService.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import pandas as pd
from datetime import datetime

from metadata_service import MetadataService
from unified_classifier import UnifiedClassificationService

class MetadataGenerator:
    """Legacy compatibility shim for MetadataGenerator"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        # If a path is provided, we use it for the underlying service if possible,
        # otherwise we use the standard location.
        db_name = Path(db_path).name if db_path else "unified_metadata.db"
        self.service = MetadataService(db_name=db_name)
        self.classifier = UnifiedClassificationService()
        self.db_path = self.service.db_path
        
    def analyze_file_comprehensive(self, file_path: str) -> Dict[str, Any]:
        """Legacy method to analyze a file using the modern classifier"""
        path = Path(file_path)
        if not path.exists():
            return {"error": "File not found"}
            
        # Route to modern classification logic
        result = self.classifier.classify_file(path)
        
        # Format result to match legacy expectations (both old and very old keys)
        legacy_result = {
            "file_path": str(path),
            "file_name": path.name,
            "category": result.get("category", "unknown"),
            "ai_category": result.get("category", "unknown"), # legacy key
            "confidence": result.get("confidence", 0.0),
            "confidence_score": result.get("confidence", 0.0), # legacy key
            "confidence_percentage": f"{result.get('confidence', 0.0)*100:.1f}%",
            "mood": result.get("mood", "neutral"),
            "tags": result.get("tags", []),
            "auto_tags": str(result.get("tags", [])), # legacy key
            "transcript": result.get("transcript", ""),
            "word_count": len(result.get("transcript", "").split()) if result.get("transcript") else 0,
            "file_size": path.stat().st_size if path.exists() else 0,
            "file_type": path.suffix.lower().replace('.', '') if path.suffix else "unknown",
            "metadata": result.get("metadata", {})
        }
        
        # Auto-save to the new service
        self.service.upsert_file_metadata(path, result)
        
        return legacy_result

    def save_file_metadata(self, file_path: Any, metadata: Optional[Dict[str, Any]] = None):
        """Legacy method to save metadata. Supports (file_path, metadata) or just (metadata_dict)."""
        if metadata is None and isinstance(file_path, dict):
            metadata = file_path
            path_str = metadata.get('file_path')
            if not path_str:
                self.logger.error("Legacy save_file_metadata called with dict missing 'file_path'")
                return False
            path = Path(path_str)
        else:
            path = Path(file_path)
            
        self.service.upsert_file_metadata(path, metadata or {})
        return True

    def generate_comprehensive_spreadsheet(self, output_path: Optional[str] = None):
        """Legacy method to export all metadata to a spreadsheet"""
        if not output_path:
            output_path = str(Path.home() / "Documents" / f"metadata_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
            
        try:
            import sqlite3
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query("SELECT * FROM file_metadata", conn)
                
                # Add legacy column shims to the dataframe
                if 'category' in df.columns:
                    df['ai_category'] = df['category']
                if 'confidence' in df.columns:
                    df['confidence_score'] = df['confidence']
                    df['confidence_percentage'] = df['confidence'].apply(lambda x: f"{x*100:.1f}%")
                if 'file_path' in df.columns:
                    df['file_name'] = df['file_path'].apply(lambda x: Path(x).name)
                    df['file_type'] = df['file_path'].apply(lambda x: Path(x).suffix.lower().replace('.', '') or 'unknown')
                if 'transcript' in df.columns:
                    df['word_count'] = df['transcript'].apply(lambda x: len(x.split()) if x else 0)
                
                # Ensure parent directory exists
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                
                df.to_excel(output_path, index=False)
                self.logger.info(f"✅ Exported comprehensive spreadsheet to {output_path}")
                return output_path, df
        except Exception as e:
            self.logger.error(f"Failed to generate spreadsheet: {e}")
            return None, None

    def _migrate_database_schema(self, conn=None):
        """Legacy migration hook - forwarded to MetadataService initialization logic if needed"""
        # MetadataService already ensures table existence. 
        # This is a no-op shim for test compatibility.
        self.logger.info("Shim: _migrate_database_schema called (handled by MetadataService)")
        pass

    def get_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Legacy method to retrieve metadata"""
        import sqlite3
        import json
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM file_metadata WHERE file_path = ?", (file_path,))
                row = cursor.fetchone()
                if row:
                    data = dict(row)
                    if data.get('metadata_json'):
                        return json.loads(data['metadata_json'])
                    return data
                return None
        except Exception as e:
            self.logger.error(f"Error retrieving metadata: {e}")
            return None
