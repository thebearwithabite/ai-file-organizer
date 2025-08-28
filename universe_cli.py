#!/usr/bin/env python3
"""
Command Line Interface for Story Universe Knowledge Graph
Easy-to-use commands for exploring creative connections and story relationships
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from story_universe_graph import StoryUniverseKnowledgeGraph

def build_universe(show_progress: bool = True):
    """Build the complete story universe graph"""
    
    print("🌌 Building Story Universe Knowledge Graph")
    print("=" * 60)
    
    graph_system = StoryUniverseKnowledgeGraph()
    
    if show_progress:
        print("🔍 Analyzing all creative content...")
        print("🏗️  Extracting nodes and relationships...")
    
    total_elements = graph_system.build_universe_graph()
    
    if total_elements == 0:
        print("❌ No creative content found to build graph")
        print("💡 First analyze some creative files:")
        print("   creative_cli.py directory /path/to/creative/files")
        return
    
    print(f"\n🎯 Universe built successfully!")
    
    # Show overview
    overview = graph_system.get_universe_overview()
    
    print(f"📊 Universe Statistics:")
    print(f"   📍 Nodes: {overview['total_nodes']}")
    print(f"   🔗 Edges: {overview['total_edges']}")
    print(f"   🎭 Story clusters: {len(overview['story_clusters'])}")
    print(f"   🆕 Recent updates: {overview['recent_activity']}")

def show_overview(detailed: bool = False):
    """Show comprehensive universe overview"""
    
    print("🌟 Story Universe Overview")
    print("=" * 50)
    
    graph_system = StoryUniverseKnowledgeGraph()
    overview = graph_system.get_universe_overview()
    
    if overview['total_nodes'] == 0:
        print("❌ No universe data found")
        print("💡 Run: universe_cli.py build")
        return
    
    print(f"📊 Universe Statistics:")
    print(f"   📍 Total nodes: {overview['total_nodes']}")
    print(f"   🔗 Total edges: {overview['total_edges']}")
    print(f"   🆕 Recent updates: {overview['recent_activity']} nodes")
    
    # Node types breakdown
    if overview['node_types']:
        print(f"\n🎯 Content Types:")
        for node_type, count in overview['node_types'].items():
            percentage = (count / overview['total_nodes']) * 100
            print(f"   {node_type.title()}: {count} ({percentage:.1f}%)")
    
    # Most important elements
    if overview['top_nodes']:
        print(f"\n⭐ Most Important Elements:")
        for i, node in enumerate(overview['top_nodes'][:8], 1):
            importance_bar = "█" * int(node['importance'] * 10)
            print(f"   {i:2d}. {node['name']:<20} ({node['type']:<9}) {importance_bar} {node['importance']:.2f}")
    
    # Story clusters
    if overview['story_clusters']:
        print(f"\n🎭 Story Clusters ({len(overview['story_clusters'])}):")
        
        for i, cluster in enumerate(overview['story_clusters'][:5], 1):
            themes = json.loads(cluster['themes']) if cluster['themes'] else []
            projects = json.loads(cluster['projects']) if cluster['projects'] else []
            central = json.loads(cluster['central_nodes']) if cluster['central_nodes'] else []
            
            print(f"\n   {i}. {cluster['name']}")
            print(f"      🎯 Coherence: {cluster['coherence_score']:.2f}")
            print(f"      🌟 Central elements: {len(central)}")
            
            if themes and detailed:
                print(f"      🎨 Themes: {', '.join(themes)}")
            if projects and detailed:
                print(f"      🎬 Projects: {', '.join(projects)}")

def explore_connections(node_name: str, max_depth: int = 2, show_context: bool = False):
    """Explore connections for a specific story element"""
    
    print(f"🔍 Exploring Connections: {node_name}")
    print("=" * 60)
    
    graph_system = StoryUniverseKnowledgeGraph()
    connections = graph_system.find_connections(node_name, max_depth=max_depth)
    
    if 'error' in connections:
        print(f"❌ {connections['error']}")
        print("💡 Try a partial name or check spelling")
        return
    
    source = connections['source_node']
    print(f"🎯 Source: {source['name']} ({source['type']})")
    print(f"   ⭐ Importance: {source['importance']:.2f}")
    
    if not connections['connections']:
        print(f"\n❌ No connections found within {max_depth} degrees")
        return
    
    print(f"\n🔗 Found {connections['total_found']} connections:")
    
    # Group connections by depth
    by_depth = {}
    for conn in connections['connections']:
        depth = conn['depth']
        if depth not in by_depth:
            by_depth[depth] = []
        by_depth[depth].append(conn)
    
    for depth in sorted(by_depth.keys()):
        print(f"\n   📍 Depth {depth} ({len(by_depth[depth])} connections):")
        
        for i, conn in enumerate(by_depth[depth][:10], 1):
            strength_bar = "█" * int(conn['strength'] * 8)
            relationship_icon = {
                'appears_with': '👥',
                'part_of_project': '🎬',
                'involves_theme': '🎨',
                'works_for': '💼',
                'located_in': '📍',
                'opposes': '⚔️',
                'allies_with': '🤝'
            }.get(conn['relationship'], '🔗')
            
            print(f"      {i:2d}. {relationship_icon} {conn['target_name']} ({conn['target_type']})")
            print(f"          Strength: {strength_bar} {conn['strength']:.2f} via {conn['relationship']}")
            
            if show_context and conn['context']:
                print(f"          Context: {conn['context']}")

def find_node(search_term: str, node_type: str = None, limit: int = 10):
    """Find nodes by name or description"""
    
    print(f"🔍 Searching Universe: '{search_term}'")
    if node_type:
        print(f"🎯 Type filter: {node_type}")
    print("=" * 50)
    
    graph_system = StoryUniverseKnowledgeGraph()
    
    # Load graph
    graph_system._load_graph_from_database()
    
    if len(graph_system.graph.nodes()) == 0:
        print("❌ No universe data found")
        print("💡 Run: universe_cli.py build")
        return
    
    # Search nodes
    search_lower = search_term.lower()
    matches = []
    
    for node_id, node_data in graph_system.graph.nodes(data=True):
        if node_type and node_data['node_type'] != node_type:
            continue
        
        name_match = search_lower in node_data['name'].lower()
        desc_match = search_lower in node_data['description'].lower()
        
        if name_match or desc_match:
            matches.append((node_id, node_data, name_match))
    
    if not matches:
        print(f"❌ No matches found for '{search_term}'")
        if node_type:
            print(f"   in {node_type} nodes")
        return
    
    # Sort by exact name matches first, then by importance
    matches.sort(key=lambda x: (-x[2], -x[1].get('importance_score', 0)))
    
    print(f"📚 Found {len(matches)} matches:")
    
    for i, (node_id, node_data, name_match) in enumerate(matches[:limit], 1):
        match_type = "🎯 Exact" if name_match else "📝 Description"
        importance_bar = "█" * int(node_data.get('importance_score', 0) * 8)
        
        print(f"\n   {i:2d}. {node_data['name']}")
        print(f"       Type: {node_data['node_type']}")
        print(f"       Match: {match_type}")
        print(f"       Importance: {importance_bar} {node_data.get('importance_score', 0):.2f}")
        print(f"       Description: {node_data['description'][:80]}{'...' if len(node_data['description']) > 80 else ''}")
        
        # Show file count
        source_files = node_data.get('source_files', [])
        print(f"       Files: {len(source_files)} source files")

def suggest_developments(focus_node: str = None, limit: int = 10):
    """Get story development suggestions"""
    
    print("💡 Story Development Suggestions")
    print("=" * 50)
    
    graph_system = StoryUniverseKnowledgeGraph()
    
    # Load graph
    graph_system._load_graph_from_database()
    
    if len(graph_system.graph.nodes()) == 0:
        print("❌ No universe data found")
        print("💡 Run: universe_cli.py build")
        return
    
    suggestions = graph_system.suggest_story_developments(focus_node)
    
    if not suggestions:
        print("✨ Your story universe looks well-connected!")
        print("💭 All major elements seem to have good relationships")
        return
    
    print(f"🎯 Found {len(suggestions)} development opportunities:")
    
    for i, suggestion in enumerate(suggestions[:limit], 1):
        print(f"\n   {i:2d}. {suggestion}")
    
    print(f"\n💡 Pro tip: These suggestions are based on weak connections")
    print(f"   and isolated important elements in your story universe.")

def show_clusters(detailed: bool = False, limit: int = 10):
    """Show story clusters"""
    
    print("🎭 Story Clusters")
    print("=" * 40)
    
    graph_system = StoryUniverseKnowledgeGraph()
    overview = graph_system.get_universe_overview()
    
    clusters = overview.get('story_clusters', [])
    
    if not clusters:
        print("❌ No story clusters found")
        print("💡 Clusters are created automatically when you build the universe")
        return
    
    print(f"📚 Found {len(clusters)} story clusters:")
    
    for i, cluster in enumerate(clusters[:limit], 1):
        coherence_bar = "█" * int(cluster['coherence_score'] * 10)
        
        print(f"\n   {i:2d}. {cluster['name']}")
        print(f"       🎯 Coherence: {coherence_bar} {cluster['coherence_score']:.2f}")
        
        if detailed:
            central = json.loads(cluster['central_nodes']) if cluster['central_nodes'] else []
            related = json.loads(cluster['related_nodes']) if cluster['related_nodes'] else []
            themes = json.loads(cluster['themes']) if cluster['themes'] else []
            projects = json.loads(cluster['projects']) if cluster['projects'] else []
            
            if central:
                print(f"       🌟 Central: {', '.join(central)}")
            if related:
                print(f"       🔗 Related: {', '.join(related[:5])}")
                if len(related) > 5:
                    print(f"                ... and {len(related) - 5} more")
            if themes:
                print(f"       🎨 Themes: {', '.join(themes)}")
            if projects:
                print(f"       🎬 Projects: {', '.join(projects)}")
        
        print(f"       📅 Updated: {cluster['last_updated'][:10]}")

def main():
    """Command line interface for story universe knowledge graph"""
    
    parser = argparse.ArgumentParser(
        description="AI File Organizer - Story Universe Knowledge Graph",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build universe from creative content
  universe_cli.py build
  
  # Show universe overview
  universe_cli.py overview
  universe_cli.py overview --detailed
  
  # Explore connections
  universe_cli.py connections "Eleven"
  universe_cli.py connections "AI consciousness" --depth 3 --context
  
  # Find story elements
  universe_cli.py find "stranger"
  universe_cli.py find "consciousness" --type theme
  
  # View story clusters  
  universe_cli.py clusters
  universe_cli.py clusters --detailed
  
  # Get development suggestions
  universe_cli.py suggest
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Build universe
    build_parser = subparsers.add_parser('build', help='Build the story universe graph')
    build_parser.add_argument('--quiet', action='store_true', help='Minimal output')
    
    # Overview
    overview_parser = subparsers.add_parser('overview', help='Show universe overview')
    overview_parser.add_argument('--detailed', action='store_true', help='Show detailed information')
    
    # Explore connections
    conn_parser = subparsers.add_parser('connections', help='Explore connections for a story element')
    conn_parser.add_argument('node_name', help='Name of story element to explore')
    conn_parser.add_argument('--depth', type=int, default=2, help='Maximum connection depth (default: 2)')
    conn_parser.add_argument('--context', action='store_true', help='Show connection context')
    
    # Find nodes
    find_parser = subparsers.add_parser('find', help='Find story elements by name')
    find_parser.add_argument('search_term', help='Search term')
    find_parser.add_argument('--type', help='Filter by node type (character, theme, project, etc.)')
    find_parser.add_argument('--limit', type=int, default=10, help='Maximum results (default: 10)')
    
    # Story clusters
    cluster_parser = subparsers.add_parser('clusters', help='Show story clusters')
    cluster_parser.add_argument('--detailed', action='store_true', help='Show detailed cluster information')
    cluster_parser.add_argument('--limit', type=int, default=10, help='Maximum clusters to show (default: 10)')
    
    # Development suggestions
    suggest_parser = subparsers.add_parser('suggest', help='Get story development suggestions')
    suggest_parser.add_argument('--focus', help='Focus suggestions around specific element')
    suggest_parser.add_argument('--limit', type=int, default=10, help='Maximum suggestions (default: 10)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("🌌 AI File Organizer - Story Universe")
    print("=" * 60)
    
    if args.command == 'build':
        build_universe(show_progress=not args.quiet)
        
    elif args.command == 'overview':
        show_overview(args.detailed)
        
    elif args.command == 'connections':
        explore_connections(args.node_name, args.depth, args.context)
        
    elif args.command == 'find':
        find_node(args.search_term, args.type, args.limit)
        
    elif args.command == 'clusters':
        show_clusters(args.detailed, args.limit)
        
    elif args.command == 'suggest':
        suggest_developments(args.focus, args.limit)

if __name__ == "__main__":
    main()