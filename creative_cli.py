#!/usr/bin/env python3
"""
Command Line Interface for Creative AI Partner
Easy-to-use commands for analyzing creative content and tracking story elements
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from creative_ai_partner import CreativeAIPartner

def analyze_creative_file(file_path: str, show_details: bool = True):
    """Analyze a creative file for characters and story elements"""
    
    print(f"🎭 Creative Content Analysis")
    print("=" * 50)
    
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return
    
    partner = CreativeAIPartner()
    
    print(f"📄 Analyzing: {file_path.name}")
    
    try:
        analysis = partner.analyze_creative_content(file_path)
        
        print(f"\n🎯 Analysis Results:")
        print(f"   Project: {analysis.project_identified or 'Unknown/New Project'}")
        print(f"   Confidence: {analysis.analysis_confidence:.1%}")
        
        # Characters found
        if analysis.characters_found:
            print(f"\n👥 Characters Found ({len(analysis.characters_found)}):")
            for i, character in enumerate(analysis.characters_found[:10], 1):
                is_new = "✨ NEW" if character in analysis.new_characters else ""
                print(f"   {i:2d}. {character} {is_new}")
            
            if len(analysis.characters_found) > 10:
                print(f"       ... and {len(analysis.characters_found) - 10} more")
        
        # Story elements
        if analysis.story_elements:
            print(f"\n🏛️  Story Elements ({len(analysis.story_elements)}):")
            grouped_elements = {}
            
            for element in analysis.story_elements:
                if ':' in element:
                    category, name = element.split(':', 1)
                    if category not in grouped_elements:
                        grouped_elements[category] = []
                    grouped_elements[category].append(name)
                else:
                    if 'other' not in grouped_elements:
                        grouped_elements['other'] = []
                    grouped_elements['other'].append(element)
            
            for category, items in grouped_elements.items():
                print(f"   {category.title()}: {', '.join(items[:3])}")
                if len(items) > 3:
                    print(f"                ... and {len(items) - 3} more")
        
        # Themes
        if analysis.themes_detected:
            print(f"\n🎨 Themes: {', '.join(analysis.themes_detected)}")
        
        # Plot structure
        if analysis.plot_progression:
            print(f"\n📚 Plot Structure: {analysis.plot_progression}")
        
        # Character development
        if show_details and analysis.character_development:
            print(f"\n🌟 Character Development:")
            for character, development in analysis.character_development.items():
                print(f"   {character}: {development}")
        
        # Continuity issues
        if analysis.continuity_issues:
            print(f"\n⚠️  Continuity Issues ({len(analysis.continuity_issues)}):")
            for issue in analysis.continuity_issues[:5]:
                print(f"   • {issue}")
        
        # Save analysis
        success = partner.save_analysis(analysis)
        print(f"\n💾 Saved to database: {'✅' if success else '❌'}")
        
        return analysis
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return None

def show_project_overview(project_name: str):
    """Show comprehensive overview of a creative project"""
    
    print(f"🎬 Project Overview: {project_name}")
    print("=" * 60)
    
    partner = CreativeAIPartner()
    overview = partner.get_project_overview(project_name)
    
    if not overview:
        print(f"❌ Project '{project_name}' not found")
        print("💡 Use 'creative_cli.py list-projects' to see available projects")
        return
    
    project_info = overview['project_info']
    
    print(f"📊 Project Information:")
    print(f"   Name: {project_info['project_name']}")
    print(f"   Type: {project_info.get('project_type', 'Unknown')}")
    print(f"   Genre: {project_info.get('genre', 'Not specified')}")
    print(f"   Created: {project_info['created_date'][:10]}")
    print(f"   Last analyzed: {project_info['last_analyzed'][:10]}")
    
    print(f"\n📁 Files: {overview['total_files']}")
    if overview['file_analyses']:
        print("   Recent files:")
        for analysis in overview['file_analyses'][:5]:
            file_name = Path(analysis['file_path']).name
            analyzed_date = analysis['analyzed_date'][:10]
            print(f"   • {file_name} (analyzed {analyzed_date})")
    
    print(f"\n👥 Characters: {overview['total_characters']}")
    if overview['characters']:
        print("   Main characters:")
        for character in overview['characters'][:10]:
            char_name = character['name']
            mentioned_files = json.loads(character.get('mentioned_in_files', '[]'))
            print(f"   • {char_name} (appears in {len(mentioned_files)} files)")
        
        if len(overview['characters']) > 10:
            print(f"   ... and {len(overview['characters']) - 10} more characters")
    
    # Show themes if available
    themes = json.loads(project_info.get('themes', '[]'))
    if themes:
        print(f"\n🎨 Themes: {', '.join(themes)}")
    
    return overview

def find_character(character_name: str):
    """Find all appearances of a specific character"""
    
    print(f"👤 Character Search: {character_name}")
    print("=" * 50)
    
    partner = CreativeAIPartner()
    appearances = partner.find_character_appearances(character_name)
    
    if not appearances:
        print(f"❌ Character '{character_name}' not found in any analyzed files")
        return
    
    print(f"📚 Found {len(appearances)} files where '{character_name}' appears:")
    
    for i, appearance in enumerate(appearances, 1):
        file_name = Path(appearance['file_path']).name
        project = appearance['project_identified'] or 'Unknown Project'
        analyzed_date = appearance['analyzed_date'][:10]
        
        print(f"\n📄 {i}. {file_name}")
        print(f"   🎬 Project: {project}")
        print(f"   📅 Analyzed: {analyzed_date}")
        
        # Show other characters in the same file
        other_characters = json.loads(appearance['characters_found'])
        other_characters = [c for c in other_characters if c != character_name]
        if other_characters:
            print(f"   👥 Also appears with: {', '.join(other_characters[:5])}")
            if len(other_characters) > 5:
                print(f"                        ... and {len(other_characters) - 5} more")
    
    return appearances

def list_projects():
    """List all creative projects"""
    
    print(f"🎬 Creative Projects")
    print("=" * 40)
    
    partner = CreativeAIPartner()
    
    with partner._get_db_connection() as conn:
        cursor = conn.execute("""
            SELECT project_name, project_type, created_date, last_analyzed,
                   (SELECT COUNT(*) FROM file_analysis WHERE project_identified = cp.project_name) as file_count
            FROM creative_projects cp
            ORDER BY last_analyzed DESC
        """)
        
        projects = cursor.fetchall()
    
    if not projects:
        print("❌ No creative projects found")
        print("💡 Analyze some creative files first using: creative_cli.py analyze file.txt")
        return
    
    print(f"Found {len(projects)} projects:")
    
    for i, (name, proj_type, created, analyzed, file_count) in enumerate(projects, 1):
        print(f"\n{i}. {name}")
        print(f"   Type: {proj_type or 'Unknown'}")
        print(f"   Files: {file_count}")
        print(f"   Created: {created[:10]}")
        print(f"   Last updated: {analyzed[:10]}")

def list_characters(project_name: str = None, limit: int = 20):
    """List characters, optionally filtered by project"""
    
    if project_name:
        print(f"👥 Characters in '{project_name}'")
    else:
        print(f"👥 All Characters")
    
    print("=" * 50)
    
    partner = CreativeAIPartner()
    
    with partner._get_db_connection() as conn:
        if project_name:
            # Get characters from specific project
            cursor = conn.execute("""
                SELECT DISTINCT c.name, c.first_appearance, c.mentioned_in_files
                FROM characters c
                JOIN file_analysis fa ON json_extract(fa.characters_found, '$') LIKE '%' || c.name || '%'
                WHERE fa.project_identified = ?
                ORDER BY c.name
            """, (project_name,))
        else:
            # Get all characters
            cursor = conn.execute("""
                SELECT name, first_appearance, mentioned_in_files
                FROM characters
                ORDER BY json_array_length(mentioned_in_files) DESC, name
                LIMIT ?
            """, (limit,))
        
        characters = cursor.fetchall()
    
    if not characters:
        if project_name:
            print(f"❌ No characters found for project '{project_name}'")
        else:
            print("❌ No characters found")
        return
    
    print(f"Found {len(characters)} characters:")
    
    for i, (name, first_appearance, mentioned_files) in enumerate(characters, 1):
        files_list = json.loads(mentioned_files) if mentioned_files else []
        first_file = Path(first_appearance).name if first_appearance else 'Unknown'
        
        print(f"\n{i:2d}. {name}")
        print(f"    First seen in: {first_file}")
        print(f"    Appears in {len(files_list)} files")

def analyze_directory(directory: str, recursive: bool = True, file_pattern: str = "*"):
    """Analyze all creative files in a directory"""
    
    print(f"📁 Directory Creative Analysis")
    print("=" * 60)
    
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"❌ Directory not found: {directory}")
        return
    
    partner = CreativeAIPartner()
    
    print(f"📂 Directory: {dir_path}")
    print(f"🔍 Pattern: {file_pattern}")
    print(f"📊 Recursive: {recursive}")
    
    # Find files to analyze
    if recursive:
        search_pattern = f"**/{file_pattern}"
    else:
        search_pattern = file_pattern
    
    all_files = [f for f in dir_path.glob(search_pattern) 
                if f.is_file() and not f.name.startswith('.')]
    
    # Filter to likely creative content
    creative_extensions = {'.txt', '.md', '.rtf', '.pdf', '.docx', '.doc', '.fountain', '.fdx'}
    creative_files = [f for f in all_files if f.suffix.lower() in creative_extensions]
    
    if not creative_files:
        print(f"❌ No creative files found")
        return
    
    print(f"\n🎯 Found {len(creative_files)} creative files to analyze")
    
    successful = 0
    failed = 0
    total_characters = 0
    projects_found = set()
    
    for i, file_path in enumerate(creative_files, 1):
        print(f"\n📄 [{i}/{len(creative_files)}] {file_path.name}")
        
        try:
            analysis = partner.analyze_creative_content(file_path)
            success = partner.save_analysis(analysis)
            
            if success:
                successful += 1
                total_characters += len(analysis.characters_found)
                
                if analysis.project_identified:
                    projects_found.add(analysis.project_identified)
                
                print(f"   ✅ Project: {analysis.project_identified or 'Unknown'}")
                print(f"      Characters: {len(analysis.characters_found)}")
                print(f"      Confidence: {analysis.analysis_confidence:.0%}")
            else:
                failed += 1
                print(f"   ❌ Failed to save analysis")
        
        except Exception as e:
            failed += 1
            print(f"   ❌ Error: {str(e)[:50]}...")
    
    print(f"\n📊 Directory Analysis Summary:")
    print(f"   ✅ Successful: {successful}")
    print(f"   ❌ Failed: {failed}")
    print(f"   👥 Total characters found: {total_characters}")
    print(f"   🎬 Projects identified: {len(projects_found)}")
    
    if projects_found:
        print(f"      Projects: {', '.join(projects_found)}")

def main():
    """Command line interface for creative AI partner"""
    
    parser = argparse.ArgumentParser(
        description="AI File Organizer - Creative AI Partner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze single creative file
  creative_cli.py analyze script.pdf
  creative_cli.py analyze treatment.docx --details
  
  # Analyze directory
  creative_cli.py directory /Users/user/Scripts
  creative_cli.py directory /Users/user/Creative --pattern "*.txt"
  
  # View project information
  creative_cli.py project "Stranger Things"
  creative_cli.py list-projects
  
  # Find characters
  creative_cli.py character "Eleven"
  creative_cli.py characters --project "Creative Project"
  creative_cli.py characters --limit 10
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Analyze single file
    analyze_parser = subparsers.add_parser('analyze', help='Analyze a creative file')
    analyze_parser.add_argument('file_path', help='Path to creative file')
    analyze_parser.add_argument('--details', action='store_true', help='Show detailed analysis')
    
    # Analyze directory
    dir_parser = subparsers.add_parser('directory', help='Analyze all creative files in directory')
    dir_parser.add_argument('directory', help='Directory to analyze')
    dir_parser.add_argument('--pattern', default='*', help='File pattern to match (default: *)')
    dir_parser.add_argument('--no-recursive', action='store_true', help="Don't analyze subdirectories")
    
    # Project overview
    project_parser = subparsers.add_parser('project', help='Show project overview')
    project_parser.add_argument('project_name', help='Name of project')
    
    # List projects
    subparsers.add_parser('list-projects', help='List all creative projects')
    
    # Find character
    char_parser = subparsers.add_parser('character', help='Find character appearances')
    char_parser.add_argument('character_name', help='Character name to search for')
    
    # List characters
    chars_parser = subparsers.add_parser('characters', help='List characters')
    chars_parser.add_argument('--project', help='Filter by project name')
    chars_parser.add_argument('--limit', type=int, default=20, help='Maximum results (default: 20)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("🎭 AI File Organizer - Creative AI Partner")
    print("=" * 60)
    
    if args.command == 'analyze':
        analyze_creative_file(args.file_path, args.details)
        
    elif args.command == 'directory':
        analyze_directory(args.directory, not args.no_recursive, args.pattern)
        
    elif args.command == 'project':
        show_project_overview(args.project_name)
        
    elif args.command == 'list-projects':
        list_projects()
        
    elif args.command == 'character':
        find_character(args.character_name)
        
    elif args.command == 'characters':
        list_characters(args.project, args.limit)

if __name__ == "__main__":
    main()