# Technical Demo Video Script: AI File Organizer

## Production Notes
- **Length**: 4 minutes
- **Target Audience**: Developers, productivity hackers, and forks looking to deploy or study the codebase.
- **Tone**: Pragmatic, crisp, and high-fidelity.
- **Music**: Lo-fi, focus-oriented instrumental.
- **Visual Style**: Clean screen capture, dark mode, high contrast, smooth zooms on terminals.

---

## Storyboard & Narration

### Scene 1: The Problem & The Staging Area (0:00 - 0:45)
*   **Visual**: Screen recording showing a messy `Downloads` directory (spreadsheets, image mockups, audio wavs). Zoom in on the file system structure.
*   **Action**: Open a terminal and run `python interactive_organizer.py organize --dry-run`.
*   **Narration (Voiceover)**:
    "We’ve all been there: a cluttered Downloads folder full of agreements, spreadsheets, design assets, and audio takes. Finding anything feels impossible. This is the AI File Organizer, an intelligent, macOS-integrated personal librarian designed to reduce cognitive load and organize files by content."

### Scene 2: Interactive Staging & Confidence Gates (0:45 - 1:45)
*   **Visual**: Transition to terminal output showing files being analyzed. The terminal displays a file with high confidence being automatically classified, then stops at a lower confidence file (e.g. a kitchen invoice) and prompts the user.
*   **Action**: Press 'y' to confirm organization. Show the file moving to `/organized_files/finance/`.
*   **Narration (Voiceover)**:
    "Under the hood, a unified classification engine analyzes file text, images via Gemini, and audio spectral data. When AI confidence is eighty-five percent or higher, it organizes automatically. When it's not, the system engages an interactive prompt or a native AppleScript GUI, keeping you in control with simple, binary decisions."

### Scene 3: AppleScript & macOS Workflows (1:45 - 2:30)
*   **Visual**: Demonstrate the system status bar application or the native Finder dialog popping up when a file is staged.
*   **Action**: Click the status menu bar option, select "Search Archive," and query a document.
*   **Narration (Voiceover)**:
    "Integration is native. Using macOS AppleScript bindings, you can trigger scans or search your organized database directly from Finder, bypassing terminal complexity entirely and reducing the friction of staying organized."

### Scene 4: The Final Agno Retrieval Loop (2:30 - 3:30)
*   **Visual**: Clear terminal. Run `python agno_retrieval_loop.py`. The Agno agent starts, indexing `/organized_files` and writing to `~/AI_METADATA_SYSTEM/databases/archive_index.db`.
*   **Action**: Type query: *"Find Ryan Thomson's Q1 invoice details"* and show the agent's tool call to `FileTools` and its markdown summary response.
*   **Narration (Voiceover)**:
    "To close the loop, we've integrated Agno. Running the retrieval script initializes a standalone RAG agent. It indexes your organized directories and provides a semantic retrieval interface. You query your archive in natural language, and Agno searches, extracts, and summarizes the contents on the fly."

### Scene 5: Security Rules & Extensibility (3:30 - 4:00)
*   **Visual**: Open `path_config.py` in VS Code and highlight the SQLite database path definitions (Rule 3) and the `.noai` boundary check script.
*   **Narration (Voiceover)**:
    "Security is baked in. Database, metadata, and caches are isolated to the local system folder, and directories containing a dot-no-ai marker are strictly skipped. The codebase is clean, portable, and ready for you to clone and extend on GitHub. Find the full setup details in the README."

---

## Call to Action (End Card)
*   **Text**:
    *   **AI File Organizer: Intelligent macOS Librarian**
    *   Repository: `github.com/thebearwithabite/ai-file-organizer`
    *   Setup: `pip install -r requirements.txt`
