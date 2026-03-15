# Read URL Tool - Webpage Content Extraction

## Overview

The **Read URL Tool** (`read_url`) allows Project Myriad's AI agents to fetch and read the actual text content of any webpage. This complements the `search_web` tool by enabling deep content analysis of specific URLs.

---

## 🎯 Purpose

While `search_web` finds information, `read_url` **reads** the detailed content:

```
search_web  → "Here are 3 articles about quantum computing"
read_url    → "Let me read that article for you... [full article text]"
```

Perfect for:
- Reading articles the user provides
- Following up on search results with detailed content
- Accessing documentation pages
- Reading blog posts, papers, and web content
- Extracting information from specific pages

---

## 🛠️ Implementation

### Tool Definition

**File:** `core/tools/utility/read_url.py` (158 lines)

```python
class ReadUrlTool(Tool):
    """Tool for fetching and reading webpage content."""
    
    @property
    def name(self) -> str:
        return "read_url"
    
    @property
    def description(self) -> str:
        return (
            "Read the full text content of a specific webpage by URL. "
            "Fetches the page, strips HTML/CSS/JavaScript, and returns "
            "clean, readable text..."
        )
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The full URL (http:// or https://)"
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Max characters (default: 10000)",
                    "default": 10000
                }
            },
            "required": ["url"]
        }
```

### OpenAI Function Calling Schema

```json
{
  "type": "function",
  "function": {
    "name": "read_url",
    "description": "Read the full text content of a specific webpage by URL...",
    "parameters": {
      "type": "object",
      "properties": {
        "url": {
          "type": "string",
          "description": "The full URL of the webpage to read (must start with http:// or https://)."
        },
        "max_chars": {
          "type": "integer",
          "description": "Maximum number of characters to return (default: 10000).",
          "default": 10000
        }
      },
      "required": ["url"]
    }
  }
}
```

---

## 🔧 How It Works

### Step-by-Step Process

1. **URL Validation**
   ```python
   if not url.startswith(('http://', 'https://')):
       return "Invalid URL: must start with http:// or https://"
   ```

2. **Fetch Webpage**
   ```python
   import requests
   response = requests.get(url, headers=headers, timeout=10)
   ```

3. **Parse HTML**
   ```python
   from bs4 import BeautifulSoup
   soup = BeautifulSoup(response.content, 'html.parser')
   ```

4. **Strip Non-Content Elements**
   ```python
   # Remove: script, style, nav, footer, header, aside, iframe, noscript
   for element in soup(['script', 'style', 'nav', ...]):
       element.decompose()
   ```

5. **Extract Clean Text**
   ```python
   text = soup.get_text(separator='\n', strip=True)
   # Clean whitespace, remove empty lines
   ```

6. **Truncate if Needed**
   ```python
   if len(clean_text) > max_chars:
       clean_text = clean_text[:max_chars]
   ```

7. **Format Result**
   ```
   Page Title: [Article Title]
   URL: https://example.com/article
   Content Length: 8432 characters
   ==================================================
   
   [Clean text content here...]
   ```

---

## 📊 Features

### ✅ Clean Text Extraction

Removes all HTML noise:
- ❌ `<script>` tags and JavaScript
- ❌ `<style>` tags and CSS
- ❌ Navigation menus (`<nav>`)
- ❌ Headers and footers
- ❌ Sidebars and ads (`<aside>`)
- ❌ Iframes and embedded content
- ✅ Returns only readable text!

### ✅ Configurable Length

```python
# Short summary (1000 chars)
read_url(url="...", max_chars=1000)

# Standard article (10000 chars - default)
read_url(url="...")

# Long documentation (30000 chars)
read_url(url="...", max_chars=30000)

# Maximum allowed (50000 chars)
read_url(url="...", max_chars=50000)
```

### ✅ Error Handling

Comprehensive error messages for:

**404 Not Found:**
```
Error: Page not found (404)
URL: https://example.com/missing
The requested page does not exist.
```

**403 Forbidden:**
```
Error: Access forbidden (403)
URL: https://example.com/blocked
The server is blocking automated access to this page.
```

**Timeout:**
```
Error: Request timed out while fetching [url]
The server took too long to respond (>10 seconds).
```

**Connection Error:**
```
Error: Connection failed for [url]
Could not connect to the server. Check if the URL is correct.
```

### ✅ Smart User-Agent

Uses a realistic browser User-Agent to avoid blocking:
```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...'
}
```

---

## 🚀 Usage Examples

### Example 1: User Provides URL

```
User: "Can you read this article for me? 
       https://example.com/quantum-computing-breakthrough"

AI: *calls read_url(url="https://example.com/quantum-computing-breakthrough")*

AI: "I've read the article! Here's what it says:

The article titled 'Major Breakthrough in Quantum Computing' 
discusses how researchers at MIT have developed a new type of 
qubit that maintains coherence for 10x longer than previous 
designs. The key innovation is...

[Continues with detailed summary based on actual article content]
"
```

### Example 2: Following Search Results

```
User: "Find me articles about AI ethics and read the top one"

AI: *calls search_web(query="AI ethics articles")*
    → Gets: "1. AI Ethics Guidelines - https://example.com/ai-ethics"

AI: *calls read_url(url="https://example.com/ai-ethics")*
    → Reads full article content

AI: "I found several articles on AI ethics and read the top result 
     for you. The article covers five key principles:

1. Transparency - AI systems should be explainable...
2. Fairness - Algorithms must avoid bias...
3. Privacy - User data must be protected...
[etc.]

Would you like me to read any of the other articles I found?"
```

### Example 3: Multi-Step Research

```
User: "Research climate change solutions"

AI Strategy:
  1. search_web(query="climate change solutions")
     → Finds 3 relevant URLs
  
  2. read_url(url=first_result)
     → Reads detailed content of top article
  
  3. read_url(url=second_result)
     → Reads another perspective
  
  4. Synthesizes information from both sources

AI Response:
  "I've researched climate change solutions by reading two comprehensive 
   articles. Here's what I found:
   
   From the IPCC report, the key solutions include:
   [detailed points from first article]
   
   The Nature article adds additional insights:
   [detailed points from second article]
   
   Combining these sources, the most promising approaches are..."
```

### Example 4: Documentation Reading

```
User: "How do I use async/await in Python? Read the official docs"

AI: *calls search_web(query="Python async await documentation")*
    → Finds: "https://docs.python.org/3/library/asyncio.html"

AI: *calls read_url(url="https://docs.python.org/3/library/asyncio.html")*
    → Reads official Python documentation

AI: "I've read the official Python asyncio documentation. Here's how 
     async/await works:

[Provides detailed explanation based on actual docs content, with 
 accurate code examples and explanations from the real documentation]
"
```

---

## 🔄 Integration with Agentic Loop

The `read_url` tool is **automatically integrated** into the existing agentic loop in `MessageProcessor._execute_tool_loop()`:

```python
# NO CHANGES NEEDED - Already works!

while tool_iterations < max_iterations:
    # 1. Call LLM with ALL tool schemas (including read_url)
    response = client.chat.completions.create(
        messages=messages,
        tools=[search_web, read_url, ...]  # All tools registered
    )
    
    # 2. Parse response
    tool_call = parse_tool_call(response)
    
    # 3. Execute whichever tool was called
    if tool_call:
        if tool_call["tool"] == "search_web":
            result = execute_search_web(...)
        elif tool_call["tool"] == "read_url":  # ← Handled automatically!
            result = execute_read_url(...)
        # etc.
        
        # 4. Inject result back into conversation
        messages.append({"role": "user", "content": result})
        
        # 5. Continue loop - LLM reads result and responds
        continue
    
    # Final response
    return response
```

**The tool is registered in `BUILTIN_TOOLS` and automatically available!**

---

## ⚙️ Configuration

### Character Limits

The `max_chars` parameter prevents massive pages from overwhelming the LLM:

```python
# Default: 10,000 characters (~2000 words)
read_url(url="...")

# Clamped between 100 and 50,000
max_chars = max(100, min(50000, max_chars))
```

**Why 10,000 default?**
- Most articles: 1,000-5,000 characters
- With context: ~2,500 tokens for GPT-4
- Leaves room for conversation history
- Balance between detail and context window

### Timeout Settings

```python
# Request timeout: 10 seconds
response = requests.get(url, timeout=10)
```

Fast enough to avoid hanging, long enough for slow servers.

---

## 🎯 Tool Comparison

| Feature | `search_web` | `read_url` |
|---------|-------------|-----------|
| **Purpose** | Find information | Read specific content |
| **Input** | Search query | Direct URL |
| **Output** | 3-10 search results | Full page text |
| **Use Case** | "Find articles about X" | "Read this article" |
| **Content Depth** | Snippets (1-2 sentences) | Full text (10K chars) |
| **Multiple Results** | Yes (3-10 pages) | No (1 page) |
| **When to Use** | Discovery | Deep reading |

### Combined Power

```
1. search_web("topic")     → Find relevant pages
2. read_url(found_url)     → Read detailed content
3. Synthesize → Complete research!
```

---

## 🛡️ Security & Safety

### URL Validation

```python
# Only allow HTTP/HTTPS
if not url.startswith(('http://', 'https://')):
    return "Invalid URL"
```

### Timeout Protection

```python
# 10-second timeout prevents hanging
requests.get(url, timeout=10)
```

### User-Agent Spoofing

```python
# Realistic browser headers
headers = {'User-Agent': 'Mozilla/5.0 ...'}
```

Prevents being blocked as a bot by most sites.

### Content Length Limits

```python
# Maximum 50,000 characters
# Prevents memory exhaustion
max_chars = min(50000, max_chars)
```

---

## 🐛 Troubleshooting

### Issue: "Access forbidden (403)"

**Cause:** Website blocking automated access

**Solutions:**
1. Some sites block bots - normal behavior
2. Try reading a different source
3. User can manually read and paste content

### Issue: "Request timed out"

**Cause:** Slow server or large page

**Solutions:**
1. Retry the request
2. Try a different URL
3. Server might be overloaded

### Issue: "Page not found (404)"

**Cause:** Broken link or incorrect URL

**Solutions:**
1. Verify URL is correct
2. Try searching for updated link
3. Page may have been removed

### Issue: Content looks messy

**Cause:** Complex page structure

**Solutions:**
1. The tool does its best to clean HTML
2. Some sites have poor structure
3. Try `max_chars` parameter for shorter excerpt

---

## 📈 Performance

### Typical Response Times

```
Small article (< 50KB):     ~1-2 seconds
Medium page (50-200KB):     ~2-4 seconds
Large page (> 200KB):       ~4-8 seconds
Timeout threshold:          10 seconds
```

### Memory Usage

```
Typical article:            ~10-50 KB
Maximum (50K chars):        ~50 KB
Very lightweight!
```

### Rate Limiting

No built-in rate limiting - relies on:
- Polite User-Agent header
- Reasonable timeout (10s)
- Max tool iterations (5 per message)

**Best practice:** Don't read dozens of URLs in one message.

---

## 🔮 Advanced Use Cases

### Academic Research

```
User: "Analyze this research paper for me"
User: [provides arxiv.org URL]

AI: *calls read_url(url=paper_url, max_chars=30000)*
AI: "I've read the entire paper. Here's my analysis:

Abstract Summary: [...]
Key Findings: [...]
Methodology: [...]
Conclusions: [...]
Critical Analysis: [...]
"
```

### Competitive Analysis

```
User: "Compare these three competitor websites"

AI: *calls read_url(url=competitor1)*
AI: *calls read_url(url=competitor2)*
AI: *calls read_url(url=competitor3)*

AI: "I've analyzed all three competitor sites:

Competitor 1:
  - Main features: [...]
  - Pricing: [...]
  
Competitor 2:
  - Main features: [...]
  - Pricing: [...]
  
[Detailed comparison table]
"
```

### Documentation Lookup

```
User: "How do I configure nginx for reverse proxy?"

AI: *searches for nginx docs*
AI: *reads official documentation page*
AI: "According to the official nginx documentation:

[Provides accurate, doc-based answer with config examples]
"
```

---

## 🎓 Best Practices

### When to Use `read_url`

✅ **Good:**
- User provides a specific URL
- Following up on search results
- Reading articles/documentation
- Deep analysis of specific content

❌ **Avoid:**
- User asks general question (use search instead)
- URL is likely to be blocked (paywalls, etc.)
- Multiple URLs in rapid succession (rate limiting)

### Optimal max_chars Settings

```
Quick summary:           1,000-3,000 chars
Standard article:       10,000 chars (default)
Long documentation:     20,000-30,000 chars
Academic paper:         30,000-50,000 chars
```

### Combining with Search

```python
# GOOD: Search, then read top result
1. search_web(query="topic")
2. read_url(url=top_result)

# BETTER: Search, read multiple, synthesize
1. search_web(query="topic")
2. read_url(url=result1)
3. read_url(url=result2)
4. Compare and synthesize
```

---

## 📦 Dependencies

```bash
# Added to requirements.txt
requests>=2.31.0        # HTTP client
beautifulsoup4>=4.12.0  # HTML parsing
```

Install:
```bash
pip install requests beautifulsoup4
# Or
pip install -r requirements.txt
```

---

## 🔧 Technical Details

### HTML Parsing

Uses **BeautifulSoup4** with the built-in `html.parser`:

```python
soup = BeautifulSoup(response.content, 'html.parser')
```

**Why BeautifulSoup?**
- ✅ Robust HTML parsing
- ✅ Handles malformed HTML
- ✅ Easy element removal
- ✅ Clean text extraction

### Text Cleaning Process

```python
# 1. Remove non-content elements
for element in soup(['script', 'style', 'nav', ...]):
    element.decompose()

# 2. Extract text with newline separators
text = soup.get_text(separator='\n', strip=True)

# 3. Clean whitespace
lines = [line.strip() for line in text.splitlines()]
lines = [line for line in lines if line]  # Remove empty
clean_text = '\n'.join(lines)
```

### Error Handling Hierarchy

```
1. URL validation    → "Invalid URL"
2. Library check     → "Library not installed"
3. Timeout          → "Request timed out"
4. Connection       → "Connection failed"
5. HTTP errors      → "Error: HTTP [code]"
6. Generic errors   → "Error reading URL"
```

All errors return descriptive messages, never crash.

---

## 📊 Statistics

### Output Format

```
Page Title: [Extracted from <title> tag]
URL: [Original URL]
Content Length: [Character count]
==================================================

[Clean text content]

[Truncation notice if applicable]
```

**Includes:**
- Page title for context
- Original URL for reference
- Content length for transparency
- Truncation notice if limited

---

## 🎉 Summary

### What Was Implemented

✅ **ReadUrlTool class** (158 lines)
  - Fetches webpage content via `requests`
  - Parses HTML with `BeautifulSoup4`
  - Strips all non-content elements
  - Returns clean, readable text
  - Configurable character limit (100-50K)
  - Comprehensive error handling

✅ **Tool Schema** (OpenAI format)
  - Function name: `read_url`
  - Parameters: `url` (required), `max_chars` (optional)
  - Automatically registered in BUILTIN_TOOLS

✅ **Agentic Loop Integration**
  - NO changes needed to `agent_core.py`
  - NO changes needed to `message_processor.py`
  - Tool automatically available via ToolRegistry
  - Works alongside search_web and all other tools

✅ **Dependencies**
  - `requests>=2.31.0`
  - `beautifulsoup4>=4.12.0`

### Files Modified

```
✅ core/tools/utility/read_url.py      (NEW - 158 lines)
✅ core/tools/utility/__init__.py      (+2 lines)
✅ core/tools/__init__.py              (+3 lines)
✅ requirements.txt                    (+2 lines)
```

---

**The `read_url` tool is fully operational and ready to read the web! 📖🌐**
