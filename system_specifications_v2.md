# MacBook Auto-Organization System v2.0 - Technical Specifications
*Updated: 2025-08-13*

## 🎯 Core Philosophy: Natural Transition Design

### Staging-First Approach
- **7-day staging period** for Desktop/Downloads files
- **Gradual learning** of folder structure vs immediate perfection
- **ADHD-friendly** - work with natural patterns, not against them

## 🏗️ System Architecture

### Phase 1: File Organization System
**Components:**
- Desktop/Downloads monitor (AppleScript)
- Classification engine (Python)
- 7-day staging workflow
- Confidence-based organization

**Testing Protocol:**
✅ Test after each component completion
✅ Test with real file samples
✅ Test user interaction flows
✅ Measure organization accuracy

### Phase 2: Local LLM Librarian  
**Components:**
- Content extraction (PDF, DOCX, Pages, Notebooks)
- Local embedding generation (sentence-transformers)
- Vector database (ChromaDB)
- Natural language query interface

**Hardware Requirements:**
- **RAM:** 8GB minimum, 16GB+ recommended
- **Storage:** 5-10GB for models and index
- **Processor:** M1/M2 MacBook (optimal)

**Testing Protocol:**
✅ Test indexing speed (target: 1000 files/hour)
✅ Test query response time (target: <2 seconds)
✅ Test search accuracy with real queries
✅ Test memory usage (target: <4GB)

### Phase 3: Google Drive Integration
**Components:**
- Cloud sync configuration
- Tagging system implementation
- Mobile access optimization
- Collaborative features

**Testing Protocol:**
✅ Test sync reliability
✅ Test tagging accuracy
✅ Test mobile search performance
✅ Test sharing workflows

## 📅 7-Day Staging Workflow

### Daily Operations
**Time:** 11:00 PM (non-intrusive)
**Action:** Scan active folders for 7-day-old files

### File Age Triggers
- **0-7 days:** Monitor only
- **7 days:** Gentle organization suggestion
- **14+ days:** Cleanup suggestion
- **30+ days:** Archive recommendation

### User Interaction Modes
- **Learning Mode:** Observe patterns, no automation
- **Suggestion Mode:** Ask before organizing
- **Smart Mode:** Auto-organize high-confidence files
- **Expert Mode:** Full automation with edge case queries

## 🤖 LLM Librarian Specifications

### Local-Only Architecture
**Cost:** $0 (no API fees)
**Privacy:** 100% local processing
**Performance:** Sub-2-second query responses

### Content Extraction Capabilities
```
PDFs: Full text + metadata
DOCX/Pages: Text + formatting
Jupyter: Code + markdown cells  
Audio: Metadata + transcription
Images: OCR + metadata
```

### Query Types Supported
```
Semantic: "Find contracts with exclusivity clauses"
Temporal: "What was I working on last month?"
Relational: "Show me files related to Stranger Things"
Categorical: "Find all financial documents"
Content-based: "Scripts mentioning AI consciousness"
```

### Search Index Levels
- **Level 1:** Filename + basic metadata (instant)
- **Level 2:** First 1000 characters (fast)
- **Level 3:** Full content analysis (comprehensive)

## 🏷️ Enhanced Tagging System

### Tag Categories
```json
{
  "people": ["FinnWolfhard", "StrangerThings", "Netflix"],
  "projects": ["PapersThatDream", "PlayStation", "Refinery"],
  "doc_types": ["Contract", "Script", "Audio", "Financial"],
  "status": ["Active", "Completed", "Draft", "Archive"],
  "priority": ["Urgent", "High", "Normal", "Low"],
  "time_periods": ["2024", "2025", "PilotSeason", "TaxSeason"]
}
```

### Auto-Tagging Rules
```python
# High-confidence tagging
if "Finn Wolfhard" in filename or content:
    add_tags(["FinnWolfhard", "Entertainment"])
    
if "Payment Report" in filename:
    add_tags(["Financial", "Refinery", "Business"])
```

## 🧪 Testing Framework

### Test Categories
1. **Unit Tests:** Individual components
2. **Integration Tests:** Component interactions  
3. **User Experience Tests:** Real workflow validation
4. **Performance Tests:** Speed and resource usage
5. **Accuracy Tests:** Organization and search precision

### Testing Schedule
- **After each feature completion**
- **Before phase transitions**
- **Weekly performance benchmarks**
- **Monthly user experience reviews**

### Success Metrics
- **Organization Accuracy:** >90% correct classifications
- **User Satisfaction:** Natural workflow integration
- **Search Performance:** <2 second response time
- **System Stability:** 99%+ uptime
- **Learning Effectiveness:** Improving accuracy over time

## 🚀 Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- [ ] Create 7-day staging system
- [ ] Build classification engine
- [ ] Test with real file samples
- [ ] **TEST:** Accuracy >85% on sample files

### Phase 2: Intelligence (Weeks 3-4)  
- [ ] Implement local content indexing
- [ ] Build natural language query system
- [ ] Create search interface
- [ ] **TEST:** Query response <2 seconds

### Phase 3: Integration (Weeks 5-6)
- [ ] Google Drive migration
- [ ] Enhanced tagging system
- [ ] Mobile optimization
- [ ] **TEST:** End-to-end workflow validation

### Phase 4: Optimization (Weeks 7-8)
- [ ] Performance tuning
- [ ] User experience refinement
- [ ] Documentation completion
- [ ] **TEST:** Full system stress testing

## 📊 Performance Targets

### Speed Benchmarks
- File classification: <5 seconds per file
- Content indexing: 1000 files per hour
- Query response: <2 seconds average
- Initial setup: <30 minutes

### Accuracy Targets
- Entertainment files: >95% correct classification
- Financial documents: >90% correct classification
- Creative content: >85% correct classification
- General files: >80% correct classification

### Resource Usage
- Memory: <4GB during active use
- Storage: <10GB total footprint
- CPU: <20% average utilization
- Battery impact: <5% additional drain

## 🔒 Privacy & Security

### Data Handling
- All processing remains local
- No cloud API calls for sensitive content
- User controls what gets indexed
- Encryption for sensitive file index

### Content Exclusions
- Password-protected files
- Files marked as confidential
- Temporary/cache files
- System files

---

*This living document will be updated as the system evolves through testing and real-world usage.*