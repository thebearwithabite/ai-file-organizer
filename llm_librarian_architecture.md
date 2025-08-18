# Local LLM Librarian - Hybrid Architecture Design
*Created: 2025-08-13*

## 🎯 Architecture Overview: Best of Both Worlds

### Hybrid Processing Strategy
```python
class HybridLibrarian:
    """
    Combines fast metadata search with deep content analysis
    Optimized for MacBook Air performance and privacy
    """
    def __init__(self):
        self.metadata_index = FastMetadataSearch()  # < 1 second
        self.content_index = DeepContentSearch()    # < 5 seconds
        self.smart_cache = LRUCache(1000)           # Most accessed files
        
    def query(self, question, depth="smart"):
        """
        Three-tier search system:
        1. Fast: Metadata + filename search
        2. Smart: Cached content + selective deep search  
        3. Deep: Full content analysis
        """
```

## 🧠 Content Extraction Pipeline

### Supported File Types
```python
EXTRACTORS = {
    '.pdf': PDFExtractor(),         # Full text + metadata
    '.docx': DocxExtractor(),       # Text + formatting
    '.pages': PagesExtractor(),     # Apple Pages documents  
    '.ipynb': NotebookExtractor(),  # Code + markdown cells
    '.txt': PlainTextExtractor(),   # Simple text files
    '.md': MarkdownExtractor(),     # Structured markdown
    '.mp3/.wav': AudioMetadata(),   # Duration, bitrate, etc.
    '.jpg/.png': ImageOCR()         # Text extraction from images
}
```

### Text Processing Chain
```python
def process_content(file_path):
    # 1. Extract raw content
    raw_text = extract_text(file_path)
    
    # 2. Clean and normalize  
    cleaned_text = clean_text(raw_text)
    
    # 3. Create searchable chunks
    chunks = chunk_text(cleaned_text, overlap=100)
    
    # 4. Generate embeddings
    embeddings = create_embeddings(chunks)
    
    # 5. Store with metadata
    return {
        'content': chunks,
        'embeddings': embeddings,
        'metadata': extract_metadata(file_path),
        'indexed_date': datetime.now()
    }
```

## 🚀 Local Model Stack

### Embedding Model (Semantic Search)
```python
# sentence-transformers/all-MiniLM-L6-v2
# - Size: ~90MB
# - Speed: 1000+ sentences/second on M1
# - Quality: Excellent for document similarity
# - Cost: Free, no API calls
```

### Text Processing Models  
```python
# Optional: Local LLM via Ollama
# - Llama 2 7B or Mistral 7B
# - Size: ~4GB
# - Use case: Query understanding, summarization
# - Fallback: Rule-based processing
```

### Vector Database
```python
# ChromaDB - Lightweight, embedded
# - No server required
# - Persistent storage
# - Fast similarity search
# - Memory efficient
```

## 🎯 Query Processing Intelligence

### Natural Language Understanding
```python
class QueryProcessor:
    def parse_query(self, question):
        """
        Examples:
        "Find Client Name Wolfhard contracts from 2024"
        → person: "Client Name Wolfhard", type: "contracts", date: "2024"
        
        "Show me scripts about AI consciousness" 
        → type: "scripts", topic: "AI consciousness"
        
        "What was I working on last month?"
        → timeframe: "last month", type: "any"
        """
        
        # Extract entities
        entities = self.extract_entities(question)
        
        # Determine search strategy
        if entities['timeframe']:
            return self.temporal_search(entities)
        elif entities['person']:
            return self.person_search(entities)  
        elif entities['topic']:
            return self.semantic_search(entities)
        else:
            return self.general_search(entities)
```

### Search Strategy Selection
```python
def smart_search(self, query_data):
    """
    Adaptive search based on query characteristics
    """
    
    # Fast path: Exact filename matches
    if query_data['exact_terms']:
        results = self.metadata_search(query_data)
        if len(results) >= 5:
            return self.rank_results(results)
    
    # Medium path: Cached content search
    if query_data['cached_likely']:
        cached_results = self.cache_search(query_data)
        if self.quality_score(cached_results) > 0.7:
            return cached_results
    
    # Deep path: Full content analysis
    return self.deep_content_search(query_data)
```

## 📊 Performance Optimization

### Smart Caching Strategy
```python
class SmartCache:
    """
    Cache frequently accessed files in memory
    Prioritize by access pattern and file importance
    """
    def __init__(self):
        self.hot_cache = {}      # Last 24 hours
        self.warm_cache = {}     # Last week  
        self.cold_storage = {}   # On-demand loading
        
    def cache_priority(self, file_path):
        """
        Priority scoring:
        - Recent files: High priority
        - Frequently accessed: High priority  
        - Entertainment industry: Medium priority
        - Archive files: Low priority
        """
```

### Indexing Optimization
```python
class IncrementalIndexer:
    """
    Only re-index changed files
    Background processing during idle time
    """
    def should_reindex(self, file_path):
        current_hash = self.get_file_hash(file_path)
        stored_hash = self.index_metadata.get(file_path, {}).get('hash')
        return current_hash != stored_hash
        
    def background_indexing(self):
        """
        Run during system idle time
        Process 10-50 files per session
        Monitor system resources
        """
```

## 🔍 Advanced Query Features

### Relationship Discovery
```python
def find_related_files(self, base_file):
    """
    Find files connected by:
    - Shared people (Client Name Wolfhard → all related contracts)
    - Shared projects (Stranger Things → scripts, schedules, contracts)
    - Temporal proximity (files from same time period)
    - Content similarity (similar topics/themes)
    """
    
    relationships = {
        'people': self.extract_people_mentioned(base_file),
        'projects': self.extract_projects_mentioned(base_file),
        'timeframe': self.get_file_timeframe(base_file),
        'topics': self.extract_topics(base_file)
    }
    
    return self.search_by_relationships(relationships)
```

### Time-Travel Queries
```python
def temporal_search(self, timeframe, context=None):
    """
    "What was I working on in July 2024?"
    "Show me contracts signed last quarter"
    "Find creative projects from this year"
    """
    
    # Parse time expressions
    date_range = self.parse_timeframe(timeframe)
    
    # Filter by date
    candidates = self.filter_by_date_range(date_range)
    
    # Add context if provided
    if context:
        candidates = self.filter_by_context(candidates, context)
    
    return self.group_by_relevance(candidates)
```

## 🎪 User Interface Design

### Command Line Interface
```python
# Simple queries
$ librarian "find finn wolfhard contracts"
$ librarian "what did I work on last week?"
$ librarian "show me audio projects"

# Advanced queries  
$ librarian --deep "scripts mentioning AI consciousness"
$ librarian --time "2024-07" --type "financial"
```

### Python API
```python
from librarian import LocalLibrarian

lib = LocalLibrarian("/Users/user/Documents")

# Quick searches
results = lib.search("Client Name Wolfhard contracts")

# Advanced searches
results = lib.semantic_search("AI consciousness themes")
related = lib.find_related(results[0])
timeline = lib.temporal_search("last month", context="creative")
```

### Future: Voice Interface
```python
# "Hey Librarian, find my Stranger Things contracts"
# "Show me what I was working on yesterday"  
# "Find all files related to this project"
```

## 🛠️ Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Basic file indexing system
- [ ] Metadata extraction pipeline
- [ ] Simple text search
- [ ] **TEST:** Index 1000 files in <1 hour

### Phase 2: Intelligence (Week 2)
- [ ] Embedding generation
- [ ] Vector similarity search
- [ ] Query parsing logic
- [ ] **TEST:** Query response <2 seconds

### Phase 3: Optimization (Week 3)
- [ ] Smart caching system
- [ ] Incremental indexing
- [ ] Performance monitoring
- [ ] **TEST:** Memory usage <4GB

### Phase 4: Advanced Features (Week 4)
- [ ] Relationship discovery
- [ ] Temporal queries
- [ ] Result ranking
- [ ] **TEST:** Search accuracy >85%

## 🎯 Success Metrics

### Performance Targets
- **Initial indexing:** 1000 files/hour
- **Query response:** <2 seconds average
- **Memory usage:** <4GB during operation
- **Accuracy:** >85% relevant results

### User Experience Goals
- **Natural queries:** Plain English questions work
- **Progressive disclosure:** Simple → advanced features
- **Non-intrusive:** Background processing only
- **Reliable:** Consistent, predictable results

---

*This architecture balances power, privacy, and performance for your specific MacBook and workflow needs.*