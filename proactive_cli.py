#!/usr/bin/env python3
"""
Proactive Learning CLI for AI File Organizer
Easy command-line interface for proactive learning and folder evolution
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add project directory to path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from proactive_learning_engine import ProactiveLearningEngine

def show_status(engine: ProactiveLearningEngine):
    """Show current proactive learning status"""
    print("🤖 AI File Organizer - Proactive Learning Status")
    print("=" * 60)
    
    try:
        # Quick analysis to get current insights
        analysis = engine.analyze_current_state()
        
        print(f"📅 Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🧠 Learning Insights: {len(analysis['insights'])}")
        print(f"📁 Folder Suggestions: {len(analysis['folder_suggestions'])}")
        print(f"⚡ Auto-Actions Available: {len(analysis['auto_actions'])}")
        
        # Show top insights
        if analysis['insights']:
            print(f"\n🔍 Top Learning Insights:")
            for i, insight in enumerate(analysis['insights'][:5], 1):
                print(f"   [{i}] {insight.description}")
                print(f"       💡 {insight.suggested_action}")
                print(f"       📊 Confidence: {insight.confidence:.1%}, Files: {insight.file_count}")
        
        # Show folder suggestions
        if analysis['folder_suggestions']:
            print(f"\n📂 Folder Suggestions (ADHD Priority Order):")
            for i, suggestion in enumerate(analysis['folder_suggestions'], 1):
                print(f"   [{i}] {suggestion.folder_name}")
                print(f"       📍 Path: {suggestion.folder_path}")
                print(f"       🎯 Confidence: {suggestion.confidence:.1%}")
                print(f"       🧠 ADHD Priority: {suggestion.adhd_priority}/10")
                print(f"       🚨 Urgency: {suggestion.urgency}")
        
        if not analysis['insights'] and not analysis['folder_suggestions']:
            print("\n✅ System is well-organized! No immediate improvements needed.")
            print("💡 The system will continue learning from your usage patterns.")
        
    except Exception as e:
        print(f"❌ Error getting status: {e}")

def run_analysis(engine: ProactiveLearningEngine, implement: bool = False, interactive: bool = True):
    """Run proactive learning analysis"""
    
    print("🧠 Running Proactive Learning Analysis...")
    print("-" * 40)
    
    try:
        results = engine.run_proactive_analysis(interactive=interactive)
        
        # Show summary
        analysis = results['analysis']
        print(f"\n📊 Analysis Summary:")
        print(f"   🔍 Insights discovered: {len(analysis['insights'])}")
        print(f"   📁 Folder suggestions: {len(analysis['folder_suggestions'])}")
        print(f"   ⚡ Auto-actions identified: {len(analysis['auto_actions'])}")
        
        if 'implementation_results' in results:
            impl = results['implementation_results']
            print(f"\n🚀 Implementation Results:")
            print(f"   ✅ Folders created: {len(impl.get('implemented', []))}")
            print(f"   ⏭️  Suggestions skipped: {len(impl.get('skipped', []))}")
            print(f"   ❌ Errors encountered: {len(impl.get('errors', []))}")
            
            if impl.get('implemented'):
                print(f"\n🎉 New folders created:")
                for folder in impl['implemented']:
                    print(f"      📁 {folder}")
        
        print(f"\n✅ Proactive learning session completed at {results['timestamp']}")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")

def show_suggestions(engine: ProactiveLearningEngine):
    """Show current folder suggestions without implementing"""
    
    print("📁 Current Folder Suggestions")
    print("-" * 30)
    
    try:
        analysis = engine.analyze_current_state()
        suggestions = analysis['folder_suggestions']
        
        if not suggestions:
            print("✅ No folder suggestions at this time.")
            print("💡 System will generate suggestions as it learns from your usage patterns.")
            return
        
        for i, suggestion in enumerate(suggestions, 1):
            print(f"\n📂 [{i}] {suggestion.folder_name}")
            print(f"    📍 Proposed Path: {suggestion.folder_path}")
            print(f"    🎯 Confidence: {suggestion.confidence:.1%}")
            print(f"    🧠 ADHD Priority: {suggestion.adhd_priority}/10")
            print(f"    🚨 Urgency: {suggestion.urgency}")
            print(f"    💭 Reasoning:")
            for reason in suggestion.reasoning:
                print(f"       • {reason}")
            
            if suggestion.supporting_files:
                print(f"    📄 Supporting Files ({len(suggestion.supporting_files)}):")
                for file_info in suggestion.supporting_files[:3]:
                    print(f"       - {file_info}")
                if len(suggestion.supporting_files) > 3:
                    print(f"       ... and {len(suggestion.supporting_files) - 3} more")
        
        print(f"\n💡 To implement these suggestions, run:")
        print(f"   python proactive_cli.py learn --implement")
        
    except Exception as e:
        print(f"❌ Error getting suggestions: {e}")

def show_history(engine: ProactiveLearningEngine):
    """Show history of implemented changes"""
    
    print("📜 Proactive Learning History")
    print("-" * 30)
    
    try:
        import sqlite3
        
        with sqlite3.connect(engine.db_path) as conn:
            # Get implemented folder suggestions
            cursor = conn.execute("""
                SELECT folder_name, folder_path, confidence, adhd_priority, 
                       implementation_date, status
                FROM folder_suggestions
                WHERE status IN ('auto_implemented', 'accepted')
                ORDER BY implementation_date DESC
                LIMIT 10
            """)
            
            suggestions = cursor.fetchall()
            
            if suggestions:
                print("🏗️  Recently Created Folders:")
                for folder_name, folder_path, confidence, priority, impl_date, status in suggestions:
                    date_str = datetime.fromisoformat(impl_date).strftime('%Y-%m-%d %H:%M')
                    print(f"   📁 {folder_name}")
                    print(f"      📍 {folder_path}")
                    print(f"      🎯 {confidence:.1%} confidence, priority {priority}/10")
                    print(f"      📅 Created: {date_str} ({status})")
                    print()
            else:
                print("📝 No folders have been auto-created yet.")
            
            # Get auto-changes log
            cursor = conn.execute("""
                SELECT change_type, change_description, files_affected, 
                       implemented_date, success
                FROM auto_changes_log
                ORDER BY implemented_date DESC
                LIMIT 5
            """)
            
            changes = cursor.fetchall()
            
            if changes:
                print("⚡ Recent Auto-Changes:")
                for change_type, description, files_affected, impl_date, success in changes:
                    date_str = datetime.fromisoformat(impl_date).strftime('%Y-%m-%d %H:%M')
                    status_icon = "✅" if success else "❌"
                    print(f"   {status_icon} {description}")
                    print(f"      📊 Affected {files_affected} files on {date_str}")
                    print()
        
    except Exception as e:
        print(f"❌ Error getting history: {e}")

def main():
    """Main CLI entry point"""
    
    parser = argparse.ArgumentParser(
        description='AI File Organizer - Proactive Learning CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  proactive_cli.py status                    # Show current learning status
  proactive_cli.py learn                     # Run analysis (interactive)
  proactive_cli.py learn --implement         # Run analysis and implement suggestions
  proactive_cli.py learn --non-interactive   # Run analysis without prompts
  proactive_cli.py suggestions               # Show current suggestions only
  proactive_cli.py history                   # Show history of changes
  
ADHD-Friendly Features:
  • Clear visual feedback with icons and colors
  • Manageable suggestion batches (max 3 at once)
  • Explicit confirmation required for changes
  • Priority-based ordering for cognitive load reduction
        """
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show current proactive learning status')
    
    # Learn command
    learn_parser = subparsers.add_parser('learn', help='Run proactive learning analysis')
    learn_parser.add_argument('--implement', action='store_true', 
                             help='Implement suggestions after analysis')
    learn_parser.add_argument('--non-interactive', action='store_true',
                             help='Run without user prompts')
    
    # Suggestions command
    suggestions_parser = subparsers.add_parser('suggestions', help='Show current folder suggestions')
    
    # History command
    history_parser = subparsers.add_parser('history', help='Show history of implemented changes')
    
    # Global options
    parser.add_argument('--base-dir', help='Base directory for AI organizer')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Default to status if no command provided
    if not args.command:
        args.command = 'status'
    
    try:
        # Initialize proactive learning engine
        engine = ProactiveLearningEngine(args.base_dir)
        
        # Route to appropriate function
        if args.command == 'status':
            show_status(engine)
        elif args.command == 'learn':
            run_analysis(engine, 
                        implement=args.implement, 
                        interactive=not args.non_interactive)
        elif args.command == 'suggestions':
            show_suggestions(engine)
        elif args.command == 'history':
            show_history(engine)
        else:
            parser.print_help()
            
    except KeyboardInterrupt:
        print(f"\n👋 Proactive learning session cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()