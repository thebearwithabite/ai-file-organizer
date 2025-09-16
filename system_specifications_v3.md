# AI File Organizer - System Specifications v3.0

## 1. Vision & Core Principles

The vision is to create a proactive, intelligent file librarian that transforms chaotic professional and creative workflows into an organized, searchable, and intuitive content ecosystem.

This system is designed with a core philosophy of reducing cognitive load, specifically for users with ADHD. It prioritizes:
- **Proactive Automation:** The system works in the background, learning user patterns and organizing content without constant intervention.
- **Semantic Understanding:** It goes beyond filenames and metadata to understand the *meaning* of the content within files.
- **Effortless Interaction:** Finding and organizing files should feel as natural as a conversation.
- **User Control:** Despite its autonomy, the user can always guide the system, adjust its learning, and override its decisions through a clear and simple interface.

## 2. Proposed V3 Architecture

The v3 architecture evolves the system from a collection of separate command-line scripts into a unified, API-driven application. This provides robustness, scalability, and a foundation for a modern user interface.

The core components are a **FastAPI Backend** and a **Web-Based UI**.

```mermaid
graph TD
    subgraph User Interaction
        A[Web Browser UI]
        B[AppleScript]
    end

    subgraph FastAPI Backend (Local Server)
        C[API Endpoints]
        D[Unified Classification Engine]
        E[Orchestrator/Workflow Manager]
        F[Search & Vector DB Interface]
        G[Content Extraction Service]
    end

    subgraph Core Services
        H[ChromaDB Vector Store]
        I[File System Monitor]
    end

    A <--> C
    B --> A
    C --> E
    E --> D
    E --> F
    E --> G
    E --> I
    F --> H
    D --> F
    G --> F
```

- **FastAPI Backend:** A single Python application that exposes all system functionality through a REST API. This replaces the multiple `main()` entry points in the current scripts.
- **Web-Based UI:** A local web interface served by the FastAPI backend, providing a rich, interactive experience for the user.
- **AppleScript (Optional):** The existing AppleScript apps can be simplified to be launchers that open the Web UI in the user's default browser.

## 3. The Unified Classification Engine

This is the most critical evolution in v3. The classification engine will be upgraded from a purely rule-based system to a **semantic-first AI model**.

**Objective:** Classify files based on their content's meaning, not just their filenames.

**Mechanism:**

1.  **Semantic Category Definitions:** In `classification_rules.json`, each category will have a new `semantic_description` field.
    - *Example:* For the "contracts" category, the description would be "A legal document outlining an agreement for services, payment, and terms between parties."
    - On startup, the backend will generate and cache a vector embedding for each of these descriptions.

2.  **New Classification Workflow:**
    - A new file is detected.
    - The **Content Extraction Service** reads the text from the file.
    - A vector embedding is generated for the extracted text.
    - The file's embedding is compared against the cached embeddings of all defined categories (using cosine similarity).
    - The category with the highest similarity score becomes the primary classification candidate, and its score becomes the initial `confidence`.

3.  **Confidence Score Enhancement:**
    - The final confidence score will be a weighted blend of semantic similarity and the existing rule-based checks.
    - **Semantic Score (70% weight):** The cosine similarity from the step above.
    - **Keyword/Metadata Score (30% weight):** The score from the existing filename/metadata analysis. This acts as a "booster" if keywords like "contract" or "agreement" are present.

**Benefit:** The system will be able to correctly classify a PDF named `Project_X_unsigned.pdf` as a contract because it understands the legal language inside the document, a massive leap in intelligence.

## 4. The FastAPI Backend API

The backend will expose the following RESTful endpoints. This provides a stable, structured way for any UI to interact with the system, eliminating the fragile parsing of `stdout`.

### Search Endpoints
- `GET /api/search`
  - **Query Params:** `q: str`, `mode: str = 'auto'`, `limit: int = 10`
  - **Returns:** `JSON { "results": [{ "file_path": "...", "relevance": 0.9, "summary": "...", ... }] }`

### Organization & Classification Endpoints
- `GET /api/triage/files_to_review`
  - **Description:** Gets a list of files that the system has processed but is not confident enough to move automatically.
  - **Returns:** `JSON { "files": [{ "file_path": "...", "suggested_category": "...", "confidence": 0.65, ... }] }`

- `POST /api/triage/classify`
  - **Description:** Allows the user to confirm or correct a classification.
  - **Body:** `JSON { "file_path": "...", "confirmed_category": "..." }`
  - **Returns:** `JSON { "success": true, "message": "File organized successfully." }`

### System & Status Endpoints
- `GET /api/system/status`
  - **Description:** Returns statistics and status information about the system.
  - **Returns:** `JSON { "indexed_files": 1234, "files_in_staging": 56, "last_run": "..." }`

- `POST /api/system/run_index`
  - **Description:** Triggers a full or incremental re-indexing of the content library.
  - **Returns:** `JSON { "success": true, "message": "Indexing started." }`

## 5. The Web-Based User Interface

The UI will be a simple, clean, and modern single-page application that runs locally in the browser.

- **Technology:** Served directly from the FastAPI backend. Can be built with simple HTML/JavaScript and a library like **htmx** for dynamic updates without needing a complex framework like React.

### 5.1. Design & Aesthetics

- **Philosophy:** The design should be minimalist, futuristic, and clean, creating a calm and focused user experience. The aesthetic is inspired by modern macOS design, emphasizing clarity and simplicity.

- **Color Palette:**
    - **Primary Theme:** A dark mode-inspired theme using cool blues and purples, often in soft, abstract gradients for backgrounds.
    - **Components:** Utilize a "frosted glass" (glassmorphism) effect for primary components like the command bar. This involves translucency and a background blur.
    - **Content Cards:** Clean, off-white rectangles with high contrast for readability.
    - **Accent Color:** A serene, electric blue should be used for interactive elements like cursors, highlights, and focus indicators.
    - **Tag Colors:** Muted, soft colors for tags (e.g., soft green, gentle orange) to be easily scannable without being distracting.

- **Layout & Components:**
    - **Command Bar:** A floating, centered, rounded rectangle. It should feature a soft, glowing 1px border to lift it off the background.
    - **Search Results:** Results appear as individual "cards" that animate smoothly into view. Each card should have generous padding, rounded corners, and ample white space.
    - **Spacing:** The overall layout should feel spacious and uncluttered.

- **Typography:**
    - **Primary Font:** A clean, modern sans-serif font, similar to Inter or the native macOS San Francisco Pro font.
    - **Hierarchy:**
        - **Search Query/Input Text:** Dark charcoal gray.
        - **Result Titles (Filenames):** Bold charcoal gray.
        - **Result Summaries:** Smaller, lighter gray to create a clear visual hierarchy.

- **Animation & Effects:**
    - **Fluid Motion:** Animations should be smooth and fluid, such as the cascading of search result cards.
    - **Pulsing Elements:** Subtle pulsing effects (e.g., on the cursor) can be used to indicate active states without being jarring.

### 5.2. Key Screens (Wireframe Descriptions)

1.  **Dashboard (Home Page):**
    - A large, prominent search bar is the main focus.
    - A "Triage Inbox" summary card showing "X files need your review."
    - System status indicators (e.g., "Monitoring X files," "Last indexed: Y").
    - Quick action buttons: "Start Indexing," "Organize Staging Area."

2.  **Search Results Page:**
    - Displays results from a `/api/search` call.
    - Each result is a card with:
        - File icon and name.
        - Relevance score and summary.
        - Action buttons: `Open File`, `Show in Finder`, `Re-classify`.
    - For image/video results, a small thumbnail preview is shown.

3.  **Triage Center:**
    - A dedicated view for files requiring manual classification.
    - Files are presented one by one or in a list.
    - For each file, it shows:
        - The filename and a preview (if possible).
        - The AI's suggested category and confidence score.
        - A simple dropdown menu of all available categories.
    - The user can select the correct category and click "Confirm" to file it away. This provides crucial training data back to the system.

## 6. Development Roadmap

This is a proposed plan for implementing the v3 changes in logical phases.

**Phase 1: Backend & API-ification**
- **Goal:** Convert the existing Python scripts into a unified FastAPI application.
- **Steps:**
    1. Set up a new main application file (`main.py`) with FastAPI.
    2. Refactor the logic from `librarian.py`, `classification_engine.py`, etc., into service classes (e.g., `SearchService`, `OrganizationService`).
    3. Implement the API endpoints defined in Section 4. At this stage, they will call the *existing* logic. The classification engine will still be rule-based.
    4. Test the API endpoints using a tool like Postman or `curl`.

**Phase 2: Unify the Classification Engine**
- **Goal:** Implement the semantic-first classification logic.
- **Steps:**
    1. Add `semantic_description` to the `classification_rules.json`.
    2. Implement the logic to generate and cache embeddings for these descriptions.
    3. Modify the `ClassificationService` to implement the new workflow: generate content embeddings, calculate similarity, and blend the scores.
    4. Update the `/api/triage/classify` endpoint to be able to feed user corrections back into the model for future learning (e.g., by creating associations).

**Phase 3: UI Development**
- **Goal:** Build the web-based frontend.
- **Steps:**
    1. Create the basic HTML, CSS, and JavaScript files for the frontend.
    2. Build the Dashboard page, hooking it up to the `/api/system/status` endpoint.
    3. Build the Search page, making calls to the `/api/search` endpoint and rendering the results dynamically.
    4. Build the Triage Center, which will be the most interactive part, fetching files from `/api/triage/files_to_review` and sending confirmations to `/api/triage/classify`.

**Phase 4: Integration & Polish**
- **Goal:** Tie everything together into a seamless application.
- **Steps:**
    1. Update the AppleScript launchers to simply open the web UI.
    2. Implement a background process manager to run the file monitor and the FastAPI server.
    3. Write comprehensive user documentation for the new v3 system.
