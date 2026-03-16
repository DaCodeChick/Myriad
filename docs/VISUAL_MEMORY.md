# Visual Memory Engine

Platform-agnostic character appearance extraction and image generation system.

## Architecture

This system follows the modular feature architecture:

- **`core/features/visual_memory/`** - Feature module directory
  - **`visual_memory_feature.py`** - Feature class implementing BaseFeature
  - **`visual_manager.py`** - Platform-agnostic core engine (NO discord imports)
  - **`__init__.py`** - Package exports
- **`adapters/commands/visual_commands.py`** - Discord command interface

The Visual Memory feature is completely independent and does NOT depend on roleplay or any other feature.

## Features

### 1. Visual Profile Extraction
- Upload character reference images
- Gemini Vision analyzes and extracts comprehensive visual tags
- Safety filters disabled (BLOCK_NONE) to allow suggestive/NSFW reference art
- Stores profiles in SQLite database

### 2. Character Image Generation
- Generate images using stored character profiles
- Combines visual tags with action prompts
- Uses Imagen 3 for high-quality output
- Quality tags added automatically ("masterpiece, best quality")

## Setup

### Prerequisites

```bash
# Install Google GenAI SDK
pip install google-genai

# Set API key in .env
GEMINI_API_KEY=your_api_key_here
```

### Load Commands (Discord)

Add to your bot's command loading in `adapters/discord/bot.py`:

```python
# Load Visual Memory commands
await bot.load_extension("adapters.commands.visual_commands")
```

## Discord Commands

### `/visual_learn <character_name> <image>`
Learn a character's appearance from a reference image.

**Example:**
```
/visual_learn alice reference.png
```

**Output:**
```
✓ Learned Visual Profile: alice
Extracted Tags:
long silver hair, purple eyes, gothic lolita dress, black and white,
lace details, ribbon, petite build, pale skin, mysterious expression
```

### `/visual_generate <character_name> <action> [aspect_ratio]`
Generate an image of a learned character.

**Example:**
```
/visual_generate alice "standing in a moonlit forest" 16:9
```

**Output:**
Generates and posts an image combining Alice's visual profile with the action.

### `/visual_show <character_name>`
Display a character's stored visual profile.

### `/visual_list`
List all characters with visual profiles.

### `/visual_delete <character_name>`
Delete a character's visual profile.

## Python API Usage

### Basic Usage

```python
from core.features.visual_memory import VisualManager

# Initialize manager
visual_manager = VisualManager(
    db_path="data/visual_profiles.db",
    gemini_api_key="your_key"  # Optional, reads from env
)

# Extract visual profile from image
with open("character.png", "rb") as f:
    image_bytes = f.read()

visual_tags = await visual_manager.extract_and_save_profile(
    character_name="alice",
    image_bytes=image_bytes
)

print(f"Extracted tags: {visual_tags}")

# Generate character image
image_bytes = await visual_manager.generate_character_image(
    character_name="alice",
    action_prompt="standing in a moonlit forest",
    aspect_ratio="16:9"
)

# Save generated image
with open("output.png", "wb") as f:
    f.write(image_bytes)
```

### Advanced Usage

```python
# Retrieve stored profile
visual_tags = visual_manager.get_visual_profile("alice")

# List all characters
characters = visual_manager.list_characters()
print(f"Characters: {', '.join(characters)}")

# Delete profile
deleted = visual_manager.delete_profile("alice")
```

## Database Schema

```sql
CREATE TABLE visual_profiles (
    character_name TEXT PRIMARY KEY,
    visual_tags TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Safety Settings

### Vision Extraction
- **Safety: BLOCK_NONE** - Allows analysis of suggestive/NSFW reference art
- **Model:** gemini-1.5-pro
- **Temperature:** 0.5 (consistent extraction)

### Image Generation
- **Safety: block_only_high** - Allows mature content
- **Model:** imagen-3.0-generate-001
- **Format:** PNG (no watermark)

## Example Workflow

1. **Learn character appearance:**
   ```
   /visual_learn alice reference_art.png
   → Extracts: "long silver hair, purple eyes, gothic dress..."
   ```

2. **Generate character in scenes:**
   ```
   /visual_generate alice "drinking tea in a Victorian parlor"
   /visual_generate alice "walking through rain with umbrella"
   /visual_generate alice "reading a book in library"
   ```

3. **All generations use the same consistent character appearance!**

## Integration with AgentCore

The Visual Memory Engine can be loaded as an optional feature in AgentCore:

```python
from core.agent_core import AgentCore
from core.features.visual_memory import VisualMemoryFeature

# Initialize AgentCore with visual memory feature
agent_core = AgentCore(
    config=config,
    enable_roleplay=True,
    enable_visual_memory=True,  # Enable visual memory feature
)

# Access visual memory feature
visual_feature = agent_core.features.get("visual_memory")
if visual_feature:
    # Extract profile
    visual_tags = await visual_feature.extract_and_save_profile(
        character_name="alice",
        image_bytes=image_bytes
    )
    
    # Generate image
    image_bytes = await visual_feature.generate_character_image(
        character_name="alice",
        action_prompt="standing in moonlit forest"
    )
```

## Integration with Existing Systems

The Visual Memory Engine is completely independent and can be integrated with:

- **Persona System** - Generate consistent character images
- **Scenario System** - Visualize world locations
- **User Masks** - Generate user avatar images

Example integration:

```python
# In persona_manager.py
from core.features.visual_memory import VisualManager

async def generate_persona_image(self, persona_id: str, action: str):
    """Generate image for a persona."""
    visual_manager = VisualManager()
    
    # First time: learn from persona's reference art
    if not visual_manager.get_visual_profile(persona_id):
        persona = self.get_persona(persona_id)
        if persona.reference_image:
            await visual_manager.extract_and_save_profile(
                character_name=persona_id,
                image_bytes=persona.reference_image
            )
    
    # Generate image
    return await visual_manager.generate_character_image(
        character_name=persona_id,
        action_prompt=action
    )
```

## Error Handling

```python
try:
    visual_tags = await visual_manager.extract_and_save_profile(
        character_name="alice",
        image_bytes=image_bytes
    )
except ValueError as e:
    # API key missing or invalid image
    print(f"Configuration error: {e}")
except Exception as e:
    # Vision API error (filtered, quota, etc.)
    print(f"Extraction failed: {e}")

try:
    image_bytes = await visual_manager.generate_character_image(
        character_name="alice",
        action_prompt="standing"
    )
except ValueError as e:
    # Character not found in database
    print(f"No profile for character: {e}")
except Exception as e:
    # Generation API error
    print(f"Generation failed: {e}")
```

## Performance Notes

- **Vision Extraction:** ~3-5 seconds per image
- **Image Generation:** ~5-10 seconds per image
- **Database:** SQLite (local, no network overhead)
- **Concurrency:** Fully async (use `await`)

## Future Enhancements

Potential improvements:

1. **Style Presets** - Save/load style modifiers (anime, realistic, etc.)
2. **Multi-Reference Learning** - Average multiple reference images
3. **Tag Editing** - Manual visual tag refinement via UI
4. **Negative Tags** - Store "never include" tags per character
5. **Generation History** - Track all generated images per character
6. **Batch Generation** - Generate multiple variations at once

## Troubleshooting

### "Visual Memory Engine is not available"
- Check `GEMINI_API_KEY` is set in `.env`
- Verify `google-genai` is installed: `pip install google-genai`

### "No visual profile found"
- Run `/visual_learn` first to create the profile
- Character names are case-insensitive and stored lowercase

### "Image was filtered for safety"
- The action prompt triggered safety filters
- Try rephrasing the action description
- Contact Google AI if filters seem overly aggressive

### "Gemini returned empty response"
- Reference image may have triggered safety filters
- Try a different reference image
- Check image file is valid and not corrupted
