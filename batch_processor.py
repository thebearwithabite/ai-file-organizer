#!/usr/bin/env python3
"""
Batch Processing with Progress Tracking for AI File Organizer
Handles large collections of files with real-time progress updates and recovery
Based on AudioAI organizer batch processing patterns
"""

import sys
import os
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
import signal

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from interactive_classifier import InteractiveClassifier
from interaction_modes import InteractionMode
from integrated_organizer import IntegratedOrganizer
from metadata_generator import MetadataGenerator

@dataclass
class BatchJob:
    """Represents a batch processing job"""
    job_id: str
    name: str
    files: List[Path]
    mode: InteractionMode
    dry_run: bool
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"  # pending, running, paused, completed, failed, cancelled

@dataclass 
class FileResult:
    """Result of processing a single file"""
    file_path: Path
    success: bool
    action_taken: str
    error_message: Optional[str] = None
    classification: Optional[str] = None
    confidence: Optional[float] = None
    processing_time: float = 0.0
    questions_asked: int = 0

@dataclass
class BatchProgress:
    """Real-time progress tracking"""
    total_files: int
    processed: int
    successful: int
    failed: int
    skipped: int
    questions_asked: int
    current_file: Optional[str] = None
    start_time: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    files_per_minute: float = 0.0

class BatchProcessor:
    """
    Handles batch processing of files with progress tracking and recovery
    Like AudioAI batch processing but for document organization
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "Documents" / "AI_ORGANIZER_BASE"
        self.batch_dir = self.base_dir / "04_METADATA_SYSTEM" / "batch_jobs"
        self.batch_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.classifier = InteractiveClassifier(str(self.base_dir))
        self.organizer = IntegratedOrganizer(str(self.base_dir))
        self.metadata_generator = MetadataGenerator(str(self.base_dir))
        
        # Progress tracking
        self.current_job: Optional[BatchJob] = None
        self.current_progress = BatchProgress(0, 0, 0, 0, 0, 0)
        self.is_running = False
        self.is_paused = False
        self.stop_requested = False
        
        # Database for job tracking
        self.db_path = self.batch_dir / "batch_jobs.db"
        self._init_job_database()
        
        # Progress callbacks
        self.progress_callbacks: List[Callable[[BatchProgress], None]] = []
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _init_job_database(self):
        """Initialize SQLite database for job tracking"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS batch_jobs (
                    job_id TEXT PRIMARY KEY,
                    name TEXT,
                    file_count INTEGER,
                    mode TEXT,
                    dry_run BOOLEAN,
                    status TEXT,
                    created_at TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    total_files INTEGER,
                    processed_files INTEGER,
                    successful_files INTEGER,
                    failed_files INTEGER,
                    skipped_files INTEGER,
                    questions_asked INTEGER,
                    error_message TEXT,
                    config_json TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT,
                    file_path TEXT,
                    success BOOLEAN,
                    action_taken TEXT,
                    error_message TEXT,
                    classification TEXT,
                    confidence REAL,
                    processing_time REAL,
                    questions_asked INTEGER,
                    processed_at TEXT,
                    FOREIGN KEY (job_id) REFERENCES batch_jobs (job_id)
                )
            """)
            
            conn.commit()
    
    def create_batch_job(self, name: str, files: List[Path], mode: InteractionMode, dry_run: bool = True) -> BatchJob:
        """Create a new batch job"""
        
        job_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(files)}"
        
        job = BatchJob(
            job_id=job_id,
            name=name,
            files=files,
            mode=mode,
            dry_run=dry_run,
            created_at=datetime.now()
        )
        
        # Save to database
        self._save_job_to_db(job)
        
        print(f"✅ Created batch job: {job_id}")
        print(f"   Name: {name}")
        print(f"   Files: {len(files)}")
        print(f"   Mode: {mode.value}")
        print(f"   Dry run: {dry_run}")
        
        return job
    
    def _save_job_to_db(self, job: BatchJob):
        """Save batch job to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO batch_jobs 
                (job_id, name, file_count, mode, dry_run, status, created_at, 
                 started_at, completed_at, total_files, processed_files, 
                 successful_files, failed_files, skipped_files, questions_asked)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.job_id, job.name, len(job.files), job.mode.value, job.dry_run,
                job.status, job.created_at.isoformat(),
                job.started_at.isoformat() if job.started_at else None,
                job.completed_at.isoformat() if job.completed_at else None,
                len(job.files), 0, 0, 0, 0, 0
            ))
            conn.commit()
    
    def _save_file_result(self, job_id: str, result: FileResult):
        """Save file processing result to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO file_results 
                (job_id, file_path, success, action_taken, error_message, 
                 classification, confidence, processing_time, questions_asked, processed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id, str(result.file_path), result.success, result.action_taken,
                result.error_message, result.classification, result.confidence,
                result.processing_time, result.questions_asked, datetime.now().isoformat()
            ))
            conn.commit()
    
    def add_progress_callback(self, callback: Callable[[BatchProgress], None]):
        """Add a progress callback function"""
        self.progress_callbacks.append(callback)
    
    def _update_progress(self, current_file: str = None):
        """Update progress and notify callbacks"""
        with self.lock:
            if current_file:
                self.current_progress.current_file = current_file
            
            # Calculate estimated completion time
            if self.current_progress.processed > 0 and self.current_progress.start_time:
                elapsed = (datetime.now() - self.current_progress.start_time).total_seconds()
                self.current_progress.files_per_minute = (self.current_progress.processed / elapsed) * 60
                
                remaining_files = self.current_progress.total_files - self.current_progress.processed
                if self.current_progress.files_per_minute > 0:
                    remaining_minutes = remaining_files / self.current_progress.files_per_minute
                    self.current_progress.estimated_completion = datetime.now() + timedelta(minutes=remaining_minutes)
            
            # Notify callbacks
            for callback in self.progress_callbacks:
                try:
                    callback(self.current_progress)
                except Exception as e:
                    print(f"Progress callback error: {e}")
    
    def run_batch_job(self, job: BatchJob, max_workers: int = 1) -> Dict[str, Any]:
        """
        Run a batch job with progress tracking
        max_workers=1 for interactive mode, higher for automatic modes
        """
        
        print(f"\n🚀 Starting Batch Job: {job.name}")
        print("=" * 60)
        
        # Set up progress tracking
        self.current_job = job
        self.current_progress = BatchProgress(
            total_files=len(job.files),
            processed=0,
            successful=0,
            failed=0,
            skipped=0,
            questions_asked=0,
            start_time=datetime.now()
        )
        
        # Update job status
        job.status = "running"
        job.started_at = datetime.now()
        self._save_job_to_db(job)
        
        # Set interaction mode
        self.classifier.set_interaction_mode(job.mode)
        
        self.is_running = True
        self.stop_requested = False
        results = []
        
        try:
            if max_workers == 1 or job.mode in [InteractionMode.ALWAYS, InteractionMode.SMART]:
                # Sequential processing for interactive modes
                results = self._process_sequential(job)
            else:
                # Parallel processing for automatic modes
                results = self._process_parallel(job, max_workers)
                
        except KeyboardInterrupt:
            print(f"\n⏸️  Batch job interrupted by user")
            job.status = "paused"
        except Exception as e:
            print(f"\n❌ Batch job failed: {e}")
            job.status = "failed"
        else:
            print(f"\n✅ Batch job completed successfully")
            job.status = "completed"
        finally:
            job.completed_at = datetime.now()
            self._save_job_to_db(job)
            self.is_running = False
        
        # Generate summary
        summary = self._generate_job_summary(job, results)
        
        # Generate metadata spreadsheet if successful files
        if self.current_progress.successful > 0:
            try:
                print(f"\n📊 Generating metadata spreadsheet...")
                output_path, _ = self.metadata_generator.generate_comprehensive_spreadsheet()
                summary['metadata_spreadsheet'] = output_path
            except Exception as e:
                print(f"⚠️  Could not generate metadata spreadsheet: {e}")
        
        return summary
    
    def _process_sequential(self, job: BatchJob) -> List[FileResult]:
        """Process files sequentially (for interactive modes)"""
        results = []
        
        for i, file_path in enumerate(job.files):
            if self.stop_requested:
                break
                
            print(f"\n📄 [{i+1}/{len(job.files)}] {file_path.name}")
            
            # Update progress
            self._update_progress(file_path.name)
            
            # Process single file
            result = self._process_single_file(file_path, job)
            results.append(result)
            
            # Update counters
            with self.lock:
                self.current_progress.processed += 1
                if result.success:
                    self.current_progress.successful += 1
                else:
                    self.current_progress.failed += 1
                
                if result.action_taken == "skipped":
                    self.current_progress.skipped += 1
                
                self.current_progress.questions_asked += result.questions_asked
            
            # Save result to database
            self._save_file_result(job.job_id, result)
            
            # Show progress periodically
            if i % 10 == 0 or i == len(job.files) - 1:
                self._show_progress()
        
        return results
    
    def _process_parallel(self, job: BatchJob, max_workers: int) -> List[FileResult]:
        """Process files in parallel (for automatic modes only)"""
        results = []
        
        print(f"🔄 Processing with {max_workers} workers...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all jobs
            future_to_file = {
                executor.submit(self._process_single_file, file_path, job): file_path 
                for file_path in job.files
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_file):
                if self.stop_requested:
                    break
                    
                file_path = future_to_file[future]
                
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Update counters
                    with self.lock:
                        self.current_progress.processed += 1
                        if result.success:
                            self.current_progress.successful += 1
                        else:
                            self.current_progress.failed += 1
                        
                        if result.action_taken == "skipped":
                            self.current_progress.skipped += 1
                    
                    # Save result
                    self._save_file_result(job.job_id, result)
                    
                    # Update progress display
                    if self.current_progress.processed % 10 == 0:
                        self._show_progress()
                
                except Exception as e:
                    print(f"❌ Error processing {file_path.name}: {e}")
                    
                    result = FileResult(
                        file_path=file_path,
                        success=False,
                        action_taken="error",
                        error_message=str(e)
                    )
                    results.append(result)
                    
                    with self.lock:
                        self.current_progress.processed += 1
                        self.current_progress.failed += 1
        
        return results
    
    def _process_single_file(self, file_path: Path, job: BatchJob) -> FileResult:
        """Process a single file and return result"""
        
        start_time = time.time()
        
        try:
            # Use integrated organizer for complete workflow
            organize_result = self.organizer.organize_file(
                file_path, 
                dry_run=job.dry_run,
                show_preview=(job.mode in [InteractionMode.ALWAYS, InteractionMode.SMART])
            )
            
            processing_time = time.time() - start_time
            
            result = FileResult(
                file_path=file_path,
                success=organize_result['success'],
                action_taken=organize_result['action_taken'],
                error_message=organize_result.get('error'),
                classification=organize_result.get('classification', {}).get('category'),
                confidence=organize_result.get('confidence'),
                processing_time=processing_time,
                questions_asked=1 if organize_result.get('action_taken') == 'interactive' else 0
            )
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            return FileResult(
                file_path=file_path,
                success=False,
                action_taken="error",
                error_message=str(e),
                processing_time=processing_time
            )
    
    def _show_progress(self):
        """Display current progress"""
        progress = self.current_progress
        
        if progress.total_files == 0:
            return
        
        percent_complete = (progress.processed / progress.total_files) * 100
        
        print(f"\n📈 Progress: {progress.processed}/{progress.total_files} ({percent_complete:.1f}%)")
        print(f"   ✅ Successful: {progress.successful}")
        print(f"   ❌ Failed: {progress.failed}")
        print(f"   ⏭️  Skipped: {progress.skipped}")
        print(f"   ❓ Questions: {progress.questions_asked}")
        
        if progress.files_per_minute > 0:
            print(f"   ⚡ Speed: {progress.files_per_minute:.1f} files/min")
            
        if progress.estimated_completion:
            eta = progress.estimated_completion.strftime("%H:%M:%S")
            print(f"   🕐 ETA: {eta}")
    
    def _generate_job_summary(self, job: BatchJob, results: List[FileResult]) -> Dict[str, Any]:
        """Generate comprehensive job summary"""
        
        total_time = (job.completed_at - job.started_at).total_seconds() if job.completed_at and job.started_at else 0
        
        summary = {
            'job_id': job.job_id,
            'name': job.name,
            'status': job.status,
            'mode': job.mode.value,
            'dry_run': job.dry_run,
            'total_files': len(job.files),
            'processed_files': len(results),
            'successful_files': sum(1 for r in results if r.success),
            'failed_files': sum(1 for r in results if not r.success),
            'skipped_files': sum(1 for r in results if r.action_taken == "skipped"),
            'questions_asked': sum(r.questions_asked for r in results),
            'total_time_seconds': total_time,
            'average_time_per_file': total_time / len(results) if results else 0,
            'files_per_minute': (len(results) / total_time * 60) if total_time > 0 else 0,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None
        }
        
        # Show summary
        print(f"\n📊 Batch Job Summary")
        print("=" * 40)
        print(f"Job ID: {summary['job_id']}")
        print(f"Status: {summary['status']}")
        print(f"Mode: {summary['mode']}")
        print(f"Files processed: {summary['processed_files']}/{summary['total_files']}")
        print(f"Success rate: {(summary['successful_files']/summary['processed_files']*100):.1f}%" if summary['processed_files'] > 0 else "0%")
        print(f"Total time: {total_time/60:.1f} minutes")
        print(f"Speed: {summary['files_per_minute']:.1f} files/minute")
        
        return summary
    
    def pause_job(self):
        """Pause current job"""
        if self.is_running:
            self.is_paused = True
            print("⏸️  Pausing batch job...")
    
    def resume_job(self):
        """Resume paused job"""
        if self.is_paused:
            self.is_paused = False
            print("▶️  Resuming batch job...")
    
    def stop_job(self):
        """Stop current job gracefully"""
        if self.is_running:
            self.stop_requested = True
            print("⏹️  Stopping batch job...")
    
    def _signal_handler(self, signum, frame):
        """Handle interrupt signals gracefully"""
        print(f"\n⏸️  Received signal {signum}, gracefully stopping...")
        self.stop_job()
    
    def list_jobs(self) -> List[Dict]:
        """List all batch jobs"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT job_id, name, status, file_count, mode, dry_run, 
                       created_at, started_at, completed_at, successful_files, failed_files
                FROM batch_jobs 
                ORDER BY created_at DESC
            """)
            
            jobs = []
            for row in cursor.fetchall():
                jobs.append({
                    'job_id': row[0],
                    'name': row[1], 
                    'status': row[2],
                    'file_count': row[3],
                    'mode': row[4],
                    'dry_run': row[5],
                    'created_at': row[6],
                    'started_at': row[7],
                    'completed_at': row[8],
                    'successful_files': row[9] or 0,
                    'failed_files': row[10] or 0
                })
            
            return jobs

def demo_batch_processing():
    """Demonstrate batch processing capabilities"""
    
    print("🚀 Batch Processing Demo")
    print("=" * 50)
    
    processor = BatchProcessor()
    
    # Find some test files
    test_dirs = [Path.home() / "Downloads", Path.home() / "Desktop"]
    test_files = []
    
    for test_dir in test_dirs:
        if test_dir.exists():
            files = [f for f in test_dir.iterdir() 
                    if f.is_file() and f.suffix.lower() in ['.pdf', '.docx', '.txt', '.md']]
            test_files.extend(files[:3])  # Max 3 per directory
            if len(test_files) >= 5:
                break
    
    if not test_files:
        # Use project files as fallback
        project_dir = Path(__file__).parent
        test_files = [
            project_dir / "README.md",
            project_dir / "CLAUDE.md"
        ]
        test_files = [f for f in test_files if f.exists()]
    
    if test_files:
        print(f"📁 Found {len(test_files)} test files")
        
        # Create batch job
        job = processor.create_batch_job(
            name="Demo Batch Processing",
            files=test_files,
            mode=InteractionMode.SMART,
            dry_run=True
        )
        
        # Add progress callback
        def progress_callback(progress):
            if progress.processed % 2 == 0:  # Update every 2 files
                print(f"   Progress: {progress.processed}/{progress.total_files} files processed")
        
        processor.add_progress_callback(progress_callback)
        
        # Run the job
        summary = processor.run_batch_job(job)
        
        print(f"\n✅ Demo completed!")
        
    else:
        print("❌ No test files found for demo")

if __name__ == "__main__":
    demo_batch_processing()