#!/usr/bin/env python3
"""
Database Migration Diagnostics
Investigate why the database migration tests showed issues
"""

import os
import sys
import sqlite3
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add project directory to path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from metadata_generator import MetadataGenerator

def diagnose_database_schema():
    """Diagnose the current database schema and migration behavior"""
    
    print("🔍 DATABASE SCHEMA DIAGNOSTICS")
    print("=" * 60)
    
    # Create test environment
    test_dir = Path(tempfile.mkdtemp(prefix="schema_diagnostic_"))
    
    try:
        print(f"📁 Test directory: {test_dir}")
        
        # Initialize MetadataGenerator
        metadata_gen = MetadataGenerator(str(test_dir))
        db_path = metadata_gen.db_path
        
        print(f"📄 Database path: {db_path}")
        
        # Check initial schema
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("PRAGMA table_info(file_metadata)")
            initial_columns = cursor.fetchall()
            
            print(f"\n📊 Initial Schema ({len(initial_columns)} columns):")
            for i, col in enumerate(initial_columns, 1):
                print(f"   {i:2d}. {col[1]} ({col[2]}) - Default: {col[4]}")
        
        # Check for Google Drive columns specifically
        gdrive_columns = ['gdrive_upload', 'gdrive_folder', 'gdrive_file_id', 
                         'gdrive_category', 'gdrive_confidence', 'upload_timestamp', 
                         'space_freed_mb']
        
        column_names = [col[1] for col in initial_columns]
        missing_columns = [col for col in gdrive_columns if col not in column_names]
        existing_gdrive_columns = [col for col in gdrive_columns if col in column_names]
        
        print(f"\n📈 Google Drive Columns Status:")
        print(f"   ✅ Already present: {len(existing_gdrive_columns)} - {existing_gdrive_columns}")
        print(f"   ❌ Missing: {len(missing_columns)} - {missing_columns}")
        
        # Test migration on database with missing columns
        if missing_columns:
            print(f"\n🔧 Testing migration with {len(missing_columns)} missing columns...")
            
            # Force migration
            with sqlite3.connect(db_path) as conn:
                metadata_gen._migrate_database_schema(conn)
                
                # Check schema after migration
                cursor = conn.execute("PRAGMA table_info(file_metadata)")
                post_migration_columns = cursor.fetchall()
                
                print(f"📊 Post-Migration Schema ({len(post_migration_columns)} columns):")
                for i, col in enumerate(post_migration_columns, 1):
                    print(f"   {i:2d}. {col[1]} ({col[2]}) - Default: {col[4]}")
                
                # Check if all Google Drive columns are now present
                post_column_names = [col[1] for col in post_migration_columns]
                still_missing = [col for col in gdrive_columns if col not in post_column_names]
                newly_added = [col for col in gdrive_columns if col not in column_names and col in post_column_names]
                
                print(f"\n📈 Migration Results:")
                print(f"   ✅ Newly added: {len(newly_added)} - {newly_added}")
                print(f"   ❌ Still missing: {len(still_missing)} - {still_missing}")
                
                if len(newly_added) > 0:
                    print("✅ Migration successfully added columns")
                else:
                    print("❌ Migration did not add expected columns")
        else:
            print("✅ All Google Drive columns already present - migration would be no-op")
        
        # Test data insertion with Google Drive fields
        print(f"\n📝 Testing Google Drive Data Insertion:")
        
        with sqlite3.connect(db_path) as conn:
            try:
                test_data = {
                    'file_path': '/test/gdrive_test.pdf',
                    'file_name': 'gdrive_test.pdf',
                    'file_type': 'Document',
                    'file_size': 1024,
                    'indexed_date': datetime.now().isoformat(),
                    'gdrive_upload': True,
                    'gdrive_folder': 'Test Folder',
                    'gdrive_file_id': 'test_file_id_123',
                    'gdrive_category': 'document',
                    'gdrive_confidence': 0.95,
                    'upload_timestamp': datetime.now().isoformat(),
                    'space_freed_mb': 1.0
                }
                
                columns = list(test_data.keys())
                values = list(test_data.values())
                placeholders = ', '.join(['?' for _ in values])
                column_names = ', '.join(columns)
                
                conn.execute(f"""
                    INSERT INTO file_metadata ({column_names})
                    VALUES ({placeholders})
                """, values)
                conn.commit()
                
                print("✅ Successfully inserted data with Google Drive fields")
                
                # Verify the data
                cursor = conn.execute("""
                    SELECT gdrive_upload, gdrive_folder, gdrive_confidence 
                    FROM file_metadata WHERE file_path = ?
                """, ('/test/gdrive_test.pdf',))
                result = cursor.fetchone()
                
                if result and result[0] == 1 and result[1] == 'Test Folder' and result[2] == 0.95:
                    print("✅ Data verification successful - Google Drive fields accessible")
                else:
                    print(f"❌ Data verification failed: {result}")
                    
            except sqlite3.Error as e:
                print(f"❌ Data insertion failed: {e}")
        
    except Exception as e:
        print(f"❌ Diagnostic failed: {e}")
    
    finally:
        # Cleanup
        if test_dir.exists():
            shutil.rmtree(test_dir)
            print(f"\n🧹 Cleaned up test directory")


def test_migration_scenarios():
    """Test different migration scenarios"""
    
    print("\n🧪 MIGRATION SCENARIO TESTING")
    print("=" * 60)
    
    scenarios = [
        ("Fresh Database", lambda conn: None),  # No pre-setup
        ("Database with Basic Data", add_basic_data),
        ("Database with Partial Columns", add_partial_gdrive_columns)
    ]
    
    for scenario_name, setup_func in scenarios:
        print(f"\n📊 Testing: {scenario_name}")
        print("-" * 40)
        
        test_dir = Path(tempfile.mkdtemp(prefix=f"migration_scenario_"))
        
        try:
            metadata_gen = MetadataGenerator(str(test_dir))
            
            with sqlite3.connect(metadata_gen.db_path) as conn:
                # Setup scenario
                if setup_func:
                    setup_func(conn)
                
                # Get initial state
                cursor = conn.execute("PRAGMA table_info(file_metadata)")
                initial_columns = [row[1] for row in cursor.fetchall()]
                
                print(f"   Initial columns: {len(initial_columns)}")
                
                # Run migration
                metadata_gen._migrate_database_schema(conn)
                
                # Get final state
                cursor = conn.execute("PRAGMA table_info(file_metadata)")
                final_columns = [row[1] for row in cursor.fetchall()]
                
                print(f"   Final columns: {len(final_columns)}")
                
                added_columns = [col for col in final_columns if col not in initial_columns]
                print(f"   Added columns: {len(added_columns)} - {added_columns}")
                
                # Test data persistence
                cursor = conn.execute("SELECT COUNT(*) FROM file_metadata")
                row_count = cursor.fetchone()[0]
                print(f"   Data rows: {row_count}")
                
        except Exception as e:
            print(f"   ❌ Scenario failed: {e}")
        
        finally:
            shutil.rmtree(test_dir)


def add_basic_data(conn):
    """Add some basic data to test data preservation"""
    conn.execute("""
        INSERT INTO file_metadata (file_path, file_name, file_type, file_size, indexed_date)
        VALUES 
        ('/test/doc1.pdf', 'doc1.pdf', 'Document', 1024, ?),
        ('/test/doc2.txt', 'doc2.txt', 'Text', 512, ?)
    """, (datetime.now().isoformat(), datetime.now().isoformat()))
    conn.commit()


def add_partial_gdrive_columns(conn):
    """Add some but not all Google Drive columns to test partial migration"""
    try:
        # Add only some of the Google Drive columns
        conn.execute("ALTER TABLE file_metadata ADD COLUMN gdrive_upload BOOLEAN DEFAULT 0")
        conn.execute("ALTER TABLE file_metadata ADD COLUMN gdrive_folder TEXT")
        conn.commit()
    except sqlite3.Error:
        pass  # Columns might already exist


if __name__ == "__main__":
    diagnose_database_schema()
    test_migration_scenarios()