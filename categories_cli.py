#!/usr/bin/env python3
"""
Command Line Interface for Custom Categories
Easy-to-use commands for managing custom file categories
"""

import sys
import argparse
import json
from pathlib import Path

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from custom_categories import CustomCategoryManager

def list_categories(show_details: bool = False):
    """List all custom categories"""
    
    print("📊 Custom File Categories")
    print("=" * 50)
    
    manager = CustomCategoryManager()
    categories = manager.list_categories()
    
    if not categories:
        print("❌ No custom categories found")
        print("\n💡 Use 'install-defaults' to get started with built-in templates")
        return
    
    for category in categories:
        print(f"📁 {category['display_name']} ({category['category_name']})")
        
        if show_details:
            print(f"   Description: {category['description']}")
            
            keywords = json.loads(category['keywords'])
            if keywords:
                print(f"   Keywords: {', '.join(keywords[:5])}{'...' if len(keywords) > 5 else ''}")
            
            file_types = json.loads(category['file_types'])
            if file_types:
                print(f"   File types: {', '.join(file_types)}")
            
            print(f"   Used: {category['usage_count']} times")
            print(f"   Created: {category['created_date'][:10]}")
        
        print()

def create_category(name: str, display_name: str, description: str, 
                   keywords: str = "", patterns: str = "", file_types: str = ""):
    """Create a new custom category"""
    
    print(f"📝 Creating Custom Category: {display_name}")
    print("=" * 60)
    
    manager = CustomCategoryManager()
    
    # Parse comma-separated inputs
    keywords_list = [k.strip() for k in keywords.split(',') if k.strip()] if keywords else []
    patterns_list = [p.strip() for p in patterns.split(',') if p.strip()] if patterns else []
    file_types_list = [f.strip() for f in file_types.split(',') if f.strip()] if file_types else ['.pdf', '.docx', '.txt']
    
    print(f"Category name: {name}")
    print(f"Display name: {display_name}")
    print(f"Description: {description}")
    print(f"Keywords: {keywords_list}")
    print(f"Patterns: {patterns_list}")
    print(f"File types: {file_types_list}")
    
    success = manager.create_custom_category(
        category_name=name,
        display_name=display_name,
        description=description,
        keywords=keywords_list,
        patterns=patterns_list,
        file_types=file_types_list
    )
    
    if success:
        print(f"\n✅ Category created successfully!")
        print(f"💡 Add training examples with: categories_cli.py train {name} /path/to/example/file.pdf")
    else:
        print(f"\n❌ Failed to create category")

def add_training_example(category_name: str, file_path: str, positive: bool = True):
    """Add a training example for a category"""
    
    print(f"📚 Adding Training Example")
    print("=" * 40)
    
    manager = CustomCategoryManager()
    
    # Check if category exists
    category_info = manager.get_category_info(category_name)
    if not category_info:
        print(f"❌ Category '{category_name}' not found")
        return
    
    print(f"Category: {category_info['display_name']}")
    print(f"Example file: {Path(file_path).name}")
    print(f"Type: {'Positive' if positive else 'Negative'} example")
    
    success = manager.add_training_example(category_name, file_path, positive)
    
    if success:
        print(f"\n💡 Training example added! The system will learn from this.")
    else:
        print(f"\n❌ Failed to add training example")

def test_file(file_path: str):
    """Test classification of a specific file"""
    
    print(f"🔍 Testing File Classification")
    print("=" * 50)
    
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        print(f"❌ File not found: {file_path}")
        return
    
    print(f"File: {file_path_obj.name}")
    print(f"Type: {file_path_obj.suffix}")
    print(f"Size: {file_path_obj.stat().st_size / 1024:.1f} KB")
    
    manager = CustomCategoryManager()
    result = manager.classify_with_custom_categories(file_path_obj)
    
    if result:
        print(f"\n✅ Classification Result:")
        print(f"   Category: {result['display_name']}")
        print(f"   Confidence: {result['confidence']:.1%}")
        print(f"   Source: {result['source']}")
    else:
        print(f"\n❌ No custom category match found")
        print(f"💡 Consider creating a custom category or adding training examples")

def show_category_details(category_name: str):
    """Show detailed information about a category"""
    
    print(f"📋 Category Details")
    print("=" * 40)
    
    manager = CustomCategoryManager()
    
    # Get category info
    category = manager.get_category_info(category_name)
    if not category:
        print(f"❌ Category '{category_name}' not found")
        return
    
    print(f"📁 {category['display_name']}")
    print(f"   Internal name: {category['category_name']}")
    print(f"   Description: {category['description']}")
    print(f"   Parent category: {category['parent_category'] or 'None'}")
    print(f"   Usage count: {category['usage_count']}")
    print(f"   Created: {category['created_date'][:10]}")
    print(f"   Updated: {category['updated_date'][:10]}")
    print(f"   Active: {'Yes' if category['is_active'] else 'No'}")
    
    # Show keywords
    keywords = json.loads(category['keywords'])
    if keywords:
        print(f"\n🔤 Keywords:")
        for keyword in keywords:
            print(f"   - {keyword}")
    
    # Show patterns
    patterns = json.loads(category['patterns'])
    if patterns:
        print(f"\n🔍 Patterns:")
        for pattern in patterns:
            print(f"   - {pattern}")
    
    # Show file types
    file_types = json.loads(category['file_types'])
    if file_types:
        print(f"\n📄 File Types:")
        for file_type in file_types:
            print(f"   - {file_type}")
    
    # Show training examples
    examples = manager.get_training_examples(category_name)
    if examples:
        print(f"\n📚 Training Examples ({len(examples)}):")
        for example in examples[:5]:  # Show first 5
            example_file = Path(example['example_file_path'])
            print(f"   - {example_file.name} ({'positive' if example['is_positive_example'] else 'negative'})")
        
        if len(examples) > 5:
            print(f"   ... and {len(examples) - 5} more")
    else:
        print(f"\n📚 No training examples yet")

def install_defaults():
    """Install built-in category templates"""
    
    print("📦 Installing Default Categories")
    print("=" * 50)
    
    manager = CustomCategoryManager()
    installed = manager.install_default_categories()
    
    if installed > 0:
        print(f"\n✅ Installed {installed} default categories")
        print(f"💡 Use 'categories_cli.py list --details' to see them")
    else:
        print(f"\n⚠️  Categories may already be installed")

def update_category(category_name: str, **updates):
    """Update an existing category"""
    
    print(f"✏️  Updating Category: {category_name}")
    print("=" * 50)
    
    manager = CustomCategoryManager()
    
    # Check if category exists
    if not manager.get_category_info(category_name):
        print(f"❌ Category '{category_name}' not found")
        return
    
    # Process updates
    processed_updates = {}
    for key, value in updates.items():
        if value is not None:
            if key in ['keywords', 'patterns', 'file_types'] and isinstance(value, str):
                processed_updates[key] = [v.strip() for v in value.split(',') if v.strip()]
            else:
                processed_updates[key] = value
    
    if not processed_updates:
        print("❌ No updates provided")
        return
    
    success = manager.update_category(category_name, **processed_updates)
    
    if success:
        print(f"✅ Category updated successfully")
    else:
        print(f"❌ Failed to update category")

def delete_category(category_name: str, confirm: bool = False):
    """Delete a custom category"""
    
    if not confirm:
        print(f"⚠️  Are you sure you want to delete '{category_name}'?")
        print(f"This will delete all training examples and cannot be undone.")
        print(f"Use --confirm to actually delete the category.")
        return
    
    print(f"🗑️  Deleting Category: {category_name}")
    print("=" * 50)
    
    manager = CustomCategoryManager()
    success = manager.delete_category(category_name, confirm=True)
    
    if success:
        print(f"✅ Category deleted")
    else:
        print(f"❌ Failed to delete category")

def main():
    """Command line interface for custom categories"""
    
    parser = argparse.ArgumentParser(
        description="AI File Organizer - Custom Categories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List categories
  categories_cli.py list
  categories_cli.py list --details
  
  # Create new category
  categories_cli.py create my_reports "Project Reports" "Weekly status reports" \\
    --keywords "status,report,weekly,progress" \\
    --file-types ".pdf,.docx"
  
  # Add training example
  categories_cli.py train my_reports /path/to/weekly_report.pdf
  
  # Test file classification
  categories_cli.py test /path/to/unknown_file.pdf
  
  # Show category details
  categories_cli.py info my_reports
  
  # Install defaults
  categories_cli.py install-defaults
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List categories
    list_parser = subparsers.add_parser('list', help='List all custom categories')
    list_parser.add_argument('--details', action='store_true', help='Show detailed information')
    
    # Create category
    create_parser = subparsers.add_parser('create', help='Create a new custom category')
    create_parser.add_argument('name', help='Internal category name (lowercase, underscores)')
    create_parser.add_argument('display_name', help='Human-readable display name')
    create_parser.add_argument('description', help='Category description')
    create_parser.add_argument('--keywords', default='', help='Comma-separated keywords')
    create_parser.add_argument('--patterns', default='', help='Comma-separated regex patterns')
    create_parser.add_argument('--file-types', default='.pdf,.docx,.txt', help='Comma-separated file extensions')
    
    # Add training example
    train_parser = subparsers.add_parser('train', help='Add training example')
    train_parser.add_argument('category', help='Category name')
    train_parser.add_argument('file_path', help='Path to example file')
    train_parser.add_argument('--negative', action='store_true', help='This is a negative example')
    
    # Test file classification
    test_parser = subparsers.add_parser('test', help='Test file classification')
    test_parser.add_argument('file_path', help='Path to file to test')
    
    # Show category info
    info_parser = subparsers.add_parser('info', help='Show category details')
    info_parser.add_argument('category', help='Category name')
    
    # Install defaults
    subparsers.add_parser('install-defaults', help='Install built-in category templates')
    
    # Update category
    update_parser = subparsers.add_parser('update', help='Update existing category')
    update_parser.add_argument('category', help='Category name')
    update_parser.add_argument('--display-name', help='New display name')
    update_parser.add_argument('--description', help='New description')
    update_parser.add_argument('--keywords', help='New comma-separated keywords')
    update_parser.add_argument('--patterns', help='New comma-separated patterns')
    update_parser.add_argument('--file-types', help='New comma-separated file types')
    
    # Delete category
    delete_parser = subparsers.add_parser('delete', help='Delete a custom category')
    delete_parser.add_argument('category', help='Category name')
    delete_parser.add_argument('--confirm', action='store_true', help='Confirm deletion')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("📁 AI File Organizer - Custom Categories")
    print("=" * 60)
    
    if args.command == 'list':
        list_categories(args.details)
        
    elif args.command == 'create':
        create_category(args.name, args.display_name, args.description,
                       args.keywords, args.patterns, args.file_types)
        
    elif args.command == 'train':
        add_training_example(args.category, args.file_path, not args.negative)
        
    elif args.command == 'test':
        test_file(args.file_path)
        
    elif args.command == 'info':
        show_category_details(args.category)
        
    elif args.command == 'install-defaults':
        install_defaults()
        
    elif args.command == 'update':
        updates = {}
        if args.display_name:
            updates['display_name'] = args.display_name
        if args.description:
            updates['description'] = args.description
        if args.keywords:
            updates['keywords'] = args.keywords
        if args.patterns:
            updates['patterns'] = args.patterns
        if args.file_types:
            updates['file_types'] = args.file_types
        
        update_category(args.category, **updates)
        
    elif args.command == 'delete':
        delete_category(args.category, args.confirm)

if __name__ == "__main__":
    main()