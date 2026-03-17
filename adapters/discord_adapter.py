"""
Discord Frontend Adapter - Platform bridge for Project Myriad.

This module provides the main entry point for running the Discord bot.
The actual bot implementation has been refactored into the adapters/discord/ module.

REFACTORED (RDSSC Phase 5):
- Extracted bot implementation to adapters/discord/bot.py
- Extracted event handlers to adapters/discord/event_handlers.py
- Extracted vision processing to adapters/discord/vision_processor.py
- Extracted utilities to adapters/discord/utils.py
"""

from core.agent_core import AgentCore
from core.config import MyriadConfig
from core.vision_bridge import VisionBridge
from core.vision_cache_service import VisionCacheService
from adapters.discord import create_discord_bot


def run_discord_adapter() -> None:
    """Main entry point for the Discord adapter."""
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv()

    # Load configuration
    config = MyriadConfig.from_env()
    print(f"Loaded configuration: {config}")

    # Initialize VisionBridge if configured
    vision_bridge = None
    if config.vision.is_available:
        try:
            vision_bridge = VisionBridge(
                vision_api_key=config.vision.api_key,
                vision_base_url=config.vision.base_url,
                vision_model=config.vision.model,
            )
            print(f"✓ Vision Bridge enabled: {config.vision.base_url}")
        except Exception as e:
            print(f"⚠ Vision Bridge initialization failed: {e}")
            print("  Continuing without vision support...")
    else:
        if not config.vision.enabled:
            print("ℹ Vision disabled via VISION_ENABLED=false")
        else:
            print("ℹ Vision Bridge not configured (set VISION_BASE_URL to enable)")

    # Initialize VisionCacheService if configured (needed for persona appearance caching)
    vision_cache_service = None
    if config.vision.is_available:
        try:
            vision_cache_service = VisionCacheService(
                vision_api_key=config.vision.api_key,
                vision_base_url=config.vision.base_url,
                vision_model=config.vision.model,
            )
            print(f"✓ Vision Cache Service enabled: {config.vision.base_url}")
        except Exception as e:
            print(f"⚠ Vision Cache Service initialization failed: {e}")
            print("  Continuing without vision cache support...")
    else:
        if not config.vision.enabled:
            print("ℹ Vision Cache Service disabled via VISION_ENABLED=false")
        else:
            print(
                "ℹ Vision Cache Service not configured (set VISION_BASE_URL to enable)"
            )

    # Initialize AgentCore (platform-agnostic) with vision service for persona appearances
    print("→ Initializing AgentCore...", flush=True)
    agent_core = AgentCore(config=config, vision_service=vision_cache_service)
    print("✓ AgentCore initialized", flush=True)

    # Create Discord adapter
    print("→ Creating Discord bot...", flush=True)
    bot = create_discord_bot(agent_core, vision_bridge, vision_cache_service)
    print("✓ Discord bot created", flush=True)

    # Run bot
    print("Starting Myriad Discord Adapter...", flush=True)
    bot.run(config.discord_token)


if __name__ == "__main__":
    run_discord_adapter()
