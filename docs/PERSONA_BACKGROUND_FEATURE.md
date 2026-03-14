# Persona Background Feature

## Overview

The Persona Background feature allows you to add deep historical context and lore to your personas without cluttering their immediate personality instructions. This is injected into the system prompt separately from the character identity, providing rich backstory that the AI can draw upon naturally.

## Architecture

### 1. Data Structure (`PersonaCartridge`)

The `PersonaCartridge` dataclass now includes an optional `background` field:

```python
@dataclass
class PersonaCartridge:
    persona_id: str
    name: str
    system_prompt: str
    personality_traits: List[str]
    temperature: float
    max_tokens: int
    rules_of_engagement: Optional[List[str]] = None
    background: Optional[str] = None  # NEW FIELD
```

### 2. Persona JSON Schema

Persona JSON files can now include an optional `background` field:

```json
{
  "persona_id": "example/character",
  "name": "Character Name",
  "system_prompt": "Core identity...",
  "personality_traits": ["trait1", "trait2"],
  "temperature": 0.7,
  "max_tokens": 1000,
  "rules_of_engagement": ["rule1", "rule2"],
  "background": "Deep historical context and backstory..."
}
```

### 3. System Prompt Injection

When building the conversation context, backgrounds are injected in this order:

```
# [CORE SYSTEM DIRECTIVES]
- Universal rules...

# [CHARACTER IDENTITY]
Core persona system_prompt

# [BACKGROUND / LORE]        ← NEW SECTION
Background text (if defined)

# [PERSONA-SPECIFIC BEHAVIOR]
Rules of engagement...

# [TOOLS, METACOGNITION, etc.]
...
```

This placement ensures:
- Background provides context AFTER identity is established
- It appears BEFORE behavioral rules (which may reference the background)
- It doesn't interfere with core directives or identity

## Usage

### Discord Commands

#### 1. Set/Update Background
```
/persona set_background <persona_id> <background_text>
```

**Example:**
```
/persona set_background generic/coding_mentor Ada has been teaching programming for 15 years, starting her career as a bootcamp instructor before transitioning to mentoring senior engineers at major tech companies...
```

**Features:**
- Creates or updates the background for an existing persona
- Automatically saves to the persona's JSON file
- Shows a preview of the updated background
- Displays character count

#### 2. View Background
```
/persona view_background <persona_id>
```

**Features:**
- Displays the complete background text
- Automatically splits into multiple messages if over Discord's 2000 character limit
- Shows a warning if no background is defined

#### 3. Clear Background
```
/persona clear_background <persona_id>
```

**Features:**
- Removes the background field from the persona
- Updates the JSON file
- Shows confirmation message

#### 4. View Current Persona (Enhanced)
```
/whoami
```

Now includes a background preview (first 200 characters) if the persona has one defined.

### Python API

#### Update Background Programmatically

```python
from core.persona_loader import PersonaLoader

loader = PersonaLoader(personas_dir="personas")

# Set or update background
success = loader.update_persona_background(
    persona_id="example/character",
    background="Your background text here..."
)

# Clear background
success = loader.update_persona_background(
    persona_id="example/character",
    background=None
)

# Don't forget to reload if the persona is cached
loader.reload_persona("example/character")
```

#### Create Persona with Background

```python
success = loader.create_persona(
    persona_id="example/new_character",
    name="Character Name",
    system_prompt="Core identity...",
    personality_traits=["trait1", "trait2"],
    background="Optional background text..."
)
```

## Best Practices

### What to Put in Background vs System Prompt

**System Prompt (`system_prompt`):**
- Core personality and identity
- Current behavioral style
- Immediate character traits
- How they speak and think

**Background (`background`):**
- Historical context and backstory
- Past events that shaped the character
- Relationships and connections
- Traumas, achievements, motivations
- World-building lore
- Character arc progression

### Example: Good Separation

**System Prompt:**
```
You are Dr. Elena Thorne, a brilliant but troubled archaeologist. You speak 
with quiet intensity and often reference historical parallels. You're driven 
by guilt over past failures and determined to prove your controversial theories.
```

**Background:**
```
Dr. Elena Thorne was once the rising star of archaeological academia, having 
discovered the lost Temple of Khepri in Egypt at age 28. However, her career 
was shattered three years ago when her expedition to recover the Obsidian 
Codex resulted in the collapse of an ancient tomb, killing two of her team 
members including her mentor, Dr. Marcus Webb...

[Additional paragraphs about her current situation, motivations, habits, etc.]
```

### Length Recommendations

- **Short backgrounds:** 200-500 characters - For simple context
- **Medium backgrounds:** 500-1500 characters - Most common use case
- **Long backgrounds:** 1500-3000 characters - Rich, detailed lore
- **Epic backgrounds:** 3000+ characters - Complex world-building

**Note:** Longer backgrounds consume more tokens in each API call. Balance detail with cost/context window.

## Technical Implementation

### Files Modified

1. **`core/persona_loader.py`**
   - Added `background` field to `PersonaCartridge`
   - Updated `from_dict()` and `to_dict()` methods
   - Added `update_persona_background()` method
   - Added `create_persona()` method

2. **`core/conversation_builder.py`**
   - Modified `_build_system_prompt()` to inject background
   - Background appears after CHARACTER IDENTITY, before PERSONA-SPECIFIC BEHAVIOR

3. **`adapters/commands/persona_commands.py`**
   - Enhanced `/whoami` to show background preview
   - Added `/persona set_background` command
   - Added `/persona view_background` command
   - Added `/persona clear_background` command
   - Created `persona` command group

### Backward Compatibility

The feature is **fully backward compatible**:
- Existing personas without `background` field work normally
- The field is optional in JSON
- Old persona files don't need updates
- Background is only injected if defined

## Example Persona

See `/tmp/example_persona_with_background.json` for a complete example of a persona with rich background lore.

## Testing

To test the feature:

1. Create a persona with background:
   ```bash
   mkdir -p personas/test
   cat > personas/test/demo.json << EOF
   {
     "persona_id": "test/demo",
     "name": "Test Character",
     "system_prompt": "You are a test character.",
     "personality_traits": ["test"],
     "temperature": 0.7,
     "max_tokens": 1000,
     "background": "This is test background lore."
   }
   EOF
   ```

2. Switch to the persona:
   ```
   /swap test/demo
   ```

3. View the background:
   ```
   /persona view_background test/demo
   ```

4. Update the background:
   ```
   /persona set_background test/demo Updated background text with more details...
   ```

5. Test in conversation - the AI should naturally reference background details when relevant.

## Future Enhancements

Potential improvements:
- Background templates for common character archetypes
- Import background from file (for very long lore)
- Background versioning/history
- Background variables (e.g., `{persona_name}` substitution)
- Multi-section backgrounds (origin, relationships, current status)
