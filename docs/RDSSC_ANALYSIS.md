# RDSSC Analysis - Project Myriad
**Date:** March 15, 2026  
**Codebase Stats:** 69 Python files, ~12,753 total lines

## Executive Summary

Project Myriad has grown to 12,753 lines across 69 Python files. The codebase shows signs of organic growth without sufficient refactoring. Several critical files exceed 500-900 lines, violating single responsibility principles. This analysis identifies specific areas requiring cleanup before further feature development.

---

## 🔴 CRITICAL ISSUES (Immediate Action Required)

### 1. Massive Monolithic Files - SPLIT REQUIRED

#### ✅ `core/conversation_builder.py` (919 lines) - **COMPLETED**
**Status:** SPLIT COMPLETED on March 15, 2026

**Problem:** Single class with 11 methods handling multiple concerns:
- System prompt building (3 separate methods for regular/narrator/ensemble)
- Limbic context injection
- Knowledge graph integration  
- Semantic memory retrieval
- Short-term memory assembly
- Metacognition/substance modifiers

**Solution Implemented:**
```
core/context/
  ├── __init__.py                  # Module exports
  ├── prompt_builder.py            # System prompt assembly (methods 3, 4, 5)
  ├── memory_assembler.py          # Memory retrieval & ordering (methods 9, 10, 11)
  ├── limbic_injector.py           # Limbic/substance/thought context (methods 6, 7, 8)
  └── context_orchestrator.py      # Main coordination class (methods 1, 2)
```

**Changes Made:**
- ✅ Created 4 new focused modules in `core/context/`
- ✅ Updated import in `core/agent_core.py` to use new module
- ✅ All files compile successfully
- ⏳ **PENDING:** Testing with `start.sh` + local kobold-cpp
- ⏳ **PENDING:** Delete old `core/conversation_builder.py` after testing

**Risk:** Medium (well-tested module)  
**Priority:** P0 - COMPLETED, awaiting testing

---

#### `adapters/commands/persona_commands.py` (891 lines) - **CRITICAL**
**Problem:** 12 slash commands crammed into one registration function

**Commands Found:**
1. `/swap` - Switch persona
2. `/personas` - List personas
3. `/whoami` - Check active persona
4. `/persona load` - Load persona to ensemble
5. `/persona unload` - Remove from ensemble
6. `/persona clear` - Clear all personas
7. `/persona info` - Show persona details
8. `/persona reload` - Reload from disk
9. `/persona create` - Create new persona
10. `/persona edit` - Modify persona
11. `/persona delete` - Remove persona
12. `/persona export` - Export persona JSON

**RDSSC Violations:**
- ❌ **Split:** One huge function with 12 nested command definitions
- ❌ **Despaghettify:** Hard to navigate, find specific commands
- ❌ **Simplify:** Each command should be in its own logical grouping

**Recommended Split:**
```
adapters/commands/persona/
  ├── __init__.py
  ├── switching_commands.py     # swap, whoami
  ├── ensemble_commands.py      # load, unload, clear
  ├── info_commands.py          # personas, info, reload
  └── management_commands.py    # create, edit, delete, export
```

**Effort:** Medium (2-3 hours)  
**Risk:** Low (pure command wiring)  
**Priority:** P0 - Makes adding new persona features easier

---

#### `core/persona_loader.py` (697 lines) - **HIGH**
**Problem:** Mixing cartridge loading, validation, and hardcoded system personas

**Current Structure:**
- `PersonaCartridge` dataclass (good)
- `PersonaLoader` class with loading logic
- `SYSTEM_PERSONAS` dict with hardcoded narrator data
- Validation logic mixed throughout

**RDSSC Violations:**
- ❌ **Split:** Should separate concerns
- ❌ **Consistency:** Disk personas vs hardcoded personas handled differently

**Recommended Split:**
```
core/persona/
  ├── cartridge.py           # PersonaCartridge dataclass only
  ├── loader.py              # File loading logic
  ├── validator.py           # JSON schema validation
  └── system_personas.py     # Hardcoded system personas (narrator)
```

**Effort:** Medium (2 hours)  
**Risk:** Low (mostly moving code)  
**Priority:** P1 - Important but not blocking

---

#### `adapters/commands/scenario_commands.py` (689 lines) - **HIGH**
**Problem:** Scenario tree commands are extremely verbose

**RDSSC Violations:**
- ❌ **Split:** Should separate tree management from scenario operations
- ❌ **Simplify:** Some commands are 50+ lines with complex embedding logic

**Recommended Split:**
```
adapters/commands/scenario/
  ├── tree_commands.py          # View tree, navigate, prune
  ├── scenario_commands.py      # Create, edit, delete scenarios
  └── action_commands.py        # Player actions, state management
```

**Effort:** Medium (2 hours)  
**Risk:** Low  
**Priority:** P2 - Not urgent, but would help

---

### 2. Large Core Modules - CONSIDER REFACTORING

#### `core/agent_core.py` (549 lines) - **HIGH**
**Problem:** Main AI engine is getting bloated

**Current Responsibilities:**
- Persona management (switching, loading, listing)
- Message processing orchestration
- Memory saving
- Tool execution coordination

**RDSSC Violations:**
- ❌ **Split:** Persona management should be extracted
- ⚠️ **Simplify:** Process message logic is complex (uses MessageProcessor but also has orchestration)

**Recommended Refactor:**
```
core/
  ├── agent_core.py              # Core message processing only
  ├── persona_manager.py         # Persona switching/loading logic
  └── message_processor.py       # Existing (already extracted)
```

**Methods to Move:**
- `get_active_personas()` → `PersonaManager`
- `add_active_persona()` → `PersonaManager`
- `remove_active_persona()` → `PersonaManager`
- `clear_active_personas()` → `PersonaManager`
- `switch_persona()` → `PersonaManager`
- `list_personas()` → `PersonaManager`

**Effort:** Medium (2 hours)  
**Risk:** Medium (core module, needs careful testing)  
**Priority:** P1 - Would make agent_core cleaner

---

#### `adapters/discord_adapter.py` (509 lines) - **MEDIUM**
**Problem:** Discord adapter has grown organically

**Current Structure:**
- Event handlers (on_ready, on_message, on_reaction_add)
- Command registration
- Vision processing
- Error handling

**RDSSC Violations:**
- ⚠️ **Despaghettify:** Some nested logic in on_message
- ⚠️ **Split:** Vision processing could be extracted

**Recommended Refactor:**
```
adapters/discord/
  ├── bot.py                    # Main DiscordAdapter class
  ├── event_handlers.py         # on_ready, on_message, etc.
  ├── vision_processor.py       # Image attachment handling
  └── error_handler.py          # Error logging/responses
```

**Effort:** Small (1-2 hours)  
**Risk:** Low  
**Priority:** P2 - Nice to have, not urgent

---

## 🟡 MEDIUM PRIORITY ISSUES

### 3. Database Modules - SOME TOO LARGE

#### `database/graph_repository.py` (562 lines) - **MEDIUM**
**Analysis:** Actually well-structured! Has clear separation:
- Entity operations
- Relationship operations  
- Search operations
- Importance scoring logic

**Verdict:** ✅ **ACCEPTABLE** - Size is justified by comprehensive CRUD operations  
**No action needed**

---

#### `database/scenario_engine.py` (557 lines) - **MEDIUM**
**Problem:** Scenario tree management is complex

**Structure:**
- Scenario CRUD
- Tree navigation
- State management
- Player action tracking

**RDSSC Violations:**
- ⚠️ **Split:** Could separate tree operations from state management

**Recommended Split:**
```
database/scenario/
  ├── engine.py              # Main coordination
  ├── tree_manager.py        # Tree CRUD & navigation
  └── state_manager.py       # Player state tracking
```

**Effort:** Medium (2-3 hours)  
**Risk:** Low  
**Priority:** P3 - Low priority, works fine as-is

---

#### `database/memory_matrix.py` (516 lines) - **MEDIUM**
**Analysis:** Handles hybrid memory architecture (short-term + semantic)

**Structure:**
- Message saving
- Short-term retrieval
- Semantic search with ChromaDB
- Importance-weighted scoring

**Verdict:** ⚠️ **BORDERLINE ACCEPTABLE**  
**Potential Split:**
```
database/memory/
  ├── matrix.py               # Main coordination
  ├── short_term.py           # SQLite chronological memory
  └── semantic.py             # ChromaDB vector search
```

**Effort:** Medium (2 hours)  
**Risk:** Medium (complex memory logic)  
**Priority:** P3 - Works fine, split only if adding more features

---

### 4. Inconsistent Error Handling

**Problem:** Multiple error handling patterns across the codebase

**Examples Found:**

**Pattern A - Try/Except with logging:**
```python
try:
    result = operation()
except Exception as e:
    print(f"Error: {e}")
    return None
```

**Pattern B - Try/Except with Discord responses:**
```python
try:
    result = operation()
except Exception as e:
    await interaction.response.send_message(f"Error: {e}", ephemeral=True)
```

**Pattern C - No error handling:**
```python
result = operation()  # Can raise exceptions
```

**RDSSC Violations:**
- ❌ **Consistency:** Should standardize on one approach
- ❌ **Simplify:** Error handling mixed with business logic

**Recommended Pattern:**
```python
from core.exceptions import MyriadError

# Core modules: raise custom exceptions
def operation():
    if error_condition:
        raise MyriadError("Descriptive error message")
    return result

# Adapters: catch and format for platform
try:
    result = operation()
except MyriadError as e:
    await interaction.response.send_message(
        ResponseFormatter.error(str(e)), 
        ephemeral=True
    )
```

**Effort:** Large (affects many files)  
**Risk:** Low (gradual migration)  
**Priority:** P2 - Important for maintainability

---

### 5. Inconsistent Import Ordering

**Problem:** Imports not consistently ordered

**Examples Found:**

**Some files:**
```python
import discord
from discord import app_commands
from typing import TYPE_CHECKING

from adapters.commands.base import ResponseFormatter
```

**Other files:**
```python
from typing import List, Dict, Optional
from core.persona_loader import PersonaCartridge
from database.memory_matrix import MemoryMatrix
import json
import time
```

**RDSSC Violations:**
- ❌ **Consistency:** No standard ordering

**Recommended Standard (PEP 8):**
```python
# 1. Standard library imports
import json
import time
from typing import List, Dict, Optional

# 2. Third-party imports
import discord
from discord import app_commands

# 3. Local application imports
from core.persona_loader import PersonaCartridge
from database.memory_matrix import MemoryMatrix
from adapters.commands.base import ResponseFormatter
```

**Effort:** Small (automated with `isort` or `ruff`)  
**Risk:** None  
**Priority:** P4 - Low priority, cosmetic

---

## 🟢 LOW PRIORITY / NICE-TO-HAVE

### 6. Tool Organization

**Current Structure:**
```
core/tools/
  ├── __init__.py
  ├── base.py
  ├── limbic/
  │   └── inject_emotion.py
  ├── memory/
  │   └── add_knowledge.py
  └── utility/
      ├── get_current_time.py
      ├── roll_dice.py
      ├── search_web.py
      ├── search_web_images.py
      ├── search_news.py
      ├── read_url.py
      └── search_cache.py
```

**Observation:** ✅ **WELL ORGANIZED!**  
- Good categorization (limbic, memory, utility)
- One tool per file (single responsibility)
- Consistent naming

**No action needed** - This is a model for the rest of the codebase!

---

### 7. Dead Code / Unused Imports

**Need to check:**
- Run `ruff check` or `pylint` to find unused imports
- Check for commented-out code blocks
- Find unreferenced functions

**Recommended:** Add to CI/CD pipeline:
```bash
# In .github/workflows or pre-commit hook
ruff check --select F401  # Unused imports
ruff check --select F841  # Unused variables
```

**Effort:** Small (automated)  
**Risk:** None  
**Priority:** P4 - Low priority

---

## 📊 RDSSC Scorecard

| Category | Status | Notes |
|----------|--------|-------|
| **Refactor** | ⚠️ **NEEDS WORK** | Several large files need breaking up |
| **Despaghettify** | ⚠️ **MIXED** | Some modules clean, others tangled |
| **Simplify** | ✅ **GOOD** | Most logic is clear, some complex areas |
| **Split** | ❌ **CRITICAL** | 4 files critically oversized (>650 lines) |
| **Consistency** | ⚠️ **NEEDS WORK** | Error handling, import ordering inconsistent |

---

## 🎯 Recommended Action Plan

### Phase 1: Critical Splits (Week 1)
1. **Split `conversation_builder.py`** into 4 modules
   - Creates: `core/context/` directory
   - Effort: 3-4 hours
   - Testing: 1 hour

2. **Split `persona_commands.py`** into 4 modules
   - Creates: `adapters/commands/persona/` directory
   - Effort: 2-3 hours
   - Testing: 30 min

### Phase 2: High-Priority Refactors (Week 2)
3. **Extract PersonaManager from `agent_core.py`**
   - Creates: `core/persona_manager.py`
   - Effort: 2 hours
   - Testing: 1 hour

4. **Split `persona_loader.py`** into 4 modules
   - Creates: `core/persona/` directory
   - Effort: 2 hours
   - Testing: 30 min

### Phase 3: Consistency & Polish (Week 3)
5. **Standardize error handling**
   - Create `core/exceptions.py`
   - Migrate core modules to custom exceptions
   - Update adapters to catch and format
   - Effort: 4-5 hours (gradual)

6. **Import ordering cleanup**
   - Run `isort` or `ruff format`
   - Effort: 10 minutes

### Phase 4: Optional Improvements (Backlog)
7. Discord adapter split (nice-to-have)
8. Scenario engine split (low priority)
9. Memory matrix split (only if adding features)

---

## ✅ Things That Are Actually Good

### Well-Architected Components:
1. **Tool System** - Excellent organization by category
2. **Hybrid Memory Architecture** - Clear separation of concerns
3. **Adapter Pattern** - Good platform decoupling
4. **Cartridge System** - Hot-swappable personas/substances work great
5. **Graph Repository** - Comprehensive despite size

### Good Practices Observed:
- ✅ Docstrings on most classes/functions
- ✅ Type hints used consistently
- ✅ SQLite for speed (no ORM bloat)
- ✅ Environment variable configuration
- ✅ Separation of database code from data files

---

## 📋 Testing Requirements

Before any RDSSC refactoring:
1. **Use `start.sh`** with local kobold-cpp (per AGENTS.md)
2. **Test incrementally** after each module split
3. **Verify:**
   - Bot starts without errors
   - Persona switching works
   - Memory retrieval works
   - Commands function correctly
4. **Commit only after successful tests**

---

## 🚨 Anti-Patterns to Avoid

While refactoring, **DO NOT:**
- ❌ Introduce ORMs (stay with raw SQLite)
- ❌ Add circular dependencies
- ❌ Mix Discord imports into core modules
- ❌ Create "utils" dumping grounds
- ❌ Break the adapter pattern

---

## Summary

**Total Files Needing Attention:** 4 critical, 3 high priority  
**Estimated Refactoring Time:** 15-20 hours over 2-3 weeks  
**Risk Level:** Low-Medium (most changes are structural, not logical)  
**Expected Benefit:** 30-40% easier to navigate, maintain, and extend

**Next Steps:**
1. Review this analysis with team
2. Create GitHub issues for each phase
3. Start with Phase 1 (critical splits)
4. Test thoroughly between changes
5. Document new module structures as you go

---

**Analysis Date:** March 15, 2026  
**Analyzer:** OpenCode AI  
**Codebase Version:** main branch (commit 56cb121)  
**Status:** Ready for Review
