# V3 Migration Status

## Architecture Overview

```
API (services.py)
    └── UnifiedLibrarian (unified_librarian.py) ← ENTRY POINT
            ├── UnifiedClassificationService (unified_classifier.py) ✅ 
            ├── LibrarianPolicyEngine (librarian_policy.py) ✅ 
            └── GoogleDriveLibrarian (gdrive_librarian.py)
                    └── HybridLibrarian (hybrid_librarian.py) ← SEMANTIC SEARCH
                            └── UnifiedClassificationService ✅ (migrated!)
```

**All classifiers now use UnifiedClassificationService** - no more dual-classifier inconsistency.

## Current State

### ✅ Active (New System)
- `unified_classifier.py` - Main classification service
- `unified_librarian.py` - Orchestrator
- `librarian_policy.py` - Policy engine (uses UnifiedClassificationService)
- `gdrive_librarian.py` - Cloud integration
- `vision_analyzer.py` - Computer vision (fixed RGBA bug)
- `audio_analyzer.py` - Audio analysis

### ⚠️ Partially Active (Legacy Dependency)
- `hybrid_librarian.py` - Still used for semantic search/embeddings
  - Uses OLD `FileClassificationEngine` for result enrichment
  - Should be refactored to use `UnifiedClassificationService`

### ❌ Dead Code (Can Delete)
- `classification_engine.py` - Old classifier (only used by hybrid_librarian)
- `recovered_gdrive_librarian.py` - Superseded by gdrive_librarian.py
- `enhanced_librarian.py` - Superseded
- `librarian.py` - Old CLI, superseded by unified_librarian
- `unified_classifier_backup.py` - Backup file, not needed

### 🔧 CLI Tools (Low Priority)
These have `__main__` but aren't imported anywhere:
- `query_interface.py` - Standalone query tool
- `show_questions.py` - Debug tool
- `metadata_generator.py` - Standalone metadata tool
- `interactive_with_preview.py` - Interactive organizer

## Migration Tasks

### Phase 1: Quick Wins ✅
- [x] Fix RGBA→RGB conversion in vision_analyzer (commit d7b7dc0)
- [x] Update hybrid_config IP to 192.168.86.26

### Phase 2: Decouple HybridLibrarian ✅
- [x] Update `hybrid_librarian.py` to use `UnifiedClassificationService` instead of `FileClassificationEngine`
- [x] Remove `classification_engine.py` import from hybrid_librarian
- [x] Update dict access for classification results (was object attribute access)

### Phase 3: Cleanup
- [ ] Delete `classification_engine.py`
- [ ] Delete `recovered_gdrive_librarian.py`
- [ ] Delete `enhanced_librarian.py`
- [ ] Delete `unified_classifier_backup.py`
- [ ] Archive CLI tools to `tools/legacy/` or delete

## Risks

1. **HybridLibrarian classification mismatch**: Currently uses OLD classifier for search result enrichment while API uses NEW classifier. Could cause inconsistent category names.

2. **Semantic search embeddings**: HybridLibrarian handles embeddings via remote Ollama. This is working correctly.

## Recommendation

The safest immediate action is to update `hybrid_librarian.py` to use `UnifiedClassificationService`. This:
- Eliminates the dual-classifier inconsistency
- Allows deletion of `classification_engine.py`
- Keeps semantic search working

---
*Generated: 2026-02-04*
