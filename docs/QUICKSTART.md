# Quick Start Guide - Project Myriad

Get your polymorphic AI agent running in 5 minutes!

## Prerequisites

- Python 3.10 or higher
- A Discord bot token ([Get one here](https://discord.com/developers/applications))
- An OpenAI API key (or OpenRouter, or local LLM server)

## Installation

### 1. Clone and Setup Virtual Environment

```bash
cd Myriad
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file (copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN_HERE
LLM_API_KEY=YOUR_OPENAI_API_KEY_HERE
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4
MEMORY_CONTEXT_LIMIT=50
```

### 4. Setup Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Go to "Bot" tab → "Add Bot"
4. **Enable "Message Content Intent"** (Required!)
5. Copy the bot token to your `.env` file
6. Go to OAuth2 → URL Generator
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Read Messages/View Channels`
7. Use generated URL to invite bot to your server

### 5. Run the Bot

```bash
python main.py
```

You should see:

```
✓ Myriad Discord Adapter online
✓ Connected as: YourBotName#1234
✓ Available personas: brother_stud, chaos_goblin, coding_mentor, detective_noir
```

## First Conversation

### 1. Choose a Persona

In Discord, use the slash command:

```
/swap detective_noir
```

You'll see: `✓ Switched to persona: Detective Marlowe (detective_noir)`

### 2. Talk to Your AI

Mention the bot in any message:

```
@Myriad What's your take on the city at night?
```

The bot will respond in character as Detective Marlowe!

### 3. Switch Personas Mid-Conversation

```
/swap chaos_goblin
@Myriad Same question - what about the city at night?
```

Notice how the personality completely changes!

### 4. Check Your Memories

```
/stats
```

See how many memories are stored and which persona is active.

## Available Commands

| Command | Description |
|---------|-------------|
| `/swap <persona_id>` | Switch to a different persona |
| `/personas` | List all available personas |
| `/whoami` | Check your current active persona |
| `/forget [persona_id]` | Clear conversation memory (optional: only for specific persona) |
| `/stats` | View your memory statistics |

## Creating Your First Custom Persona

Create `personas/my_persona.json`:

```json
{
  "persona_id": "my_persona",
  "name": "My Custom Persona",
  "system_prompt": "You are a helpful and friendly assistant who loves to help people learn new things. You speak casually and use encouraging language.",
  "personality_traits": ["helpful", "friendly", "encouraging"],
  "temperature": 0.8,
  "max_tokens": 1000
}
```

Then in Discord:

```
/swap my_persona
@Myriad Hello!
```

## Using Local LLMs (Optional)

To use a local LLM like LM Studio or Ollama instead of OpenAI:

1. Start your local LLM server (e.g., LM Studio on port 1234)
2. Update `.env`:

```env
LLM_API_KEY=not-needed
LLM_BASE_URL=http://localhost:1234/v1
LLM_MODEL=local-model
```

The OpenAI SDK is compatible with most local LLM servers!

## Troubleshooting

### Bot doesn't respond to mentions

- Check that "Message Content Intent" is enabled in Discord Developer Portal
- Restart the bot after enabling intents

### "Import discord could not be resolved"

- Make sure you activated the virtual environment
- Run `pip install -r requirements.txt`

### "No module named 'core'"

- Make sure you're running from the Myriad directory
- Check that `__init__.py` files exist in `core/`, `database/`, and `adapters/`

### Slash commands don't appear

- Wait a few minutes (Discord caches slash commands)
- Try kicking and re-inviting the bot
- Check bot has `applications.commands` scope

## Next Steps

- Read `ARCHITECTURE.md` to understand the system design
- Create custom personas for specific use cases
- Experiment with GLOBAL vs ISOLATED memory visibility
- Explore building a new frontend adapter (Telegram, CLI, etc.)

## Pro Tips

1. **Different users, different personas**: Each Discord user maintains their own active persona independently
2. **Memory persistence**: All conversations are saved to `database/myriad_state.db`
3. **Hot reload personas**: The persona loader caches persona files, but `/swap` forces a fresh load
4. **Temperature tuning**: Lower temperature (0.3-0.5) for factual personas, higher (0.8-1.0) for creative ones

---

**You're all set! Start chatting with your polymorphic AI agent.**

For detailed documentation, see `README.md` and `ARCHITECTURE.md`.
