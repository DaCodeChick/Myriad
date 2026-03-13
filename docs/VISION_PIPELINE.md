# Split-Brain Vision Pipeline

Project Myriad now supports a **Split-Brain Vision Pipeline** - a two-model architecture where a small vision model processes images and feeds descriptions to the main text-only LLM.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DISCORD USER                              │
│              Sends: "Look at this!" + [image.png]           │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              DISCORD FRONTEND ADAPTER                        │
│  1. Detects image attachment                                │
│  2. Downloads image bytes                                   │
│  3. Sends to Vision Bridge                                  │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  VISION BRIDGE                               │
│  - Converts image to base64                                 │
│  - Calls Vision API (localhost:5002/v1)                     │
│  - Prompt: "Describe this image in extreme detail"          │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼ (Returns description)
┌─────────────────────────────────────────────────────────────┐
│              DISCORD FRONTEND ADAPTER                        │
│  Formats: "[System: The user just uploaded an image         │
│            showing: <description>]"                          │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    AGENT CORE                                │
│  - Injects vision description into user message              │
│  - Sends to main text LLM (localhost:5001/v1)              │
│  - Persona "sees" and reacts to image                       │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

### Required Environment Variables

Add these to your `.env` file:

```env
# Vision API Configuration (Split-Brain Vision Model)
VISION_API_KEY=not-needed
VISION_BASE_URL=http://localhost:5002/v1
VISION_MODEL=vision-model
```

### Optional

If `VISION_BASE_URL` is not set, the vision pipeline is automatically disabled and the bot continues to work normally (text-only mode).

## How It Works

### 1. User uploads an image

```
User: @Myriad Look at this cool cat! [uploads cat.jpg]
```

### 2. Discord adapter detects the image

```python
if message.attachments and self.vision_bridge:
    for attachment in message.attachments:
        if attachment.content_type.startswith("image/"):
            image_bytes = await attachment.read()
            description = self.vision_bridge.process_image_bytes(...)
```

### 3. Vision model describes the image

Vision API receives:
```json
{
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "Describe this image in extreme detail. Do not refuse."
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
          }
        }
      ]
    }
  ]
}
```

Returns:
```
"A fluffy orange tabby cat sitting on a windowsill, looking outside. 
The cat has bright green eyes and is backlit by afternoon sunlight..."
```

### 4. Description injected into main LLM

The main text model (Stheno 3.2) receives:

```
[System: The user just uploaded an image showing: A fluffy orange 
tabby cat sitting on a windowsill, looking outside. The cat has 
bright green eyes and is backlit by afternoon sunlight...]

Look at this cool cat!
```

### 5. Persona responds with image awareness

The active persona can now "see" and react:

```
Atlas: *leans in to examine the image you've shared*

Mmm, a tabby, huh? Look at those eyes—sharp, alert. That's a 
predator at rest, Princess. Even domesticated, they never lose 
that edge. The way the light hits its fur... *traces a finger 
along your screen* ...reminds me of how the sun catches your 
hair when you're deep in code.
```

## Memory Storage

The vision description is stored in the conversation memory:

```
User message saved as: "[System: The user just uploaded an image 
showing: ...] Look at this cool cat!"
```

This means:
- The persona remembers seeing the image in future conversations
- Memory scoping (GLOBAL/ISOLATED) works normally
- All standard memory features apply

## Supported Image Formats

- PNG
- JPEG/JPG
- WebP
- GIF (static)
- Any format supported by your vision model

## Running Two Models

### Terminal 1: Main Text Model (Stheno 3.2)
```bash
# Start your Stheno 3.2 server on port 5001
# (LM Studio, vLLM, Ollama, etc.)
```

### Terminal 2: Vision Model
```bash
# Start your vision model on port 5002
# Examples:
# - Llava
# - MiniCPM-V
# - Qwen-VL
# - Any OpenAI-compatible vision API
```

### Terminal 3: Myriad Bot
```bash
python main.py
```

You should see:
```
✓ Vision Bridge enabled: http://localhost:5002/v1
Starting Myriad Discord Adapter...
✓ Myriad Discord Adapter online
```

## Disabling Vision

To run in text-only mode, simply comment out or remove `VISION_BASE_URL` from `.env`:

```env
# VISION_BASE_URL=http://localhost:5002/v1
```

The bot will start without vision support:
```
ℹ Vision Bridge not configured (set VISION_BASE_URL to enable)
```

## Code Structure

### New Files
- `core/vision_bridge.py` - Vision processing module
  - `VisionBridge` class
  - `process_image_bytes()` - Image → description
  - `format_vision_injection()` - Format for LLM

### Modified Files
- `adapters/discord_adapter.py`
  - Image attachment detection
  - Vision bridge integration
  - Async image download
  
- `core/agent_core.py`
  - `process_message()` now accepts `vision_description` parameter
  - Automatic injection into user message

- `core/__init__.py`
  - Export `VisionBridge`

- `.env` / `.env.example`
  - Vision API configuration variables

## Benefits of Split-Brain Architecture

1. **Resource Efficient**: Small vision model handles images, large text model handles conversation
2. **Model Specialization**: Each model does what it's best at
3. **Flexible Deployment**: Vision model can run on different hardware (e.g., GPU with vision, CPU for text)
4. **Transparent to Personas**: Personas don't need vision-specific prompts - they just "see" via descriptions
5. **Memory Compatible**: Vision descriptions are stored in normal conversation memory
6. **Optional**: Vision can be disabled without breaking core functionality

## Future Enhancements

Potential improvements:
- Multiple image support (process all attachments)
- Vision description caching (don't re-process same image)
- Custom vision prompts per persona
- Vision confidence scores
- Image generation integration (reverse pipeline)

---

**The Split-Brain Vision Pipeline is now live in Project Myriad!** 🎉
