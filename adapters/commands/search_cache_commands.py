"""
Search Cache Management Commands for Discord.

Provides commands to view and manage the web search cache and rate limiter.
"""

import discord
from discord import app_commands
from typing import Optional

from core.tools.utility.search_cache import (
    get_search_cache,
    clear_search_cache,
    get_cache_stats,
    force_save_cache,
    get_rate_limiter,
)


class SearchCacheCommands(app_commands.Group):
    """Commands for managing the web search cache."""

    def __init__(self):
        super().__init__(
            name="cache",
            description="Manage the web search cache",
        )

    @app_commands.command(name="stats", description="View search cache statistics")
    async def cache_stats(self, interaction: discord.Interaction):
        """View search cache statistics."""
        stats = get_cache_stats()

        embed = discord.Embed(
            title="🗄️ Search Cache Statistics",
            color=discord.Color.blue(),
        )

        embed.add_field(
            name="Cache Size", value=f"{stats['size']} entries", inline=True
        )
        embed.add_field(name="Cache Hits", value=f"{stats['hits']}", inline=True)
        embed.add_field(name="Cache Misses", value=f"{stats['misses']}", inline=True)
        embed.add_field(name="Hit Rate", value=f"{stats['hit_rate']}%", inline=True)
        embed.add_field(
            name="Default TTL",
            value=f"{stats['default_ttl']}s ({stats['default_ttl'] // 60} min)",
            inline=True,
        )

        # Add persistence stats
        embed.add_field(
            name="Disk Saves",
            value=f"{stats.get('saves', 0)}",
            inline=True,
        )
        embed.add_field(
            name="Disk Loads",
            value=f"{stats.get('loads', 0)}",
            inline=True,
        )

        # Add cache file location
        cache_file = stats.get("cache_file", "Unknown")
        embed.add_field(
            name="Storage",
            value=f"Auto-save: {stats.get('auto_save', False)}\n{cache_file}",
            inline=False,
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="clear", description="Clear all cached search results")
    async def cache_clear(self, interaction: discord.Interaction):
        """Clear all cached search results."""
        stats_before = get_cache_stats()
        clear_search_cache()

        await interaction.response.send_message(
            f"✅ Cache cleared! Removed {stats_before['size']} cached entries.",
            ephemeral=True,
        )

    @app_commands.command(
        name="set_ttl", description="Set the default cache TTL (time-to-live)"
    )
    @app_commands.describe(
        seconds="Cache duration in seconds (default: 3600 = 1 hour)",
    )
    async def cache_set_ttl(
        self,
        interaction: discord.Interaction,
        seconds: int,
    ):
        """Set the default cache TTL."""
        if seconds < 60:
            await interaction.response.send_message(
                "❌ TTL must be at least 60 seconds.",
                ephemeral=True,
            )
            return

        if seconds > 86400:
            await interaction.response.send_message(
                "❌ TTL cannot exceed 86400 seconds (24 hours).",
                ephemeral=True,
            )
            return

        cache = get_search_cache()
        cache.set_ttl(seconds)

        minutes = seconds // 60
        hours = seconds // 3600

        time_display = f"{seconds}s"
        if hours > 0:
            time_display += f" ({hours}h)"
        elif minutes > 0:
            time_display += f" ({minutes}m)"

        await interaction.response.send_message(
            f"✅ Cache TTL updated to {time_display}",
            ephemeral=True,
        )

    @app_commands.command(name="cleanup", description="Remove expired cache entries")
    async def cache_cleanup(self, interaction: discord.Interaction):
        """Remove expired cache entries."""
        cache = get_search_cache()
        removed = cache.clear_expired()

        await interaction.response.send_message(
            f"✅ Cache cleanup complete! Removed {removed} expired entries.",
            ephemeral=True,
        )

    @app_commands.command(
        name="save", description="Force save cache to disk immediately"
    )
    async def cache_save(self, interaction: discord.Interaction):
        """Force save cache to disk."""
        force_save_cache()
        stats = get_cache_stats()

        await interaction.response.send_message(
            f"✅ Cache saved to disk! ({stats['size']} entries)\nLocation: {stats.get('cache_file', 'Unknown')}",
            ephemeral=True,
        )

    @app_commands.command(name="ratelimit", description="View rate limiter status")
    async def cache_ratelimit(self, interaction: discord.Interaction):
        """View rate limiter status."""
        rate_limiter = get_rate_limiter()
        wait_time = rate_limiter.get_wait_time()

        embed = discord.Embed(
            title="⏱️ Rate Limiter Status",
            color=discord.Color.green() if wait_time == 0 else discord.Color.orange(),
        )

        embed.add_field(
            name="Limit",
            value=f"{rate_limiter.max_requests} requests / {rate_limiter.time_window}s",
            inline=True,
        )

        # Count recent requests
        import time

        current_time = time.time()
        cutoff = current_time - rate_limiter.time_window
        recent_requests = len([t for t in rate_limiter._requests if t > cutoff])

        embed.add_field(
            name="Recent Requests",
            value=f"{recent_requests} / {rate_limiter.max_requests}",
            inline=True,
        )

        if wait_time > 0:
            embed.add_field(
                name="Wait Time",
                value=f"{wait_time:.1f}s until next request",
                inline=True,
            )
            embed.add_field(
                name="Status",
                value="⚠️ Rate limit active",
                inline=False,
            )
        else:
            embed.add_field(
                name="Status",
                value="✅ Ready for requests",
                inline=False,
            )

        await interaction.response.send_message(embed=embed)


def setup_commands(tree: app_commands.CommandTree) -> SearchCacheCommands:
    """
    Register search cache commands with the command tree.

    Args:
        tree: Discord command tree

    Returns:
        SearchCacheCommands group instance
    """
    cache_commands = SearchCacheCommands()
    tree.add_command(cache_commands)
    return cache_commands
