# Web Search Enhancements - Full Feature Suite

## Overview

This document describes the **enhanced web search capabilities** added to Project Myriad, including image search, news search, result caching, and source filtering.

---

## 🆕 New Tools

### 1. **Image Search** (`search_web_images`)

Search for images on the internet via DuckDuckGo.

**Tool Definition:**
```json
{
  "name": "search_web_images",
  "description": "Search the internet for images...",
  "parameters": {
    "query": "string (required)"
  }
}
```

**Features:**
- Returns top 5 image results
- Includes image URLs, thumbnails, resolution, and source
- Perfect for visual content requests

**Example Usage:**
```
User: "Show me pictures of red pandas"
AI: *calls search_web_images(query="red pandas")*
AI: "Here are some adorable red pandas! [shares image URLs]"
```

**Return Format:**
```
Image search results for 'red pandas':

1. Red Panda in Tree
   Resolution: 1920x1080
   Image URL: https://example.com/redpanda.jpg
   Thumbnail: https://example.com/thumb.jpg
   Source: Wildlife Photos

2. Baby Red Panda
   ...
```

---

### 2. **News Search** (`search_news`)

Search for recent news articles with date filtering.

**Tool Definition:**
```json
{
  "name": "search_news",
  "description": "Search for recent news articles...",
  "parameters": {
    "query": "string (required)",
    "days": "integer (optional, default: 7)"
  }
}
```

**Features:**
- Returns top 5 recent news articles
- Includes publication dates and sources
- Configurable time range (1-30 days)
- Perfect for current events and breaking news

**Example Usage:**
```
User: "What's the latest news about SpaceX?"
AI: *calls search_news(query="SpaceX", days=7)*
AI: "Here's the latest SpaceX news from the past week..."
```

**Return Format:**
```
Recent news for 'SpaceX' (last 7 days):

1. SpaceX Launches Starship to Orbit
   Published: 2026-03-14T10:30:00Z
   Source: Space News
   SpaceX successfully launched its Starship rocket...
   URL: https://example.com/news/1

2. NASA Awards Contract to SpaceX
   Published: 2026-03-13T15:00:00Z
   ...
```

---

### 3. **Enhanced Web Search** (`search_web` - UPDATED)

The original web search tool now includes:
- **Result caching** (1-hour TTL by default)
- **Region filtering** (localized results)
- **Configurable result count** (1-10 results)

**Updated Parameters:**
```json
{
  "query": "string (required)",
  "region": "string (optional, default: 'wt-wt')",
  "max_results": "integer (optional, default: 3)"
}
```

**Region Codes:**
- `wt-wt` - Worldwide (default)
- `us-en` - United States
- `uk-en` - United Kingdom  
- `de-de` - Germany
- `fr-fr` - France
- `jp-jp` - Japan
- And many more...

**Example with Region:**
```python
search_web(query="football news", region="uk-en", max_results=5)
```

**Caching Behavior:**
```
First call: Fetches from DuckDuckGo
Second call (within 1 hour): Returns cached result with [Cached] prefix
After 1 hour: Fetches fresh results
```

---

## 🗄️ Search Cache System

### Architecture

The search cache is a **thread-safe, in-memory cache** with automatic expiration:

```python
# Global singleton pattern
cache = get_search_cache()

# Check cache
cached = cache.get("search_web", query="Python tutorial")

# Store result (with 1-hour TTL)
cache.set("search_web", result_text, ttl=3600, query="Python tutorial")
```

### Features

✅ **Thread-Safe** - Uses `threading.Lock` for concurrent access  
✅ **Automatic Expiration** - Configurable TTL per entry  
✅ **Statistics Tracking** - Monitors hits, misses, and hit rate  
✅ **Automatic Cleanup** - Removes expired entries on demand  
✅ **Hash-Based Keys** - SHA-256 hashing for consistent cache keys  

### Cache Statistics

```python
stats = cache.get_stats()
# {
#   "size": 42,           # Number of cached entries
#   "hits": 127,          # Cache hits
#   "misses": 58,         # Cache misses
#   "hit_rate": 68.65,    # Hit rate percentage
#   "default_ttl": 3600   # Default TTL in seconds
# }
```

### Cache Management Commands

**View Cache Stats:**
```
/cache stats
```

**Clear All Cached Results:**
```
/cache clear
```

**Set Cache TTL:**
```
/cache set_ttl seconds:7200  # 2 hours
```

**Remove Expired Entries:**
```
/cache cleanup
```

---

## 📊 Tool Comparison

| Feature | `search_web` | `search_web_images` | `search_news` |
|---------|-------------|-------------------|--------------|
| **Content Type** | Text/Web | Images | News Articles |
| **Max Results** | 1-10 (configurable) | 5 | 5 |
| **Caching** | ✅ Yes (1 hour) | ❌ No | ❌ No |
| **Region Filter** | ✅ Yes | ❌ No | ❌ No |
| **Date Filter** | ❌ No | ❌ No | ✅ Yes (1-30 days) |
| **Returns** | Titles, snippets, URLs | Image URLs, thumbnails | Titles, dates, sources |

---

## 🔧 Configuration

### Default Cache Settings

```python
# In core/tools/utility/search_cache.py
SearchCache(
    default_ttl=3600  # 1 hour (in seconds)
)
```

### Modify Cache TTL

**Option 1: Discord Command**
```
/cache set_ttl seconds:1800  # 30 minutes
```

**Option 2: Programmatically**
```python
from core.tools.utility.search_cache import get_search_cache

cache = get_search_cache()
cache.set_ttl(1800)  # 30 minutes
```

### Cache TTL by Tool

Different tools can have different TTLs:

```python
# Web search: 1 hour (general info changes slowly)
cache.set("search_web", result, ttl=3600)

# News search: 10 minutes (news changes fast)
cache.set("search_news", result, ttl=600)

# Image search: 24 hours (images rarely change)
cache.set("search_web_images", result, ttl=86400)
```

---

## 🚀 Usage Examples

### Example 1: Multi-Tool Research

```
User: "I need information about climate change. Show me news, 
      images, and general info."

AI: *calls search_news(query="climate change", days=7)*
    → Gets recent news articles

AI: *calls search_web_images(query="climate change effects")*
    → Gets relevant images

AI: *calls search_web(query="climate change solutions")*
    → Gets general web results

AI: "Here's what I found about climate change:

📰 Recent News (past 7 days):
- UN Climate Summit Announces New Goals (Mar 14)
- Scientists Report Record Temperatures (Mar 13)
...

🖼️ Visual Content:
[Shares 5 image URLs showing climate effects]

📚 General Information:
1. Climate Change Solutions - IPCC Report
   Comprehensive solutions including renewable energy...
   
2. What is Climate Change? - NASA
   Scientific explanation of climate change causes...
"
```

### Example 2: Localized Search

```
User: "What's happening in the UK news today?"

AI: *calls search_news(query="UK news", days=1)*
AI: *calls search_web(query="UK current events", region="uk-en")*

AI: "Here's what's happening in the UK today:

📰 Latest UK News:
- Parliament Votes on New Bill (Today, 9:30 AM)
- London Marathon Breaks Records (Today, 8:00 AM)
...

🌐 UK Web Results (localized):
1. BBC News - UK Homepage
2. The Guardian - UK Edition
...
"
```

### Example 3: Cache Optimization

```
# First user asks
User 1: "Tell me about quantum computing"
AI: *searches (cache MISS, fetches from web)*
AI: "Quantum computing is..."

# Second user asks same thing 30 minutes later
User 2: "What is quantum computing?"
AI: *searches (cache HIT, returns cached)*
AI: "Quantum computing is..." [same result, instant]

# Third user asks 2 hours later
User 3: "Explain quantum computing"
AI: *searches (cache EXPIRED, fetches fresh)*
AI: "Quantum computing is..." [updated info]
```

---

## 🎯 Best Practices

### When to Use Each Tool

**Use `search_web`:**
- General information queries
- Factual lookups
- "What is...?" questions
- Research topics

**Use `search_web_images`:**
- Visual content requests
- "Show me pictures of..."
- "What does X look like?"
- Image-based research

**Use `search_news`:**
- Current events
- Breaking news
- "What's the latest...?"
- Recent developments (last 1-30 days)

### Cache Management

**When to clear cache:**
- After deploying new search features
- When results seem outdated
- Memory optimization needed
- Testing fresh search results

**Optimal TTL settings:**
- **News:** 5-10 minutes (fast-changing)
- **General web:** 1 hour (moderate)
- **Images:** 6-24 hours (slow-changing)
- **Academic/reference:** 24 hours (static)

---

## 📈 Performance Impact

### With Caching (Default)

```
First search:  ~2-3 seconds (network call)
Cached search: ~5-10ms (memory lookup)
```

**Performance gain:** ~200-600x faster for cached results

### Cache Hit Rates (Expected)

- **Popular queries:** 60-80% hit rate
- **Unique queries:** 10-30% hit rate
- **Average:** 40-50% hit rate

### Memory Usage

```
Typical cache entry: ~2-5 KB
100 cached results: ~250-500 KB
1000 cached results: ~2.5-5 MB
```

Very lightweight - minimal memory impact.

---

## 🔍 Advanced Features

### Custom Cache Keys

The cache uses SHA-256 hashing of tool name + arguments:

```python
# These create different cache keys:
search_web(query="python")
search_web(query="python", region="us-en")
search_web(query="python", max_results=5)
```

### Automatic Cleanup

```python
# Remove expired entries
cache.clear_expired()

# Returns number of entries removed
removed_count = cache.clear_expired()
print(f"Removed {removed_count} expired entries")
```

### Thread Safety

Multiple concurrent searches are safe:

```python
# Thread 1
search_web(query="topic A")

# Thread 2 (at same time)
search_web(query="topic B")

# Both safe - uses internal locking
```

---

## 🛠️ Troubleshooting

### Issue: Cache Not Working

**Symptoms:** Every search fetches from web, no cache hits

**Solutions:**
1. Check cache stats: `/cache stats`
2. Verify TTL isn't too short: `/cache stats`
3. Check if queries are identical (case-sensitive)

### Issue: Outdated Results

**Symptoms:** Search returns old information

**Solutions:**
1. Clear cache: `/cache clear`
2. Reduce TTL: `/cache set_ttl seconds:600`
3. Use `search_news` for time-sensitive queries

### Issue: High Memory Usage

**Symptoms:** Bot using too much RAM

**Solutions:**
1. Clear cache: `/cache clear`
2. Run cleanup: `/cache cleanup`
3. Reduce TTL to expire faster

---

## 📦 File Structure

```
core/tools/utility/
├── search_web.py           # Enhanced web search (with caching)
├── search_web_images.py    # Image search (NEW)
├── search_news.py          # News search (NEW)
├── search_cache.py         # Cache system (NEW)
└── __init__.py             # Updated exports

adapters/commands/
└── search_cache_commands.py  # Discord cache commands (NEW)
```

---

## 🔮 Future Enhancements

Potential future improvements:

1. **Persistent Cache** - Save cache to disk for persistence across restarts
2. **Cache Warming** - Pre-load common queries
3. **Smart TTL** - Adjust TTL based on query type
4. **Multi-Provider** - Fallback to Google/Bing if DuckDuckGo fails
5. **Video Search** - Add `search_web_videos` tool
6. **Advanced Filters** - Date ranges, file types, safe search
7. **Cache Analytics** - Track most popular queries
8. **Distributed Cache** - Redis integration for multi-instance deployments

---

## 📊 Summary

### Added Files
- ✅ `core/tools/utility/search_web_images.py` (97 lines)
- ✅ `core/tools/utility/search_news.py` (122 lines)
- ✅ `core/tools/utility/search_cache.py` (172 lines)
- ✅ `adapters/commands/search_cache_commands.py` (127 lines)

### Modified Files
- ✅ `core/tools/utility/search_web.py` - Added caching, region filter, max_results
- ✅ `core/tools/utility/__init__.py` - Export new tools
- ✅ `core/tools/__init__.py` - Register new tools
- ✅ `adapters/discord_adapter.py` - Register cache commands

### Total
- **4 new files** (518 lines)
- **4 modified files**
- **3 new tools** (image search, news search, enhanced web search)
- **1 new command group** (/cache with 4 subcommands)

---

**The enhanced web search system is now fully operational! 🌐✨**
