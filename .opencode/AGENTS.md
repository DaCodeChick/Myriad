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
5. **Hybrid Memory Architecture (CRITICAL):** The bot uses a multi-tier memory system:
   - **Short-Term Memory:** Last N messages (default: 10) in exact chronological order for immediate conversation flow
   - **Long-Term Semantic Memory:** ChromaDB vector search for recalling older, contextually relevant conversations
   - **Knowledge Graph Memory:** Entity-relationship storage for factual knowledge (people, preferences, facts about the world)
   - **Context Construction Order:**
     1. System Prompt (persona + rules + tool definitions)
     2. Knowledge Graph Context (relevant facts extracted by keywords from user message)
     3. Long-Term Recalled Context (from ChromaDB semantic search)
     4. Short-Term Conversation History (last 10 messages chronologically)
     5. Current user message
   - This prevents "Alzheimer's disease" where the bot loses track of the immediate conversation while maintaining long-term semantic recall and factual knowledge.
6. **Code Style:** Keep files modular. Do not dump everything into `main.py`. Separate the database logic, the Discord event loop, and the LLM API calls.
7. **Tool Use (Function Calling):** The bot supports tool/function calling where the LLM can request to execute predefined Python functions. Tools are registered in `core/tool_registry.py` and executed through a loop in `core/agent_core.py`:
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
     - `add_knowledge(entity1, entity1_type, relation, entity2, entity2_type)` - Stores facts in knowledge graph
   - Tools remain platform-agnostic (no Discord imports in tool logic)
8. **Knowledge Graph Memory:** The bot can permanently store factual knowledge as entity-relationship triplets:
   - **Database:** SQLite-based graph (`database/graph_memory.py`) with two tables:
     - `entities` - Nodes (people, concepts, objects, etc.) with id, name, type, description
     - `relationships` - Edges (source_id, target_id, relation_type)
   - **Storage Tool:** LLM can call `add_knowledge()` to store facts:
     - Example: `add_knowledge("Schala", "User", "LIKES", "Gentle Possession", "Concept")`
   - **Retrieval Pipeline:** 
     1. Extract keywords from user message
     2. Search entities table for matching names
     3. Retrieve all connected relationships
     4. Inject as `[Knowledge Graph Context]` at top of system prompt
   - **Configurable via environment:**
     - `GRAPH_MEMORY_ENABLED=true` - Enable/disable knowledge graph
     - `GRAPH_DB_PATH=data/knowledge_graph.db` - Path to graph database
   - The graph is automatically queried on every message to inject relevant factual context
9. **Decoupled Frontend (The Adapter Pattern):** The core intelligence, memory routing, and LLM logic MUST be completely platform-agnostic. Create an `AgentCore` class that only deals in raw text and JSON. Do not import `discord` into the core logic. Discord support must be built as a separate "Frontend Adapter" that imports `AgentCore` and bridges the platform to the engine.
