#!/usr/bin/env python3
"""
Test script for email integration with vector search
Tests email extraction, chunking, and semantic search
"""
import os
import sys
from pathlib import Path

# Add the project directory to the Python path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from vector_librarian import VectorLibrarian
from email_extractor import EmailExtractor

def test_email_integration():
    """Test the complete email integration"""
    print("🧪 Testing Email Integration with Vector Search")
    print("=" * 60)
    
    # Initialize librarian
    librarian = VectorLibrarian("/Users/user/Documents")
    
    if not librarian.collection:
        print("❌ Vector database not available")
        return
    
    # Test email extraction first
    print("\n📧 Step 1: Testing Email Extraction")
    print("-" * 40)
    
    extractor = EmailExtractor()
    email_files = extractor.get_recent_emails(days=365, limit=5)
    
    if not email_files:
        print("❌ No email files found")
        return
    
    print(f"✅ Found {len(email_files)} email files")
    
    # Test indexing emails
    print("\n🔍 Step 2: Indexing Emails with Smart Chunking")
    print("-" * 40)
    
    indexed_count = 0
    for email_path in email_files[:3]:  # Test with first 3 emails
        print(f"\n📩 Indexing: {email_path.name}")
        success = librarian.index_file_with_chunks(email_path)
        if success:
            indexed_count += 1
            print(f"   ✅ Successfully indexed")
        else:
            print(f"   ⚠️ Failed to index")
    
    print(f"\n📊 Indexing Complete: {indexed_count} emails indexed")
    
    # Test email-specific queries
    print(f"\n🔍 Step 3: Testing Email-Specific Queries")
    print("-" * 40)
    
    email_queries = [
        "movie project emails",
        "creative collaboration messages",
        "business meeting schedules",
        "User communications",
        "website contact form"
    ]
    
    for query in email_queries:
        print(f"\n💭 Query: '{query}'")
        results = librarian.vector_search(query, limit=3)
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result.filename}")
                print(f"     📊 Similarity: {result.semantic_score:.1%}")
                if 'email' in result.reasoning[1] if len(result.reasoning) > 1 else '':
                    print(f"     📧 Email type: {result.reasoning[1]}")
                print(f"     📝 Content: {result.matching_content[:80]}...")
        else:
            print("  ❌ No results found")
    
    # Test mixed search (documents + emails)
    print(f"\n🔍 Step 4: Testing Mixed Search (Documents + Emails)")
    print("-" * 40)
    
    # Add some document files for comparison
    doc_files = [
        "/Users/user/Documents/SAMPLE_AGREEMENT_2018.pdf"
    ]
    
    for doc_path_str in doc_files:
        doc_path = Path(doc_path_str)
        if doc_path.exists():
            print(f"📄 Indexing document: {doc_path.name}")
            librarian.index_file_with_chunks(doc_path)
    
    mixed_queries = [
        "User management",
        "creative projects and communications",
        "business agreements and emails"
    ]
    
    for query in mixed_queries:
        print(f"\n🔍 Mixed Query: '{query}'")
        results = librarian.vector_search(query, limit=5)
        
        if results:
            for i, result in enumerate(results, 1):
                doc_type = "📧 Email" if result.filename.endswith('.emlx') else "📄 Document"
                print(f"  {i}. {doc_type} {result.filename}")
                print(f"     📊 Similarity: {result.semantic_score:.1%}")
                print(f"     📝 Content: {result.matching_content[:60]}...")
        else:
            print("  ❌ No results found")
    
    # Show final stats
    stats = librarian.get_stats()
    print(f"\n📈 Final Statistics:")
    print(f"  Vector DB Available: {'✅' if stats['vector_db_available'] else '❌'}")
    if stats.get('total_chunks'):
        print(f"  Total chunks indexed: {stats['total_chunks']}")
        print(f"  Email + Document search: ✅")

if __name__ == "__main__":
    test_email_integration()