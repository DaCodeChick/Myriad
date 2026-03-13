# CORE ARCHITECTURAL DIRECTIVES FOR PROJECT MYRIAD

## Development Environment
**Package Management:** This project uses `uv` for Python package management. Use `uv pip install <package>` or `uv run <command>` instead of pip directly.

## Architecture Rules

1. **Language & Ecosystem:** All code must be written in Python 3.10+. Use `discord.py` for the bot framework. Do not use heavy ORMs like SQLAlchemy; use native `sqlite3` for absolute speed and control.
2. **The Polymorphic Engine:** The bot does NOT have a hardcoded persona. Personas are stored as hot-swappable `.json` cartridges in a `personas/` directory.
3. **State Management:** All state, active persona tracking, and memories MUST be stored in a local SQLite database (`database/myriad_state.db`).
4. **The Memory Router:** Memory is NOT a flat text file. Every memory logged in the database must have a `visibility_scope` of either 'GLOBAL' (shared across all personas) or 'ISOLATED' (only accessible to the persona that recorded it).
5. **Hybrid Memory Architecture (CRITICAL):** The bot uses a two-tier memory system:
   - **Short-Term Memory:** Last N messages (default: 10) in exact chronological order for immediate conversation flow
   - **Long-Term Semantic Memory:** ChromaDB vector search for recalling older, contextually relevant conversations
   - **Context Construction Order:**
     1. System Prompt (persona + rules)
     2. Long-Term Recalled Context (from ChromaDB semantic search)
     3. Short-Term Conversation History (last 10 messages chronologically)
     4. Current user message
   - This prevents "Alzheimer's disease" where the bot loses track of the immediate conversation while maintaining long-term semantic recall.
6. **Code Style:** Keep files modular. Do not dump everything into `main.py`. Separate the database logic, the Discord event loop, and the LLM API calls.
7. **Decoupled Frontend (The Adapter Pattern):** The core intelligence, memory routing, and LLM logic MUST be completely platform-agnostic. Create an `AgentCore` class that only deals in raw text and JSON. Do not import `discord` into the core logic. Discord support must be built as a separate "Frontend Adapter" that imports `AgentCore` and bridges the platform to the engine.
