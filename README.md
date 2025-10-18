# AI File Organizer v3.1: The Reboot

## A Note on This Project

This project is undergoing a reboot. A recent audit revealed that previous versions of this documentation described a system that was significantly more capable than the actual implemented code. Features like computer vision, audio analysis, and true content-based classification were aspirational, not real.

This new documentation, and all future work, is governed by a new **Prime Directive**: to be transparent, honest, and build a system that is genuinely useful and trustworthy, with a focus on the user's needs.

Our immediate goal is to build the **Unified Adaptive Learning System** as the true, intelligent core of this application.

---

## The Vision: A Truly Proactive System

The goal is to create a single, cohesive service that starts with your computer and works intelligently in the background to manage your files, reducing cognitive load.

1.  **Unified Startup:** A single command will launch the entire system.
2.  **Intelligent Background Processing:** A monitor will watch your `Downloads` and `Desktop` folders and, after a 7-day grace period, will automatically process new files.
3.  **The Workflow:**
    *   **Deduplication:** The system will first check if a file is a duplicate and handle it.
    *   **Content Analysis:** It will then analyze the file's content (text for documents, audio for sound files) to determine its category.
    *   **Automated Organization:** High-confidence classifications will be automatically renamed and filed.
    *   **Effortless Triage:** Low-confidence files will be sent to a web UI for your review.
4.  **Adaptive Learning:** The system will learn from your corrections. This happens in two ways:
    *   **Active Learning:** When you correct a file in the Triage UI.
    *   **Passive Learning:** When the system observes you manually moving a file from one categorized folder to another.
5.  **Total Safety:** Every action is logged in the **Easy Rollback System**, allowing any operation to be undone instantly.

## Current Implemented Features (The Ground Truth)

This is what the system can do **today**.

*   **✅ Easy Rollback System:** A fully functional safety net to undo file operations.
*   **✅ Intelligent Content Chunking:** A system for breaking down documents for semantic analysis.
*   **✅ Bulletproof Duplicate Detection:** A standalone script (`bulletproof_deduplication.py`) that can find and remove duplicate files using two-tier hashing. **Note: This is not yet integrated into the automated workflow.**
*   **🟡 Web UI & API Server:** A functional frontend and backend that is currently being re-wired to the correct, intelligent core.

## The Roadmap

Our development will proceed in the following order of priority:

1.  **Implement the Unified Adaptive Learning System:** This is the top priority. We will build the "brain" that can analyze text and audio content and learn from user feedback.
2.  **Integrate All Components:** We will connect the learning system, the deduplicator, and the background monitor into a single, automated workflow.
3.  **Enhance the UI:** We will add the user-requested features like a "Trash" option, image thumbnails, and category suggestions.
4.  **Implement Computer Vision:** Once the core system is robust, we will begin work on analyzing image content.