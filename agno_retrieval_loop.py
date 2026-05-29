#!/usr/bin/env python3
"""
agno_retrieval_loop.py
-----------------------
Final retrieval loop for the AI File Organizer.
Indexes a designated organized file directory and provides a searchable 
natural language query interface (RAG) using Agno and Google Gemini.
"""

import os
import sys
import argparse
from pathlib import Path

# Try to import Agno and its dependencies
try:
    from agno.agent import Agent
    from agno.db.sqlite import SqliteDb
    from agno.tools.file import FileTools
    from agno.models.google import Gemini
except ImportError as e:
    print(f"❌ Error: Missing required dependencies. Please run:\n"
          f"   pip install agno sqlalchemy google-genai\n"
          f"   Original error: {e}", file=sys.stderr)
    sys.exit(1)


def resolve_db_path() -> str:
    """
    Resolve the database path in compliance with the local system rules.
    On Ryan's system, this resolves to /Users/ryanthomson/AI_METADATA_SYSTEM/databases/archive_index.db.
    On other systems (forks), it creates a similar ~/AI_METADATA_SYSTEM/databases/ directory.
    """
    home = Path.home()
    metadata_dir = home / "AI_METADATA_SYSTEM"
    db_dir = metadata_dir / "databases"
    
    # Ensure local directory exists
    try:
        db_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        # Fallback to local workspace if home directory is read-only
        print("⚠️ Permission denied creating database directory under home. Falling back to local workspace.")
        db_dir = Path("./")
        
    return str(db_dir / "archive_index.db")


def get_retrieval_agent(directory_path: str, db_path: str) -> Agent:
    """
    Initialize and return the Agno Agent configured with local File Tools and SQLite DB.
    """
    # Ensure the target directory exists
    os.makedirs(directory_path, exist_ok=True)
    
    # Initialize the Google Gemini model. Uses GEMINI_API_KEY or GOOGLE_API_KEY from env
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    model = Gemini(id="gemini-2.5-flash", api_key=api_key)
    
    # Set up SQLite storage for agent sessions/runs
    storage = SqliteDb(
        db_file=db_path,
        session_table="archive_sessions",
    )
    
    agent = Agent(
        name="Archive_Navigator",
        role="Search and retrieve context from the finalized file structure",
        model=model,
        tools=[FileTools(base_dir=Path(directory_path))],
        db=storage,
        description="This agent provides the final retrieval loop for the ai-file-organizer repo.",
        instructions=[
            "Always search the local directory before answering.",
            "Use the provided file tools to list, read, or search files within the base directory.",
            "Provide file paths and metadata for all retrieved items.",
            "If a file structure regression or unexpected file layout is found, note it in the output.",
            "Format your responses cleanly in Markdown."
        ],
        markdown=True
    )
    
    return agent


def main():
    parser = argparse.ArgumentParser(description="AI File Organizer: Final Retrieval Loop (Agno Agent)")
    parser.add_argument(
        "--dir", 
        default="./organized_files", 
        help="Target organized files directory to scan/index (default: ./organized_files)"
    )
    parser.add_argument(
        "--query", 
        type=str, 
        help="Run a single query and exit. If omitted, starts an interactive shell."
    )
    args = parser.parse_args()

    # Determine paths
    target_dir = os.path.abspath(args.dir)
    db_file_path = resolve_db_path()

    print("==========================================================")
    print("🤖 AI File Organizer: Final Retrieval Loop (Agno Agent)")
    print("==========================================================")
    print(f"📂 Indexing target: {target_dir}")
    print(f"🗄️  Local database: {db_file_path}")
    print("----------------------------------------------------------")

    # Get the retrieval agent
    agent = get_retrieval_agent(target_dir, db_file_path)

    # Execute query or start loop
    if args.query:
        print(f"\n💬 Query: {args.query}\n")
        agent.print_response(args.query)
    else:
        print("\n✨ Ready! Enter your queries below (type 'exit' or 'quit' to end).")
        while True:
            try:
                query = input("\n🔍 Query > ").strip()
                if not query:
                    continue
                if query.lower() in ("exit", "quit"):
                    print("Goodbye!")
                    break
                
                print(f"\n💬 Response:")
                agent.print_response(query)
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error during retrieval: {e}")


if __name__ == "__main__":
    main()
