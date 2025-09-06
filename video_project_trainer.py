#!/usr/bin/env python3
"""
Video Project Trainer - Learns specific creative projects with 2-minute intelligent sampling
Part of AI File Organizer v3.0 - Professional Content Management Platform

Created by: RT Max
"""

import sys
import argparse
import os
from pathlib import Path
import json
import hashlib
from typing import Dict, List, Optional, Tuple
import subprocess

class VideoProjectTrainer:
    """
    Intelligent video analysis with 2-minute sampling limit for efficiency
    Learns specific creative projects and improves recognition over time
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.project_db = self.base_dir / "video_projects.json"
        self.max_analysis_seconds = 120  # 2-minute limit
        
        # Load existing project knowledge
        self.projects = self._load_projects()
    
    def _load_projects(self) -> Dict:
        """Load existing project training data"""
        if self.project_db.exists():
            try:
                with open(self.project_db, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"projects": {}, "video_analysis": {}}
    
    def _save_projects(self):
        """Save project training data"""
        try:
            with open(self.project_db, 'w') as f:
                json.dump(self.projects, f, indent=2)
        except Exception as e:
            print(f"⚠️ Warning: Could not save project data: {e}")
    
    def _get_video_duration(self, video_path: Path) -> Optional[float]:
        """Get video duration in seconds using ffprobe (if available)"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 
                'format=duration', '-of', 'csv=p=0', str(video_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return float(result.stdout.strip())
        except:
            # Fallback: estimate from file size (very rough)
            file_size_mb = video_path.stat().st_size / (1024 * 1024)
            estimated_duration = file_size_mb / 2.0  # Rough estimate: 2MB per second
            return estimated_duration
    
    def _should_limit_analysis(self, video_path: Path) -> Tuple[bool, str]:
        """Determine if video should be limited to 2 minutes and why"""
        duration = self._get_video_duration(video_path)
        
        if duration is None:
            return False, "Could not determine video duration"
        
        if duration > self.max_analysis_seconds:
            return True, f"Video is {duration:.1f}s, analyzing first {self.max_analysis_seconds}s for efficiency"
        else:
            return False, f"Full video analysis ({duration:.1f}s)"
    
    def analyze_video(self, video_path: Path, project: str = None, context: str = "general") -> Dict:
        """
        Analyze video with 2-minute intelligent sampling
        
        Args:
            video_path: Path to video file
            project: Project name for learning (e.g., "creative-content", "podcast-production")
            context: Analysis context ("professional", "creative", "general")
        
        Returns:
            Analysis results with metadata
        """
        if not video_path.exists():
            return {"error": f"Video file not found: {video_path}"}
        
        print(f"🎬 Analyzing video: {video_path.name}")
        
        # Check if we should limit analysis
        should_limit, reason = self._should_limit_analysis(video_path)
        print(f"   📏 {reason}")
        
        # Create analysis result
        video_hash = hashlib.md5(str(video_path).encode()).hexdigest()[:12]
        
        analysis = {
            "file_path": str(video_path),
            "file_name": video_path.name,
            "video_hash": video_hash,
            "project": project,
            "context": context,
            "analysis_limited": should_limit,
            "analysis_duration_limit": self.max_analysis_seconds if should_limit else None,
            "reason": reason,
            "detected_content_type": self._detect_content_type(video_path),
            "suggested_organization": self._suggest_organization(video_path, project, context)
        }
        
        # Store analysis for learning
        if project:
            self._learn_from_analysis(analysis, project)
        
        # Print results
        print(f"   🎯 Content Type: {analysis['detected_content_type']}")
        print(f"   📁 Suggested Organization: {analysis['suggested_organization']}")
        if project:
            print(f"   🧠 Learning for project: {project}")
        
        return analysis
    
    def _detect_content_type(self, video_path: Path) -> str:
        """Detect video content type based on filename and metadata"""
        name = video_path.name.lower()
        
        if any(keyword in name for keyword in ['podcast', 'interview', 'discussion']):
            return "Podcast/Interview Content"
        elif any(keyword in name for keyword in ['meeting', 'call', 'zoom']):
            return "Meeting Recording"
        elif any(keyword in name for keyword in ['creative', 'project', 'content']):
            return "Creative Content"
        elif any(keyword in name for keyword in ['demo', 'tutorial', 'how-to']):
            return "Educational Content"
        else:
            return "General Video Content"
    
    def _suggest_organization(self, video_path: Path, project: str, context: str) -> str:
        """Suggest where video should be organized"""
        content_type = self._detect_content_type(video_path)
        
        if context == "professional":
            if "meeting" in content_type.lower():
                return "Professional/Meetings/Video_Calls"
            else:
                return "Professional/Content/Videos"
        elif context == "creative":
            if "podcast" in content_type.lower():
                return "Creative/Podcast_Production/Raw_Videos"
            else:
                return "Creative/Content/Videos"
        else:
            return "Media/Videos/Uncategorized"
    
    def _learn_from_analysis(self, analysis: Dict, project: str):
        """Learn patterns from video analysis for future improvement"""
        if "projects" not in self.projects:
            self.projects["projects"] = {}
        
        if project not in self.projects["projects"]:
            self.projects["projects"][project] = {
                "video_patterns": [],
                "content_types": {},
                "organization_preferences": {}
            }
        
        # Track content type patterns
        content_type = analysis["detected_content_type"]
        project_data = self.projects["projects"][project]
        
        if content_type not in project_data["content_types"]:
            project_data["content_types"][content_type] = 0
        project_data["content_types"][content_type] += 1
        
        # Track organization preferences
        org_suggestion = analysis["suggested_organization"]
        if org_suggestion not in project_data["organization_preferences"]:
            project_data["organization_preferences"][org_suggestion] = 0
        project_data["organization_preferences"][org_suggestion] += 1
        
        # Save learning
        self._save_projects()
    
    def train_project(self, project: str, description: str = None):
        """
        Create or update project training profile
        
        Args:
            project: Project name (e.g., "creative-content", "podcast-production")
            description: Optional project description
        """
        print(f"🧠 Training project: {project}")
        
        if "projects" not in self.projects:
            self.projects["projects"] = {}
        
        if project not in self.projects["projects"]:
            self.projects["projects"][project] = {
                "description": description or f"Video project: {project}",
                "created": str(Path().cwd()),
                "video_patterns": [],
                "content_types": {},
                "organization_preferences": {}
            }
            print(f"   ✅ Created new project profile")
        else:
            print(f"   📊 Updated existing project profile")
            if description:
                self.projects["projects"][project]["description"] = description
        
        self._save_projects()
    
    def analyze_directory(self, directory: Path, project: str = None, context: str = "general", limit: int = None):
        """
        Analyze all videos in a directory with 2-minute sampling
        
        Args:
            directory: Directory to scan for videos
            project: Project name for learning
            context: Analysis context
            limit: Maximum number of videos to analyze
        """
        if not directory.exists():
            print(f"❌ Directory not found: {directory}")
            return
        
        # Find video files
        video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm'}
        video_files = [f for f in directory.iterdir() 
                      if f.is_file() and f.suffix.lower() in video_extensions]
        
        if not video_files:
            print(f"🔍 No video files found in {directory}")
            return
        
        print(f"📁 Found {len(video_files)} video files in {directory}")
        
        if limit and len(video_files) > limit:
            video_files = video_files[:limit]
            print(f"   📏 Limiting analysis to first {limit} files")
        
        # Analyze each video
        for i, video_file in enumerate(video_files, 1):
            print(f"\n[{i}/{len(video_files)}]")
            self.analyze_video(video_file, project, context)
        
        print(f"\n✅ Completed analysis of {len(video_files)} videos")
        if project:
            print(f"🧠 Project '{project}' learning updated")

def main():
    parser = argparse.ArgumentParser(description='Video Project Trainer with 2-minute intelligent sampling')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze videos in directory')
    analyze_parser.add_argument('directory', help='Directory containing videos')
    analyze_parser.add_argument('--project', help='Project name for learning')
    analyze_parser.add_argument('--context', choices=['professional', 'creative', 'general'], 
                               default='general', help='Analysis context')
    analyze_parser.add_argument('--limit', type=int, help='Maximum videos to analyze')
    
    # Train command
    train_parser = subparsers.add_parser('train', help='Create/update project profile')
    train_parser.add_argument('--project', required=True, help='Project name')
    train_parser.add_argument('--description', help='Project description')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show project training status')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    trainer = VideoProjectTrainer()
    
    if args.command == 'analyze':
        directory = Path(args.directory)
        trainer.analyze_directory(directory, args.project, args.context, args.limit)
    
    elif args.command == 'train':
        trainer.train_project(args.project, args.description)
    
    elif args.command == 'status':
        print("🧠 Video Project Trainer Status")
        print(f"📊 Projects trained: {len(trainer.projects.get('projects', {}))}")
        for project_name, project_data in trainer.projects.get('projects', {}).items():
            print(f"\n📁 Project: {project_name}")
            print(f"   📝 Description: {project_data.get('description', 'No description')}")
            print(f"   🎬 Content types: {len(project_data.get('content_types', {}))}")
            print(f"   📂 Organization patterns: {len(project_data.get('organization_preferences', {}))}")

if __name__ == "__main__":
    main()