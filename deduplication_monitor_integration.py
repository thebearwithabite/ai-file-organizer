#!/usr/bin/env python3
"""
Background Monitor Integration for Real-Time Duplicate Detection
Hooks into file system events to immediately detect and handle duplicates
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from deduplication_system import BulletproofDeduplicator
from safe_deduplication import SafeDeduplicator

class DeduplicationMonitorIntegration:
    """
    Real-time duplicate detection for background monitor
    Integrates with file system events to catch duplicates immediately
    """
    
    def __init__(self, base_dir: str = None):
        self.deduper = BulletproofDeduplicator(base_dir)
        self.safe_deduper = SafeDeduplicator(base_dir)
        
        # Real-time settings
        self.auto_delete_safe_duplicates = False  # Start conservative
        self.notify_on_duplicates = True
        self.min_file_size_bytes = 1024  # Don't process tiny files
        
        # Duplicate detection cache (avoid re-processing same files)
        self.processed_recently = {}
        self.cache_timeout_minutes = 5
    
    def on_file_created(self, file_path: Path) -> Optional[Dict]:
        """
        Called when a new file is created (from background monitor)
        Immediately checks for duplicates using quick hash
        """
        
        if not self._should_process_file(file_path):
            return None
        
        try:
            print(f"🔍 Checking for duplicates: {file_path.name}")
            
            # Detect duplicates using the bulletproof system
            duplicates = self.deduper.detect_new_duplicate(file_path)
            
            if duplicates:
                return self._handle_duplicate_detected(file_path, duplicates)
            
            # No duplicates found - file is unique
            return {
                'action': 'unique_file',
                'file_path': str(file_path),
                'message': f"✅ Unique file: {file_path.name}"
            }
        
        except Exception as e:
            print(f"⚠️ Error checking duplicates for {file_path.name}: {e}")
            return None
    
    def on_file_modified(self, file_path: Path) -> Optional[Dict]:
        """
        Called when a file is modified (from background monitor)
        Recalculates hashes and updates duplicate status
        """
        
        if not self._should_process_file(file_path):
            return None
        
        try:
            # Recalculate hashes for modified file
            record = self.deduper.hash_file(file_path, force_rehash=True)
            
            print(f"🔄 Updated hashes for modified file: {file_path.name}")
            
            # Check if it's now a duplicate of something else
            duplicates = []
            potential_duplicates = self.deduper.find_duplicates_by_quick_hash(record.quick_hash)
            
            for potential in potential_duplicates:
                potential_path = Path(potential.file_path)
                if (potential_path.exists() and 
                    potential_path != file_path and
                    potential.secure_hash == record.secure_hash):
                    duplicates.append(potential_path)
            
            if duplicates:
                return self._handle_duplicate_detected(file_path, duplicates)
            
            return {
                'action': 'file_updated',
                'file_path': str(file_path),
                'message': f"🔄 Hashes updated: {file_path.name}"
            }
        
        except Exception as e:
            print(f"⚠️ Error updating hashes for {file_path.name}: {e}")
            return None
    
    def _should_process_file(self, file_path: Path) -> bool:
        """Check if file should be processed for duplicate detection"""
        
        # Skip if file doesn't exist or is too small
        if not file_path.exists() or not file_path.is_file():
            return False
        
        try:
            file_size = file_path.stat().st_size
            if file_size < self.min_file_size_bytes:
                return False
        except:
            return False
        
        # Skip system files and temporary files
        if file_path.name.startswith('.') or file_path.name.startswith('~'):
            return False
        
        # Skip files we've processed recently (avoid duplicate work)
        file_key = str(file_path)
        now = datetime.now()
        
        if file_key in self.processed_recently:
            last_processed = self.processed_recently[file_key]
            if (now - last_processed).total_seconds() < self.cache_timeout_minutes * 60:
                return False
        
        # Update processed cache
        self.processed_recently[file_key] = now
        
        # Clean old entries from cache
        self._clean_processed_cache()
        
        return True
    
    def _clean_processed_cache(self):
        """Remove old entries from processed cache"""
        now = datetime.now()
        timeout_seconds = self.cache_timeout_minutes * 60
        
        keys_to_remove = []
        for file_key, processed_time in self.processed_recently.items():
            if (now - processed_time).total_seconds() > timeout_seconds:
                keys_to_remove.append(file_key)
        
        for key in keys_to_remove:
            del self.processed_recently[key]
    
    def _handle_duplicate_detected(self, new_file: Path, duplicates: List[Path]) -> Dict:
        """Handle when a duplicate is detected"""
        
        duplicate_info = {
            'action': 'duplicate_detected',
            'new_file': str(new_file),
            'duplicates': [str(d) for d in duplicates],
            'duplicate_count': len(duplicates) + 1,
            'message': f"🚨 Duplicate detected: {new_file.name}"
        }
        
        if self.notify_on_duplicates:
            print(f"🚨 DUPLICATE DETECTED: {new_file.name}")
            print(f"   Matches {len(duplicates)} existing file(s):")
            for dup in duplicates[:3]:  # Show first 3
                print(f"   📄 {dup}")
            
            if len(duplicates) > 3:
                print(f"   📄 ... and {len(duplicates) - 3} more")
        
        # If auto-delete is enabled and it's safe, handle automatically
        if self.auto_delete_safe_duplicates:
            safety_result = self._attempt_safe_auto_deletion(new_file, duplicates)
            duplicate_info.update(safety_result)
        else:
            duplicate_info['suggested_action'] = "Review manually or enable auto-deletion"
        
        return duplicate_info
    
    def _attempt_safe_auto_deletion(self, new_file: Path, duplicates: List[Path]) -> Dict:
        """Attempt to safely auto-delete if conditions are met"""
        
        all_files = [new_file] + duplicates
        
        # Create a temporary duplicate group for analysis
        from safe_deduplication import DuplicateGroup
        
        try:
            # Calculate safety score
            safety_score = self.safe_deduper.calculate_safety_score(all_files)
            original_file = self.safe_deduper._choose_original_file(all_files)
            
            # Only auto-delete if very safe and not the original
            if (safety_score >= 0.9 and  # Very high safety threshold
                new_file != original_file and
                new_file.stat().st_size < 50 * 1024 * 1024):  # < 50MB
                
                try:
                    # Create backup
                    backup_path = self.safe_deduper._create_backup(new_file, "auto_delete")
                    
                    # Delete the file
                    new_file.unlink()
                    
                    # Log the deletion
                    self.safe_deduper._log_deletion(new_file, original_file, "auto_delete", backup_path)
                    
                    print(f"✅ Auto-deleted safe duplicate: {new_file.name}")
                    
                    return {
                        'auto_action': 'deleted',
                        'backup_created': str(backup_path),
                        'kept_original': str(original_file),
                        'safety_score': safety_score
                    }
                
                except Exception as e:
                    print(f"❌ Auto-deletion failed: {e}")
                    return {'auto_action': 'failed', 'error': str(e)}
            
            else:
                return {
                    'auto_action': 'skipped',
                    'reason': f"Safety score {safety_score:.1%} below threshold or file too large",
                    'requires_manual_review': True
                }
        
        except Exception as e:
            return {'auto_action': 'error', 'error': str(e)}
    
    def enable_auto_deletion(self):
        """Enable automatic deletion of safe duplicates"""
        self.auto_delete_safe_duplicates = True
        print("✅ Auto-deletion of safe duplicates enabled")
        print("⚠️  Only files with 90%+ safety score will be auto-deleted")
    
    def disable_auto_deletion(self):
        """Disable automatic deletion"""
        self.auto_delete_safe_duplicates = False
        print("🔒 Auto-deletion disabled - duplicates will only be detected")
    
    def get_status(self) -> Dict:
        """Get current status of deduplication monitoring"""
        return {
            'auto_delete_enabled': self.auto_delete_safe_duplicates,
            'notifications_enabled': self.notify_on_duplicates,
            'min_file_size_bytes': self.min_file_size_bytes,
            'recently_processed_count': len(self.processed_recently),
            'database_path': str(self.deduper.db_path)
        }

# Integration function for background monitor
def integrate_with_background_monitor(monitor_instance):
    """
    Integrate deduplication with existing background monitor
    Call this from background_monitor.py initialization
    """
    
    dedup_integration = DeduplicationMonitorIntegration()
    
    # Hook into monitor's file event callbacks
    original_on_file_created = getattr(monitor_instance, 'on_file_created', lambda x: None)
    original_on_file_modified = getattr(monitor_instance, 'on_file_modified', lambda x: None)
    
    def enhanced_on_file_created(file_path):
        # Run original handler
        original_result = original_on_file_created(file_path)
        
        # Run deduplication check
        dedup_result = dedup_integration.on_file_created(Path(file_path))
        
        return {'original': original_result, 'deduplication': dedup_result}
    
    def enhanced_on_file_modified(file_path):
        # Run original handler  
        original_result = original_on_file_modified(file_path)
        
        # Run deduplication check
        dedup_result = dedup_integration.on_file_modified(Path(file_path))
        
        return {'original': original_result, 'deduplication': dedup_result}
    
    # Replace monitor's handlers
    monitor_instance.on_file_created = enhanced_on_file_created
    monitor_instance.on_file_modified = enhanced_on_file_modified
    
    print("✅ Deduplication monitoring integrated with background monitor")
    
    return dedup_integration

if __name__ == "__main__":
    # Test the integration
    integration = DeduplicationMonitorIntegration()
    
    print("🔍 Deduplication Monitor Integration")
    print("=" * 50)
    print("Status:", integration.get_status())
    
    # Test with a file (if provided)
    if len(sys.argv) > 1:
        test_file = Path(sys.argv[1])
        if test_file.exists():
            print(f"\n🧪 Testing with: {test_file}")
            result = integration.on_file_created(test_file)
            print(f"Result: {result}")