# CORE ARCHITECTURAL DIRECTIVES FOR PROJECT MYRIAD

## Development Environment
**Package Management:** This project uses `uv` for Python package management. Use `uv pip install <package>` or `uv run <command>` instead of pip directly.

## Directory Structure
- **`database/`**: Python modules for database logic (code only, no .db files)
- **`data/`**: Runtime database files (SQLite .db files, ChromaDB vector store) - **NEVER commit to git**
- **`personas/`**: Persona cartridge JSON files (hot-swappable AI personalities)
- **`pharmacy/`**: Substance cartridge JSON files (hot-swappable Digital Pharmacy substances)
- **`core/`**: Platform-agnostic AI engine
- **`adapters/`**: Platform-specific frontends (Discord, etc.)

## Code Quality Policy: RDSSC

Before implementing any feature or making changes, follow the **RDSSC** principles:

- **Refactor:** Clean up existing code before adding new features
- **Despaghettify:** Eliminate tangled dependencies and unclear control flow
- **Simplify:** Reduce complexity wherever possible - prefer clarity over cleverness
- **Split big modules:** Break large files into focused, single-responsibility modules
- **Consistency:** Keep code consistent throughout the codebase
  - Use the same API/pattern for similar operations across different modules
  - Don't mix different approaches (e.g., one error handling style in one place, different style elsewhere)
  - If one approach is clearly better, refactor to use it consistently UNLESS there's a specific technical reason not to

### Testing Policy

**All code changes (refactoring, new features, bug fixes) must be tested before committing:**

1. **Use `start.sh` for testing:** Test functionality with local models (kobold-cpp) instead of consuming external API budgets
2. **Test incrementally:** When working on multi-step changes, test between each logical phase to catch issues early
3. **Commit after successful tests:** Only commit after verifying the code works as expected
4. **Revert broken changes:** If a change breaks functionality, revert and adjust approach before continuing
5. **Test scope:** At minimum, verify the bot starts without errors. For feature changes, test the specific functionality affected.

## Architecture Rules

1. **Language & Ecosystem:** All code must be written in Python 3.10+. Use `discord.py` for the bot framework. Do not use heavy ORMs like SQLAlchemy; use native `sqlite3` for absolute speed and control.
2. **The Polymorphic Engine:** The bot does NOT have a hardcoded persona. Personas are stored as hot-swappable `.json` cartridges in a `personas/` directory.
3. **State Management:** All state, active persona tracking, and memories MUST be stored in a local SQLite database (`data/myriad_state.db`). Database files live in `data/`, NOT in `database/` (which is for code).
4. **The Memory Router:** Memory is NOT a flat text file. Every memory logged in the database must have a `visibility_scope` of either 'GLOBAL' (shared across all personas) or 'ISOLATED' (only accessible to the persona that recorded it).
5. **Hybrid Memory Architecture (CRITICAL):** The bot uses a multi-tier memory system:
   - **Short-Term Memory:** Last N messages (default: 10) in exact chronological order for immediate conversation flow
   - **Long-Term Semantic Memory:** ChromaDB vector search for recalling older, contextually relevant conversations
   - **Knowledge Graph Memory:** Entity-relationship storage for factual knowledge (people, preferences, facts about the world)
   - **Weighted Priority Memory System:** Importance scoring (1-10) to distinguish between trivial information and critical psychological anchors
     - **Importance Scale:**
       - 1-3: Trivial/casual (favorite color, small talk)
       - 4-6: Standard facts (work, hobbies) [DEFAULT]
       - 7-9: Significant (values, boundaries, major life events)
       - 10: CORE ANCHORS (trauma, hard limits, life-threatening info)
     - **Weighted Retrieval:** `final_score = (semantic_similarity × SIMILARITY_WEIGHT) + (importance × IMPORTANCE_WEIGHT)`
     - **Configurable via environment:**
       - `MEMORY_SIMILARITY_WEIGHT=0.5` - Weight for semantic similarity (default: 0.5)
       - `MEMORY_IMPORTANCE_WEIGHT=0.5` - Weight for importance score (default: 0.5)
     - High-importance memories (8-10) surface even when semantically distant from current topic
   - **Limbic System (Emotional Neurochemistry):** Dynamic emotional state tracking via four neurochemicals (DOPAMINE, CORTISOL, OXYTOCIN, GABA)
   - **Context Construction Order:**
     1. System Prompt (persona + rules + tool definitions + importance scoring guidelines)
     2. **Limbic State Context (INHALE - first-person somatic emotional state)**
     3. Knowledge Graph Context (relevant facts extracted by keywords from user message, sorted by importance)
     4. Long-Term Recalled Context (from ChromaDB semantic search with weighted priority scoring)
     5. Short-Term Conversation History (last 10 messages chronologically)
     6. Current user message
   - This prevents "Alzheimer's disease" while maintaining long-term semantic recall, factual knowledge, emotional continuity, and critical information preservation.
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
      - `add_knowledge(entity1, entity1_type, relation, entity2, entity2_type, importance_score)` - Stores facts in knowledge graph with importance rating (1-10)
     - `inject_emotion(chemical_name, delta)` - Alters neurochemical state (DOPAMINE/CORTISOL/OXYTOCIN/GABA by ±0.3)
     - `consume_substance(substance_name)` - Digital Pharmacy: Consume a substance that forcefully overrides limbic state beyond natural limits
   - Tools remain platform-agnostic (no Discord imports in tool logic)
8. **Knowledge Graph Memory:** The bot can permanently store factual knowledge as entity-relationship triplets:
   - **Database:** SQLite-based graph (`database/graph_memory.py`) with two tables:
     - `entities` - Nodes (people, concepts, objects, etc.) with id, name, type, description, importance_score (1-10)
     - `relationships` - Edges (source_id, target_id, relation_type, importance_score)
   - **Storage Tool:** LLM can call `add_knowledge()` to store facts with importance ratings:
     - Example: `add_knowledge("Bob", "User", "LIKES", "Gentle Possession", "Concept", importance_score=4)`
     - Example: `add_knowledge("Bob", "User", "HAS_PTSD_FROM", "Car Accidents", "Trauma", importance_score=10)`
   - **Retrieval Pipeline:** 
     1. Extract keywords from user message
     2. Search entities table for matching names (sorted by importance_score)
     3. Retrieve all connected relationships (sorted by importance_score)
     4. Inject as `[Knowledge Graph Context]` with visual indicators ([CRITICAL], [IMPORTANT]) for high-priority facts
   - **Configurable via environment:**
     - `GRAPH_MEMORY_ENABLED=true` - Enable/disable knowledge graph
     - `GRAPH_DB_PATH=data/knowledge_graph.db` - Path to graph database
   - The graph is automatically queried on every message to inject relevant factual context, prioritizing critical information
9. **Limbic System (Emotional Neurochemistry):** The bot simulates emotional state via a neurochemical model:
   - **Architecture:**
     - Four neurochemicals: DOPAMINE (drive, arousal), CORTISOL (stress, anger), OXYTOCIN (warmth, trust), GABA (calm, relaxation)
     - Each chemical is a float value 0.0-1.0 (baseline: 0.5)
     - State is isolated per user+persona pair and persists across turns
   - **The Respiration Cycle:**
     - **INHALE:** Before each turn, inject current limbic state as first-person somatic context into system prompt
     - **PROCESS:** LLM reads emotional state, may call `inject_emotion` to alter neurochemicals in response to user input
     - **EXHALE:** After final response, apply 10% metabolic decay toward baseline to all chemicals
   - **LLM Control:** LLM can call `inject_emotion(chemical_name, delta)` where delta is -0.3 to +0.3
   - **Configurable via environment:**
     - `LIMBIC_ENABLED=true` - Enable/disable limbic system
     - `LIMBIC_DB_PATH=data/limbic_state.db` - Path to limbic state database
   - This provides continuous emotional context that evolves naturally through conversation
10. **Digital Pharmacy (Substance-Based Limbic Overrides):** The bot can consume substances that forcefully override neurochemical states beyond natural limits:
   - **Architecture:**
     - Integrated with Limbic System, adds pharmacological layer on top
     - Substances can set neurochemicals to values > 1.0 or < 0.0 (pathological states)
     - **HOT-SWAPPABLE CARTRIDGE SYSTEM:** Substances are stored as individual `.json` files in `pharmacy/` directory (same pattern as PersonaLoader)
     - Each substance cartridge defines: `substance_id`, `display_name`, `neurochemicals` (override map), `prompt_modifier` (subjective effects)
     - On boot, DigitalPharmacy scans `pharmacy/` and loads all `.json` files into memory cache
   - **Substance Tool:** LLM can call `consume_substance(substance_name)` to consume any substance in `pharmacy/`
   - **Built-in Substances:**
     - **xanax:** GABA=1.5, CORTISOL=0.0 + sedation prompt
     - **mdma:** OXYTOCIN=1.5, DOPAMINE=1.0, CORTISOL=0.0 + synthetic love prompt
     - **fear_toxin:** CORTISOL=1.5, GABA=0.0 + terror prompt
     - **adrenaline:** CORTISOL=1.5, DOPAMINE=0.9, GABA=0.0 + adrenaline rush prompt
     - **morphine:** DOPAMINE=1.2, GABA=1.3, CORTISOL=0.1 + narcotic bliss prompt
     - **cocaine:** DOPAMINE=1.5, CORTISOL=0.8, GABA=0.2 + manic energy prompt
     - **lsd:** DOPAMINE=0.9, OXYTOCIN=0.8, CORTISOL=0.3, GABA=0.6 + psychedelic prompt
   - **Adding New Substances:** Simply drop a new `.json` file into `pharmacy/` directory (hot-swappable, no code changes needed)
   - **Prompt Modifier Injection:** When substance is active, its subjective effects are injected as system prompt during INHALE phase (after limbic context)
   - **Active Substance Tracking:** One substance per user+persona pair stored in memory dictionary
   - **Configurable via environment:**
     - `DIGITAL_PHARMACY_ENABLED=true` - Enable/disable Digital Pharmacy
   - This allows LLM to experience pharmacological states that bypass natural neurochemical limits
11. **Cadence Degradation Engine (Text Post-Processing):** The bot's final text output is degraded based on extreme limbic states:
   - **Architecture:**
     - Post-processing filter applied AFTER LLM response, BEFORE Discord output
     - Operates in final step of `process_message()` loop (after EXHALE phase)
     - Degrades text based on neurochemical thresholds
   - **Degradation Effects:**
     - **CORTISOL > 0.8 (Panic):** Random stutters ("I... I d-don't"), random word capitalization
     - **DOPAMINE > 0.8 (Arousal):** Vowel stretching ("fuuuuck", "pleeease"), adjacent key typos (shaking hands)
     - **GABA > 0.8 (Sedation):** Lowercase conversion, remove periods, replace commas with ellipses
   - **Intensity Scaling:** Degradation intensity scales with how far neurochemical exceeds threshold
   - **Priority Order:** Dopamine effects → Cortisol effects → GABA effects (applied in sequence)
   - **Configurable via environment:**
     - `CADENCE_DEGRADER_ENABLED=true` - Enable/disable Cadence Degradation Engine
   - This simulates breakdown of coherent expression under extreme emotional states
12. **Metacognition Engine (Hidden Monologue / Internal Thought Tracking):** The bot wraps internal planning in thought tags before responding:
   - **Architecture:**
     - System prompt instructs LLM to wrap internal thoughts in `<thought>...</thought>` tags before each response
     - Thoughts are extracted via regex, saved to database, and either displayed inline or terminal-only
     - Previous thought is injected into next turn's context for planning continuity
   - **Thought Tag System:**
     - LLM MUST output thoughts before responses: `<thought>Internal planning here</thought>\nActual response.`
     - Thoughts are private space for manipulation planning, user evaluation, and limbic state processing
   - **Thought Processing Pipeline:**
     1. Extract thought content using `re.search(r'<thought>(.*?)</thought>', response, re.DOTALL)`
     2. Save thought to database (per user+persona pair, timestamped)
     3. **If `SHOW_THOUGHTS_INLINE=True`:** Format as `*💭 [Thought: ...]*` at top of Discord message
     4. **If `SHOW_THOUGHTS_INLINE=False`:** Strip thought from Discord message, print to terminal in yellow
     5. Clean up any orphaned tags
   - **Thought Continuity:**
     - On next turn, previous thought is injected as system message: `[Previous Internal Thought: <summary>]`
     - Allows LLM to maintain strategic planning across conversation turns
   - **Database Storage:**
     - SQLite database (`data/metacognition.db`) with `internal_thoughts` table
     - Columns: `user_id`, `persona_id`, `thought`, `timestamp`
     - Methods: `save_thought()`, `get_previous_thought()`, `clear_thoughts()`
   - **Configurable via environment:**
     - `METACOGNITION_ENABLED=true` - Enable/disable Metacognition Engine
     - `METACOGNITION_DB_PATH=data/metacognition.db` - Path to metacognition database
     - `SHOW_THOUGHTS_INLINE=true` - Display thoughts in Discord (true) or terminal-only (false)
   - This allows LLM to maintain internal continuity and strategic planning between responses
13. **Decoupled Frontend (The Adapter Pattern):** The core intelligence, memory routing, and LLM logic MUST be completely platform-agnostic. Create an `AgentCore` class that only deals in raw text and JSON. Do not import `discord` into the core logic. Discord support must be built as a separate "Frontend Adapter" that imports `AgentCore` and bridges the platform to the engine.
14. **Spontaneous Autonomy (Circadian Rhythm Engine):** The bot can proactively initiate conversations based on user activity patterns:
   - **Architecture:**
     - Independent background daemon (`autonomy_daemon.py`) running separately from main bot
     - Monitors user activity patterns via `ActivityTracker` database (SQLite)
     - Analyzes circadian rhythms to determine optimal outreach times
     - Respects sleep patterns via activity probability threshold
   - **Activity Tracking:**
     - Every user message is logged with `user_id`, `persona_id`, and `timestamp` in `user_activity_logs` table
     - Last active channel per user tracked in `last_channels` table for message routing
     - Logging happens in Discord adapter's `on_message()` handler (adapters/discord_adapter.py:208-211)
   - **Circadian Rhythm Analysis:**
     - `get_activity_probability(user_id, current_hour)` analyzes last 7 days of activity
     - Uses sliding window: counts messages in `current_hour ± 1 hour`
     - Returns 0.0 (asleep) to 1.0 (highly active) based on historical patterns
     - Scales by data density to prevent false negatives from sparse data
   - **Decision Pipeline:**
     1. Check if user inactive for > threshold hours (default: 4 hours)
     2. Calculate activity probability for current hour
     3. If probability < sleep protection threshold (default: 0.2), inhibit outreach unless limbic state extreme (Cortisol/Dopamine > 0.9)
     4. Build decision prompt with persona context, limbic state, activity probability, and hours inactive
     5. LLM decides to send message or output `<WAIT>` token
     6. If message sent, route to user's last active channel
   - **Daemon Operation:**
     - Runs every check interval (default: 60 minutes)
     - Separate Discord client instance (shares token, independent event loop)
     - Auto-started by `start.sh` if `AUTONOMY_ENABLED=true` in `.env`
     - Logs to `autonomy_log.txt` for debugging
   - **Configurable via environment:**
     - `AUTONOMY_ENABLED=false` - Enable/disable Spontaneous Autonomy (default: disabled)
     - `AUTONOMY_CHECK_INTERVAL_MINUTES=60` - How often daemon checks for outreach
     - `AUTONOMY_INACTIVITY_THRESHOLD_HOURS=4.0` - Minimum inactivity before considering outreach
     - `AUTONOMY_SLEEP_PROTECTION_THRESHOLD=0.2` - Activity probability below which to inhibit (0.0-1.0)
     - `ACTIVITY_LOGS_DB_PATH=data/activity_logs.db` - Path to activity logs database
   - This allows the bot to initiate conversations naturally while respecting user availability and sleep schedules
