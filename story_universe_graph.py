#!/usr/bin/env python3
"""
Story Universe Knowledge Graph System for AI File Organizer
Creates visual maps of creative connections, characters, themes, and relationships
Perfect for tracking complex storytelling across multiple projects and files
"""

import sys
import os
import sqlite3
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict
from collections import Counter, defaultdict
import networkx as nx
from itertools import combinations

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from creative_ai_partner import CreativeAIPartner
from creative_idea_generator import CreativeIdeaGenerator

@dataclass
class UniverseNode:
    """Represents a node in the story universe graph"""
    node_id: str
    node_type: str  # character, theme, project, location, concept, organization
    name: str
    description: str
    properties: Dict[str, Any]
    source_files: List[str]
    first_appearance: str
    last_updated: datetime
    importance_score: float

@dataclass
class UniverseEdge:
    """Represents a relationship between nodes"""
    edge_id: str
    source_node: str
    target_node: str
    relationship_type: str  # appears_with, works_for, located_in, involves_theme, etc.
    strength: float
    context: str
    source_files: List[str]
    first_seen: str
    last_updated: datetime

@dataclass
class StoryCluster:
    """Represents a cluster of related story elements"""
    cluster_id: str
    name: str
    central_nodes: List[str]
    related_nodes: List[str]
    themes: List[str]
    projects: List[str]
    coherence_score: float

class StoryUniverseKnowledgeGraph:
    """
    Advanced knowledge graph system for tracking creative universe connections
    Builds comprehensive maps of characters, themes, and story relationships
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.home() / "Documents" / "AI_ORGANIZER_BASE"
        self.graph_dir = self.base_dir / "04_METADATA_SYSTEM" / "story_universe"
        self.graph_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize dependencies
        self.creative_partner = CreativeAIPartner(str(self.base_dir))
        self.idea_generator = CreativeIdeaGenerator(str(self.base_dir))
        
        # Database for knowledge graph
        self.db_path = self.graph_dir / "story_universe.db"
        self._init_graph_db()
        
        # NetworkX graph for analysis
        self.graph = nx.Graph()
        
        # Node type configurations
        self.node_types = {
            'character': {
                'color': '#FF6B6B',  # Red
                'size_multiplier': 1.5,
                'importance_weight': 1.0
            },
            'theme': {
                'color': '#4ECDC4',  # Teal
                'size_multiplier': 1.2,
                'importance_weight': 0.8
            },
            'project': {
                'color': '#45B7D1',  # Blue
                'size_multiplier': 2.0,
                'importance_weight': 1.2
            },
            'location': {
                'color': '#96CEB4',  # Green
                'size_multiplier': 1.0,
                'importance_weight': 0.7
            },
            'concept': {
                'color': '#FFEAA7',  # Yellow
                'size_multiplier': 1.1,
                'importance_weight': 0.9
            },
            'organization': {
                'color': '#DDA0DD',  # Plum
                'size_multiplier': 1.3,
                'importance_weight': 0.8
            }
        }
        
        # Relationship types and their weights
        self.relationship_types = {
            'appears_with': {'weight': 0.8, 'description': 'Characters appear together'},
            'works_for': {'weight': 0.7, 'description': 'Employment/service relationship'},
            'located_in': {'weight': 0.6, 'description': 'Location relationship'},
            'involves_theme': {'weight': 0.5, 'description': 'Thematic connection'},
            'part_of_project': {'weight': 0.9, 'description': 'Project membership'},
            'opposes': {'weight': 0.8, 'description': 'Antagonistic relationship'},
            'allies_with': {'weight': 0.8, 'description': 'Collaborative relationship'},
            'created_by': {'weight': 0.7, 'description': 'Creation relationship'},
            'influences': {'weight': 0.6, 'description': 'Influence relationship'},
            'similar_to': {'weight': 0.4, 'description': 'Similarity connection'}
        }
    
    def _init_graph_db(self):
        """Initialize SQLite database for knowledge graph"""
        with sqlite3.connect(self.db_path) as conn:
            # Nodes table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS universe_nodes (
                    node_id TEXT PRIMARY KEY,
                    node_type TEXT,
                    name TEXT,
                    description TEXT,
                    properties TEXT,  -- JSON
                    source_files TEXT,  -- JSON array
                    first_appearance TEXT,
                    last_updated TEXT,
                    importance_score REAL
                )
            """)
            
            # Edges table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS universe_edges (
                    edge_id TEXT PRIMARY KEY,
                    source_node TEXT,
                    target_node TEXT,
                    relationship_type TEXT,
                    strength REAL,
                    context TEXT,
                    source_files TEXT,  -- JSON array
                    first_seen TEXT,
                    last_updated TEXT,
                    FOREIGN KEY (source_node) REFERENCES universe_nodes (node_id),
                    FOREIGN KEY (target_node) REFERENCES universe_nodes (node_id)
                )
            """)
            
            # Story clusters table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS story_clusters (
                    cluster_id TEXT PRIMARY KEY,
                    name TEXT,
                    central_nodes TEXT,  -- JSON array
                    related_nodes TEXT,  -- JSON array
                    themes TEXT,  -- JSON array
                    projects TEXT,  -- JSON array
                    coherence_score REAL,
                    created_date TEXT,
                    last_updated TEXT
                )
            """)
            
            # Graph snapshots for version control
            conn.execute("""
                CREATE TABLE IF NOT EXISTS graph_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_date TEXT,
                    total_nodes INTEGER,
                    total_edges INTEGER,
                    node_data TEXT,  -- JSON
                    edge_data TEXT,  -- JSON
                    description TEXT
                )
            """)
            
            conn.commit()
    
    def build_universe_graph(self) -> int:
        """Build the complete story universe graph from all analyzed content"""
        
        print("🌌 Building Story Universe Knowledge Graph...")
        print("=" * 60)
        
        nodes_created = 0
        edges_created = 0
        
        # Get all creative analyses
        with sqlite3.connect(self.creative_partner.db_path) as conn:
            cursor = conn.execute("""
                SELECT file_path, project_identified, characters_found, themes_detected,
                       story_elements, character_development, plot_progression,
                       analyzed_date
                FROM file_analysis
                ORDER BY analyzed_date DESC
            """)
            
            analyses = cursor.fetchall()
        
        if not analyses:
            print("❌ No creative content analyzed yet")
            return 0
        
        print(f"📚 Processing {len(analyses)} analyzed files...")
        
        # Process each analysis to extract nodes and relationships
        for analysis in analyses:
            file_path, project, characters_json, themes_json, elements_json, dev_json, plot, analyzed_date = analysis
            
            # Extract nodes from this file
            file_nodes = self._extract_nodes_from_analysis(
                file_path, project, characters_json, themes_json, 
                elements_json, dev_json, plot, analyzed_date
            )
            
            for node in file_nodes:
                if self._save_node(node):
                    nodes_created += 1
            
            # Extract relationships from this file
            file_edges = self._extract_edges_from_analysis(
                file_path, characters_json, themes_json, elements_json, project
            )
            
            for edge in file_edges:
                if self._save_edge(edge):
                    edges_created += 1
        
        # Build NetworkX graph from database
        self._load_graph_from_database()
        
        # Detect story clusters
        clusters_found = self._detect_story_clusters()
        
        # Calculate importance scores
        self._calculate_importance_scores()
        
        # Create snapshot
        self._create_graph_snapshot(f"Graph build with {nodes_created} nodes, {edges_created} edges")
        
        print(f"✅ Universe graph built successfully!")
        print(f"   📍 Nodes: {nodes_created}")
        print(f"   🔗 Edges: {edges_created}")
        print(f"   🎭 Story clusters: {clusters_found}")
        
        return nodes_created + edges_created
    
    def _extract_nodes_from_analysis(self, file_path: str, project: str, 
                                   characters_json: str, themes_json: str,
                                   elements_json: str, dev_json: str, 
                                   plot: str, analyzed_date: str) -> List[UniverseNode]:
        """Extract nodes from a single file analysis"""
        
        nodes = []
        
        # Extract character nodes
        if characters_json:
            characters = json.loads(characters_json)
            for character in characters:
                node_id = f"character:{character.lower().replace(' ', '_')}"
                
                # Get character development info
                character_dev = ""
                if dev_json:
                    dev_data = json.loads(dev_json)
                    character_dev = dev_data.get(character, "")
                
                nodes.append(UniverseNode(
                    node_id=node_id,
                    node_type="character",
                    name=character,
                    description=f"Character from {project or 'unknown project'}",
                    properties={
                        'development': character_dev,
                        'plot_role': plot if plot else ""
                    },
                    source_files=[file_path],
                    first_appearance=file_path,
                    last_updated=datetime.now(),
                    importance_score=1.0
                ))
        
        # Extract theme nodes
        if themes_json:
            themes = json.loads(themes_json)
            for theme in themes:
                node_id = f"theme:{theme.lower().replace(' ', '_')}"
                
                nodes.append(UniverseNode(
                    node_id=node_id,
                    node_type="theme",
                    name=theme,
                    description=f"Thematic element",
                    properties={
                        'context': plot if plot else "",
                        'project_context': project or ""
                    },
                    source_files=[file_path],
                    first_appearance=file_path,
                    last_updated=datetime.now(),
                    importance_score=0.8
                ))
        
        # Extract project node
        if project:
            node_id = f"project:{project.lower().replace(' ', '_')}"
            
            nodes.append(UniverseNode(
                node_id=node_id,
                node_type="project",
                name=project,
                description=f"Creative project",
                properties={
                    'plot_structure': plot if plot else "",
                    'character_count': len(json.loads(characters_json)) if characters_json else 0,
                    'theme_count': len(json.loads(themes_json)) if themes_json else 0
                },
                source_files=[file_path],
                first_appearance=file_path,
                last_updated=datetime.now(),
                importance_score=1.2
            ))
        
        # Extract story elements as concept nodes
        if elements_json:
            elements = json.loads(elements_json)
            for element in elements:
                # Parse structured elements
                if ':' in element:
                    element_type, element_name = element.split(':', 1)
                    
                    if element_type.lower() in ['location', 'setting']:
                        node_type = 'location'
                    elif element_type.lower() in ['organization', 'company']:
                        node_type = 'organization'
                    else:
                        node_type = 'concept'
                    
                    node_id = f"{node_type}:{element_name.lower().replace(' ', '_')}"
                    
                    nodes.append(UniverseNode(
                        node_id=node_id,
                        node_type=node_type,
                        name=element_name,
                        description=f"{element_type.title()} from {project or 'story'}",
                        properties={
                            'category': element_type,
                            'project_context': project or ""
                        },
                        source_files=[file_path],
                        first_appearance=file_path,
                        last_updated=datetime.now(),
                        importance_score=0.7
                    ))
        
        return nodes
    
    def _extract_edges_from_analysis(self, file_path: str, characters_json: str,
                                   themes_json: str, elements_json: str, 
                                   project: str) -> List[UniverseEdge]:
        """Extract relationships from a single file analysis"""
        
        edges = []
        
        # Character co-occurrence relationships
        if characters_json:
            characters = json.loads(characters_json)
            
            for char1, char2 in combinations(characters, 2):
                source_id = f"character:{char1.lower().replace(' ', '_')}"
                target_id = f"character:{char2.lower().replace(' ', '_')}"
                edge_id = f"{source_id}--appears_with--{target_id}"
                
                edges.append(UniverseEdge(
                    edge_id=edge_id,
                    source_node=source_id,
                    target_node=target_id,
                    relationship_type="appears_with",
                    strength=0.8,
                    context=f"Both appear in {Path(file_path).name}",
                    source_files=[file_path],
                    first_seen=file_path,
                    last_updated=datetime.now()
                ))
        
        # Character-theme relationships
        if characters_json and themes_json:
            characters = json.loads(characters_json)
            themes = json.loads(themes_json)
            
            for character in characters:
                for theme in themes:
                    char_id = f"character:{character.lower().replace(' ', '_')}"
                    theme_id = f"theme:{theme.lower().replace(' ', '_')}"
                    edge_id = f"{char_id}--involves_theme--{theme_id}"
                    
                    edges.append(UniverseEdge(
                        edge_id=edge_id,
                        source_node=char_id,
                        target_node=theme_id,
                        relationship_type="involves_theme",
                        strength=0.5,
                        context=f"Character explores theme in {Path(file_path).name}",
                        source_files=[file_path],
                        first_seen=file_path,
                        last_updated=datetime.now()
                    ))
        
        # Project relationships
        if project:
            project_id = f"project:{project.lower().replace(' ', '_')}"
            
            # Project-character relationships
            if characters_json:
                characters = json.loads(characters_json)
                for character in characters:
                    char_id = f"character:{character.lower().replace(' ', '_')}"
                    edge_id = f"{char_id}--part_of_project--{project_id}"
                    
                    edges.append(UniverseEdge(
                        edge_id=edge_id,
                        source_node=char_id,
                        target_node=project_id,
                        relationship_type="part_of_project",
                        strength=0.9,
                        context=f"Character in project {project}",
                        source_files=[file_path],
                        first_seen=file_path,
                        last_updated=datetime.now()
                    ))
            
            # Project-theme relationships
            if themes_json:
                themes = json.loads(themes_json)
                for theme in themes:
                    theme_id = f"theme:{theme.lower().replace(' ', '_')}"
                    edge_id = f"{project_id}--involves_theme--{theme_id}"
                    
                    edges.append(UniverseEdge(
                        edge_id=edge_id,
                        source_node=project_id,
                        target_node=theme_id,
                        relationship_type="involves_theme",
                        strength=0.7,
                        context=f"Project explores theme {theme}",
                        source_files=[file_path],
                        first_seen=file_path,
                        last_updated=datetime.now()
                    ))
        
        return edges
    
    def _save_node(self, node: UniverseNode) -> bool:
        """Save or update a node in the database"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if node exists
                cursor = conn.execute("SELECT node_id FROM universe_nodes WHERE node_id = ?", (node.node_id,))
                exists = cursor.fetchone()
                
                if exists:
                    # Update existing node
                    conn.execute("""
                        UPDATE universe_nodes 
                        SET description = ?, properties = ?, 
                            source_files = json_insert(COALESCE(source_files, '[]'), '$[#]', ?),
                            last_updated = ?, importance_score = ?
                        WHERE node_id = ?
                    """, (
                        node.description,
                        json.dumps(node.properties),
                        node.source_files[0] if node.source_files else "",
                        node.last_updated.isoformat(),
                        node.importance_score,
                        node.node_id
                    ))
                else:
                    # Insert new node
                    conn.execute("""
                        INSERT INTO universe_nodes
                        (node_id, node_type, name, description, properties, source_files,
                         first_appearance, last_updated, importance_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        node.node_id,
                        node.node_type,
                        node.name,
                        node.description,
                        json.dumps(node.properties),
                        json.dumps(node.source_files),
                        node.first_appearance,
                        node.last_updated.isoformat(),
                        node.importance_score
                    ))
                
                conn.commit()
                return True
        
        except Exception as e:
            print(f"❌ Error saving node {node.node_id}: {e}")
            return False
    
    def _save_edge(self, edge: UniverseEdge) -> bool:
        """Save or update an edge in the database"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if edge exists
                cursor = conn.execute("SELECT edge_id FROM universe_edges WHERE edge_id = ?", (edge.edge_id,))
                exists = cursor.fetchone()
                
                if exists:
                    # Update existing edge - increase strength
                    conn.execute("""
                        UPDATE universe_edges 
                        SET strength = MIN(strength + 0.1, 1.0),
                            context = ?, 
                            source_files = json_insert(COALESCE(source_files, '[]'), '$[#]', ?),
                            last_updated = ?
                        WHERE edge_id = ?
                    """, (
                        edge.context,
                        edge.source_files[0] if edge.source_files else "",
                        edge.last_updated.isoformat(),
                        edge.edge_id
                    ))
                else:
                    # Insert new edge
                    conn.execute("""
                        INSERT INTO universe_edges
                        (edge_id, source_node, target_node, relationship_type, strength,
                         context, source_files, first_seen, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        edge.edge_id,
                        edge.source_node,
                        edge.target_node,
                        edge.relationship_type,
                        edge.strength,
                        edge.context,
                        json.dumps(edge.source_files),
                        edge.first_seen,
                        edge.last_updated.isoformat()
                    ))
                
                conn.commit()
                return True
        
        except Exception as e:
            print(f"❌ Error saving edge {edge.edge_id}: {e}")
            return False
    
    def _load_graph_from_database(self):
        """Load the graph structure into NetworkX from database"""
        
        self.graph.clear()
        
        with sqlite3.connect(self.db_path) as conn:
            # Load nodes
            cursor = conn.execute("SELECT * FROM universe_nodes")
            columns = [desc[0] for desc in cursor.description]
            
            for row in cursor.fetchall():
                node_data = dict(zip(columns, row))
                
                self.graph.add_node(
                    node_data['node_id'],
                    node_type=node_data['node_type'],
                    name=node_data['name'],
                    description=node_data['description'],
                    properties=json.loads(node_data['properties']),
                    source_files=json.loads(node_data['source_files']),
                    importance_score=node_data['importance_score']
                )
            
            # Load edges
            cursor = conn.execute("SELECT * FROM universe_edges")
            columns = [desc[0] for desc in cursor.description]
            
            for row in cursor.fetchall():
                edge_data = dict(zip(columns, row))
                
                self.graph.add_edge(
                    edge_data['source_node'],
                    edge_data['target_node'],
                    relationship_type=edge_data['relationship_type'],
                    strength=edge_data['strength'],
                    context=edge_data['context'],
                    source_files=json.loads(edge_data['source_files'])
                )
    
    def _detect_story_clusters(self) -> int:
        """Detect clusters of related story elements"""
        
        clusters_created = 0
        
        if len(self.graph.nodes()) < 3:
            return 0
        
        # Try to use community detection if available
        try:
            import community as community_louvain
            
            # Create undirected graph for community detection
            undirected_graph = nx.Graph()
            for u, v, data in self.graph.edges(data=True):
                undirected_graph.add_edge(u, v, weight=data['strength'])
            
            # Detect communities
            communities = community_louvain.best_partition(undirected_graph)
            
            # Group nodes by community
            community_groups = defaultdict(list)
            for node, community_id in communities.items():
                community_groups[community_id].append(node)
            
            # Create story clusters from communities
            for community_id, nodes in community_groups.items():
                if len(nodes) >= 2:  # Only create clusters with multiple nodes
                    
                    # Analyze cluster composition
                    node_types = [self.graph.nodes[node]['node_type'] for node in nodes]
                    node_type_counts = Counter(node_types)
                    
                    # Determine cluster name and characteristics
                    if 'project' in node_type_counts:
                        project_nodes = [n for n in nodes if self.graph.nodes[n]['node_type'] == 'project']
                        cluster_name = f"Project: {self.graph.nodes[project_nodes[0]]['name']}"
                        central_nodes = project_nodes
                    elif node_type_counts.get('character', 0) >= 2:
                        char_nodes = [n for n in nodes if self.graph.nodes[n]['node_type'] == 'character']
                        cluster_name = f"Character Group: {', '.join([self.graph.nodes[n]['name'] for n in char_nodes[:2]])}"
                        central_nodes = char_nodes[:3]
                    else:
                        cluster_name = f"Story Cluster {community_id}"
                        central_nodes = nodes[:2]
                    
                    # Extract themes and projects
                    themes = [self.graph.nodes[n]['name'] for n in nodes 
                             if self.graph.nodes[n]['node_type'] == 'theme']
                    projects = [self.graph.nodes[n]['name'] for n in nodes 
                               if self.graph.nodes[n]['node_type'] == 'project']
                    
                    # Calculate coherence score based on connectivity
                    cluster_subgraph = self.graph.subgraph(nodes)
                    density = nx.density(cluster_subgraph)
                    coherence_score = min(density * len(nodes) / 10, 1.0)
                    
                    cluster = StoryCluster(
                        cluster_id=f"cluster_{community_id}",
                        name=cluster_name,
                        central_nodes=central_nodes,
                        related_nodes=[n for n in nodes if n not in central_nodes],
                        themes=themes,
                        projects=projects,
                        coherence_score=coherence_score
                    )
                    
                    if self._save_cluster(cluster):
                        clusters_created += 1
        
        except ImportError:
            print("⚠️  Advanced clustering requires python-louvain: pip install python-louvain")
            print("📍 Creating basic clusters using connectivity...")
            
            # Fallback: create clusters based on connected components
            connected_components = list(nx.connected_components(self.graph))
            
            for i, nodes in enumerate(connected_components):
                if len(nodes) >= 2:
                    nodes_list = list(nodes)
                    
                    # Simple cluster naming
                    node_types = [self.graph.nodes[node]['node_type'] for node in nodes_list]
                    node_type_counts = Counter(node_types)
                    
                    if 'project' in node_type_counts:
                        project_nodes = [n for n in nodes_list if self.graph.nodes[n]['node_type'] == 'project']
                        cluster_name = f"Project: {self.graph.nodes[project_nodes[0]]['name']}"
                    elif node_type_counts.get('character', 0) >= 2:
                        char_nodes = [n for n in nodes_list if self.graph.nodes[n]['node_type'] == 'character'][:2]
                        cluster_name = f"Characters: {', '.join([self.graph.nodes[n]['name'] for n in char_nodes])}"
                    else:
                        cluster_name = f"Connected Group {i+1}"
                    
                    # Extract info
                    themes = [self.graph.nodes[n]['name'] for n in nodes_list 
                             if self.graph.nodes[n]['node_type'] == 'theme']
                    projects = [self.graph.nodes[n]['name'] for n in nodes_list 
                               if self.graph.nodes[n]['node_type'] == 'project']
                    
                    cluster = StoryCluster(
                        cluster_id=f"component_{i}",
                        name=cluster_name,
                        central_nodes=nodes_list[:2],
                        related_nodes=nodes_list[2:],
                        themes=themes,
                        projects=projects,
                        coherence_score=0.7
                    )
                    
                    if self._save_cluster(cluster):
                        clusters_created += 1
            
        except Exception as e:
            print(f"⚠️  Cluster detection error: {e}")
        
        return clusters_created
    
    def _save_cluster(self, cluster: StoryCluster) -> bool:
        """Save a story cluster to database"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO story_clusters
                    (cluster_id, name, central_nodes, related_nodes, themes, projects,
                     coherence_score, created_date, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cluster.cluster_id,
                    cluster.name,
                    json.dumps(cluster.central_nodes),
                    json.dumps(cluster.related_nodes),
                    json.dumps(cluster.themes),
                    json.dumps(cluster.projects),
                    cluster.coherence_score,
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
                conn.commit()
            
            return True
        
        except Exception as e:
            print(f"❌ Error saving cluster: {e}")
            return False
    
    def _calculate_importance_scores(self):
        """Calculate importance scores based on graph structure"""
        
        if len(self.graph.nodes()) == 0:
            return
        
        # Calculate centrality measures
        try:
            degree_centrality = nx.degree_centrality(self.graph)
            betweenness_centrality = nx.betweenness_centrality(self.graph)
            closeness_centrality = nx.closeness_centrality(self.graph)
        except:
            degree_centrality = {node: 0.5 for node in self.graph.nodes()}
            betweenness_centrality = {node: 0.5 for node in self.graph.nodes()}
            closeness_centrality = {node: 0.5 for node in self.graph.nodes()}
        
        # Update importance scores
        with sqlite3.connect(self.db_path) as conn:
            for node_id in self.graph.nodes():
                node_data = self.graph.nodes[node_id]
                node_type = node_data['node_type']
                
                # Base importance from node type
                base_importance = self.node_types.get(node_type, {}).get('importance_weight', 0.5)
                
                # Centrality-based importance
                degree_score = degree_centrality.get(node_id, 0)
                between_score = betweenness_centrality.get(node_id, 0)
                close_score = closeness_centrality.get(node_id, 0)
                
                # File count importance (more appearances = more important)
                file_count = len(node_data.get('source_files', []))
                file_score = min(file_count / 10, 1.0)
                
                # Combined importance score
                importance = (base_importance * 0.3 + 
                            degree_score * 0.25 + 
                            between_score * 0.2 + 
                            close_score * 0.15 + 
                            file_score * 0.1)
                
                conn.execute("""
                    UPDATE universe_nodes 
                    SET importance_score = ? 
                    WHERE node_id = ?
                """, (importance, node_id))
            
            conn.commit()
    
    def _create_graph_snapshot(self, description: str):
        """Create a snapshot of the current graph state"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get all nodes and edges
                cursor = conn.execute("SELECT * FROM universe_nodes")
                node_columns = [desc[0] for desc in cursor.description]
                nodes_data = [dict(zip(node_columns, row)) for row in cursor.fetchall()]
                
                cursor = conn.execute("SELECT * FROM universe_edges")
                edge_columns = [desc[0] for desc in cursor.description]
                edges_data = [dict(zip(edge_columns, row)) for row in cursor.fetchall()]
                
                # Save snapshot
                conn.execute("""
                    INSERT INTO graph_snapshots
                    (snapshot_date, total_nodes, total_edges, node_data, edge_data, description)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(),
                    len(nodes_data),
                    len(edges_data),
                    json.dumps(nodes_data),
                    json.dumps(edges_data),
                    description
                ))
                conn.commit()
        
        except Exception as e:
            print(f"⚠️  Could not create snapshot: {e}")
    
    def get_universe_overview(self) -> Dict[str, Any]:
        """Get comprehensive overview of the story universe"""
        
        with sqlite3.connect(self.db_path) as conn:
            # Basic statistics
            cursor = conn.execute("SELECT COUNT(*) FROM universe_nodes")
            total_nodes = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM universe_edges")
            total_edges = cursor.fetchone()[0]
            
            # Nodes by type
            cursor = conn.execute("""
                SELECT node_type, COUNT(*) as count
                FROM universe_nodes
                GROUP BY node_type
                ORDER BY count DESC
            """)
            node_types = dict(cursor.fetchall())
            
            # Most important nodes
            cursor = conn.execute("""
                SELECT node_id, node_type, name, importance_score
                FROM universe_nodes
                ORDER BY importance_score DESC
                LIMIT 10
            """)
            top_nodes = cursor.fetchall()
            
            # Story clusters
            cursor = conn.execute("SELECT * FROM story_clusters ORDER BY coherence_score DESC")
            cluster_columns = [desc[0] for desc in cursor.description]
            clusters = [dict(zip(cluster_columns, row)) for row in cursor.fetchall()]
            
            # Recent activity
            cursor = conn.execute("""
                SELECT COUNT(*) FROM universe_nodes 
                WHERE last_updated > datetime('now', '-7 days')
            """)
            recent_nodes = cursor.fetchone()[0]
            
            return {
                'total_nodes': total_nodes,
                'total_edges': total_edges,
                'node_types': node_types,
                'top_nodes': [
                    {
                        'id': row[0],
                        'type': row[1], 
                        'name': row[2],
                        'importance': row[3]
                    } for row in top_nodes
                ],
                'story_clusters': clusters,
                'recent_activity': recent_nodes,
                'generated_at': datetime.now().isoformat()
            }
    
    def find_connections(self, node_name: str, max_depth: int = 2) -> Dict[str, Any]:
        """Find all connections for a specific node"""
        
        # Find node by name
        matching_nodes = []
        for node_id, node_data in self.graph.nodes(data=True):
            if node_name.lower() in node_data['name'].lower():
                matching_nodes.append((node_id, node_data))
        
        if not matching_nodes:
            return {'error': f'No nodes found matching "{node_name}"'}
        
        # Use first match
        target_node, target_data = matching_nodes[0]
        
        # Find connections within max_depth
        connections = []
        visited = set()
        
        def explore_connections(current_node, depth, path):
            if depth > max_depth or current_node in visited:
                return
            
            visited.add(current_node)
            
            for neighbor in self.graph.neighbors(current_node):
                if neighbor not in path:  # Avoid cycles
                    edge_data = self.graph.edges[current_node, neighbor]
                    neighbor_data = self.graph.nodes[neighbor]
                    
                    connections.append({
                        'path': path + [neighbor],
                        'depth': depth,
                        'relationship': edge_data['relationship_type'],
                        'strength': edge_data['strength'],
                        'target_name': neighbor_data['name'],
                        'target_type': neighbor_data['node_type'],
                        'context': edge_data.get('context', '')
                    })
                    
                    if depth < max_depth:
                        explore_connections(neighbor, depth + 1, path + [neighbor])
        
        explore_connections(target_node, 1, [target_node])
        
        # Sort by strength and depth
        connections.sort(key=lambda x: (-x['strength'], x['depth']))
        
        return {
            'source_node': {
                'id': target_node,
                'name': target_data['name'],
                'type': target_data['node_type'],
                'importance': target_data.get('importance_score', 0)
            },
            'connections': connections[:20],  # Top 20 connections
            'total_found': len(connections)
        }
    
    def suggest_story_developments(self, focus_node: str = None) -> List[str]:
        """Suggest potential story developments based on graph structure"""
        
        suggestions = []
        
        # Find weak connections that could be strengthened
        weak_edges = [(u, v, data) for u, v, data in self.graph.edges(data=True) 
                     if data['strength'] < 0.5]
        
        for u, v, data in weak_edges[:5]:
            u_data = self.graph.nodes[u]
            v_data = self.graph.nodes[v]
            
            if u_data['node_type'] == 'character' and v_data['node_type'] == 'character':
                suggestions.append(
                    f"Develop the relationship between {u_data['name']} and {v_data['name']} "
                    f"- they currently have a weak connection ({data['relationship_type']})"
                )
        
        # Find isolated important nodes
        isolated_nodes = [node for node in self.graph.nodes() 
                         if self.graph.degree(node) <= 1 and 
                         self.graph.nodes[node].get('importance_score', 0) > 0.7]
        
        for node in isolated_nodes:
            node_data = self.graph.nodes[node]
            suggestions.append(
                f"Connect {node_data['name']} to other story elements "
                f"- this important {node_data['node_type']} is currently isolated"
            )
        
        # Find themes without enough character connections
        theme_nodes = [node for node in self.graph.nodes() 
                      if self.graph.nodes[node]['node_type'] == 'theme']
        
        for theme_node in theme_nodes:
            theme_data = self.graph.nodes[theme_node]
            character_connections = sum(1 for neighbor in self.graph.neighbors(theme_node) 
                                      if self.graph.nodes[neighbor]['node_type'] == 'character')
            
            if character_connections < 2:
                suggestions.append(
                    f"Explore theme '{theme_data['name']}' through more characters "
                    f"- currently only connected to {character_connections} character(s)"
                )
        
        return suggestions[:10]  # Top 10 suggestions

def test_story_universe_graph():
    """Test the story universe knowledge graph system"""
    
    print("🌌 Testing Story Universe Knowledge Graph")
    print("=" * 60)
    
    graph_system = StoryUniverseKnowledgeGraph()
    
    # Build the universe graph
    print("🏗️  Building universe graph...")
    total_elements = graph_system.build_universe_graph()
    
    if total_elements == 0:
        print("❌ No creative content found to build graph")
        print("💡 Run creative_cli.py to analyze some creative files first")
        return
    
    # Get universe overview
    print(f"\n🌟 Universe Overview:")
    overview = graph_system.get_universe_overview()
    
    print(f"   📍 Total nodes: {overview['total_nodes']}")
    print(f"   🔗 Total edges: {overview['total_edges']}")
    print(f"   🎭 Story clusters: {len(overview['story_clusters'])}")
    
    # Show node types
    if overview['node_types']:
        print(f"\n📊 Node Types:")
        for node_type, count in overview['node_types'].items():
            print(f"   {node_type}: {count}")
    
    # Show most important nodes
    if overview['top_nodes']:
        print(f"\n⭐ Most Important Elements:")
        for i, node in enumerate(overview['top_nodes'][:5], 1):
            print(f"   {i}. {node['name']} ({node['type']}) - importance: {node['importance']:.2f}")
    
    # Show story clusters
    if overview['story_clusters']:
        print(f"\n🎭 Story Clusters:")
        for i, cluster in enumerate(overview['story_clusters'][:3], 1):
            cluster_data = cluster
            themes = json.loads(cluster_data['themes']) if cluster_data['themes'] else []
            projects = json.loads(cluster_data['projects']) if cluster_data['projects'] else []
            
            print(f"\n   {i}. {cluster_data['name']}")
            print(f"      Coherence: {cluster_data['coherence_score']:.2f}")
            if themes:
                print(f"      Themes: {', '.join(themes)}")
            if projects:
                print(f"      Projects: {', '.join(projects)}")
    
    # Test connection finding
    if overview['top_nodes']:
        test_node = overview['top_nodes'][0]['name']
        print(f"\n🔍 Testing connections for '{test_node}':")
        
        connections = graph_system.find_connections(test_node, max_depth=2)
        
        if 'connections' in connections:
            print(f"   Found {connections['total_found']} connections")
            for i, conn in enumerate(connections['connections'][:5], 1):
                print(f"   {i}. → {conn['target_name']} ({conn['target_type']}) "
                      f"via {conn['relationship']} (strength: {conn['strength']:.2f})")
    
    # Test story development suggestions
    print(f"\n💡 Story Development Suggestions:")
    suggestions = graph_system.suggest_story_developments()
    
    for i, suggestion in enumerate(suggestions[:5], 1):
        print(f"   {i}. {suggestion}")
    
    print(f"\n✅ Story universe graph test completed!")

if __name__ == "__main__":
    test_story_universe_graph()