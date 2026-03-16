# Gemini API Integration Guide

## Overview

Project Myriad now supports **Google Gemini** as an alternative LLM provider alongside the existing OpenAI-compatible local API. This integration includes **complete safety override** (all filters set to `BLOCK_NONE`) for uncensored roleplay.

## Features

- ✅ **Provider Toggle**: Switch between `local` and `gemini` via config
- ✅ **Safety Overrides**: All harm categories set to `BLOCK_NONE`:
  - HATE_SPEECH
  - HARASSMENT  
  - SEXUALLY_EXPLICIT
  - DANGEROUS_CONTENT
- ✅ **Drop-in Replacement**: Works with existing persona system, limbic engine, memory, and all other features
- ✅ **Async Support**: Native async API calls with event loop handling

## Setup

### 1. Install Dependencies

```bash
pip install google-generativeai>=0.8.0
```

Or update from requirements.txt:

```bash
pip install -r requirements.txt
```

### 2. Get API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the key

### 3. Configure Environment

Edit your `.env` file:

```bash
# Set provider to "gemini" (or "local" for OpenAI-compatible)
LLM_PROVIDER=gemini

# Add your Gemini API key
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Specify model (defaults to gemini-1.5-pro)
GEMINI_MODEL=gemini-1.5-pro
```

**Important**: Keep your existing `LLM_API_KEY` and `LLM_BASE_URL` settings for when you want to switch back to local mode.

### 4. Start the Bot

```bash
python main.py
```

The bot will now use Gemini for all LLM generation with safety filters disabled.

## Switching Between Providers

To switch between local and Gemini:

**Local (OpenAI-compatible)**:
```bash
LLM_PROVIDER=local
```

**Gemini**:
```bash
LLM_PROVIDER=gemini
```

No code changes required - restart the bot after changing the `.env` file.

## Testing

Run the test suite to verify your Gemini configuration:

```bash
python test_gemini.py
```

This will test:
- ✅ Basic initialization and API calls
- ✅ Safety override functionality (mature content)
- ✅ Multi-turn conversation with context

## Architecture

### Module: `core/gemini_engine.py`

**`GeminiEngine` class**:
- Handles Gemini API initialization with safety overrides
- Converts OpenAI-style chat format to Gemini format
- Async response generation

**Key method**: `generate_response(system_prompt, chat_history, temperature, max_tokens)`
- Takes OpenAI-style messages
- Returns string response (or None on error)
- Applies `BLOCK_NONE` to all safety categories

### Integration Points

1. **`core/config.py`**: Added `LLMConfig.provider` and Gemini-specific settings
2. **`core/agent_core.py`**: Conditionally initializes Gemini or OpenAI client
3. **`core/message_processor.py`**: Routes LLM calls to correct provider

## Safety Configuration

**CRITICAL**: This integration explicitly disables ALL safety filters for uncensored roleplay. The safety settings are:

```python
safety_settings = {
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}
```

These settings are applied to:
- Model initialization
- Every API call (re-applied as parameter)

## Troubleshooting

**"google-generativeai not installed"**:
```bash
pip install google-generativeai
```

**"GEMINI_API_KEY not found"**:
- Check `.env` file has `GEMINI_API_KEY=your_key_here`
- Verify no typos in the variable name
- Restart the bot after adding the key

**"Response blocked or empty"**:
- Safety settings may not be working
- Check API key has proper permissions
- Try updating to latest `google-generativeai` library

**Rate limits**:
- Gemini has rate limits (60 requests/minute for free tier)
- Consider upgrading to paid tier for higher limits

## Model Options

Available Gemini models (as of Jan 2024):

- `gemini-1.5-pro` (recommended, default)
- `gemini-1.5-flash` (faster, cheaper)
- `gemini-1.0-pro` (legacy)

Set via `GEMINI_MODEL` in `.env`.

## Cost Comparison

**Gemini Pricing** (approximate):
- Free tier: 60 requests/minute
- Paid tier: Variable pricing

**Local Models**:
- Free (self-hosted)
- Hardware costs

Choose based on your needs.

## Known Limitations

1. **Tool calling**: Gemini uses different function calling format - Project Myriad's tool system designed for OpenAI format. Tool calls will work but may need format adaptation.

2. **System prompts**: Gemini doesn't have native "system" role. The integration prepends system messages as user messages.

3. **Response format**: Gemini may format responses differently than local models. Test thoroughly with your personas.

## Support

For issues with the Gemini integration:

1. Check that `google-generativeai` is installed
2. Verify API key is valid and has quota
3. Run `test_gemini.py` to diagnose issues
4. Check console output for error messages

---

**Built for Project Myriad** - Uncensored AI roleplay with hybrid memory architecture.
