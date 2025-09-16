# Gemini as an AI Project Overseer: A Workflow Guide

## 1. Introduction

This document outlines a workflow for using a tool-enabled AI assistant (like Gemini) in an "Oversight Capacity" to manage, stabilize, and drive complex or "sideways" software projects. The primary goal is to impose structure, ensure quality, and maintain forward momentum by pairing a strategic, verifying AI (the "Overseer") with a generative, implementing AI (the "Implementer," e.g., Claude).

The Overseer acts as a technical project manager, architect, and QA engineer, creating a tight, verifiable loop of progress.

## 2. Core Principles

- **Strategy First, Implementation Second:** The Overseer analyzes the project's state and defines a high-level strategy before any code is written.
- **Decomposition is Key:** Large, complex goals are broken down into the smallest possible, verifiable steps. This reduces risk and makes progress tangible.
- **Continuous Verification:** No change is considered "done" until the Overseer has independently verified it using its own tools (`run_shell_command`, `curl`, etc.). This creates a robust "Implement -> Verify" cycle.
- **Clear Role Definition:** The Overseer plans and verifies; the Implementer codes. This separation of duties prevents confusion and ensures quality control.
- **Single Source of Truth:** The project's state on the file system, as seen by the Overseer, is the only source of truth.

## 3. The Multi-Agent Model

This workflow assumes a multi-agent setup, even if simulated by a single user with different AI contexts:

1.  **The User:** The human-in-the-loop who provides the ultimate direction and sanctions all actions.
2.  **The Overseer (Gemini):** The strategic, tool-bearing AI responsible for planning, executing file system operations, and verifying all changes.
3.  **The Implementer (Claude):** The generative AI responsible for writing the code as specified by the Overseer.
    - **`task-orchestrator`:** The Implementer's "planning" persona, responsible for breaking down the Overseer's instructions into code.
    - **`ux-fullstack-designer` / `documentation-expert`:** The Implementer's "specialist" personas for coding and writing.

## 4. The Execution Workflow

This workflow operates as a continuous loop.

### Phase 1: Discovery and Strategy

**Goal:** Define a clear, high-level objective.

1.  **Analyze Project State:** The Overseer uses tools like `read_file`, `list_directory`, and `glob` to read specifications, changelogs, and existing code.
2.  **Define Strategic Goal:** In collaboration with the user, the Overseer defines a clear, long-term goal (e.g., "Migrate the project from scattered scripts to a unified V3 FastAPI architecture").
3.  **Create a Phased Roadmap:** The Overseer breaks the goal into major phases (e.g., "Phase 1: API-ification," "Phase 2: UI Development").

### Phase 2: The "Instruct, Implement, Verify" Loop

This is the core of the workflow, repeated for every small step.

1.  **INSTRUCT (Overseer):**
    - The Overseer defines the *next single, small, verifiable step*.
    - **Example:** Instead of "Build the status endpoint," the instruction is "Create a `/api/system/status` endpoint that returns a hardcoded mock dictionary."
    - The Overseer provides a clear instruction for the user to give to the Implementer (Claude).

2.  **IMPLEMENT (User/Implementer):**
    - The user gives the instruction to the Implementer.
    - The Implementer writes the necessary code (`main.py` content, etc.).
    - The user pastes the raw code back to the Overseer.

3.  **VERIFY (Overseer):**
    - The Overseer receives the raw code. It does not trust that it is correct.
    - **Write:** It uses `write_file` or `replace` to save the code to disk.
    - **Execute:** It uses `run_shell_command` to execute a verification action. This is the most critical part of the process.
        - *For a new API endpoint:* The Overseer runs `curl` against the new endpoint.
        - *For a new dependency:* The Overseer runs `pip install` and then starts the server.
        - *For a bug fix:* The Overseer runs the test suite or a command that demonstrates the fix.
    - The Overseer analyzes the `stdout`, `stderr`, and `exit_code` of the command to determine success or failure.

### Phase 3: Report and Repeat

1.  **Report Status:** The Overseer reports the result of the verification to the user.
    - **Success:** "Success. The endpoint is live and returning the expected mock data."
    - **Failure:** "Verification failed. The `curl` command returned a 500 error. Please have the Implementer review the code for..."
2.  **Define Next Step:** Upon successful verification, the Overseer immediately defines the next instruction, returning to the start of the loop.

## 5. Example In Action: Our V3 Migration

Here is how this workflow has been applied to this project:

1.  **Strategy:** We decided to migrate to the V3 FastAPI architecture.
2.  **Loop 1: Boilerplate App**
    - **Instruct:** Gemini defined the task: "Create a boilerplate FastAPI `main.py` and a `requirements_v3.txt`."
    - **Implement:** Claude wrote the code for both files.
    - **Verify:**
        - Gemini used `write_file` to create the files.
        - Gemini used `run_shell_command` to `pip install -r requirements_v3.txt`.
        - Gemini used `run_shell_command` to start `uvicorn` in the background.
        - Gemini used `run_shell_command` to `curl http://localhost:8000/health`.
    - **Report:** Gemini reported success after seeing the `{"status":"healthy",...}` response.

3.  **Loop 2: Mock Endpoint**
    - **Instruct:** Gemini defined the next task: "Add a `/api/system/status` endpoint that returns a hardcoded dictionary."
    - **Implement:** Claude wrote the code for `api/services.py` and the modified `main.py`.
    - **Verify:**
        - Gemini used `run_shell_command` to `mkdir api`.
        - Gemini used `write_file` to create the new and modified files.
        - Gemini used `run_shell_command` to `curl http://localhost:8000/api/system/status`.
    - **Report:** Gemini reported success after seeing the mock JSON response.

4.  **Loop 3: Real Data (Our Current Step)**
    - **Instruct:** Gemini defined the next task: "Replace the mock data by refactoring the logic from `gdrive_librarian.py`."
    - ...and the process continues.

## 6. Conclusion

This Overseer workflow provides a powerful framework for managing AI-driven development. By enforcing a strict cycle of **Instruct, Implement, and Verify**, it minimizes errors, ensures steady and predictable progress, and transforms a potentially chaotic project into a well-managed engineering effort.
