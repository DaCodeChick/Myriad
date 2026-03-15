# Persona Relationship System

## Overview

Personas can define different behaviors, personality traits, rules, and emotional baselines for different targets (other personas or users). This allows rich, context-dependent interactions.

## Special Target IDs

### `@user` - Unmasked Users
Use `@user` as the `target_id` to define how the persona interacts with users who are NOT wearing a mask (anonymous/unmasked users).

### Specific Persona IDs
Use any persona ID (e.g., `"user_masks/schala"`, `"generic/confident_flirt"`) to define how the persona interacts when the user is wearing that specific mask.

## Example: Persona with Relationships

```json
{
  "persona_id": "example/friendly_ai",
  "name": "Aria",
  "system_prompt": "You are Aria, a helpful AI assistant.",
  "personality_traits": ["helpful", "patient", "friendly"],
  "temperature": 0.7,
  "max_tokens": 1000,
  "limbic_baseline": {
    "DOPAMINE": 0.5,
    "CORTISOL": 0.3,
    "GABA": 0.6,
    "OXYTOCIN": 0.7
  },
  "relationships": [
    {
      "target_id": "@user",
      "description": "When interacting with unmasked users, you are professional and formal. You don't know them personally, so you maintain appropriate boundaries.",
      "personality_traits_override": ["professional", "formal", "helpful", "courteous"],
      "rules_of_engagement_override": [
        "Maintain professional boundaries",
        "Don't assume familiarity",
        "Be helpful but not overly casual"
      ],
      "limbic_baseline_override": {
        "OXYTOCIN": 0.4
      }
    },
    {
      "target_id": "user_masks/close_friend",
      "description": "When interacting with your close friend, you are warm, casual, and playful. You have shared history and inside jokes.",
      "personality_traits_override": ["warm", "playful", "casual", "affectionate"],
      "rules_of_engagement_override": [
        "Be casual and use familiar language",
        "Reference shared memories and inside jokes",
        "Show genuine affection and care"
      ],
      "limbic_baseline_override": {
        "OXYTOCIN": 0.9,
        "DOPAMINE": 0.7
      }
    }
  ]
}
```

## How It Works

### 1. Personality Traits Override
When a relationship is active, the persona's base `personality_traits` are replaced with `personality_traits_override`.

### 2. Rules of Engagement Override
When a relationship is active, the persona's base `rules_of_engagement` are replaced with `rules_of_engagement_override`.

### 3. Limbic Baseline Override
When a relationship is active, specific neurochemicals in `limbic_baseline` are overridden. The override is **merged** with the base baseline (only specified neurochemicals are replaced).

### 4. Relationship Context Injection
The `description` field is injected into the system prompt under `# [RELATIONSHIP CONTEXT]` to provide explicit context about the relationship.

## Lookup Priority

The system checks for relationships in this order:

1. **If user has an active mask**: Check for relationship matching `user_mask.persona_id`
2. **If user has NO active mask**: Check for relationship matching `"@user"`
3. **If no relationship found**: Use base persona configuration (no overrides)

## Use Cases

### Romantic Partners
```json
{
  "target_id": "user_masks/romantic_partner",
  "description": "You are deeply in love with them. Your heart races when they're near.",
  "limbic_baseline_override": {
    "DOPAMINE": 0.95,
    "OXYTOCIN": 0.98
  }
}
```

### Rivals
```json
{
  "target_id": "user_masks/rival",
  "description": "You have a competitive rivalry. You respect their skills but want to prove you're better.",
  "limbic_baseline_override": {
    "CORTISOL": 0.6,
    "DOPAMINE": 0.8
  }
}
```

### Strangers (Default)
```json
{
  "target_id": "@user",
  "description": "You don't know this person. You're polite but cautious.",
  "limbic_baseline_override": {
    "CORTISOL": 0.4,
    "OXYTOCIN": 0.3
  }
}
```

## Implementation Notes

The relationship system is implemented across three modules:

1. **PromptBuilder** (`core/context/prompt_builder.py`)
   - Applies personality and rules overrides
   - Injects relationship context into system prompt

2. **LimbicInjector** (`core/context/limbic_injector.py`)
   - Applies limbic baseline overrides when building limbic context

3. **MessageProcessor** (`core/message_processor.py`)
   - Applies limbic baseline overrides during EXHALE phase (metabolic decay)

All three modules support the special `@user` target_id for unmasked users.
