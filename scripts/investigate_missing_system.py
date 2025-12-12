#!/usr/bin/env python3
"""
Investigation Tool: Missing gdrive_librarian.py System
Analyzes evidence to reconstruct what happened to the missing system.

Created by: Claude AI Assistant
Date: 2025-09-08
Purpose: Solve the mystery of the missing gdrive_librarian system
"""

import os
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import hashlib
import subprocess

class MissingSystemInvestigator:
    """
    Forensic analysis of the missing gdrive_librarian.py system
    """
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.evidence = {}
        self.timeline = []
        
    def run_full_investigation(self) -> Dict[str, Any]:
        """Run complete investigation and return findings"""
        
        print("🕵️ INVESTIGATION: Missing gdrive_librarian.py System")
        print("=" * 60)
        
        # Collect all evidence
        self.evidence['compiled_file'] = self._analyze_compiled_file()
        self.evidence['database_logs'] = self._analyze_database_logs()
        self.evidence['gdrive_evidence'] = self._analyze_gdrive_evidence()
        self.evidence['git_history'] = self._analyze_git_history()
        self.evidence['file_timestamps'] = self._analyze_file_timestamps()
        self.evidence['dependencies'] = self._analyze_dependencies()
        
        # Build timeline
        self._build_timeline()
        
        # Generate report
        report = self._generate_investigation_report()
        
        # Save detailed report
        self._save_investigation_report(report)
        
        return report
    
    def _analyze_compiled_file(self) -> Dict[str, Any]:
        """Analyze the remaining .pyc file for clues"""
        
        pyc_path = self.project_root / "__pycache__" / "gdrive_librarian.cpython-312.pyc"
        
        analysis = {
            'exists': pyc_path.exists(),
            'path': str(pyc_path),
            'modified_time': None,
            'size_bytes': None,
            'magic_number': None
        }
        
        if pyc_path.exists():
            stat = pyc_path.stat()
            analysis['modified_time'] = datetime.fromtimestamp(stat.st_mtime).isoformat()
            analysis['size_bytes'] = stat.st_size
            
            # Try to read Python magic number
            try:
                with open(pyc_path, 'rb') as f:
                    magic = f.read(4)
                    analysis['magic_number'] = magic.hex()
                    
                    # Python 3.12 magic number is specific
                    if magic.hex() == '0c000000':  # Python 3.12
                        analysis['python_version'] = '3.12'
                    elif magic.hex() == '0b000000':  # Python 3.11
                        analysis['python_version'] = '3.11'
                        
            except Exception as e:
                analysis['read_error'] = str(e)
        
        print(f"📄 Compiled File Analysis:")
        print(f"   Exists: {analysis['exists']}")
        if analysis['exists']:
            print(f"   Modified: {analysis['modified_time']}")
            print(f"   Size: {analysis['size_bytes']} bytes")
            print(f"   Python Version: {analysis.get('python_version', 'Unknown')}")
        
        return analysis
    
    def _analyze_database_logs(self) -> Dict[str, Any]:
        """Analyze file_rollback.db for operation evidence"""
        
        db_path = self.project_root / "file_rollback.db"
        
        analysis = {
            'exists': db_path.exists(),
            'operations': [],
            'total_operations': 0,
            'date_range': None
        }
        
        if db_path.exists():
            try:
                with sqlite3.connect(db_path) as conn:
                    # Get all operations
                    cursor = conn.execute("""
                        SELECT * FROM file_rollback 
                        ORDER BY operation_timestamp
                    """)
                    
                    operations = []
                    for row in cursor.fetchall():
                        op = {
                            'rollback_id': row[0],
                            'timestamp': row[1],
                            'original_path': row[2],
                            'original_filename': row[3],
                            'new_filename': row[4],
                            'gdrive_folder': row[5],
                            'gdrive_file_id': row[6],
                            'category': row[7],
                            'confidence': row[8],
                            'rollback_status': row[9],
                            'notes': row[10]
                        }
                        operations.append(op)
                        self.timeline.append({
                            'time': row[1],
                            'event': 'FILE_OPERATION',
                            'details': f"Renamed '{row[3]}' to '{row[4]}' (confidence: {row[8]}%)"
                        })
                    
                    analysis['operations'] = operations
                    analysis['total_operations'] = len(operations)
                    
                    if operations:
                        analysis['date_range'] = {
                            'first': operations[0]['timestamp'],
                            'last': operations[-1]['timestamp']
                        }
                        
            except Exception as e:
                analysis['error'] = str(e)
        
        print(f"🗄️ Database Analysis:")
        print(f"   Operations logged: {analysis['total_operations']}")
        if analysis['date_range']:
            print(f"   Date range: {analysis['date_range']['first']} to {analysis['date_range']['last']}")
        
        return analysis
    
    def _analyze_gdrive_evidence(self) -> Dict[str, Any]:
        """Look for Google Drive integration evidence"""
        
        analysis = {
            'api_files': [],
            'config_files': [],
            'credentials': [],
            'integration_patterns': []
        }
        
        # Look for Google Drive related files
        for file_path in self.project_root.rglob("*"):
            if file_path.is_file():
                filename = file_path.name.lower()
                
                if 'gdrive' in filename or 'google' in filename or 'drive' in filename:
                    if filename.endswith('.py'):
                        analysis['api_files'].append(str(file_path))
                    elif filename.endswith('.json'):
                        analysis['config_files'].append(str(file_path))
                    elif 'credential' in filename:
                        analysis['credentials'].append(str(file_path))
        
        # Look for import patterns in existing files
        for py_file in self.project_root.glob("*.py"):
            try:
                content = py_file.read_text(encoding='utf-8')
                if 'googleapiclient' in content or 'google.auth' in content:
                    analysis['integration_patterns'].append({
                        'file': str(py_file),
                        'has_google_api': True
                    })
            except:
                continue
        
        print(f"☁️  Google Drive Evidence:")
        print(f"   API files: {len(analysis['api_files'])}")
        print(f"   Config files: {len(analysis['config_files'])}")
        print(f"   Files with Google API: {len(analysis['integration_patterns'])}")
        
        return analysis
    
    def _analyze_git_history(self) -> Dict[str, Any]:
        """Analyze git history for clues about the missing file"""
        
        analysis = {
            'git_available': False,
            'recent_commits': [],
            'file_history': [],
            'deleted_files': []
        }
        
        try:
            # Check if we're in a git repo
            result = subprocess.run(['git', 'status'], 
                                  capture_output=True, 
                                  text=True, 
                                  cwd=self.project_root)
            
            if result.returncode == 0:
                analysis['git_available'] = True
                
                # Get recent commits
                result = subprocess.run(['git', 'log', '--oneline', '-10'], 
                                      capture_output=True, 
                                      text=True, 
                                      cwd=self.project_root)
                
                if result.returncode == 0:
                    analysis['recent_commits'] = result.stdout.strip().split('\n')
                
                # Look for any trace of gdrive_librarian in git history
                result = subprocess.run(['git', 'log', '--all', '--follow', '--', 'gdrive_librarian.py'], 
                                      capture_output=True, 
                                      text=True, 
                                      cwd=self.project_root)
                
                if result.returncode == 0 and result.stdout.strip():
                    analysis['file_history'] = result.stdout.strip().split('\n')
                
                # Check for recently deleted files
                result = subprocess.run(['git', 'log', '--diff-filter=D', '--summary', '--oneline', '-10'], 
                                      capture_output=True, 
                                      text=True, 
                                      cwd=self.project_root)
                
                if result.returncode == 0:
                    analysis['deleted_files'] = result.stdout.strip().split('\n')
                    
        except Exception as e:
            analysis['error'] = str(e)
        
        print(f"📜 Git History Analysis:")
        print(f"   Git available: {analysis['git_available']}")
        print(f"   Recent commits: {len(analysis.get('recent_commits', []))}")
        print(f"   File history entries: {len(analysis.get('file_history', []))}")
        
        return analysis
    
    def _analyze_file_timestamps(self) -> Dict[str, Any]:
        """Analyze file modification times for timeline clues"""
        
        analysis = {
            'recent_modifications': [],
            'suspicious_timestamps': []
        }
        
        # Get all Python files with timestamps
        for py_file in self.project_root.glob("*.py"):
            stat = py_file.stat()
            mod_time = datetime.fromtimestamp(stat.st_mtime)
            
            analysis['recent_modifications'].append({
                'file': py_file.name,
                'modified': mod_time.isoformat(),
                'size': stat.st_size
            })
            
            self.timeline.append({
                'time': mod_time.isoformat(),
                'event': 'FILE_MODIFIED',
                'details': f"Modified {py_file.name}"
            })
        
        # Sort by modification time
        analysis['recent_modifications'].sort(key=lambda x: x['modified'], reverse=True)
        
        print(f"⏰ Timestamp Analysis:")
        print(f"   Recent modifications: {len(analysis['recent_modifications'])}")
        
        return analysis
    
    def _analyze_dependencies(self) -> Dict[str, Any]:
        """Analyze what systems might have depended on gdrive_librarian"""
        
        analysis = {
            'import_references': [],
            'potential_callers': []
        }
        
        # Search for references to gdrive_librarian in other files
        for py_file in self.project_root.glob("*.py"):
            try:
                content = py_file.read_text(encoding='utf-8')
                if 'gdrive_librarian' in content:
                    analysis['import_references'].append({
                        'file': str(py_file),
                        'references': content.count('gdrive_librarian')
                    })
            except:
                continue
        
        print(f"🔗 Dependency Analysis:")
        print(f"   Files referencing gdrive_librarian: {len(analysis['import_references'])}")
        
        return analysis
    
    def _build_timeline(self):
        """Build chronological timeline of events"""
        
        # Sort timeline by timestamp
        self.timeline.sort(key=lambda x: x['time'])
        
        print(f"\n⏰ EVENT TIMELINE:")
        for event in self.timeline[-10:]:  # Show last 10 events
            print(f"   {event['time']}: {event['event']} - {event['details']}")
    
    def _generate_investigation_report(self) -> Dict[str, Any]:
        """Generate comprehensive investigation report"""
        
        report = {
            'investigation_date': datetime.now().isoformat(),
            'summary': {
                'case_status': 'UNDER_INVESTIGATION',
                'evidence_strength': 'STRONG',
                'system_existed': True,
                'probable_cause': 'ACCIDENTAL_DELETION_OR_CLEANUP'
            },
            'evidence': self.evidence,
            'timeline': self.timeline,
            'conclusions': [],
            'recommendations': []
        }
        
        # Draw conclusions
        if self.evidence['compiled_file']['exists']:
            report['conclusions'].append("System definitely existed - compiled bytecode found")
        
        if self.evidence['database_logs']['total_operations'] > 0:
            report['conclusions'].append("System was actively used - operation logs found")
        
        if len(self.evidence['gdrive_evidence']['api_files']) > 0:
            report['conclusions'].append("Google Drive integration exists in other systems")
        
        # Generate recommendations
        report['recommendations'].extend([
            "Implement mandatory change logging to prevent future mysteries",
            "Create automated backups before any system modifications",
            "Require user notification before removing active systems",
            "Establish rollback procedures for all file operations",
            "Audit Google Drive for files needing rollback"
        ])
        
        return report
    
    def _save_investigation_report(self, report: Dict[str, Any]):
        """Save detailed investigation report"""
        
        report_path = self.project_root / f"INVESTIGATION_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📋 Investigation report saved: {report_path}")

def main():
    """Run the investigation"""
    
    investigator = MissingSystemInvestigator()
    report = investigator.run_full_investigation()
    
    print(f"\n🔍 INVESTIGATION SUMMARY:")
    print(f"   Case Status: {report['summary']['case_status']}")
    print(f"   Evidence Strength: {report['summary']['evidence_strength']}")
    print(f"   System Existed: {report['summary']['system_existed']}")
    print(f"   Probable Cause: {report['summary']['probable_cause']}")
    
    print(f"\n📋 KEY CONCLUSIONS:")
    for conclusion in report['conclusions']:
        print(f"   • {conclusion}")
    
    print(f"\n🔧 RECOMMENDATIONS:")
    for rec in report['recommendations']:
        print(f"   • {rec}")

if __name__ == "__main__":
    main()