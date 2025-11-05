# Phase 3: VEO Prompt Integration & Repurposing Spec

This document outlines the architecture and implementation plan for integrating VEO prompt generation capabilities into the AI File Organizer.

## 1. High-Level Goal

To create a searchable, indexed library of VEO-style JSON prompts for every video file managed by the system. This will enable a future "Repurposing Agent" to intelligently find, modify, and reuse existing video assets.

## 2. Core Architecture

The integration will reuse existing components and add two new Python modules for the core logic, extending the existing SQLite database.

```
AI FILE ORGANIZER (Your existing system)
├── SQLite Databases
│   ├── metadata_tracking.db       ← Add VEO prompts here
│   ├── adaptive_learning.db       ← Already learns patterns
│   └── content_index.db           ← Already has vector embeddings
│
├── Python Modules (Just add these)
│   ├── veo_prompt_generator.py    ← Port from geminiService.ts
│   │   ├── generate_shot_list()
│   │   ├── generate_scene_plan()
│   │   └── generate_veo_json()
│   │
│   └── reverse_prompt_builder.py  ← New, uses existing vision_analyzer
│       ├── analyze_video()         ← Uses vision_analyzer.py
│       └── create_veo_json()       ← Reverse-engineers prompt
│
└── Web Interface (localhost:8000)
    └── Add "Generate VEO Prompt" tab
```

## 3. Implementation Plan

### Part A: Forward Generation (New Scripts → Prompts)

This involves porting the logic from the VEO Prompt Machine to generate prompts from new scripts.

```python
# veo_prompt_generator.py
import sqlite3

class VeoPromptGenerator:
    def __init__(self, adaptive_learning, db_path):
        self.learning = adaptive_learning  # Use existing system!
        self.db = sqlite3.connect(db_path)
        
    def generate_full_project(self, script_text):
        """Complete VEO pipeline"""
        project_name = self._generate_project_name(script_text)
        shot_list = self._generate_shot_list(script_text)
        
        for scene in self._group_by_scene(shot_list):
            scene_plan = self._generate_scene_plan(script_text, scene)
            
            for shot in scene:
                veo_json = self._generate_veo_json(
                    script_text, shot, scene_plan
                )
                
                # Store in existing database
                self._store_prompt(veo_json)
                
                # Learn patterns (existing system!)
                self.learning.record_classification({
                    'shot_id': shot['id'],
                    'veo_json': veo_json,
                    'source': 'generated'
                })
```

### Part B: Reverse Engineering (Existing Videos → Prompts)

This involves using the existing `vision_analyzer` to create prompts for videos already on disk.

```python
# reverse_prompt_builder.py
from vision_analyzer import VisionAnalyzer  # Already exists!

class ReversePromptBuilder:
    def __init__(self, vision_analyzer, adaptive_learning):
        self.vision = vision_analyzer  # Reuse existing!
        self.learning = adaptive_learning
        
    def reverse_engineer_video(self, video_path):
        """Create VEO JSON from existing video"""
        # Use your existing vision analyzer
        analysis = self.vision.analyze_video(video_path)
        
        # Convert to VEO JSON format
        veo_json = self._analysis_to_veo_json(analysis)
        
        # Store with high confidence (it's already made!)
        self._store_prompt(veo_json, confidence=0.95)
        
        # Learn from this too
        self.learning.record_classification({
            'video_path': video_path,
            'veo_json': veo_json,
            'source': 'reverse_engineered'
        })
```

### Part C: The Repurposing Agent (Future)

This is the end-goal agent that will leverage the prompt library.

```python
# veo_repurposing_agent.py
import sqlite3

class VeoRepurposingAgent:
    def __init__(self, db_path, adaptive_learning):
        self.db = sqlite3.connect(db_path)
        self.learning = adaptive_learning
        
    def find_similar_shots(self, target_prompt):
        """Use existing vector search!"""
        # Your ChromaDB/vector store already does this
        similar = self.learning.find_similar_patterns(
            target_prompt, 
            threshold=0.85
        )
        return similar
        
    def generate_variation(self, base_prompt, style_params):
        """Vista-style iterative refinement"""
        candidates = []
        for i in range(5):
            variation = self._modify_prompt(base_prompt, style_params)
            candidates.append(variation)
            
        # Tournament selection (simple for now)
        best = self._select_best(candidates)
        
        # Learn from this selection
        self.learning.record_preference(best)
        
        return best
```

## 4. Database Schema Extension

The `metadata_tracking.db` will be extended with a new table.

```sql
-- Add VEO prompts table
CREATE TABLE veo_prompts (
    id TEXT PRIMARY KEY,
    shot_id TEXT,
    source TEXT,  -- 'generated' or 'reverse_engineered'
    veo_json TEXT,  -- Store the full JSON
    video_path TEXT,
    confidence REAL,
    created_at TIMESTAMP,
    learned_from INTEGER DEFAULT 0
);

-- Index for fast lookups
CREATE INDEX idx_shot_id ON veo_prompts(shot_id);
CREATE INDEX idx_video_path ON veo_prompts(video_path);
```

## 5. Benefits of This Approach

*   **Uses What You Have:** No new services, just extends existing code.
*   **ADHD-Friendly:** Stays local, works offline, fast response.
*   **Learns Automatically:** The existing adaptive learning system will track everything.
*   **Simple Integration:** Add 2-3 Python files, extend 1 database.
*   **No New Costs:** Uses the existing Gemini API setup, no Firebase/backend billing.
