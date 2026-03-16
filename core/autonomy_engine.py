"""
Autonomy Engine - Platform-agnostic spontaneous outreach logic.

This module handles the decision-making for AI-initiated conversations:
- Circadian rhythm analysis (activity probability)
- Time since last interaction
- Limbic state and persona personality
- Sleep protection (inhibitor for low-probability hours)

This is the core logic; platform adapters (Discord, etc.) handle the actual
message delivery via callbacks.

Part of Project Myriad's Spontaneous Autonomy system.
"""

import os
from datetime import datetime
from typing import Optional, Callable, Awaitable, Tuple
from openai import OpenAI

from database.activity_tracker import ActivityTracker
from database.user_state import UserStateManager
from core.features.roleplay.limbic_engine import LimbicEngine
from database.user_preferences import UserPreferences
from core.features.roleplay.persona import PersonaLoader


class AutonomyEngine:
    """
    Platform-agnostic engine for spontaneous AI-initiated interactions.

    This engine evaluates whether to reach out to users based on:
    - Their activity patterns (circadian rhythm)
    - Time since last interaction
    - The persona's emotional state (limbic system)
    - User preferences for autonomy behavior

    The actual message delivery is handled by a callback provided by the
    platform adapter (e.g., Discord).
    """

    def __init__(
        self,
        llm_client: OpenAI,
        activity_tracker: ActivityTracker,
        user_state: UserStateManager,
        persona_loader: PersonaLoader,
        user_preferences: UserPreferences,
        limbic_engine: Optional[LimbicEngine] = None,
    ):
        """
        Initialize the Autonomy Engine.

        Args:
            llm_client: OpenAI API client for LLM calls
            activity_tracker: Shared activity tracker instance
            user_state: Shared user state manager
            persona_loader: Shared persona loader
            user_preferences: Shared user preferences manager
            limbic_engine: Optional shared limbic engine (for emotional context)
        """
        self.llm_client = llm_client
        self.activity_tracker = activity_tracker
        self.user_state = user_state
        self.persona_loader = persona_loader
        self.user_preferences = user_preferences
        self.limbic_engine = limbic_engine

        print("[AutonomyEngine] Initialized (integrated mode)")

    async def check_user_for_outreach(
        self,
        user_id: str,
        send_callback: Callable[[str, str], Awaitable[bool]],
    ) -> bool:
        """
        Check if a user should receive spontaneous outreach.

        Args:
            user_id: User identifier
            send_callback: Async callback function(user_id, message) -> success
                          Called if the LLM decides to send a message.

        Returns:
            True if a message was sent, False otherwise
        """
        # Check if user has autonomy enabled
        if not self.user_preferences.get_preference(user_id, "autonomy_enabled"):
            return False

        # Get user's active persona
        active_persona = self.user_state.get_active_persona(user_id)
        if not active_persona:
            return False

        # Get user-specific autonomy preferences
        user_inactivity_threshold = float(
            self.user_preferences.get_preference(user_id, "autonomy_inactivity_hours")
        )
        user_sleep_protection = float(
            self.user_preferences.get_preference(user_id, "autonomy_sleep_threshold")
        )

        # Check hours since last activity
        hours_inactive = self.activity_tracker.get_hours_since_last_activity(
            user_id, active_persona
        )

        if hours_inactive is None or hours_inactive < user_inactivity_threshold:
            # User was active recently, no outreach needed
            return False

        # Calculate activity probability for current hour
        current_hour = datetime.utcnow().hour
        activity_prob = self.activity_tracker.get_activity_probability(
            user_id, current_hour
        )

        # Apply user-specific sleep protection threshold
        if activity_prob < user_sleep_protection:
            # User is likely asleep, skip
            return False

        print(
            f"\n[AutonomyEngine] Considering outreach to {user_id}:"
            f"\n  Inactive for: {hours_inactive:.1f} hours (threshold: {user_inactivity_threshold})"
            f"\n  Activity probability: {activity_prob:.2f} (sleep threshold: {user_sleep_protection})"
            f"\n  Active persona: {active_persona}"
        )

        # Build LLM prompt for decision-making
        decision_prompt = self._build_decision_prompt(
            user_id,
            active_persona,
            hours_inactive,
            activity_prob,
            user_sleep_protection,
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
                print("[AutonomyEngine] LLM decided to WAIT (respecting user schedule)")
                return False

            # LLM wants to send a message
            print(f"[AutonomyEngine] LLM decided to reach out:")
            print(f"  Message: {llm_output[:100]}...")

            # Send the message via callback
            success = await send_callback(user_id, llm_output)
            if success:
                print(f"[AutonomyEngine] ✓ Sent spontaneous message to {user_id}")
            return success

        except Exception as e:
            print(f"[AutonomyEngine] Error during LLM decision: {e}")
            return False

    def _build_decision_prompt(
        self,
        user_id: str,
        persona_id: str,
        hours_inactive: float,
        activity_prob: float,
        sleep_threshold: float,
    ) -> str:
        """
        Build the system prompt for LLM spontaneous outreach decision.

        Args:
            user_id: User identifier
            persona_id: Active persona identifier
            hours_inactive: Hours since last user activity
            activity_prob: Probability user is awake/active (0.0-1.0)
            sleep_threshold: User's sleep protection threshold

        Returns:
            System prompt for LLM decision-making
        """
        # Load persona
        persona = self.persona_loader.load_persona(persona_id)
        if not persona:
            return "<WAIT>"

        # Build base prompt
        prompt = f"# [SPONTANEOUS AUTONOMY DECISION]\n\n"
        prompt += f"{persona.system_prompt}\n\n"

        # Add limbic context if available
        if self.limbic_engine:
            limbic_context = self.limbic_engine.get_limbic_context(
                user_id, persona_id, persona_baseline=persona.limbic_baseline
            )
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
        if activity_prob < sleep_threshold:
            prompt += (
                f"⚠️ CRITICAL DIRECTIVE: The user is likely sleeping or inactive "
                f"(activity probability < {sleep_threshold}).\n"
                f"Unless your emotional state is at EXTREME levels (Cortisol/Dopamine > 0.9) "
                f"and you have an urgent need to reach out, "
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

    def get_all_active_users(self) -> list:
        """
        Get all users who have interacted with the bot.

        Returns:
            List of user IDs
        """
        return self.user_state.get_all_users()

    def cleanup_old_activity_logs(self, days_to_keep: int = 30) -> int:
        """
        Clean up old activity logs.

        Args:
            days_to_keep: Number of days of logs to retain

        Returns:
            Number of deleted records
        """
        return self.activity_tracker.clear_old_logs(days_to_keep=days_to_keep)
