# Provider System - Quick Reference

## Switching Providers

Edit `.env` file:

### Use Local Model (OpenAI-compatible)
```bash
LLM_PROVIDER=local
```

### Use Google Gemini
```bash
LLM_PROVIDER=gemini
```

Restart bot after changing.

---

## Provider Comparison

| Feature | Local (OpenAI-compatible) | Gemini |
|---------|---------------------------|--------|
| **Cost** | Free (self-hosted) | Free tier + paid |
| **Speed** | Depends on hardware | Fast (cloud) |
| **Privacy** | Complete (local) | Cloud-based |
| **Models** | Any compatible model | Gemini 1.5 Pro/Flash |
| **Safety Filters** | None (local control) | Disabled (BLOCK_NONE) |
| **Rate Limits** | None (local) | 60 req/min (free tier) |

---

## File Structure

```
core/providers/
├── __init__.py               # Package exports
├── base.py                   # LLMProvider interface (50 lines)
├── factory.py                # ProviderFactory (70 lines)
├── openai_provider.py        # OpenAI implementation (90 lines)
└── gemini_provider.py        # Gemini implementation (200 lines)

Total: ~410 lines of modular, testable code
```

---

## Common Tasks

### Get Current Provider
```python
from core.providers import ProviderFactory
from core.config import MyriadConfig

config = MyriadConfig.from_env()
provider = ProviderFactory.create_provider(config.llm)

print(f"Using: {provider.provider_name}")
print(f"Model: {provider.model_name}")
```

### Generate Response
```python
response = await provider.generate(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ],
    temperature=0.9,
    max_tokens=500,
)
```

### Test Provider
```bash
python test_providers.py
```

---

## Environment Variables

### Both Providers
```bash
LLM_PROVIDER=local  # or "gemini"
```

### Local Provider
```bash
LLM_API_KEY=not-needed
LLM_BASE_URL=http://localhost:5001/v1
LLM_MODEL=your-model-name
```

### Gemini Provider
```bash
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-pro
```

---

## Troubleshooting

### "No module named 'google.generativeai'"
```bash
pip install google-generativeai
```

### "GEMINI_API_KEY not found"
Add to `.env`:
```bash
GEMINI_API_KEY=your_key_here
```

### Provider not switching
1. Check `.env` has `LLM_PROVIDER=...`
2. Restart the bot
3. Check console output for provider initialization message

### "Unknown LLM provider"
Valid providers: `local`, `openai`, `gemini`

---

## Architecture Benefits

✅ **Modular**: Each provider is self-contained  
✅ **Testable**: Mock providers for unit tests  
✅ **Extensible**: Add new providers easily  
✅ **Type-Safe**: Abstract interface enforces consistency  
✅ **Clean**: No conditional logic in core code  

---

## Documentation

- **Setup Guide**: `docs/GEMINI_SETUP.md`
- **Architecture**: `docs/PROVIDER_ARCHITECTURE.md`
- **Migration**: `docs/PROVIDER_REFACTORING_SUMMARY.md`

---

**Quick Start**: Set `LLM_PROVIDER` in `.env` → Restart bot → Done!
