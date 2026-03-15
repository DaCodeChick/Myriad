# Web Search Tool - Internet Access for Project Myriad

## Overview

The Web Search Tool (`search_web`) provides Project Myriad's AI agents with **real-time internet access** via DuckDuckGo search. This enables the AI to look up current events, recent information, and facts beyond its training data.

## Architecture

### 1. The Web Search Tool (`core/tools/utility/search_web.py`)

The tool is implemented as a modular class following the established Tool pattern:

```python
class SearchWebTool(Tool):
    """Tool for searching the internet for real-time information."""
    
    @property
    def name(self) -> str:
        return "search_web"
    
    @property
    def description(self) -> str:
        return "Search the internet for real-time information..."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query..."
                }
            },
            "required": ["query"]
        }
    
    def execute(self, query: str) -> str:
        """Execute web search and return top 3 results"""
        # Uses duckduckgo-search library
        # Returns formatted results with titles, snippets, URLs
```

**Key Features:**
- Returns top 3 search results with titles, descriptions, and URLs
- Graceful fallback if `duckduckgo-search` is not installed
- Error handling for network issues
- Clean, formatted output for LLM consumption

### 2. The Tool Schema (OpenAI Function Calling Format)

The tool is automatically registered with the LLM using OpenAI's function calling format:

```json
{
  "type": "function",
  "function": {
    "name": "search_web",
    "description": "Search the internet for real-time information, current events, facts, news, or any information that requires up-to-date knowledge...",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "The search query to look up on the internet. Be specific and concise."
        }
      },
      "required": ["query"]
    }
  }
}
```

This schema is passed to the LLM during every API call, allowing it to understand when and how to use the tool.

### 3. The Agentic Loop (`core/message_processor.py`)

The existing `MessageProcessor` already implements the complete agentic loop with tool execution. Here's how it works:

#### **Tool Execution Loop Flow:**

```
1. User sends message
   ↓
2. LLM receives message + tool schemas
   ↓
3. LLM responds (either tool call JSON or natural text)
   ↓
4. Is it a tool call?
   ├─ YES → Execute tool (search_web)
   │         ↓
   │    Get search results
   │         ↓
   │    Inject results as system message
   │         ↓
   │    Call LLM again (go to step 2)
   │         ↓
   │    LLM reads results and generates final response
   │
   └─ NO → Return response to user
```

#### **Implementation Details:**

```python
# In MessageProcessor._execute_tool_loop()

while tool_iterations < self.max_tool_iterations:
    # Call LLM
    response = self.client.chat.completions.create(
        model=self.model,
        messages=messages,
        temperature=persona.temperature,
        max_tokens=persona.max_tokens,
    )
    
    assistant_message = response.choices[0].message.content
    
    # Check if this is a tool call
    if tool_registry:
        tool_call = parse_tool_call(assistant_message)
        
        if tool_call:
            tool_name = tool_call["tool"]      # "search_web"
            tool_args = tool_call["arguments"]  # {"query": "..."}
            
            # Execute the tool
            result = tool_registry.execute_tool(tool_name, tool_args)
            tool_response_text = format_tool_response(tool_name, result)
            
            # Inject tool result back into conversation
            messages.append({"role": "assistant", "content": assistant_message})
            messages.append({"role": "user", "content": tool_response_text})
            
            # Continue loop (call LLM again with results)
            continue
    
    # Not a tool call - this is the final response
    return assistant_message
```

## Example Conversation

**User:** "What's happening in the news today about AI?"

**LLM (Internal Tool Call):**
```json
{
  "tool": "search_web",
  "arguments": {
    "query": "AI news today"
  }
}
```

**System (Tool Response):**
```
[Tool Response: search_web]
Result: Search results for 'AI news today':

1. OpenAI Announces GPT-5
   Major breakthrough in language model capabilities announced today...
   Source: https://example.com/news/ai-1

2. AI Regulation Bill Passes Senate
   New legislation to regulate artificial intelligence development...
   Source: https://example.com/news/ai-2

3. Google's AI Makes Medical Breakthrough
   New AI system achieves 95% accuracy in early cancer detection...
   Source: https://example.com/news/ai-3
[End Tool Response]
```

**LLM (Final Response to User):**
"There's quite a lot happening in AI today! The biggest news is OpenAI's announcement of GPT-5, which represents a major breakthrough in language model capabilities. Additionally, a significant AI regulation bill just passed the Senate, establishing new guidelines for AI development. On the medical front, Google's latest AI system is making waves with 95% accuracy in early cancer detection. Would you like me to elaborate on any of these stories?"

## Installation

Add the required dependency:

```bash
pip install duckduckgo-search>=6.0.0
```

Or install from requirements.txt:

```bash
pip install -r requirements.txt
```

## Configuration

The web search tool is **automatically enabled** when:

1. Tool calling is enabled in config (`tools.enabled = True`)
2. The `duckduckgo-search` library is installed

No additional configuration is needed. The tool will gracefully degrade if the library is not available.

## Usage

Users don't need to explicitly invoke the tool. The AI will automatically use it when appropriate:

**Triggers web search:**
- "What's in the news today?"
- "Tell me about recent developments in quantum computing"
- "Who won the game last night?"
- "What's the weather forecast for tomorrow?"

**Does NOT trigger web search:**
- "Tell me about yourself" (uses persona memory)
- "What did we talk about yesterday?" (uses conversation history)
- "Roll a dice" (uses different tool)

## Tool Execution Limits

- **Max iterations per message:** Configurable via `config.tools.max_iterations` (default: 5)
- **Results per search:** 3 top results
- **Timeout:** Handled by duckduckgo-search library

## Integration Points

### File Structure
```
core/tools/
├── base.py                    # Base Tool class
├── __init__.py                # Tool registry (includes SearchWebTool)
└── utility/
    ├── __init__.py            # Utility tools exports
    ├── get_current_time.py    # Time tool
    ├── roll_dice.py           # Dice tool
    └── search_web.py          # ⭐ Web search tool (NEW)
```

### Registration Flow
```
1. SearchWebTool defined in core/tools/utility/search_web.py
   ↓
2. Imported in core/tools/utility/__init__.py
   ↓
3. Registered in core/tools/__init__.py (BUILTIN_TOOLS list)
   ↓
4. ToolRegistry loads all BUILTIN_TOOLS automatically
   ↓
5. Tool schemas passed to LLM on every API call
```

## Advanced Features

### Graceful Degradation

If `duckduckgo-search` is not installed:
```python
# Tool still loads but returns helpful error message
"Web search unavailable: duckduckgo-search library not installed.
To enable web search, install: pip install duckduckgo-search"
```

### Error Handling

Network errors, rate limits, and search failures are gracefully handled:
```python
try:
    # Perform search
    results = list(ddgs.text(query, max_results=3))
except Exception as e:
    return f"Error performing web search: {str(e)}"
```

### Memory Integration

Tool calls and results are automatically saved to memory:
```python
# In MessageProcessor._execute_tool_loop()
if on_message_saved:
    on_message_saved("assistant", assistant_message)  # Tool call JSON
    on_message_saved("user", tool_response_text)       # Search results
```

This means:
- The AI remembers what it searched for
- Conversation history includes tool interactions
- Memory Matrix can recall past web searches

## Future Enhancements

Potential improvements:

1. **Image Search** - Add `search_web_images(query)` for visual results
2. **News-Specific Search** - Add `search_news(query, days=7)` for recent news
3. **Caching** - Cache search results to reduce API calls
4. **Source Filtering** - Allow filtering by domain or date range
5. **Multi-Provider** - Add fallback to Google, Bing, or other search APIs

## Troubleshooting

**Tool not being called:**
- Verify tools are enabled: `config.tools.enabled = True`
- Check LLM supports function calling (most modern models do)
- Ensure query clearly requires real-time information

**"duckduckgo-search library not installed" error:**
```bash
pip install duckduckgo-search
```

**Rate limiting:**
- DuckDuckGo has rate limits; add delays between searches if needed
- Consider implementing request throttling in future versions

## Credits

- **DuckDuckGo Search:** https://github.com/deedy5/duckduckgo_search
- **OpenAI Function Calling:** https://platform.openai.com/docs/guides/function-calling

---

**The web search tool is now live in Project Myriad! 🌐✨**
