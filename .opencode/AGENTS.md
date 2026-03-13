# CORE ARCHITECTURAL DIRECTIVES FOR PROJECT MYRIAD

## Development Environment
**Package Management:** This project uses `uv` for Python package management. Use `uv pip install <package>` or `uv run <command>` instead of pip directly.

## Directory Structure
- **`database/`**: Python modules for database logic (code only, no .db files)
- **`data/`**: Runtime database files (SQLite .db files, ChromaDB vector store) - **NEVER commit to git**
- **`personas/`**: Persona cartridge JSON files
- **`core/`**: Platform-agnostic AI engine
- **`adapters/`**: Platform-specific frontends (Discord, etc.)

## Architecture Rules

1. **Language & Ecosystem:** All code must be written in Python 3.10+. Use `discord.py` for the bot framework. Do not use heavy ORMs like SQLAlchemy; use native `sqlite3` for absolute speed and control.
2. **The Polymorphic Engine:** The bot does NOT have a hardcoded persona. Personas are stored as hot-swappable `.json` cartridges in a `personas/` directory.
3. **State Management:** All state, active persona tracking, and memories MUST be stored in a local SQLite database (`data/myriad_state.db`). Database files live in `data/`, NOT in `database/` (which is for code).
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
7. **Tool Use (Function Calling):** The bot supports tool/function calling where the LLM can request to execute predefined Python functions (like getting the current time or rolling dice). Tools are registered in `core/tool_registry.py` and executed through a loop in `core/agent_core.py`:
   - **Tool Execution Loop:**
     1. LLM receives tool definitions in the system prompt
     2. When LLM needs a tool, it outputs JSON: `{"tool": "tool_name", "arguments": {...}}`
     3. Python detects the JSON, executes the function, and injects the result back into conversation
     4. LLM reads the result and provides final response to user
   - **Configurable via environment:**
     - `TOOLS_ENABLED=true` - Enable/disable tool use
     - `MAX_TOOL_ITERATIONS=5` - Maximum tool calls per message (prevents infinite loops)
   - **Built-in Tools:**
     - `get_current_time()` - Returns current date/time
     - `roll_dice(sides)` - Rolls a dice with N sides
   - Tools remain platform-agnostic (no Discord imports in tool logic)
8. **Decoupled Frontend (The Adapter Pattern):** The core intelligence, memory routing, and LLM logic MUST be completely platform-agnostic. Create an `AgentCore` class that only deals in raw text and JSON. Do not import `discord` into the core logic. Discord support must be built as a separate "Frontend Adapter" that imports `AgentCore` and bridges the platform to the engine.
