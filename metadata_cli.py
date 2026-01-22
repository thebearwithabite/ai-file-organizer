#!/usr/bin/env python3
"""
Command Line Interface for Metadata Generation
Easy-to-use commands for generating comprehensive file metadata spreadsheets
"""

import sys
import argparse
from pathlib import Path

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from metadata_generator import MetadataGenerator

def analyze_directory(directory: str, output_format: str = 'xlsx', recursive: bool = True):
    """Analyze all files in a directory and generate metadata"""
    
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"❌ Directory not found: {directory}")
        return
    
    print(f"📁 Analyzing directory: {dir_path}")
    print("=" * 60)
    
    generator = MetadataGenerator()
    
    # Find files to analyze
    if recursive:
        file_patterns = ['**/*']
    else:
        file_patterns = ['*']
    
    all_files = []
    for pattern in file_patterns:
        all_files.extend(dir_path.glob(pattern))
    
    # Filter to actual files (not directories)
    files_to_analyze = [f for f in all_files if f.is_file() and not f.name.startswith('.')]
    
    print(f"🔍 Found {len(files_to_analyze)} files to analyze")
    
    if not files_to_analyze:
        print("❌ No files found to analyze")
        return
    
    # Analyze each file
    successful = 0
    failed = 0
    
    for i, file_path in enumerate(files_to_analyze, 1):
        print(f"\n📄 [{i}/{len(files_to_analyze)}] {file_path.name}")
        
        try:
            metadata = generator.analyze_file_comprehensive(file_path)
            success = generator.save_file_metadata(metadata)
            
            if success:
                successful += 1
                print(f"   ✅ Analyzed - Category: {metadata.get('ai_category', 'Unknown')} "
                      f"({metadata.get('confidence_score', 0)*100:.1f}%)")
            else:
                failed += 1
                print(f"   ❌ Failed to save metadata")
                
        except Exception as e:
            failed += 1
            print(f"   ❌ Error: {e}")
    
    print(f"\n📊 Analysis Complete:")
    print(f"   ✅ Successful: {successful}")
    print(f"   ❌ Failed: {failed}")
    
    # Generate spreadsheet
    if successful > 0:
        print(f"\n📋 Generating {output_format.upper()} spreadsheet...")
        output_path, df = generator.generate_comprehensive_spreadsheet(output_format)
        
        if output_path:
            print(f"✅ Spreadsheet saved: {Path(output_path).name}")
            return output_path
    
    return None

def analyze_single_file(file_path: str, show_details: bool = True):
    """Analyze a single file and show detailed results"""
    
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return
    
    print(f"📄 Analyzing: {file_path.name}")
    print("=" * 60)
    
    generator = MetadataGenerator()
    
    try:
        metadata = generator.analyze_file_comprehensive(file_path)
        
        if show_details:
            print(f"📊 Analysis Results:")
            print(f"   File Type: {metadata.get('file_type', 'Unknown')}")
            print(f"   Size: {metadata.get('file_size', 0)/1024:.1f} KB")
            print(f"   Modified: {metadata.get('modified_date', 'Unknown')}")
            print(f"   AI Category: {metadata.get('ai_category', 'Unknown')}")
            print(f"   Confidence: {metadata.get('confidence_score', 0)*100:.1f}%")
            print(f"   Word Count: {metadata.get('word_count', 0):,}")
            
            # Show content preview
            preview = metadata.get('content_preview', '')
            if preview:
                print(f"   Content Preview: {preview[:200]}...")
            
            # Show people/entities
            people = metadata.get('people_mentioned', '[]')
            if people != '[]':
                print(f"   People Mentioned: {people}")
            
            # Show tags
            tags = metadata.get('auto_tags', '[]')
            if tags != '[]':
                print(f"   Auto Tags: {tags}")
        
        # Save to database
        success = generator.save_file_metadata(metadata)
        print(f"\n💾 Saved to database: {'✅' if success else '❌'}")
        
        return metadata
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return None

def generate_report_only():
    """Generate spreadsheet from existing database without analyzing new files"""
    
    print("📋 Generating Report from Existing Data")
    print("=" * 50)
    
    generator = MetadataGenerator()
    
    try:
        output_path, df = generator.generate_comprehensive_spreadsheet()
        
        if output_path and df is not None:
            print(f"✅ Report generated: {Path(output_path).name}")
            print(f"📈 Summary:")
            print(f"   Total files: {len(df)}")
            print(f"   File types: {df['file_type'].nunique()}")
            print(f"   Categories: {df['ai_category'].nunique()}")
            
            # Show top categories
            if not df.empty:
                top_categories = df['ai_category'].value_counts().head(5)
                print(f"   Top categories:")
                for category, count in top_categories.items():
                    print(f"     {category}: {count} files")
            
            return output_path
        else:
            print("❌ No data found. Analyze some files first.")
            return None
            
    except Exception as e:
        print(f"❌ Report generation failed: {e}")
        return None

def show_statistics():
    """Show statistics about analyzed files"""
    
    print("📊 File Analysis Statistics")
    print("=" * 40)
    
    generator = MetadataGenerator()
    
    try:
        import sqlite3
        import pandas as pd
        
        with sqlite3.connect(generator.db_path) as conn:
            df = pd.read_sql_query("SELECT * FROM file_metadata", conn)
        
        if df.empty:
            print("❌ No analyzed files found.")
            return
        
        print(f"📁 Total files analyzed: {len(df)}")
        print(f"💾 Total size: {df['file_size'].sum() / (1024**3):.2f} GB")
        
        print(f"\n📊 File Types:")
        file_type_counts = df['file_type'].value_counts()
        for file_type, count in file_type_counts.head(10).items():
            print(f"   {file_type}: {count}")
        
        print(f"\n🎯 Categories:")
        category_counts = df['ai_category'].value_counts()
        for category, count in category_counts.head(10).items():
            print(f"   {category}: {count}")
        
        print(f"\n📈 Confidence Distribution:")
        high_conf = len(df[df['confidence_score'] >= 0.8])
        med_conf = len(df[(df['confidence_score'] >= 0.5) & (df['confidence_score'] < 0.8)])
        low_conf = len(df[df['confidence_score'] < 0.5])
        
        print(f"   High confidence (80%+): {high_conf}")
        print(f"   Medium confidence (50-80%): {med_conf}")
        print(f"   Low confidence (<50%): {low_conf}")
        
    except Exception as e:
        print(f"❌ Error loading statistics: {e}")

def main():
    """Command line interface for metadata generation"""
    
    parser = argparse.ArgumentParser(
        description="AI File Organizer - Metadata Generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  metadata_cli.py analyze /Users/user/Documents --format xlsx
  metadata_cli.py file /path/to/document.pdf --details
  metadata_cli.py report
  metadata_cli.py stats
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Analyze directory command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze all files in a directory')
    analyze_parser.add_argument('directory', help='Directory to analyze')
    analyze_parser.add_argument('--format', choices=['xlsx', 'csv'], default='xlsx', 
                               help='Output format (default: xlsx)')
    analyze_parser.add_argument('--no-recursive', action='store_true', 
                               help='Don\'t analyze subdirectories')
    
    # Single file command
    file_parser = subparsers.add_parser('file', help='Analyze a single file')
    file_parser.add_argument('file_path', help='Path to file to analyze')
    file_parser.add_argument('--details', action='store_true', 
                            help='Show detailed analysis results')
    
    # Report command
    subparsers.add_parser('report', help='Generate spreadsheet from existing data')
    
    # Statistics command
    subparsers.add_parser('stats', help='Show analysis statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("📊 AI File Organizer - Metadata Generation")
    print("=" * 60)
    
    if args.command == 'analyze':
        analyze_directory(
            args.directory, 
            args.format,
            recursive=not args.no_recursive
        )
        
    elif args.command == 'file':
        analyze_single_file(args.file_path, args.details)
        
    elif args.command == 'report':
        generate_report_only()
        
    elif args.command == 'stats':
        show_statistics()

if __name__ == "__main__":
    main()