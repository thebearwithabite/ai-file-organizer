#!/usr/bin/env python3
"""
Command Line Interface for Audio AI Analysis
Easy-to-use commands for analyzing and organizing audio files with full AudioAI integration
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from audio_ai_analyzer import AudioAIAnalyzer

def analyze_audio(file_path: str, transcribe: bool = False, show_details: bool = False):
    """Analyze a single audio file with full AudioAI capabilities"""
    
    print("🎵 Audio AI Analysis")
    print("=" * 50)
    
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"❌ Audio file not found: {file_path}")
        return
    
    analyzer = AudioAIAnalyzer()
    
    print(f"📄 Analyzing: {file_path.name}")
    print(f"📁 Size: {file_path.stat().st_size / (1024*1024):.1f} MB")
    
    try:
        # Run comprehensive analysis
        analysis = analyzer.analyze_audio_file(file_path)
        
        # Basic results
        print(f"\n🎯 Analysis Results:")
        print(f"   Content Type: {analysis.content_type}")
        print(f"   Confidence: {analysis.confidence_score:.2f}")
        print(f"   Duration: {analysis.duration_seconds:.1f} seconds")
        print(f"   Quality: {analysis.audio_quality}")
        print(f"   Importance: {analysis.importance_score:.2f}")
        
        # Technical details
        if show_details:
            print(f"\n🔧 Technical Details:")
            print(f"   Sample Rate: {analysis.sample_rate} Hz")
            print(f"   Channels: {analysis.channels}")
            print(f"   Codec: {analysis.codec}")
            print(f"   Dynamic Range: {analysis.dynamic_range:.3f}")
            print(f"   Noise Level: {analysis.noise_level:.3f}")
        
        # Speech analysis
        if analysis.has_speech:
            print(f"\n🗣️  Speech Analysis:")
            print(f"   Speech Detected: Yes")
            print(f"   Speech Segments: {len(analysis.speech_segments)}")
            print(f"   Estimated Speakers: {analysis.estimated_speakers}")
            print(f"   Speech Clarity: {analysis.speech_clarity:.2f}")
            
            if transcribe:
                print(f"\n📝 Transcription:")
                transcript = analyzer.transcribe_audio(analysis)
                if transcript:
                    print(f"   {transcript}")
                else:
                    print(f"   ⚠️  Transcription failed or not available")
        
        # Music analysis
        if analysis.has_music:
            print(f"\n🎵 Music Analysis:")
            print(f"   Music Detected: Yes")
            if analysis.tempo:
                print(f"   Tempo: {analysis.tempo:.1f} BPM")
            if analysis.key:
                print(f"   Key: {analysis.key}")
            print(f"   Energy: {analysis.energy:.2f}")
            print(f"   Danceability: {analysis.danceability:.2f}")
        
        # Creative tags
        if analysis.creative_tags:
            print(f"\n🏷️  Creative Tags:")
            for tag in analysis.creative_tags:
                print(f"   • {tag}")
        
        # Project context
        if analysis.project_context and analysis.project_context != "unassigned":
            print(f"\n🎬 Project Context: {analysis.project_context}")
        
        # Organization suggestion
        print(f"\n📋 Organization Suggestion:")
        if analysis.content_type == 'interview':
            print(f"   → Entertainment_Industry/Interviews/")
        elif analysis.content_type == 'voice_sample':
            print(f"   → Entertainment_Industry/Voice_Samples/")
        elif analysis.content_type == 'scene_audio':
            print(f"   → Entertainment_Industry/Scene_Work/")
        elif analysis.content_type == 'music':
            print(f"   → Creative_Projects/Music/")
        else:
            print(f"   → Audio_Files/{analysis.content_type.title()}/")
        
        # Save analysis
        success = analyzer.save_analysis(analysis)
        print(f"\n💾 Analysis saved: {'✅' if success else '❌'}")
        
        return analysis
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return None

def analyze_directory(directory: str, recursive: bool = True, transcribe: bool = False):
    """Analyze all audio files in a directory"""
    
    print("📁 Directory Audio Analysis")
    print("=" * 60)
    
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"❌ Directory not found: {directory}")
        return
    
    analyzer = AudioAIAnalyzer()
    
    print(f"📂 Directory: {dir_path}")
    print(f"🔍 Recursive: {recursive}")
    
    # Find audio files
    audio_extensions = {'.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma', '.aiff'}
    
    if recursive:
        audio_files = []
        for ext in audio_extensions:
            audio_files.extend(dir_path.rglob(f"*{ext}"))
    else:
        audio_files = []
        for ext in audio_extensions:
            audio_files.extend(dir_path.glob(f"*{ext}"))
    
    if not audio_files:
        print(f"❌ No audio files found")
        return
    
    print(f"\n🎯 Found {len(audio_files)} audio files to analyze")
    
    successful = 0
    failed = 0
    content_types = {}
    total_duration = 0
    
    for i, audio_file in enumerate(audio_files, 1):
        print(f"\n📄 [{i}/{len(audio_files)}] {audio_file.name}")
        
        try:
            analysis = analyzer.analyze_audio_file(audio_file)
            
            # Try transcription if requested
            if transcribe and analysis.has_speech:
                analyzer.transcribe_audio(analysis)
            
            # Save analysis
            success = analyzer.save_analysis(analysis)
            
            if success:
                successful += 1
                content_types[analysis.content_type] = content_types.get(analysis.content_type, 0) + 1
                total_duration += analysis.duration_seconds
                
                print(f"   ✅ {analysis.content_type} ({analysis.duration_seconds:.1f}s)")
                if analysis.creative_tags:
                    print(f"      Tags: {', '.join(analysis.creative_tags[:3])}")
            else:
                failed += 1
                print(f"   ❌ Failed to save analysis")
        
        except Exception as e:
            failed += 1
            print(f"   ❌ Error: {str(e)[:50]}...")
    
    # Summary
    print(f"\n📊 Analysis Summary:")
    print(f"   ✅ Successful: {successful}")
    print(f"   ❌ Failed: {failed}")
    print(f"   ⏱️  Total Duration: {total_duration/3600:.1f} hours")
    
    if content_types:
        print(f"\n🎭 Content Types Found:")
        for content_type, count in sorted(content_types.items(), key=lambda x: x[1], reverse=True):
            print(f"   {content_type}: {count} files")

def show_audio_stats():
    """Show statistics from all analyzed audio files"""
    
    print("📊 Audio Analysis Statistics")
    print("=" * 50)
    
    analyzer = AudioAIAnalyzer()
    
    try:
        import sqlite3
        
        with sqlite3.connect(analyzer.db_path) as conn:
            # Total files analyzed
            cursor = conn.execute("SELECT COUNT(*) FROM audio_analysis")
            total_files = cursor.fetchone()[0]
            
            if total_files == 0:
                print("❌ No audio files analyzed yet")
                print("💡 Run: audio_cli.py analyze <file> or audio_cli.py directory <path>")
                return
            
            print(f"📈 Total files analyzed: {total_files}")
            
            # Content types
            cursor = conn.execute("""
                SELECT content_type, COUNT(*) as count
                FROM audio_analysis
                GROUP BY content_type
                ORDER BY count DESC
            """)
            content_types = cursor.fetchall()
            
            print(f"\n🎭 Content Types:")
            for content_type, count in content_types:
                percentage = (count / total_files) * 100
                print(f"   {content_type}: {count} ({percentage:.1f}%)")
            
            # Quality distribution
            cursor = conn.execute("""
                SELECT audio_quality, COUNT(*) as count
                FROM audio_analysis
                GROUP BY audio_quality
                ORDER BY count DESC
            """)
            quality_dist = cursor.fetchall()
            
            print(f"\n🎯 Quality Distribution:")
            for quality, count in quality_dist:
                percentage = (count / total_files) * 100
                print(f"   {quality}: {count} ({percentage:.1f}%)")
            
            # Duration stats
            cursor = conn.execute("""
                SELECT 
                    AVG(duration_seconds) as avg_duration,
                    MIN(duration_seconds) as min_duration,
                    MAX(duration_seconds) as max_duration,
                    SUM(duration_seconds) as total_duration
                FROM audio_analysis
            """)
            duration_stats = cursor.fetchone()
            
            print(f"\n⏱️  Duration Statistics:")
            print(f"   Average: {duration_stats[0]/60:.1f} minutes")
            print(f"   Shortest: {duration_stats[1]:.1f} seconds")
            print(f"   Longest: {duration_stats[2]/60:.1f} minutes")
            print(f"   Total: {duration_stats[3]/3600:.1f} hours")
            
            # Project distribution
            cursor = conn.execute("""
                SELECT project_context, COUNT(*) as count
                FROM audio_analysis
                WHERE project_context IS NOT NULL AND project_context != 'unassigned'
                GROUP BY project_context
                ORDER BY count DESC
            """)
            projects = cursor.fetchall()
            
            if projects:
                print(f"\n🎬 Project Distribution:")
                for project, count in projects:
                    print(f"   {project}: {count} files")
            
            # Recent activity
            cursor = conn.execute("""
                SELECT COUNT(*) FROM audio_analysis 
                WHERE analyzed_date > datetime('now', '-7 days')
            """)
            recent_count = cursor.fetchone()[0]
            
            print(f"\n📅 Recent Activity:")
            print(f"   Files analyzed in last 7 days: {recent_count}")
            
    except Exception as e:
        print(f"❌ Error retrieving statistics: {e}")

def search_audio(query: str, content_type: str = None, limit: int = 10):
    """Search analyzed audio files"""
    
    print(f"🔍 Audio Search: '{query}'")
    print("=" * 50)
    
    analyzer = AudioAIAnalyzer()
    
    try:
        import sqlite3
        
        with sqlite3.connect(analyzer.db_path) as conn:
            # Build search query
            sql_query = """
                SELECT file_path, file_name, content_type, duration_seconds, 
                       creative_tags, transcription, confidence_score
                FROM audio_analysis
                WHERE (file_name LIKE ? OR transcription LIKE ? OR creative_tags LIKE ?)
            """
            params = [f"%{query}%", f"%{query}%", f"%{query}%"]
            
            if content_type:
                sql_query += " AND content_type = ?"
                params.append(content_type)
            
            sql_query += " ORDER BY confidence_score DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(sql_query, params)
            results = cursor.fetchall()
            
            if not results:
                print(f"❌ No audio files found matching '{query}'")
                return
            
            print(f"📚 Found {len(results)} matching audio files:")
            
            for i, result in enumerate(results, 1):
                file_path, file_name, content_type, duration, tags_json, transcript, confidence = result
                
                print(f"\n   {i}. {file_name}")
                print(f"      Type: {content_type}")
                print(f"      Duration: {duration/60:.1f} minutes")
                print(f"      Confidence: {confidence:.2f}")
                
                if tags_json:
                    try:
                        tags = json.loads(tags_json)
                        if tags:
                            print(f"      Tags: {', '.join(tags[:3])}")
                    except:
                        pass
                
                if transcript and query.lower() in transcript.lower():
                    # Show context around the match
                    transcript_lower = transcript.lower()
                    query_lower = query.lower()
                    match_pos = transcript_lower.find(query_lower)
                    if match_pos != -1:
                        start = max(0, match_pos - 50)
                        end = min(len(transcript), match_pos + len(query) + 50)
                        context = transcript[start:end]
                        print(f"      Context: ...{context}...")
                
                print(f"      Path: {Path(file_path).parent}")
            
    except Exception as e:
        print(f"❌ Search failed: {e}")

def main():
    """Command line interface for Audio AI analysis"""
    
    parser = argparse.ArgumentParser(
        description="AI File Organizer - Audio AI Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze single audio file
  audio_cli.py analyze interview.mp3
  audio_cli.py analyze scene_audio.wav --transcribe --details
  
  # Analyze directory
  audio_cli.py directory /Users/user/Audio
  audio_cli.py directory /Users/user/Downloads --transcribe
  
  # Search analyzed audio
  audio_cli.py search "consciousness"
  audio_cli.py search "interview" --type interview
  
  # View statistics
  audio_cli.py stats
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Analyze single file
    analyze_parser = subparsers.add_parser('analyze', help='Analyze a single audio file')
    analyze_parser.add_argument('file_path', help='Path to audio file')
    analyze_parser.add_argument('--transcribe', action='store_true', help='Include speech transcription')
    analyze_parser.add_argument('--details', action='store_true', help='Show technical details')
    
    # Analyze directory
    dir_parser = subparsers.add_parser('directory', help='Analyze all audio files in directory')
    dir_parser.add_argument('directory', help='Directory to analyze')
    dir_parser.add_argument('--no-recursive', action='store_true', help="Don't analyze subdirectories")
    dir_parser.add_argument('--transcribe', action='store_true', help='Include speech transcription')
    
    # Search audio files
    search_parser = subparsers.add_parser('search', help='Search analyzed audio files')
    search_parser.add_argument('query', help='Search term')
    search_parser.add_argument('--type', help='Filter by content type')
    search_parser.add_argument('--limit', type=int, default=10, help='Maximum results (default: 10)')
    
    # Statistics
    subparsers.add_parser('stats', help='Show audio analysis statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("🎵 AI File Organizer - Audio AI Analysis")
    print("=" * 60)
    
    if args.command == 'analyze':
        analyze_audio(args.file_path, args.transcribe, args.details)
        
    elif args.command == 'directory':
        analyze_directory(args.directory, not args.no_recursive, args.transcribe)
        
    elif args.command == 'search':
        search_audio(args.query, args.type, args.limit)
        
    elif args.command == 'stats':
        show_audio_stats()

if __name__ == "__main__":
    main()