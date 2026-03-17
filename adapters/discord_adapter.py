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
from core.init_logger import init_log
from adapters.discord import create_discord_bot


def run_discord_adapter() -> None:
    """Main entry point for the Discord adapter."""
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv()

    # Load configuration
    config = MyriadConfig.from_env()

    # Configure initialization logging level
    init_log.set_level(config.logging.init_log_level)

    print(f"Loaded configuration: {config}", flush=True)

    # Initialize VisionBridge if configured
    vision_bridge = None
    if config.vision.is_available:
        try:
            vision_bridge = VisionBridge(
                vision_api_key=config.vision.api_key,
                vision_base_url=config.vision.base_url,
                vision_model=config.vision.model,
            )
            init_log.info(f"✓ Vision Bridge enabled: {config.vision.base_url}")
        except Exception as e:
            init_log.warning(f"⚠ Vision Bridge initialization failed: {e}")
            init_log.warning("  Continuing without vision support...")
    else:
        if not config.vision.enabled:
            init_log.info("ℹ Vision disabled via VISION_ENABLED=false")
        else:
            init_log.info(
                "ℹ Vision Bridge not configured (set VISION_BASE_URL to enable)"
            )

    # Initialize VisionCacheService if configured (needed for persona appearance caching)
    vision_cache_service = None
    if config.vision.is_available:
        try:
            vision_cache_service = VisionCacheService(
                vision_api_key=config.vision.api_key,
                vision_base_url=config.vision.base_url,
                vision_model=config.vision.model,
            )
            init_log.info(f"✓ Vision Cache Service enabled: {config.vision.base_url}")
        except Exception as e:
            init_log.warning(f"⚠ Vision Cache Service initialization failed: {e}")
            init_log.warning("  Continuing without vision cache support...")
    else:
        if not config.vision.enabled:
            init_log.info("ℹ Vision Cache Service disabled via VISION_ENABLED=false")
        else:
            init_log.info(
                "ℹ Vision Cache Service not configured (set VISION_BASE_URL to enable)"
            )

    # Initialize AgentCore (platform-agnostic) with vision service for persona appearances
    init_log.info("→ Initializing AgentCore...")
    agent_core = AgentCore(config=config, vision_service=vision_cache_service)
    init_log.info("✓ AgentCore initialized")

    # Create Discord adapter
    init_log.debug("→ Creating Discord bot...")
    bot = create_discord_bot(agent_core, vision_bridge, vision_cache_service)
    init_log.debug("✓ Discord bot created")

    # Run bot
    init_log.info("Starting Myriad Discord Adapter...")
    bot.run(config.discord_token)


if __name__ == "__main__":
    run_discord_adapter()
