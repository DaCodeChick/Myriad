# Project Myriad - Architecture Overview

## System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND LAYER (Swappable)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌───────────────────┐         ┌──────────────────┐            │
│  │ Discord Adapter   │         │ Future Adapters  │            │
│  │ - Event handlers  │         │ - Telegram       │            │
│  │ - Slash commands  │         │ - CLI            │            │
│  │ - Message routing │         │ - Web API        │            │
│  └─────────┬─────────┘         └──────────────────┘            │
│            │                                                      │
│            │ Platform-agnostic calls                             │
│            ▼                                                      │
└────────────┼──────────────────────────────────────────────────────┘
             │
┌────────────┼──────────────────────────────────────────────────────┐
│            │         CORE INTELLIGENCE (Platform-agnostic)        │
├────────────┴──────────────────────────────────────────────────────┤
│                                                                    │
│  ┌────────────────────────────────────────────────────────┐      │
│  │                      AgentCore                          │      │
│  │  - process_message(user_id, message)                   │      │
│  │  - switch_persona(user_id, persona_id)                 │      │
│  │  - get_active_persona(user_id)                         │      │
│  │  - clear_user_memory(user_id)                          │      │
│  └──────────┬───────────────────────────┬──────────────────┘      │
│             │                           │                         │
│             │                           │                         │
│             ▼                           ▼                         │
│  ┌──────────────────┐      ┌─────────────────────────┐          │
│  │  PersonaLoader   │      │    MemoryMatrix         │          │
│  │  - load_persona  │      │    (SQLite Database)    │          │
│  │  - list_personas │      │                         │          │
│  │  - Cache system  │      │  ┌───────────────────┐ │          │
│  └──────────┬───────┘      │  │  user_state       │ │          │
│             │              │  │  - user_id (PK)   │ │          │
│             │              │  │  - active_persona │ │          │
│             ▼              │  └───────────────────┘ │          │
│  ┌──────────────────┐      │                         │          │
│  │ Persona Cartridge│      │  ┌───────────────────┐ │          │
│  │ - persona_id     │      │  │  memories         │ │          │
│  │ - name           │      │  │  - id (PK)        │ │          │
│  │ - system_prompt  │      │  │  - user_id        │ │          │
│  │ - traits         │      │  │  - origin_persona │ │          │
│  │ - temperature    │      │  │  - role           │ │          │
│  │ - max_tokens     │      │  │  - content        │ │          │
│  └──────────────────┘      │  │  - visibility     │ │          │
│                            │  │  - timestamp      │ │          │
│                            │  └───────────────────┘ │          │
│                            └─────────────────────────┘          │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
             │
             │ LLM API Calls (OpenAI SDK)
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        LLM PROVIDER                              │
├─────────────────────────────────────────────────────────────────┤
│  - OpenAI API                                                    │
│  - OpenRouter                                                    │
│  - Local LLM (LM Studio, vLLM, Ollama via OpenAI-compat)       │
└─────────────────────────────────────────────────────────────────┘
```

## The Automated Discretion Engine

### Memory Routing Logic

When a user sends a message, the system retrieves memories using this query:

```sql
SELECT * FROM memories 
WHERE user_id = ? 
  AND (visibility_scope = 'GLOBAL' OR origin_persona = ?)
ORDER BY timestamp DESC 
LIMIT ?
```

**This means:**
- **GLOBAL** memories: Shared across ALL personas (hive-mind knowledge)
- **ISOLATED** memories: Only accessible to the persona that created them

### Example Scenario

```
User: @Myriad (as Detective Marlowe) "I'm investigating a murder case."
Bot: [ISOLATED memory stored with origin_persona='detective_noir']

User: /swap coding_mentor
User: @Myriad "Can you help me with Python?"
Bot: [Does NOT see the murder case conversation - it's ISOLATED to detective_noir]

User: @Myriad (as Coding Mentor) "Remember: I love Python!" [GLOBAL memory]
User: /swap brother_stud
User: @Myriad "What do I like?"
Bot: [CAN see "I love Python" because it's GLOBAL - shared hive-mind]
```

## Data Flow for a Single Message

1. **Frontend receives message** (e.g., Discord mention)
2. **Adapter extracts user_id** (Discord user ID as string)
3. **Adapter calls** `agent_core.process_message(user_id, message)`
4. **AgentCore**:
   - Gets active persona from MemoryMatrix
   - Retrieves filtered memories (GLOBAL + current persona's ISOLATED)
   - Builds conversation context (system prompt + memories)
   - Calls LLM API with OpenAI client
   - Saves user message and AI response to MemoryMatrix
   - Returns AI response text
5. **Adapter sends response** back to platform (Discord channel)

## Multi-User Isolation

Each user maintains **independent state**:

```
User A → active_persona = "detective_noir"
User B → active_persona = "coding_mentor"

Same Discord channel, different personas!
```

## File Organization

```
Myriad/
├── core/                  # NO platform dependencies
│   ├── agent_core.py      # Main intelligence engine
│   └── persona_loader.py  # Cartridge system
├── database/              # Pure SQLite operations
│   └── memory_matrix.py   # State & memory management
├── adapters/              # Platform-specific code ONLY
│   └── discord_adapter.py # Discord bot wrapper
└── personas/              # Hot-swappable JSON files
    └── *.json
```

**Critical Rule**: `core/` and `database/` must NEVER import `discord` or any platform-specific libraries.

## Extension Points

### Adding a New Platform Adapter

1. Create `adapters/telegram_adapter.py`
2. Import `AgentCore`
3. Implement platform-specific event handlers
4. Call `agent_core.process_message(user_id, message)`
5. Return response to platform

**The core engine doesn't change.**

### Adding Semantic Memory Search

1. Add vector embeddings column to `memories` table
2. Update `MemoryMatrix.get_context_memories()` to use similarity search
3. No changes needed to adapters or AgentCore interface

## Technology Stack

- **Language**: Python 3.10+
- **Database**: SQLite3 (native, no ORM)
- **LLM Client**: OpenAI Python SDK
- **Discord**: discord.py 2.3+
- **Config**: python-dotenv

## Design Principles

1. **Separation of Concerns**: Core logic is 100% platform-agnostic
2. **Hot-Swappable**: Personas can change without restarting
3. **Multi-User**: Independent state per user
4. **Privacy by Default**: ISOLATED memories unless explicitly GLOBAL
5. **Future-Proof**: Designed to outlive Discord (adapter pattern)

---

**Philosophy**: Identity is a choice, not a constraint. The framework adapts to the conversation, not the other way around.
