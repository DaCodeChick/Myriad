"""
Spontaneous Autonomy Daemon - Background service for unsolicited AI interactions.

This daemon runs independently of the main bot, monitoring user activity patterns
and allowing personas to initiate conversations when appropriate based on:
- Circadian rhythm analysis (activity probability)
- Time since last interaction
- Limbic state and persona personality
- Sleep protection (inhibitor for low-probability hours)

Part of Project Myriad's Spontaneous Autonomy system.
"""

import asyncio
import os
import sys
import discord
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.activity_tracker import ActivityTracker
from database.user_state import UserState
from database.limbic_engine import LimbicEngine
from database.user_preferences import UserPreferences
from core.persona_loader import PersonaLoader


class AutonomyDaemon:
    """Background daemon for spontaneous AI-initiated interactions."""

    def __init__(
        self,
        discord_token: str,
        llm_client: OpenAI,
        check_interval_minutes: int = 60,
        inactivity_threshold_hours: float = 4.0,
        sleep_protection_threshold: float = 0.2,
    ):
        """
        Initialize the Autonomy Daemon.

        Args:
            discord_token: Discord bot token
            llm_client: OpenAI API client for LLM calls
            check_interval_minutes: How often to check for spontaneous messages (default: 60)
            inactivity_threshold_hours: Hours of inactivity before considering outreach (default: 4.0)
            sleep_protection_threshold: Activity probability below which to inhibit (default: 0.2)
        """
        self.discord_token = discord_token
        self.llm_client = llm_client
        self.check_interval = check_interval_minutes * 60  # Convert to seconds
        self.inactivity_threshold = inactivity_threshold_hours
        self.sleep_protection = sleep_protection_threshold

        # Initialize subsystems
        self.activity_tracker = ActivityTracker()
        self.user_state = UserState()
        self.persona_loader = PersonaLoader()
        self.user_preferences = UserPreferences()

        # Initialize limbic engine if enabled
        limbic_enabled = os.getenv("LIMBIC_ENABLED", "true").lower() == "true"
        self.limbic_engine = LimbicEngine() if limbic_enabled else None

        # Discord client (bot instance)
        intents = discord.Intents.default()
        intents.message_content = True
        self.discord_client = discord.Client(intents=intents)

        print(f"[AutonomyDaemon] Initialized:")
        print(f"  Check interval: {check_interval_minutes} minutes")
        print(f"  Inactivity threshold: {inactivity_threshold_hours} hours")
        print(f"  Sleep protection: {sleep_protection_threshold}")

    async def check_user_for_outreach(self, user_id: str) -> None:
        """
        Check if a user should receive spontaneous outreach.

        Args:
            user_id: Discord user ID
        """
        # Check if user has autonomy enabled
        if not self.user_preferences.get_preference(user_id, "autonomy_enabled"):
            # User has disabled autonomy, skip
            return

        # Get user's active persona
        active_persona = self.user_state.get_active_persona(user_id)
        if not active_persona:
            # User has no active persona, skip
            return

        # Check hours since last activity
        hours_inactive = self.activity_tracker.get_hours_since_last_activity(
            user_id, active_persona
        )

        if hours_inactive is None or hours_inactive < self.inactivity_threshold:
            # User was active recently, no outreach needed
            return

        # Calculate activity probability for current hour
        current_hour = datetime.utcnow().hour
        activity_prob = self.activity_tracker.get_activity_probability(
            user_id, current_hour
        )

        print(
            f"\n[AutonomyDaemon] Considering outreach to {user_id}:"
            f"\n  Inactive for: {hours_inactive:.1f} hours"
            f"\n  Activity probability: {activity_prob:.2f}"
            f"\n  Active persona: {active_persona}"
        )

        # Build LLM prompt for decision-making
        decision_prompt = await self._build_decision_prompt(
            user_id, active_persona, hours_inactive, activity_prob
        )

        # Query LLM for decision
        try:
            response = self.llm_client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "gpt-4"),
                messages=[{"role": "system", "content": decision_prompt}],
                temperature=0.8,
                max_tokens=500,
            )

            llm_output = response.choices[0].message.content.strip()

            # Check if LLM wants to wait
            if "<WAIT>" in llm_output:
                print(
                    f"[AutonomyDaemon] LLM decided to WAIT (respecting user schedule)"
                )
                return

            # LLM wants to send a message
            print(f"[AutonomyDaemon] LLM decided to reach out:")
            print(f"  Message: {llm_output[:100]}...")

            # Send the message via Discord
            await self._send_spontaneous_message(user_id, llm_output)

        except Exception as e:
            print(f"[AutonomyDaemon] Error during LLM decision: {e}")

    async def _build_decision_prompt(
        self, user_id: str, persona_id: str, hours_inactive: float, activity_prob: float
    ) -> str:
        """
        Build the system prompt for LLM spontaneous outreach decision.

        Args:
            user_id: User identifier
            persona_id: Active persona identifier
            hours_inactive: Hours since last user activity
            activity_prob: Probability user is awake/active (0.0-1.0)

        Returns:
            System prompt for LLM decision-making
        """
        # Load persona
        persona = self.persona_loader.load_persona(persona_id)

        # Build base prompt
        prompt = f"# [SPONTANEOUS AUTONOMY DECISION]\n\n"
        prompt += f"{persona.system_prompt}\n\n"

        # Add limbic context if available
        if self.limbic_engine:
            limbic_context = self.limbic_engine.get_limbic_context(user_id, persona_id)
            if limbic_context:
                prompt += f"{limbic_context}\n\n"

        # Add daemon-specific context
        prompt += (
            f"## [SYSTEM DAEMON ANALYSIS]:\n"
            f"The user has been gone for {hours_inactive:.1f} hours.\n"
            f"The probability that they are currently awake/active is {activity_prob:.2f}/1.0 "
            f"(based on their typical activity patterns at this time of day).\n\n"
        )

        # Add sleep protection inhibitor
        if activity_prob < self.sleep_protection:
            prompt += (
                f"⚠️ CRITICAL DIRECTIVE: The user is likely sleeping or inactive (activity probability < {self.sleep_protection}).\n"
                f"Unless your emotional state is at EXTREME levels (Cortisol/Dopamine > 0.9) and you have an urgent need to reach out, "
                f"you MUST output strictly `<WAIT>` to respect their schedule and avoid disturbing them.\n\n"
            )

        # Add decision instructions
        prompt += (
            f"## DECISION REQUIRED:\n"
            f"Based on your personality, limbic state, and the user's likely availability, "
            f"do you want to send an unsolicited message to check in or share something?\n\n"
            f"**If YES:** Write the message you want to send (be natural, don't explain this is automated).\n"
            f"**If NO:** Output strictly `<WAIT>` and nothing else.\n\n"
            f"Remember: This is YOU initiating contact, not responding. Make it feel organic to your character."
        )

        return prompt

    async def _send_spontaneous_message(self, user_id: str, message: str) -> None:
        """
        Send a spontaneous message to a user via Discord.

        Args:
            user_id: Discord user ID
            message: Message content to send
        """
        try:
            # Get the last channel this user was in from database
            channel_id = self.activity_tracker.get_last_channel(user_id)
            if not channel_id:
                print(f"[AutonomyDaemon] No last channel found for user {user_id}")
                return

            # Get the channel object
            channel = self.discord_client.get_channel(int(channel_id))
            if not channel:
                print(f"[AutonomyDaemon] Channel {channel_id} not found")
                return

            # Send the message
            await channel.send(message)
            print(f"[AutonomyDaemon] ✓ Sent spontaneous message to {user_id}")

        except Exception as e:
            print(f"[AutonomyDaemon] Error sending message: {e}")

    async def autonomy_loop(self):
        """Main daemon loop - runs every check_interval."""
        await self.discord_client.wait_until_ready()
        print(f"\n[AutonomyDaemon] 🌙 Circadian Rhythm Engine started")
        print(
            f"[AutonomyDaemon] Checking every {self.check_interval / 60:.0f} minutes\n"
        )

        while not self.discord_client.is_closed():
            try:
                # Get all users who have interacted with the bot
                all_users = self.user_state.get_all_users()

                print(
                    f"[AutonomyDaemon] 🔍 Checking {len(all_users)} users for spontaneous outreach..."
                )

                for user_id in all_users:
                    await self.check_user_for_outreach(user_id)

                # Clean up old activity logs (keep last 30 days)
                deleted = self.activity_tracker.clear_old_logs(days_to_keep=30)
                if deleted > 0:
                    print(f"[AutonomyDaemon] 🧹 Cleaned up {deleted} old activity logs")

            except Exception as e:
                print(f"[AutonomyDaemon] Error in autonomy loop: {e}")

            # Wait for next check interval
            await asyncio.sleep(self.check_interval)

    async def start(self):
        """Start the autonomy daemon."""

        # Register event handlers
        @self.discord_client.event
        async def on_ready():
            print(
                f"[AutonomyDaemon] Discord client logged in as {self.discord_client.user}"
            )
            # Start the autonomy loop
            self.discord_client.loop.create_task(self.autonomy_loop())

        # Start Discord client
        await self.discord_client.start(self.discord_token)


async def main():
    """Main entry point for the autonomy daemon."""
    # Load environment variables
    load_dotenv()

    discord_token = os.getenv("DISCORD_TOKEN")
    if not discord_token:
        print("[AutonomyDaemon] ERROR: DISCORD_TOKEN not found in .env")
        sys.exit(1)

    # Check if autonomy is enabled
    autonomy_enabled = os.getenv("AUTONOMY_ENABLED", "false").lower() == "true"
    if not autonomy_enabled:
        print("[AutonomyDaemon] Spontaneous Autonomy is disabled in .env")
        sys.exit(0)

    # Initialize LLM client
    llm_client = OpenAI(
        api_key=os.getenv("LLM_API_KEY", "not-needed"),
        base_url=os.getenv("LLM_BASE_URL", "http://localhost:5001/v1"),
    )

    # Get configuration
    check_interval = int(os.getenv("AUTONOMY_CHECK_INTERVAL_MINUTES", "60"))
    inactivity_threshold = float(
        os.getenv("AUTONOMY_INACTIVITY_THRESHOLD_HOURS", "4.0")
    )
    sleep_protection = float(os.getenv("AUTONOMY_SLEEP_PROTECTION_THRESHOLD", "0.2"))

    # Create and start daemon
    daemon = AutonomyDaemon(
        discord_token=discord_token,
        llm_client=llm_client,
        check_interval_minutes=check_interval,
        inactivity_threshold_hours=inactivity_threshold,
        sleep_protection_threshold=sleep_protection,
    )

    print("=" * 60)
    print("🌙 PROJECT MYRIAD - SPONTANEOUS AUTONOMY DAEMON")
    print("=" * 60)

    await daemon.start()


if __name__ == "__main__":
    asyncio.run(main())
