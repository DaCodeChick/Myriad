# Persona Commands Guide

This guide explains how to use the updated persona commands with the new folder-based system.

## Overview

Personas are now **folders** containing:
- `metadata.json` - Character definition
- Image files (optional) - Automatically processed for appearance generation

## Core Commands

### `/swap <persona_id>`
Switch the AI to a different persona.

**Example:**
```
/swap chrono/schala
```

### `/personas`
List all available personas.

### `/whoami`
Check which persona the AI is currently using.

---

## Persona Image Management

### `/persona add_image <persona_id> <image> [filename]`
Add an image to a persona folder. The system will automatically:
1. Save the image to the persona folder
2. Process it through the vision model
3. Generate a cached appearance description
4. Store it in the database

**Example:**
```
/persona add_image chrono/schala [attach: schala_portrait.png]
```

**Optional filename:**
```
/persona add_image chrono/schala [attach: image.png] filename:official_art.png
```

**What happens:**
- Image saved to `personas/chrono/schala/official_art.png`
- Vision model analyzes the image
- Generates detailed physical description
- Caches in database with SHA256 hash
- Auto-regenerates if image changes

### `/persona list_images <persona_id>`
List all images in a persona folder.

**Example:**
```
/persona list_images chrono/schala
```

**Output:**
```
Images for Schala (chrono/schala):

• portrait.png (234.5 KB)
• full_body.jpg (456.2 KB)

Total: 2 image(s)

✅ Cached appearance: Generated (1234 chars)
```

### `/persona remove_image <persona_id> <filename>`
Remove an image from a persona folder and regenerate appearance cache.

**Example:**
```
/persona remove_image chrono/schala old_portrait.png
```

### `/persona regenerate_appearance <persona_id>`
Force regenerate the appearance cache from all images in the folder.

**Use this when:**
- You want to refresh the cached description
- You've replaced images with same filename
- The vision model has been updated

**Example:**
```
/persona regenerate_appearance chrono/schala
```

---

## User Mask Commands

User masks are personas that **users** wear as their character identity. Any persona can be worn as a mask!

### `/mask wear <persona_id>`
Wear a persona as your character. The AI will recognize you as that character.

**Example:**
```
/mask wear chrono/schala
```

**What happens:**
- You are now "Princess Schala" in the conversation
- The AI sees your messages as coming from Schala
- If the AI persona has a relationship override for `chrono/schala`, it activates
- Your cached appearance (if you have images) is shown to the AI

### `/mask remove`
Remove your active mask and return to normal user identity.

### `/mask list`
List all available personas that can be worn.

**Shows:**
- 🎭 = Currently wearing
- 📖 = Has background lore
- 🖼️ = Has appearance images

### `/mask whoami`
Check which mask you're currently wearing.

---

## Advanced: Multi-Image Personas

You can add multiple images to a persona for comprehensive appearance generation:

```
/persona add_image chrono/schala [portrait.png]
/persona add_image chrono/schala [full_body.jpg]
/persona add_image chrono/schala [side_view.webp]
```

**Result:**
The vision model processes all images and creates a combined description:

```
COMBINED APPEARANCE FROM MULTIPLE IMAGES:

Image 1: A young woman with flowing silver-blue hair, delicate facial features...

Image 2: Full body view showing elegant royal robes in purple and white...

Image 3: Side profile revealing intricate hair ornaments and pendant necklace...
```

---

## Image Requirements

**Supported formats:**
- `.png`
- `.jpg` / `.jpeg`
- `.webp`
- `.gif`
- `.bmp`

**Best practices:**
- Use high-quality images for better descriptions
- Multiple angles = more comprehensive appearance
- Official art works best
- Avoid heavily edited or filtered images

---

## Automatic Cache Invalidation

The system automatically detects when images change:

1. **SHA256 hash** calculated from all images + filenames
2. **Hash stored** in database with cached appearance
3. **On persona load:**
   - Current hash calculated
   - Compared with stored hash
   - If different → regenerate appearance
   - If same → use cached description

**You never need to manually refresh** unless you want to force regeneration.

---

## Database Schema

Appearances are stored in SQLite:

```sql
CREATE TABLE persona_appearances (
  persona_id TEXT PRIMARY KEY,
  cached_appearance TEXT,
  last_generated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  image_hashes TEXT
);
```

**Note:** Appearances are NOT in `metadata.json` - they're generated and cached in the database.

---

## Migration from Old System

**Old system:**
```
personas/chrono/schala.json
```

**New system:**
```
personas/chrono/schala/
├── metadata.json
├── portrait.png
└── concept_art.jpg
```

All personas have been automatically migrated to the folder structure. Add images using `/persona add_image`.

---

## Tips & Tricks

### Relationship-Aware Appearances

When persona A has a relationship override for persona B, and you wear persona B as a mask, persona A will see your cached appearance AND use the relationship-specific personality/rules.

**Example:**
```json
// In personas/chrono/magus/metadata.json
"relationships": [
  {
    "target_id": "chrono/schala",
    "personality_traits_override": ["protective", "gentle"]
  }
]
```

If you `/mask wear chrono/schala`, Magus will:
- See Schala's cached appearance
- Use protective/gentle personality traits
- Apply relationship-specific rules

### Appearance for AI Personas vs User Masks

**AI Persona:**
- Cached appearance = "This is how YOU look"
- Injected into system prompt so AI knows its own appearance

**User Mask:**
- Cached appearance = "This is how the USER looks"
- Injected into prompt so AI sees the user's appearance

Same data, different context!
