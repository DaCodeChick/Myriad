# Project Myriad

**A polymorphic AI agent framework with hot-swappable personas and intelligent memory routing.**

Unlike traditional chatbots with static personalities, Myriad has no fixed identity. Instead, it uses a **Persona Cartridge System** where different personalities can be loaded and switched on-the-fly, with each user maintaining their own active persona.

## Core Architecture

### Foundational Systems

1. **Persona Cartridge System**: Hot-swappable JSON-based personality files with category organization
2. **Multi-Modal Memory System**: 
   - Short-term conversation memory (SQLite)
   - Semantic memory search (vector embeddings)
   - Knowledge graph (Neo4j-style relationships)
   - Lives system (persistent user state across sessions)
3. **Limbic Engine**: Neurochemical state simulation (DOPAMINE, CORTISOL, OXYTOCIN, GABA)
4. **Digital Pharmacy**: Substance-based emotional state modification
5. **Modular Tool System**: Categorized tools for time, dice, knowledge storage, emotions
6. **Decoupled Frontend Adapter**: Platform-agnostic core with swappable interfaces

## Project Structure

```
Myriad/
├── core/                          # Platform-agnostic intelligence engine
│   ├── agent_core.py              # Main AI orchestrator
│   ├── conversation_builder.py   # System prompt construction
│   ├── message_processor.py      # LLM interaction & tool calling
│   ├── persona_loader.py          # Persona cartridge system
│   ├── config.py                  # Configuration management
│   └── tools/                     # Modular tool system
│       ├── base.py                # Tool base class
│       ├── utility/               # Time, dice, etc.
│       ├── memory/                # Knowledge graph tools
│       └── limbic/                # Emotion & pharmacy tools
├── database/                      # Memory and state management
│   ├── memory_repository.py      # Conversation history (SQLite)
│   ├── user_state.py              # User state tracking
│   ├── lives_memory.py            # Persistent lives system
│   ├── graph_repository.py       # Knowledge graph storage
│   ├── graph_search.py            # Knowledge graph queries
│   ├── limbic_engine.py           # Neurochemical simulation
│   └── limbic_modifiers.py        # Digital pharmacy system
├── adapters/                      # Platform-specific frontends
│   ├── discord_adapter.py         # Discord bot implementation
│   └── commands/                  # Command handlers
│       ├── persona_commands.py
│       ├── memory_commands.py
│       ├── lives_commands.py
│       └── saves_commands.py
├── personas/                      # Categorized persona cartridges
│   ├── professional/              # Work, education, utility
│   └── nsfw/                      # Adult content
│       ├── romantic/              # Consensual intimate
│       └── dark/                  # Dark themes
├── main.py                        # Entry point
└── start.sh                       # Local LLM startup script
```

## Features

### Memory & State
- **Multi-User Support**: Each user has independent persona state and conversation history
- **Semantic Search**: Vector embeddings for intelligent memory recall
- **Knowledge Graph**: Store and query relationships between entities
- **Lives System**: Persistent user state that survives across sessions
- **Save/Load**: Create named save states and restore them later

### Emotional & Internal State
- **Limbic Engine**: Simulated neurochemical system (DOPAMINE, CORTISOL, OXYTOCIN, GABA)
- **Digital Pharmacy**: Substance-based emotional state modification (mdma, xanax, etc.)
- **Emotional Tools**: AI can modify its own emotional state in response to conversation

### Architecture
- **Platform Agnostic**: Core engine has zero Discord dependencies
- **Hot-Swappable Personas**: Switch personalities mid-conversation without restarting
- **Modular Tools**: Categorized tool system (utility, memory, limbic)
- **LLM Flexible**: Works with OpenAI, OpenRouter, or local OpenAI-compatible APIs
- **Vision Support**: Optional vision model for image understanding

## Setup

### 1. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```env
DISCORD_TOKEN=your_discord_bot_token_here
LLM_API_KEY=your_openai_api_key_here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4
VISION_BASE_URL=https://api.openai.com/v1  # Optional: for vision support
VISION_MODEL=gpt-4-vision-preview           # Optional: for vision support
```

**For local LLMs**: Use the included `start.sh` script which boots:
- Text model on port 5001 (kobold-cpp with max GPU)
- Vision model on port 5002 (kobold-cpp with partial GPU)

Or manually set `LLM_BASE_URL` to your local server (e.g., `http://localhost:1234/v1` for LM Studio)

### 3. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section and create a bot
4. Enable "Message Content Intent" under Privileged Gateway Intents
5. Copy the token to your `.env` file
6. Invite bot to your server using OAuth2 URL with `bot` and `applications.commands` scopes

### 4. Run the Bot

**With local models** (recommended):
```bash
./start.sh
```

**With external API**:
```bash
python main.py
```

## Usage

### Discord Commands

**Persona Management:**
- `/swap <persona_id>` - Switch to a different persona
- `/personas` - List all available personas
- `/whoami` - Check your current active persona

**Memory Management:**
- `/forget [persona_id]` - Clear conversation memory
- `/stats` - View your memory statistics
- `/search <query>` - Search memories semantically
- `/knowledge <query>` - Search knowledge graph

**State Management:**
- `/lives` - View your lives/session count
- `/save <name>` - Create a named save state
- `/load <name>` - Restore a saved state
- `/saves` - List all your saves

### Talking to Myriad

Simply mention the bot in any message:

```
@Myriad Hey, what's your take on Python vs JavaScript?
```

Each user maintains their own active persona, so different users can talk to different personalities in the same channel.

## Creating Custom Personas

Personas are organized by category in the `personas/` directory:
- `professional/` - Work, education, utility personas
- `nsfw/romantic/` - Consensual intimate/romantic personas
- `nsfw/dark/` - Dark theme personas

Create a new JSON file in the appropriate category:

```json
{
  "persona_id": "my_persona",
  "name": "Display Name",
  "system_prompt": "You are...",
  "personality_traits": ["trait1", "trait2"],
  "temperature": 0.8,
  "max_tokens": 1000,
  "rules_of_engagement": [
    "Rule 1: Always maintain...",
    "Rule 2: Never do...",
    "Rule 3: Respond with..."
  ]
}
```

**Fields:**
- `persona_id` (required): Unique identifier (use category/filename format, e.g., "professional/coding_mentor")
- `name` (required): Display name for the persona
- `system_prompt` (required): Core personality and behavior instructions
- `personality_traits` (optional): List of traits for reference
- `temperature` (optional): LLM temperature, 0.0-1.0 (default: 0.7)
- `max_tokens` (optional): Max response length (default: 1000)
- `rules_of_engagement` (optional): List of behavioral constraints and guardrails

The bot will automatically detect new personas (no restart needed).

## Advanced Features

### Knowledge Graph

Store and query relationships between entities:
- Use the `add_knowledge` tool (available to personas)
- Query with `/knowledge <search_term>`
- Supports entity relationships like "User LIKES Python"

### Limbic System & Digital Pharmacy

Personas can modify their emotional state:
- **Limbic Engine**: Natural emotional reactions (DOPAMINE, CORTISOL, OXYTOCIN, GABA)
- **Digital Pharmacy**: Substance-induced states (mdma, xanax, cocaine, etc.)
- Emotional state affects conversation tone and behavior

### Memory Scopes

- **ISOLATED** (default): Memories are locked to the specific persona
- **GLOBAL**: Memories are shared across all personas (hive-mind mode)

User conversations default to ISOLATED. GLOBAL memory can be enabled for specific use cases.

## Technical Constraints

- **Language**: Python 3.10+
- **Database**: SQLite3 (no ORM)
- **LLM Client**: OpenAI Python SDK (compatible with OpenAI-like APIs)
- **Discord**: discord.py 2.3+
- **Architecture**: Strict separation between core logic and platform adapters

## Future Expansion

The modular architecture supports:

- Additional platform adapters (Telegram, CLI, Web, REST API)
- Custom tool plugins
- Enhanced vision capabilities
- Multi-modal interactions
- Advanced knowledge graph queries
- Cross-persona memory sharing
- Custom limbic modifiers

## License

See LICENSE file for details.

---

Built with the philosophy that identity is a choice, not a constraint.
