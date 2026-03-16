# Visual Memory Feature - Architecture Summary

## Feature Structure

Following Project Myriad's modular feature architecture, the Visual Memory Engine is now properly segregated:

```
core/features/visual_memory/
├── __init__.py                    # Package exports
├── visual_memory_feature.py       # Feature class (implements BaseFeature)
└── visual_manager.py              # Core engine (platform-agnostic)

adapters/commands/
└── visual_commands.py             # Discord command interface

docs/
└── VISUAL_MEMORY.md               # Documentation

tests/
└── test_visual_engine.py          # Platform-agnostic tests
```

## Feature Architecture Pattern

The Visual Memory feature follows the same pattern as the Roleplay feature:

### 1. Feature Class (`visual_memory_feature.py`)

Implements `BaseFeature` abstract class:

```python
class VisualMemoryFeature(BaseFeature):
    @property
    def name(self) -> str:
        return "visual_memory"
    
    def initialize(self, **dependencies) -> None:
        # Initialize visual_manager
        pass
    
    # Delegation methods
    async def extract_and_save_profile(...)
    async def generate_character_image(...)
    def get_visual_profile(...)
    def list_characters(...)
    def delete_profile(...)
```

### 2. Core Engine (`visual_manager.py`)

Platform-agnostic API - **NO** Discord imports:

```python
class VisualManager:
    """Pure data/API layer for visual profiles."""
    
    def __init__(self, db_path: str, gemini_api_key: str = None):
        # Initialize SQLite database
        # Initialize Gemini client
        pass
    
    async def extract_and_save_profile(...)
    async def generate_character_image(...)
    def get_visual_profile(...)
    def list_characters(...)
    def delete_profile(...)
```

### 3. Discord Interface (`visual_commands.py`)

Discord-specific UI wrapper:

```python
class VisualCommands(commands.Cog):
    """Discord commands wrapping VisualManager."""
    
    @app_commands.command(name="visual_learn")
    async def visual_learn(...)
    
    @app_commands.command(name="visual_generate")
    async def visual_generate(...)
    
    # ... more commands
```

## Integration with AgentCore

### Current State

The Visual Memory feature is **independent** and doesn't require AgentCore integration. It can be used standalone:

```python
from core.features.visual_memory import VisualManager

visual_manager = VisualManager()
await visual_manager.extract_and_save_profile(...)
```

### Future Integration (Optional)

If you want to integrate with AgentCore's feature loading system (like roleplay), you would:

1. **Add to AgentCore (`core/agent_core.py`)**:

```python
def __init__(
    self,
    config: MyriadConfig,
    db_path: str = "data/myriad_state.db",
    enable_roleplay: bool = True,
    enable_visual_memory: bool = False,  # New parameter
):
    # ... existing code ...
    
    # Load Visual Memory Feature (if enabled)
    if enable_visual_memory:
        self._load_visual_memory_feature()

def _load_visual_memory_feature(self) -> None:
    """Load the visual memory feature."""
    from core.features.visual_memory import VisualMemoryFeature
    
    visual_memory = VisualMemoryFeature(
        config=self.config,
        db_path="data/visual_profiles.db",
        gemini_api_key=self.config.llm.api_key,  # Or separate key
    )
    
    visual_memory.initialize()
    self.features["visual_memory"] = visual_memory
```

2. **Add delegation methods** (optional, for backward compatibility):

```python
# In AgentCore
async def extract_visual_profile(self, character_name: str, image_bytes: bytes) -> str:
    """Extract visual profile (requires visual_memory feature)."""
    if "visual_memory" not in self.features:
        raise RuntimeError("Visual Memory feature not loaded")
    return await self.features["visual_memory"].extract_and_save_profile(
        character_name, image_bytes
    )
```

## Key Benefits

### ✅ Modular Architecture
- Visual Memory is a **feature**, not core infrastructure
- Can be enabled/disabled independently
- Follows same pattern as Roleplay feature

### ✅ Platform-Agnostic
- `VisualManager` has ZERO Discord dependencies
- Can be used in CLI, web UI, Telegram bot, etc.
- Easy to test without Discord

### ✅ Clean Separation
- **Feature layer**: `VisualMemoryFeature` (follows BaseFeature interface)
- **Engine layer**: `VisualManager` (pure API/data logic)
- **UI layer**: `VisualCommands` (Discord-specific)

### ✅ Independent
- Does NOT depend on roleplay feature
- Can be used standalone or with other features
- Own database, own configuration

## Import Paths

### Correct Imports

```python
# Import the feature
from core.features.visual_memory import VisualMemoryFeature

# Import the core engine directly
from core.features.visual_memory import VisualManager

# Import from feature package
from core.features import VisualMemoryFeature
```

### ❌ Old Imports (deprecated)

```python
# NO LONGER VALID
from database.visual_manager import VisualManager  # ❌ Wrong location
```

## Comparison with Roleplay Feature

| Aspect | Roleplay Feature | Visual Memory Feature |
|--------|-----------------|----------------------|
| **Location** | `core/features/roleplay/` | `core/features/visual_memory/` |
| **Feature Class** | `RoleplayFeature` | `VisualMemoryFeature` |
| **Core Engine** | Multiple managers | `VisualManager` |
| **Complexity** | High (14 modules) | Low (1 manager) |
| **Dependencies** | Many (persona, limbic, etc.) | Few (just Gemini API) |
| **Database** | Shared main DB | Own SQLite DB |
| **Platform-Agnostic** | ✅ Yes | ✅ Yes |

## File Organization

### Feature Module
```
core/features/visual_memory/
├── __init__.py                 # Exports: VisualMemoryFeature, VisualManager
├── visual_memory_feature.py    # Feature class (70 lines)
└── visual_manager.py           # Core engine (370 lines)
```

### Discord Adapter
```
adapters/commands/
└── visual_commands.py          # Discord commands (330 lines)
```

### Documentation
```
docs/
└── VISUAL_MEMORY.md            # Complete usage guide
```

### Tests
```
tests/
└── test_visual_engine.py       # Platform-agnostic tests
```

## Usage Examples

### Standalone Usage

```python
from core.features.visual_memory import VisualManager

# Direct usage without AgentCore
visual_manager = VisualManager(db_path="data/visual.db")

# Extract profile
tags = await visual_manager.extract_and_save_profile("alice", image_bytes)

# Generate image
img = await visual_manager.generate_character_image("alice", "standing")
```

### Through Feature Class

```python
from core.features.visual_memory import VisualMemoryFeature

# Using feature interface
feature = VisualMemoryFeature(
    config=None,
    db_path="data/visual.db",
    gemini_api_key="your_key"
)
feature.initialize()

# Use through feature
tags = await feature.extract_and_save_profile("alice", image_bytes)
img = await feature.generate_character_image("alice", "standing")
```

### Discord Commands

```bash
# In Discord
/visual_learn alice reference.png
/visual_generate alice "drinking tea" 16:9
/visual_show alice
/visual_list
/visual_delete alice
```

## Next Steps

1. **✅ DONE**: Refactor to feature architecture
2. **Optional**: Integrate with AgentCore feature loading
3. **Optional**: Add configuration options (default aspect ratio, quality settings, etc.)
4. **Optional**: Create tool for LLM to call (like generate_image tool)
5. **Optional**: Integrate with Persona system for automatic profile creation

## Summary

The Visual Memory Engine is now properly structured as a **modular feature** in `core/features/visual_memory/`, following the same architectural pattern as the Roleplay feature. It maintains complete platform independence and can be used standalone or integrated with AgentCore's feature system.
