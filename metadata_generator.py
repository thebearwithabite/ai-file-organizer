#!/usr/bin/env python3
"""
Comprehensive Metadata Spreadsheet Generator for AI File Organizer
Creates detailed Excel/CSV reports of file organization and analysis results
Based on AudioAI organizer metadata patterns
"""

import sys
import os
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json
from path_config import paths
import hashlib

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from content_extractor import ContentExtractor
from classification_engine import FileClassificationEngine
from interaction_modes import InteractionModeManager

class MetadataGenerator:
    """
    Generates comprehensive metadata spreadsheets for file organization
    Like AudioAI but for documents, emails, and multimedia files
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "Documents" / "AI_ORGANIZER_BASE"
        self.metadata_dir = self.base_dir / "04_METADATA_SYSTEM"
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.content_extractor = ContentExtractor(str(self.base_dir))
        self.classifier = FileClassificationEngine(str(self.base_dir))
        self.interaction_manager = InteractionModeManager(str(self.base_dir))
        
        # Database for tracking processed files
        self.db_path = paths.get_path('metadata_db')
        self._init_tracking_db()
        
        # File type classifications
        self.file_type_mappings = {
            # Documents
            '.pdf': 'Document',
            '.docx': 'Document', 
            '.doc': 'Document',
            '.pages': 'Document',
            '.txt': 'Text',
            '.md': 'Markdown',
            '.rtf': 'Rich Text',
            
            # Spreadsheets
            '.xlsx': 'Spreadsheet',
            '.xls': 'Spreadsheet', 
            '.csv': 'Data',
            '.numbers': 'Spreadsheet',
            
            # Presentations
            '.pptx': 'Presentation',
            '.ppt': 'Presentation',
            '.keynote': 'Presentation',
            
            # Images
            '.jpg': 'Image',
            '.jpeg': 'Image',
            '.png': 'Image',
            '.gif': 'Animation',
            '.svg': 'Vector Image',
            '.tiff': 'Image',
            '.bmp': 'Image',
            
            # Audio
            '.mp3': 'Audio',
            '.wav': 'Audio',
            '.aiff': 'Audio',
            '.m4a': 'Audio',
            '.flac': 'Audio',
            '.ogg': 'Audio',
            '.aup3': 'Audio Project',
            
            # Video  
            '.mp4': 'Video',
            '.mov': 'Video',
            '.avi': 'Video',
            '.mkv': 'Video',
            '.wmv': 'Video',
            '.webm': 'Video',
            
            # Code
            '.py': 'Code',
            '.js': 'Code',
            '.html': 'Web',
            '.css': 'Web',
            '.swift': 'Code',
            '.cpp': 'Code',
            
            # Email
            '.emlx': 'Email',
            '.eml': 'Email',
            
            # Archives
            '.zip': 'Archive',
            '.tar': 'Archive',
            '.gz': 'Archive',
            '.dmg': 'Disk Image'
        }
    
    def _init_tracking_db(self):
        """Initialize SQLite database for tracking file metadata"""
        with sqlite3.connect(self.db_path) as conn:
            # First, create the table with the current schema
            self._create_tables(conn)
            
            # Then, migrate any missing columns
            self._migrate_database_schema(conn)
    
    def _create_tables(self, conn):
        """Create database tables with full schema"""
        conn.execute("""
                CREATE TABLE IF NOT EXISTS file_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE,
                    file_name TEXT,
                    file_extension TEXT,
                    file_size INTEGER,
                    file_type TEXT,
                    created_date TEXT,
                    modified_date TEXT,
                    indexed_date TEXT,
                    
                    -- Classification results
                    ai_category TEXT,
                    ai_subcategory TEXT,
                    confidence_score REAL,
                    classification_method TEXT,
                    
                    -- Content analysis
                    content_preview TEXT,
                    content_length INTEGER,
                    word_count INTEGER,
                    page_count INTEGER,
                    
                    -- People and entities
                    people_mentioned TEXT,  -- JSON array
                    organizations TEXT,     -- JSON array
                    dates_mentioned TEXT,   -- JSON array
                    
                    -- Project and tagging
                    project_codes TEXT,     -- JSON array
                    auto_tags TEXT,         -- JSON array
                    user_tags TEXT,         -- JSON array
                    
                    -- File organization
                    original_location TEXT,
                    organized_location TEXT,
                    enhanced_filename TEXT,
                    organization_status TEXT,
                    
                    -- Google Drive integration
                    gdrive_upload BOOLEAN DEFAULT 0,
                    gdrive_folder TEXT,
                    gdrive_file_id TEXT,
                    gdrive_category TEXT,
                    gdrive_confidence REAL,
                    upload_timestamp TEXT,
                    space_freed_mb REAL,
                    
                    -- Audio/Video specific (when applicable)
                    duration_seconds REAL,
                    audio_bitrate INTEGER,
                    video_resolution TEXT,
                    
                    -- Processing info
                    processing_mode TEXT,
                    questions_asked INTEGER,
                    user_corrections INTEGER,
                    last_updated TEXT
                )
            """)
            
        conn.execute("""
                CREATE TABLE IF NOT EXISTS processing_sessions (
                    session_id TEXT PRIMARY KEY,
                    start_time TEXT,
                    end_time TEXT,
                    files_processed INTEGER,
                    files_organized INTEGER,
                    questions_asked INTEGER,
                    interaction_mode TEXT,
                    session_type TEXT,
                    notes TEXT
                )
            """)
            
        conn.commit()
    
    def _migrate_database_schema(self, conn):
        """Atomic database migration with backup/rollback capability"""
        import shutil
        from datetime import datetime
        
        # Step 1: Create backup before any changes
        backup_path = self._create_database_backup()
        
        try:
            # Step 2: Begin exclusive transaction for atomic operations
            conn.execute("BEGIN EXCLUSIVE TRANSACTION")
            
            # Step 3: Check existing columns
            cursor = conn.execute("PRAGMA table_info(file_metadata)")
            existing_columns = [row[1] for row in cursor.fetchall()]
            
            # Step 4: Define Google Drive columns to add
            gdrive_columns = {
                'gdrive_upload': 'BOOLEAN DEFAULT 0',
                'gdrive_folder': 'TEXT',
                'gdrive_file_id': 'TEXT', 
                'gdrive_category': 'TEXT',
                'gdrive_confidence': 'REAL',
                'upload_timestamp': 'TEXT',
                'space_freed_mb': 'REAL'
            }
            
            # Step 5: Add missing columns atomically
            migration_count = 0
            for col_name, col_type in gdrive_columns.items():
                if col_name not in existing_columns:
                    conn.execute(f"ALTER TABLE file_metadata ADD COLUMN {col_name} {col_type}")
                    migration_count += 1
                    print(f"   ✅ Added column: {col_name}")
            
            # Step 6: Commit all changes atomically
            conn.commit()
            print(f"✅ Database migration successful: {migration_count} columns added")
            
            # Step 7: Cleanup backup if successful
            if backup_path and backup_path.exists():
                backup_path.unlink()
                print(f"🗑️  Cleanup: Removed backup {backup_path.name}")
            
        except sqlite3.Error as e:
            # Step 8: Rollback transaction and restore from backup
            print(f"❌ Database migration failed: {e}")
            conn.rollback()
            
            if backup_path and backup_path.exists():
                print("🔄 Restoring database from backup...")
                try:
                    shutil.copy2(backup_path, self.db_path)
                    print("✅ Database restored from backup")
                except Exception as restore_error:
                    print(f"❌ CRITICAL: Backup restoration failed: {restore_error}")
                    print(f"📁 Manual restore required from: {backup_path}")
            
            raise e
        
        except Exception as e:
            # Handle non-SQLite errors
            print(f"❌ Unexpected migration error: {e}")
            conn.rollback()
            raise e

    def _create_database_backup(self):
        """Create timestamped backup of database before migration"""
        import shutil
        from datetime import datetime
        
        if not self.db_path.exists():
            print("📄 No existing database to backup")
            return None
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.db_path.with_name(f"{self.db_path.stem}_backup_{timestamp}.db")
            
            shutil.copy2(self.db_path, backup_path)
            print(f"📁 Database backup created: {backup_path.name}")
            return backup_path
            
        except Exception as e:
            print(f"⚠️  Could not create database backup: {e}")
            print("🚨 Proceeding without backup - increased risk!")
            return None
    
    def analyze_file_comprehensive(self, file_path: Path) -> Dict[str, Any]:
        """Perform comprehensive analysis of a single file"""
        
        try:
            stat = file_path.stat()
            
            # Basic file info
            metadata = {
                'file_path': str(file_path),
                'file_name': file_path.name,
                'file_extension': file_path.suffix.lower(),
                'file_size': stat.st_size,
                'file_type': self.file_type_mappings.get(file_path.suffix.lower(), 'Unknown'),
                'created_date': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified_date': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'indexed_date': datetime.now().isoformat()
            }
            
            # Content extraction and analysis
            content_result = self.content_extractor.extract_content(file_path)
            
            if content_result['success']:
                content = content_result['text']
                metadata.update({
                    'content_preview': content[:500] if content else '',
                    'content_length': len(content) if content else 0,
                    'word_count': len(content.split()) if content else 0,
                    'page_count': content_result.get('page_count', 0)
                })
                
                # Extract entities from content
                entities = self._extract_entities(content)
                metadata.update(entities)
                
            else:
                metadata.update({
                    'content_preview': f"Extraction failed: {content_result.get('error', 'Unknown error')}",
                    'content_length': 0,
                    'word_count': 0,
                    'page_count': 0,
                    'people_mentioned': '[]',
                    'organizations': '[]',
                    'dates_mentioned': '[]'
                })
            
            # AI Classification
            try:
                classification = self.classifier.classify_file(file_path)
                metadata.update({
                    'ai_category': classification.category,
                    'ai_subcategory': classification.subcategory,
                    'confidence_score': classification.confidence / 100,  # Convert to 0-1 scale
                    'classification_method': 'AI_Classification',
                    'auto_tags': json.dumps(classification.tags[:10]),  # Top 10 tags
                    'people_mentioned': json.dumps(classification.people)
                })
            except Exception as e:
                metadata.update({
                    'ai_category': 'Classification_Failed',
                    'ai_subcategory': '',
                    'confidence_score': 0.0,
                    'classification_method': f'Error: {str(e)}',
                    'auto_tags': '[]'
                })
            
            # Multimedia-specific analysis
            if metadata['file_type'] in ['Audio', 'Video', 'Audio Project']:
                multimedia_data = self._analyze_multimedia(file_path)
                metadata.update(multimedia_data)
            
            # Processing info
            metadata.update({
                'processing_mode': self.interaction_manager.get_interaction_mode().value,
                'questions_asked': 0,  # Will be updated if questions are asked
                'user_corrections': 0,  # Will be updated if user makes corrections
                'organization_status': 'Analyzed',
                'last_updated': datetime.now().isoformat()
            })
            
            return metadata
            
        except Exception as e:
            return {
                'file_path': str(file_path),
                'file_name': file_path.name,
                'error': f"Analysis failed: {str(e)}",
                'indexed_date': datetime.now().isoformat()
            }
    
    def _extract_entities(self, content: str) -> Dict[str, str]:
        """Extract people, organizations, and dates from content"""
        
        people = []
        organizations = []
        dates = []
        
        if not content:
            return {
                'people_mentioned': '[]',
                'organizations': '[]', 
                'dates_mentioned': '[]'
            }
        
        content_lower = content.lower()
        
        # Common people patterns (extend based on your needs)
        people_patterns = [
            'client name', 'finn', 'client', 'netflix', 'user',
            'alex', 'maya', 'torres', 'detective', 'dr. chen'
        ]
        
        for pattern in people_patterns:
            if pattern in content_lower:
                people.append(pattern.title())
        
        # Organization patterns
        org_patterns = [
            'netflix', 'management company', 'refinery', 'sag-aftra',
            'apple', 'google', 'sony', 'warner', 'disney'
        ]
        
        for pattern in org_patterns:
            if pattern in content_lower:
                organizations.append(pattern.title())
        
        # Date patterns (basic)
        import re
        date_patterns = [
            r'\b\d{4}-\d{2}-\d{2}\b',  # 2025-08-21
            r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',  # 8/21/25 or 8/21/2025
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            dates.extend(matches)
        
        return {
            'people_mentioned': json.dumps(list(set(people))[:10]),  # Unique, max 10
            'organizations': json.dumps(list(set(organizations))[:10]),
            'dates_mentioned': json.dumps(list(set(dates))[:10])
        }
    
    def _analyze_multimedia(self, file_path: Path) -> Dict[str, Any]:
        """Analyze audio/video files for additional metadata"""
        
        multimedia_data = {
            'duration_seconds': 0.0,
            'audio_bitrate': 0,
            'video_resolution': ''
        }
        
        try:
            # Try to use mutagen for audio files
            if file_path.suffix.lower() in ['.mp3', '.wav', '.m4a', '.flac', '.ogg']:
                try:
                    from mutagen import File
                    audio_file = File(file_path)
                    if audio_file and hasattr(audio_file, 'info'):
                        multimedia_data['duration_seconds'] = getattr(audio_file.info, 'length', 0.0)
                        multimedia_data['audio_bitrate'] = getattr(audio_file.info, 'bitrate', 0)
                except:
                    pass
            
            # For video files, we'd need additional libraries like opencv-python or ffmpeg-python
            # For now, just note it's a video file
            if file_path.suffix.lower() in ['.mp4', '.mov', '.avi', '.mkv']:
                multimedia_data['video_resolution'] = 'Unknown (requires video analysis)'
            
        except Exception:
            pass
        
        return multimedia_data
    
    def save_file_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Save file metadata to database"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Convert to database format
                columns = list(metadata.keys())
                values = list(metadata.values())
                placeholders = ', '.join(['?' for _ in values])
                column_names = ', '.join(columns)
                
                conn.execute(f"""
                    INSERT OR REPLACE INTO file_metadata ({column_names})
                    VALUES ({placeholders})
                """, values)
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error saving metadata: {e}")
            return False
    
    def generate_comprehensive_spreadsheet(self, output_format: str = 'xlsx') -> Tuple[str, pd.DataFrame]:
        """Generate comprehensive metadata spreadsheet"""
        
        print("📊 Generating Comprehensive Metadata Spreadsheet")
        print("=" * 60)
        
        # Load all metadata from database
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query("SELECT * FROM file_metadata ORDER BY indexed_date DESC", conn)
        
        if df.empty:
            print("⚠️  No metadata found. Process some files first.")
            return None, None
        
        # Process JSON fields for better display
        json_fields = ['people_mentioned', 'organizations', 'dates_mentioned', 'auto_tags', 'user_tags']
        for field in json_fields:
            if field in df.columns:
                df[field] = df[field].apply(self._format_json_field)
        
        # Add computed columns
        df['file_size_mb'] = (df['file_size'] / (1024 * 1024)).round(2)
        df['age_days'] = (datetime.now() - pd.to_datetime(df['modified_date'])).dt.days
        df['confidence_percentage'] = (df['confidence_score'] * 100).round(1)
        
        # Create summary statistics
        summary_stats = self._generate_summary_stats(df)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ai_file_metadata_{timestamp}.{output_format}"
        output_path = self.metadata_dir / filename
        
        # Save to file
        if output_format.lower() == 'xlsx':
            self._save_excel_with_multiple_sheets(df, summary_stats, output_path)
        else:
            df.to_csv(output_path, index=False)
        
        print(f"✅ Metadata spreadsheet generated: {output_path}")
        print(f"📊 Total files: {len(df)}")
        print(f"📁 File types: {df['file_type'].nunique()}")
        print(f"🎯 Categories: {df['ai_category'].nunique()}")
        
        return str(output_path), df
    
    def _format_json_field(self, json_str: str) -> str:
        """Format JSON field for display in spreadsheet"""
        try:
            if pd.isna(json_str) or json_str == '[]':
                return ''
            data = json.loads(json_str)
            if isinstance(data, list):
                return ', '.join(data[:5])  # Show first 5 items
            return str(data)
        except:
            return str(json_str)
    
    def _generate_summary_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate summary statistics for the metadata"""
        
        stats = {
            'total_files': len(df),
            'total_size_gb': (df['file_size'].sum() / (1024**3)).round(2),
            'file_types': df['file_type'].value_counts().to_dict(),
            'categories': df['ai_category'].value_counts().to_dict(),
            'confidence_distribution': {
                'high_confidence_90plus': len(df[df['confidence_score'] >= 0.9]),
                'medium_confidence_70_90': len(df[(df['confidence_score'] >= 0.7) & (df['confidence_score'] < 0.9)]),
                'low_confidence_below_70': len(df[df['confidence_score'] < 0.7])
            },
            'processing_modes': df['processing_mode'].value_counts().to_dict(),
            'organization_status': df['organization_status'].value_counts().to_dict(),
            'date_range': {
                'oldest_file': df['modified_date'].min(),
                'newest_file': df['modified_date'].max(),
                'analysis_date': datetime.now().isoformat()
            }
        }
        
        return stats
    
    def _save_excel_with_multiple_sheets(self, df: pd.DataFrame, stats: Dict, output_path: Path):
        """Save Excel file with multiple sheets like AudioAI"""
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Main data sheet
            df.to_excel(writer, sheet_name='File_Metadata', index=False)
            
            # Summary statistics sheet
            stats_df = pd.DataFrame([
                ['Total Files', stats['total_files']],
                ['Total Size (GB)', stats['total_size_gb']],
                ['Analysis Date', stats['date_range']['analysis_date']],
                ['', ''],
                ['High Confidence (90%+)', stats['confidence_distribution']['high_confidence_90plus']],
                ['Medium Confidence (70-90%)', stats['confidence_distribution']['medium_confidence_70_90']],
                ['Low Confidence (<70%)', stats['confidence_distribution']['low_confidence_below_70']]
            ], columns=['Metric', 'Value'])
            
            stats_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # File types breakdown
            file_types_df = pd.DataFrame(list(stats['file_types'].items()), 
                                       columns=['File_Type', 'Count'])
            file_types_df.to_excel(writer, sheet_name='File_Types', index=False)
            
            # Categories breakdown
            categories_df = pd.DataFrame(list(stats['categories'].items()), 
                                       columns=['Category', 'Count'])
            categories_df.to_excel(writer, sheet_name='Categories', index=False)
            
            # Low confidence files (need attention)
            low_confidence = df[df['confidence_score'] < 0.7][
                ['file_name', 'ai_category', 'confidence_percentage', 'file_type', 'content_preview']
            ]
            if not low_confidence.empty:
                low_confidence.to_excel(writer, sheet_name='Needs_Review', index=False)

def test_metadata_generation():
    """Test the metadata generation system"""
    
    print("🧪 Testing Metadata Generation")
    print("=" * 50)
    
    generator = MetadataGenerator()
    
    # Find some test files - try multiple locations
    test_dirs = [
        paths.get_path('temp_processing') / "Downloads_Staging",
        Path.home() / "Downloads", 
        Path.home() / "Desktop",
        Path.home() / "Documents"
    ]
    
    test_files = []
    for test_dir in test_dirs:
        if test_dir.exists():
            files = [f for f in test_dir.iterdir() 
                    if f.is_file() and not f.name.startswith('.') 
                    and f.suffix.lower() in ['.pdf', '.docx', '.txt', '.md', '.py']]
            test_files.extend(files[:2])  # Max 2 files per directory
            if len(test_files) >= 3:
                break
    
    if test_files:
        print(f"📁 Analyzing {len(test_files)} test files...")
        
        for file_path in test_files:
            print(f"\n📄 Analyzing: {file_path.name}")
            metadata = generator.analyze_file_comprehensive(file_path)
            
            # Save to database
            success = generator.save_file_metadata(metadata)
            
            if success:
                print(f"   ✅ Saved metadata")
                print(f"   📊 Category: {metadata.get('ai_category', 'Unknown')}")
                print(f"   🎯 Confidence: {metadata.get('confidence_score', 0)*100:.1f}%")
                print(f"   📝 Word count: {metadata.get('word_count', 0)}")
            else:
                print(f"   ❌ Failed to save metadata")
        
        # Generate spreadsheet
        print(f"\n📊 Generating comprehensive spreadsheet...")
        output_path, df = generator.generate_comprehensive_spreadsheet()
        
        if output_path:
            print(f"✅ Spreadsheet generated: {output_path}")
        
    else:
        print("❌ No test files found")

if __name__ == "__main__":
    test_metadata_generation()