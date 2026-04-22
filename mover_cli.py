#!/usr/bin/env python3
"""
Command Line Interface for Safe File Moving
Easy-to-use commands for safely moving and organizing files
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from safe_file_mover import SafeFileMover, MoveStrategy

def move_files(source_pattern: str, target_dir: str, strategy: str = "rename", 
               dry_run: bool = True, recursive: bool = False):
    """Move files matching a pattern to target directory"""
    
    print(f"📁 Safe File Moving")
    print("=" * 50)
    
    # Parse strategy
    strategy_map = {
        'skip': MoveStrategy.SKIP,
        'rename': MoveStrategy.RENAME, 
        'replace-same': MoveStrategy.REPLACE_IF_SAME,
        'replace-newer': MoveStrategy.REPLACE_IF_NEWER,
        'backup': MoveStrategy.BACKUP_AND_REPLACE,
        'ask': MoveStrategy.ASK_USER
    }
    
    move_strategy = strategy_map.get(strategy.lower(), MoveStrategy.RENAME)
    
    # Find source files
    source_path = Path(source_pattern)
    
    if source_path.is_file():
        # Single file
        source_files = [source_path]
    elif source_path.is_dir():
        # Directory - find all supported files
        if recursive:
            pattern = "**/*"
        else:
            pattern = "*"
        
        source_files = [f for f in source_path.glob(pattern) 
                       if f.is_file() and not f.name.startswith('.')]
    else:
        # Pattern matching
        parent_dir = source_path.parent
        pattern = source_path.name
        
        if recursive:
            pattern = f"**/{pattern}"
        
        source_files = list(parent_dir.glob(pattern))
        source_files = [f for f in source_files if f.is_file()]
    
    if not source_files:
        print(f"❌ No files found matching: {source_pattern}")
        return
    
    print(f"🔍 Found {len(source_files)} files to move")
    print(f"📂 Target directory: {target_dir}")
    print(f"⚙️  Strategy: {move_strategy.value}")
    print(f"🏃 Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    
    # Prepare moves
    target_path = Path(target_dir)
    moves = []
    
    for source_file in source_files:
        target_file = target_path / source_file.name
        moves.append((source_file, target_file))
    
    # Execute moves
    mover = SafeFileMover()
    result = mover.move_multiple_files(
        moves, 
        strategy=move_strategy,
        dry_run=dry_run,
        interaction_mode="smart"
    )
    
    # Show summary
    if dry_run:
        print(f"\n💡 This was a dry run. Use --live to actually move files.")
    
    return result

def list_recent_moves(days: int = 7):
    """List recent file move operations"""
    
    print(f"📊 Recent File Moves - Last {days} Days")
    print("=" * 60)
    
    mover = SafeFileMover()
    moves = mover.list_recent_moves(days)
    
    if not moves:
        print("❌ No recent moves found")
        return
    
    print(f"Found {len(moves)} recent moves:")
    print()
    
    for move in moves:
        status_icon = "✅" if move['success'] else "❌"
        move_date = move['move_date'][:19].replace('T', ' ')
        
        source_name = Path(move['source_path']).name
        final_name = Path(move['final_path']).name
        
        print(f"{status_icon} {move_date}")
        print(f"   {source_name} → {final_name}")
        
        if move['backup_path']:
            backup_name = Path(move['backup_path']).name
            print(f"   💾 Backup: {backup_name}")
        
        if not move['success'] and move['error_message']:
            print(f"   ❌ Error: {move['error_message']}")
        
        print()

def undo_moves(session_id: str, confirm: bool = False):
    """Undo moves from a specific session"""
    
    print(f"🔄 Undo File Moves")
    print("=" * 40)
    
    if not confirm:
        print(f"⚠️  This will attempt to undo all moves from session: {session_id}")
        print(f"⚠️  This operation cannot be undone!")
        print(f"Use --confirm to proceed.")
        return
    
    mover = SafeFileMover()
    success = mover.undo_recent_moves(session_id, confirm=True)
    
    if success:
        print(f"✅ Undo operation completed")
    else:
        print(f"❌ Undo operation failed or no moves to undo")

def show_strategies():
    """Show available move strategies"""
    
    print("⚙️  Available Move Strategies")
    print("=" * 50)
    print()
    print("🔀 skip        - Don't move if target file exists")
    print("📝 rename      - Add _2, _3 suffix if target exists (RECOMMENDED)")
    print("🔄 replace-same - Replace if files have identical content")  
    print("⏰ replace-newer - Replace if source file is newer")
    print("💾 backup      - Backup existing file then replace")
    print("❓ ask         - Ask user what to do (falls back to rename in CLI)")
    print()
    print("💡 For ADHD-friendly organization, 'rename' is recommended")
    print("   This ensures no files are ever lost or overwritten")

def show_examples():
    """Show usage examples"""
    
    print("📚 Safe File Mover - Usage Examples")
    print("=" * 60)
    print()
    print("📁 MOVE SINGLE FILE:")
    print("   mover_cli.py move document.pdf /Users/user/Documents/Organized --live")
    print()
    print("📂 MOVE ALL FILES FROM DIRECTORY:")
    print("   mover_cli.py move /Users/user/Downloads /Users/user/Documents/Sorted")
    print("   mover_cli.py move /Users/user/Desktop /Users/user/Documents/Sorted --recursive")
    print()
    print("🔍 MOVE FILES BY PATTERN:")
    print("   mover_cli.py move '/Users/user/Downloads/*.pdf' /Users/user/Documents/PDFs")
    print("   mover_cli.py move '/Users/user/Downloads/Contract*' /Users/user/Contracts")
    print()
    print("⚙️  DIFFERENT STRATEGIES:")
    print("   mover_cli.py move file.pdf /target --strategy skip")
    print("   mover_cli.py move file.pdf /target --strategy replace-same")
    print("   mover_cli.py move file.pdf /target --strategy backup")
    print()
    print("📊 VIEW RECENT MOVES:")
    print("   mover_cli.py history --days 7")
    print("   mover_cli.py history --days 30")
    print()
    print("🔄 UNDO MOVES:")
    print("   mover_cli.py undo move_20250822_160000_123 --confirm")
    print()
    print("💡 SAFETY TIPS:")
    print("   • Always test with dry run first (default)")
    print("   • Use 'rename' strategy to avoid data loss")
    print("   • Check history before undoing moves")
    print("   • Backups are stored in 99_BACKUP_ARCHIVE/file_moves/")

def main():
    """Command line interface for safe file moving"""
    
    parser = argparse.ArgumentParser(
        description="AI File Organizer - Safe File Moving",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Move files command
    move_parser = subparsers.add_parser('move', help='Move files safely')
    move_parser.add_argument('source', help='Source file, directory, or pattern')
    move_parser.add_argument('target', help='Target directory')
    move_parser.add_argument('--strategy', choices=['skip', 'rename', 'replace-same', 'replace-newer', 'backup', 'ask'],
                           default='rename', help='Collision handling strategy (default: rename)')
    move_parser.add_argument('--live', action='store_true', help='Actually move files (default is dry-run)')
    move_parser.add_argument('--recursive', action='store_true', help='Include subdirectories')
    
    # History command
    history_parser = subparsers.add_parser('history', help='Show recent file moves')
    history_parser.add_argument('--days', type=int, default=7, help='Number of days to show (default: 7)')
    
    # Undo command
    undo_parser = subparsers.add_parser('undo', help='Undo moves from a session')
    undo_parser.add_argument('session_id', help='Session ID to undo')
    undo_parser.add_argument('--confirm', action='store_true', help='Confirm the undo operation')
    
    # Info commands
    subparsers.add_parser('strategies', help='Show available move strategies')
    subparsers.add_parser('examples', help='Show usage examples')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("🔒 AI File Organizer - Safe File Moving")
    print("=" * 60)
    
    if args.command == 'move':
        move_files(args.source, args.target, args.strategy, not args.live, args.recursive)
        
    elif args.command == 'history':
        list_recent_moves(args.days)
        
    elif args.command == 'undo':
        undo_moves(args.session_id, args.confirm)
        
    elif args.command == 'strategies':
        show_strategies()
        
    elif args.command == 'examples':
        show_examples()

if __name__ == "__main__":
    main()