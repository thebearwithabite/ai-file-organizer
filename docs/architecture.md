# System Architecture & Design

This document details the architectural design, security protocols, and data pathways for the **AI File Organizer**. It is written for engineers, contributors, and forks looking to understand the technical implementation and design decisions.

---

## Architecture Blueprint

The AI File Organizer integrates local file operations, metadata tracking, machine learning models, and Google Drive cloud streaming. 

```mermaid
graph TD
    %% Source Pathways
    A[Loose Raw Files / Downloads] -->|staging_monitor.py| B[Inbox Staging Queue]
    
    %% Staging & Exclusion Logic
    B -->|Exclusion Check| C{Exclusion Rule?}
    C -->|Matches _NOAI or .noai| D[Skip Processing / Native Storage]
    C -->|Processable| E[interactive_organizer.py]
    
    %% Classification Engine
    E -->|Confidence < 85%| F[Interactive GUI / AppleScript / React UI]
    E -->|Confidence >= 85%| G[Unified Classifier]
    
    %% Models and Analyzers
    G -->|Text RAG / Embeddings| H[Sentence Transformers]
    G -->|Image / Video Vision| I[Gemini 2.5 Flash API]
    G -->|Audio Analysis| J[Librosa / SpeechRecognition]
    
    %% Destination Staging
    G -->|Mover CLI| K[organized_files / Google Drive]
    F -->|User Decision| K
    
    %% Metadata & Retrieval
    K -->|Sync Events| L[(Metadata Store: metadata.db)]
    
    subgraph Agno Retrieval Loop
        K -->|FileTools| M(Agno RAG Agent)
        M <-->|Session Store| N[(SQLite DB: archive_index.db)]
        M <-->|Semantic Navigation| O[Google Gemini API]
        P[User Query CLI] <-->|Natural Language Query| M
    end
    
    %% Styling
    classDef default fill:#1f2937,stroke:#374151,color:#f9fafb;
    classDef db fill:#1e3a8a,stroke:#2563eb,color:#f9fafb;
    classDef engine fill:#312e81,stroke:#4f46e5,color:#f9fafb;
    class L,N db;
    class G,M engine;
```

---

## Core Components

### 1. Unified Classification Service (`unified_classifier.py`)
Consolidates the classification logic across three primary media vectors:
*   **Text/Document Analysis**: Extracts content from PDF, DOCX, and XLSX files, generating semantic embeddings via `sentence-transformers`.
*   **Vision Analysis**: Integrates the Gemini 2.5 Flash API for computer vision processing of screenshots, diagrams, and video files.
*   **Audio Analysis**: Leverages `librosa` for audio spectral analysis (detecting BPM, spectral centroid, and texture) and `SpeechRecognition` for transcription.

### 2. Metadata Service (`metadata_service.py`)
Acts as the unified source of truth for the file organization history. Every file operation (classification, renaming, location movement) writes a record into a local SQLite database and generates individual sidecar files, facilitating quick rollbacks.

### 3. Exclusion Protocol (`_NOAI`)
Ensures data security and repository boundary safety:
*   **Folder Boundaries**: Skips directories and subdirectories matching suffix/prefix `_NOAI` or `_NO_AI`.
*   **Marker Boundaries**: Skips any folder containing a `.noai` or `.no_ai` file, including all its recursive children.

### 4. Agno Retrieval Loop (`agno_retrieval_loop.py`)
A standalone RAG agent designed using the **Agno** framework:
*   **Engine**: Backed by `Gemini 2.5 Flash`.
*   **Indexing**: Uses Agno's `FileTools` to list, read, and search the target `./organized_files` directory.
*   **Local Session Storage**: Utilizes `SqliteDb` to store agent conversations and runs.

---

## Technical Design Decisions

### SQLite & SQLite Sidecars
Instead of relying on large-scale databases, the application uses local SQLite files. This decision ensures that:
1.  The project remains 100% portable for open-source forks.
2.  File movements can be registered instantly without complex database servers.
3.  Sidecar files (`.meta.json`) preserve metadata in-place next to user files.

### Explicit Database Placement (Security Rule 3)
To prevent cluttering of workspaces and cloud sync conflicts, **all databases, caches, and learning artifacts are strictly restricted from being saved outside of the centralized system directory**:
*   **Ryan's System**: `/Users/ryanthomson/AI_METADATA_SYSTEM`
*   **General Systems (Forks)**: `~/AI_METADATA_SYSTEM`

This is enforced across the path configuration module (`path_config.py`) and inside the Agno retrieval loop script.

### ADHD-Friendly Workflows
The interactive layer is structured specifically to minimize decision fatigue:
*   **Confidence Gate**: Decisions are made automatically if the AI confidence matches or exceeds **85%**.
*   **Binary Prompts**: When the system requires user review, it offers binary prompts (yes/no or pick one of two categories) rather than overwhelming option structures.
*   **Native macOS GUI Integration**: AppleScripts generate native dialogs, reducing context switching and keeping interactions smooth.
