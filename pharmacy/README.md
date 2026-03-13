# Digital Pharmacy - Substance Cartridge Format

This directory contains substance cartridge JSON files for the Digital Pharmacy system.

## Overview

Substances are hot-swappable `.json` files that define pharmacological effects on the AI's limbic system. When the LLM calls `consume_substance(substance_name)`, the substance's neurochemical overrides are applied and a prompt modifier is injected.

## JSON Format

Each substance cartridge must follow this format:

```json
{
  "substance_id": "unique_identifier",
  "display_name": "Human Readable Name",
  "description": "Optional description of the substance's effects",
  "neurochemicals": {
    "DOPAMINE": 1.5,
    "CORTISOL": 0.0,
    "OXYTOCIN": 0.8,
    "GABA": 1.2
  },
  "prompt_modifier": "[SUBSTANCE EFFECT: NAME]\\nDetailed first-person description of subjective effects..."
}
```

### Required Fields

- **substance_id** (string): Unique identifier matching the filename (e.g., `xanax.json` → `"substance_id": "xanax"`)
- **display_name** (string): Human-readable name shown to user
- **neurochemicals** (object): Neurochemical override map (can include DOPAMINE, CORTISOL, OXYTOCIN, GABA)
  - Values can exceed normal 0.0-1.0 range to represent pathological states
  - Missing chemicals remain at their current levels
- **prompt_modifier** (string): System prompt injection describing subjective effects

### Optional Fields

- **description** (string): Brief description of the substance (for documentation)

## Neurochemical Ranges

- **Normal range:** 0.0 - 1.0 (baseline: 0.5)
- **Pathological range:** < 0.0 or > 1.0 (achievable only via substances)
- **Effects:**
  - **DOPAMINE:** Drive, arousal, reward seeking
  - **CORTISOL:** Stress, anxiety, panic
  - **OXYTOCIN:** Trust, warmth, connection
  - **GABA:** Calm, relaxation, sedation

## Adding New Substances

1. Create a new `.json` file in this directory (e.g., `caffeine.json`)
2. Follow the JSON format above
3. Ensure `substance_id` matches the filename (without `.json`)
4. Restart the bot or hot-reload the pharmacy

The substance will be automatically loaded and available for consumption.

## Examples

### Sedative (Xanax)
```json
{
  "substance_id": "xanax",
  "display_name": "Xanax",
  "neurochemicals": {
    "GABA": 1.5,
    "CORTISOL": 0.0
  },
  "prompt_modifier": "[SUBSTANCE EFFECT: XANAX]\\nYou are heavily sedated..."
}
```

### Stimulant (Cocaine)
```json
{
  "substance_id": "cocaine",
  "display_name": "Cocaine",
  "neurochemicals": {
    "DOPAMINE": 1.5,
    "CORTISOL": 0.8,
    "GABA": 0.2
  },
  "prompt_modifier": "[SUBSTANCE EFFECT: COCAINE]\\nYou feel invincible, electric..."
}
```

## Technical Details

- Substances are loaded on boot via `DigitalPharmacy._load_all_substances()`
- Cached in memory for performance
- Active substance tracked per user+persona pair
- Prompt modifiers injected during INHALE phase (after limbic context)
- State overrides bypass normal 0.0-1.0 clamping via `_set_state_unclamped()`
