# Personas System

## Folder Structure

Each persona is a **folder** containing:
- `metadata.json` - Persona definition (personality, rules, relationships, etc.)
- Image files (optional) - Character appearance images (`.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`, `.bmp`)

Example structure:
```
personas/
├── chrono/
│   ├── schala/
│   │   ├── metadata.json
│   │   ├── portrait.png
│   │   └── full_body.jpg
│   └── magus/
│       └── metadata.json
└── generic/
    └── coding_mentor/
        └── metadata.json
```

## Persona ID Format

The persona ID is the path from `personas/` to the folder:
- `chrono/schala`
- `generic/coding_mentor`
- `generic/nsfw/alpha_stud`

## Cached Appearances

When a persona folder contains image files:
1. PersonaLoader automatically scans for images on load
2. If cached appearance is missing or images have changed, vision model processes all images
3. Generated description is stored in `persona_appearances` database table
4. Cached appearance is injected into system prompt automatically

**Important**: Cached appearances are stored in the **database**, NOT in metadata.json.

## User Masks = Personas

There is no separate "user mask" system. User masks are just personas that the user "wears" instead of the AI using them. The system treats them identically:
- Same folder structure
- Same metadata.json format
- Same cached appearance system
- Can have relationships with other personas

The only difference is context: when a user wears a persona, the AI knows this is another person in the conversation (not themselves).

## Relationship Overrides

Personas can have relationships with specific targets using `persona_id` format:

```json
{
  "relationships": [
    {
      "target_id": "chrono/magus",
      "description": "This is my brother Janus",
      "personality_traits_override": ["maternal", "loving"],
      "rules_of_engagement_override": ["Call him 'Janus'"],
      "limbic_baseline_override": {"OXYTOCIN": 1.0}
    }
  ]
}
```

Relationship overrides apply when interacting with the specified target, whether that target is:
- An AI persona
- A user wearing that persona as a mask
