# Project Myriad

**A polymorphic AI agent framework with hot-swappable personas and intelligent memory routing.**

Unlike traditional chatbots with static personalities, Myriad has no fixed identity. Instead, it uses a **Persona Cartridge System** where different personalities can be loaded and switched on-the-fly, with each user maintaining their own active persona.

## Core Architecture

### The 4 Foundational Systems

1. **Persona Cartridge System**: Hot-swappable JSON-based personality files
2. **SQLite Memory Matrix**: Multi-user state tracking and conversation history
3. **Automated Discretion Engine**: Smart memory routing (GLOBAL vs ISOLATED scope)
4. **Decoupled Frontend Adapter**: Platform-agnostic core with swappable interfaces

## Project Structure

```
Myriad/
├── core/                    # Platform-agnostic intelligence engine
│   ├── agent_core.py        # Main AI engine (NO platform dependencies)
│   └── persona_loader.py    # Persona cartridge system
├── database/                # SQLite memory and state management
│   └── memory_matrix.py     # Database operations
├── adapters/                # Platform-specific frontends
│   └── discord_adapter.py   # Discord bot implementation
├── personas/                # Persona JSON cartridges
│   ├── brother_stud.json
│   ├── detective_noir.json
│   ├── coding_mentor.json
│   └── chaos_goblin.json
├── main.py                  # Entry point
└── requirements.txt
```

## Features

- **Multi-User Support**: Each Discord user has independent persona state
- **Memory Scoping**: Memories can be GLOBAL (shared hive-mind) or ISOLATED (persona-specific)
- **Platform Agnostic**: Core engine has zero Discord dependencies
- **Hot-Swappable**: Switch personas mid-conversation without restarting
- **LLM Flexible**: Point at OpenAI, OpenRouter, or local OpenAI-compatible APIs

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
MEMORY_CONTEXT_LIMIT=50
```

**For local LLMs**: Change `LLM_BASE_URL` to your local server (e.g., `http://localhost:1234/v1` for LM Studio)

### 3. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section and create a bot
4. Enable "Message Content Intent" under Privileged Gateway Intents
5. Copy the token to your `.env` file
6. Invite bot to your server using OAuth2 URL with `bot` and `applications.commands` scopes

### 4. Run the Bot

```bash
python main.py
```

## Usage

### Discord Commands

- `/swap <persona_id>` - Switch to a different persona
- `/personas` - List all available personas
- `/whoami` - Check your current active persona
- `/forget [persona_id]` - Clear conversation memory
- `/stats` - View your memory statistics

### Talking to Myriad

Simply mention the bot in any message:

```
@Myriad Hey, what's your take on Python vs JavaScript?
```

Each user maintains their own active persona, so different users can talk to different personalities in the same channel.

## Creating Custom Personas

Create a new JSON file in `personas/` directory:

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
- `persona_id` (required): Unique identifier, must match filename
- `name` (required): Display name for the persona
- `system_prompt` (required): Core personality and behavior instructions
- `personality_traits` (optional): List of traits for reference
- `temperature` (optional): LLM temperature, 0.0-1.0 (default: 0.7)
- `max_tokens` (optional): Max response length (default: 1000)
- `rules_of_engagement` (optional): List of behavioral constraints and guardrails

The bot will automatically detect new personas (no restart needed for loading, but cache may need clearing with `/swap`).

## Memory Visibility Scopes

- **ISOLATED** (default): Memories are locked to the specific persona that recorded them
- **GLOBAL**: Memories are shared across all personas (hive-mind mode)

Currently, all user conversations default to ISOLATED. GLOBAL memory can be enabled programmatically for specific use cases.

## Technical Constraints

- **Language**: Python 3.10+
- **Database**: SQLite3 (no ORM)
- **LLM Client**: OpenAI Python SDK (compatible with OpenAI-like APIs)
- **Discord**: discord.py 2.3+
- **Architecture**: Strict separation between core logic and platform adapters

## Future Expansion

The decoupled architecture allows for:

- Telegram adapter
- CLI adapter
- Web interface
- REST API
- Semantic memory search (vector embeddings)
- Cross-user GLOBAL memories for shared knowledge

## License

See LICENSE file for details.

---

Built with the philosophy that identity is a choice, not a constraint.
