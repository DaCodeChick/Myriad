# LLM Provider System - Architecture Documentation

## Overview

Project Myriad uses a **modular provider system** for LLM backends. This allows seamless switching between different LLM providers (OpenAI, Gemini, Anthropic, etc.) without changing application code.

## Architecture

### Provider Pattern

All LLM providers implement the `LLMProvider` abstract base class, ensuring a consistent interface:

```python
class LLMProvider(ABC):
    @abstractmethod
    async def generate(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float, 
        max_tokens: int
    ) -> Optional[str]:
        """Generate a response from the LLM."""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return model identifier."""
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name."""
        pass
```

### Directory Structure

```
core/
  providers/
    __init__.py              # Package exports
    base.py                  # Abstract LLMProvider interface
    factory.py               # ProviderFactory for instantiation
    openai_provider.py       # OpenAI-compatible provider
    gemini_provider.py       # Google Gemini provider
```

## Available Providers

### 1. OpenAI Provider (`openai_provider.py`)

**Supports**:
- Official OpenAI API (GPT-4, GPT-3.5-turbo, etc.)
- **Local models via OpenAI-compatible servers**:
  - KoboldCPP
  - LM Studio
  - text-generation-webui (oobabooga)
  - vLLM
  - Ollama (with OpenAI compatibility mode)

**Configuration**:
```bash
LLM_PROVIDER=local
LLM_API_KEY=not-needed          # Use "not-needed" for local servers
LLM_BASE_URL=http://localhost:5001/v1
LLM_MODEL=your-model-name
```

**Features**:
- Native OpenAI message format (no conversion needed)
- Supports all standard OpenAI parameters
- Works with any OpenAI-compatible endpoint

### 2. Gemini Provider (`gemini_provider.py`)

**Supports**:
- Google Gemini 1.5 Pro
- Google Gemini 1.5 Flash
- Google Gemini 1.0 Pro

**Configuration**:
```bash
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-1.5-pro
```

**Features**:
- **Complete safety override** (all filters set to `BLOCK_NONE`)
- Automatic format conversion (OpenAI → Gemini)
- System prompt handling (prepended as user message)
- Native async support

**Safety Settings** (for uncensored roleplay):
```python
safety_settings = {
    HARM_CATEGORY_HATE_SPEECH: BLOCK_NONE,
    HARM_CATEGORY_HARASSMENT: BLOCK_NONE,
    HARM_CATEGORY_SEXUALLY_EXPLICIT: BLOCK_NONE,
    HARM_CATEGORY_DANGEROUS_CONTENT: BLOCK_NONE,
}
```

## Usage

### Using ProviderFactory (Recommended)

The factory automatically creates the correct provider from configuration:

```python
from core.config import MyriadConfig
from core.providers import ProviderFactory

# Load configuration
config = MyriadConfig.from_env()

# Create provider automatically
provider = ProviderFactory.create_provider(config.llm)

# Use provider
response = await provider.generate(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ],
    temperature=0.9,
    max_tokens=500,
)
```

### Direct Provider Instantiation

You can also instantiate providers directly:

```python
from core.providers.openai_provider import OpenAIProvider
from core.providers.gemini_provider import GeminiProvider

# OpenAI provider
openai = OpenAIProvider(
    api_key="your-key",
    base_url="https://api.openai.com/v1",
    model="gpt-4",
)

# Gemini provider
gemini = GeminiProvider(
    api_key="your-gemini-key",
    model_name="gemini-1.5-pro",
)

# Both use the same interface
response = await openai.generate(messages, temperature=0.9, max_tokens=500)
response = await gemini.generate(messages, temperature=0.9, max_tokens=500)
```

## Integration with MessageProcessor

The `MessageProcessor` class now accepts a `provider` parameter instead of separate client/model parameters:

**Before (coupled to OpenAI)**:
```python
processor = MessageProcessor(
    client=openai_client,
    model="gpt-4",
    ...
)
```

**After (provider-agnostic)**:
```python
processor = MessageProcessor(
    provider=provider,  # Any LLMProvider instance
    ...
)
```

The processor calls `provider.generate()` internally, abstracting away provider-specific details.

## Adding New Providers

To add a new provider (e.g., Anthropic Claude):

### 1. Create Provider Class

Create `core/providers/anthropic_provider.py`:

```python
from core.providers.base import LLMProvider
from typing import List, Dict, Optional

class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model_name: str):
        # Initialize Anthropic client
        pass
    
    async def generate(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float, 
        max_tokens: int
    ) -> Optional[str]:
        # Convert OpenAI format to Anthropic format
        # Call Anthropic API
        # Return response
        pass
    
    @property
    def model_name(self) -> str:
        return self._model_name
    
    @property
    def provider_name(self) -> str:
        return "anthropic"
```

### 2. Update Factory

Add to `core/providers/factory.py`:

```python
from core.providers.anthropic_provider import AnthropicProvider

class ProviderFactory:
    @staticmethod
    def create_provider(config: LLMConfig) -> LLMProvider:
        provider_name = config.provider.lower()
        
        # ... existing providers ...
        
        elif provider_name == "anthropic":
            return AnthropicProvider(
                api_key=config.anthropic_api_key,
                model_name=config.anthropic_model,
            )
```

### 3. Update Configuration

Add to `core/config.py`:

```python
@dataclass
class LLMConfig:
    provider: str = "local"
    # ... existing fields ...
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-opus"
```

### 4. Update Environment

Add to `.env.example`:

```bash
# Anthropic Provider
ANTHROPIC_API_KEY=your_anthropic_api_key
ANTHROPIC_MODEL=claude-3-opus
```

## Testing

Run the provider test suite:

```bash
python test_providers.py
```

This tests:
- Provider factory instantiation
- OpenAI provider functionality
- Gemini provider with safety overrides
- Message format conversion
- Error handling

## Benefits of Modular Architecture

1. **Separation of Concerns**: Each provider is self-contained
2. **Easy Testing**: Mock providers for unit tests
3. **Simple Switching**: Change `LLM_PROVIDER` in `.env`
4. **Extensibility**: Add new providers without touching core code
5. **Type Safety**: Abstract interface enforces consistency
6. **No Conditional Logic**: No `if provider == "gemini"` scattered everywhere

## Migration Notes

### Old Code (Tightly Coupled)
```python
if provider == "gemini":
    response = gemini_engine.generate(...)
else:
    response = openai_client.chat.completions.create(...)
```

### New Code (Provider Pattern)
```python
response = await provider.generate(...)  # Works for any provider
```

## Provider Comparison

| Feature | OpenAI Provider | Gemini Provider |
|---------|----------------|----------------|
| **Official API** | ✅ Yes | ✅ Yes |
| **Local Models** | ✅ Yes (via OpenAI-compatible servers) | ❌ No |
| **Safety Override** | N/A | ✅ All filters disabled |
| **Native Async** | ✅ Yes | ✅ Yes |
| **System Messages** | ✅ Native support | ⚠️ Converted to user message |
| **Tool Calling** | ✅ Native support | ⚠️ Format adaptation needed |
| **Cost** | Varies (free for local) | Free tier + paid |

## Future Providers

Planned provider implementations:

- **Anthropic** (Claude 3.5 Sonnet, Opus)
- **Cohere** (Command R+)
- **Mistral** (Mistral Large)
- **Together.ai** (Multiple open models)
- **Groq** (Fast inference)

---

**Maintained by**: Project Myriad Contributors  
**Last Updated**: 2026-03-16
