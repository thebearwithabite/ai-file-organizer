#!/usr/bin/env python3
"""
Test script to demonstrate the vector librarian with smart chunking
Indexes a few sample files from User's collection
"""
import os
import sys
from pathlib import Path

# Add the project directory to the Python path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from vector_librarian import VectorLibrarian

def test_with_real_files():
    """Test the vector librarian with User's actual files"""
    print("🧪 Testing Vector Librarian with Real Files")
    print("=" * 60)
    
    # Initialize librarian
    librarian = VectorLibrarian("/Users/user/Documents")
    
    if not librarian.collection:
        print("❌ Vector database not available")
        return
    
    # Test files from User's collection
    test_files = [
        "/Users/user/Documents/SAMPLE_AGREEMENT_2018.pdf",
        "/Users/user/Documents/1408 Client Name - Record.pdf",
        "/Users/user/Documents/Projects/Papers/THE Creative Work Inspired by \"Attention Is All You Need\".pdf",
        "/Users/user/Documents/Projects/Papers/AlphaGo - Prologue and Epilogue.docx"
    ]
    
    # Index files
    indexed_count = 0
    for file_path_str in test_files:
        file_path = Path(file_path_str)
        if file_path.exists():
            print(f"\n📄 Indexing: {file_path.name}")
            success = librarian.index_file_with_chunks(file_path)
            if success:
                indexed_count += 1
                print(f"   ✅ Successfully indexed with smart chunking")
            else:
                print(f"   ⚠️ Failed to index")
        else:
            print(f"   ❌ File not found: {file_path}")
    
    print(f"\n📊 Indexing Complete: {indexed_count} files indexed")
    
    # Test queries specific to User's work
    test_queries = [
        "Client Name management agreement terms",
        "AI consciousness research papers", 
        "entertainment contract exclusivity clauses",
        "payment terms in actor agreements"
    ]
    
    print(f"\n🔍 Testing Queries:")
    print("-" * 40)
    
    for query in test_queries:
        print(f"\n💭 Query: '{query}'")
        results = librarian.vector_search(query, limit=3)
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result.filename}")
                print(f"     📊 Similarity: {result.semantic_score:.1%}")
                print(f"     🏷️ Section: {result.reasoning[1] if len(result.reasoning) > 1 else 'N/A'}")
                print(f"     📝 Content: {result.matching_content[:80]}...")
        else:
            print("  ❌ No results found")
    
    # Show stats
    stats = librarian.get_stats()
    print(f"\n📈 Final Statistics:")
    print(f"  Vector DB Available: {'✅' if stats['vector_db_available'] else '❌'}")
    if stats.get('total_chunks'):
        print(f"  Total chunks indexed: {stats['total_chunks']}")
        print(f"  Smart chunking: ✅")

if __name__ == "__main__":
    test_with_real_files()