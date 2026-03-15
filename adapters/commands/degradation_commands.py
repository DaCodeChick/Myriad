"""
Degradation Commands - User configuration for text degradation effects.

These commands allow users to customize how their AI's text degrades under
extreme limbic states (panic, arousal, sedation).
"""

import discord
import json
import os
from typing import Optional

from adapters.commands.response_formatter import ResponseFormatter


def register_degradation_commands(
    bot: "MyriadDiscordBot", tree: discord.app_commands.CommandTree
):
    """
    Register degradation configuration commands.

    Args:
        bot: Discord bot instance
        tree: Command tree for slash commands
    """
    degradation_group = discord.app_commands.Group(
        name="degradation",
        description="Configure text degradation effects (stuttering, vowel stretching, etc.)",
    )

    @degradation_group.command(
        name="preset",
        description="Apply a degradation preset (subtle, moderate, intense)",
    )
    @discord.app_commands.describe(
        preset="Preset to apply",
        persona="Optional: Apply to specific persona only (leave empty for global)",
    )
    @discord.app_commands.choices(
        preset=[
            discord.app_commands.Choice(name="Subtle (Default)", value="subtle"),
            discord.app_commands.Choice(name="Moderate", value="moderate"),
            discord.app_commands.Choice(name="Intense", value="intense"),
        ]
    )
    async def degradation_preset(
        interaction: discord.Interaction,
        preset: str,
        persona: Optional[str] = None,
    ):
        """Apply a degradation preset."""
        user_id = str(interaction.user.id)
        user_prefs = bot.agent_core.user_preferences

        try:
            # Load the system preset
            profile = user_prefs.get_degradation_profile("__system__", None, preset)

            # Save as user's profile
            user_prefs.save_degradation_profile(
                user_id, preset, profile, persona_id=persona
            )

            scope = f"persona '{persona}'" if persona else "all personas"
            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"✅ Applied **{preset}** preset to {scope}\n\n"
                    f"**Settings:**\n"
                    f"• Vowel stretch: {profile['vowel_stretch_base_chance'] * 100:.1f}% base → "
                    f"{(profile['vowel_stretch_base_chance'] + profile['vowel_stretch_scale_factor']) * 100:.1f}% max\n"
                    f"• Panic stutter: {profile['panic_stutter_base_chance'] * 100:.1f}% base → "
                    f"{(profile['panic_stutter_base_chance'] + profile['panic_stutter_scale_factor']) * 100:.1f}% max\n"
                    f"• Panic caps: {profile['panic_caps_base_chance'] * 100:.1f}% base → "
                    f"{(profile['panic_caps_base_chance'] + profile['panic_caps_scale_factor']) * 100:.1f}% max\n\n"
                    f"Use `/degradation set` to customize individual parameters."
                ),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to apply preset: {str(e)}"),
                ephemeral=True,
            )

    @degradation_group.command(
        name="set",
        description="Set a specific degradation parameter",
    )
    @discord.app_commands.describe(
        parameter="Parameter to modify",
        value="New value (0.0-1.0 for probabilities, integers for others)",
        persona="Optional: Apply to specific persona only",
    )
    @discord.app_commands.choices(
        parameter=[
            discord.app_commands.Choice(
                name="Vowel Stretch Base Chance", value="vowel_stretch_base_chance"
            ),
            discord.app_commands.Choice(
                name="Vowel Stretch Scale Factor", value="vowel_stretch_scale_factor"
            ),
            discord.app_commands.Choice(
                name="Vowel Stretch Min Word Length",
                value="vowel_stretch_min_word_length",
            ),
            discord.app_commands.Choice(
                name="Vowel Stretch Max Repeats", value="vowel_stretch_max_repeats"
            ),
            discord.app_commands.Choice(
                name="Panic Stutter Base Chance", value="panic_stutter_base_chance"
            ),
            discord.app_commands.Choice(
                name="Panic Stutter Scale Factor", value="panic_stutter_scale_factor"
            ),
            discord.app_commands.Choice(
                name="Panic Caps Base Chance", value="panic_caps_base_chance"
            ),
            discord.app_commands.Choice(
                name="Panic Caps Scale Factor", value="panic_caps_scale_factor"
            ),
            discord.app_commands.Choice(
                name="Panic Min Word Length", value="panic_min_word_length"
            ),
            discord.app_commands.Choice(
                name="Sedation Ellipsis Chance", value="sedation_ellipsis_chance"
            ),
        ]
    )
    async def degradation_set(
        interaction: discord.Interaction,
        parameter: str,
        value: float,
        persona: Optional[str] = None,
    ):
        """Set a specific degradation parameter."""
        user_id = str(interaction.user.id)
        user_prefs = bot.agent_core.user_preferences

        try:
            # Validate value ranges
            is_probability = parameter.endswith("_chance") or parameter.endswith(
                "_factor"
            )
            is_int_param = "length" in parameter or "repeats" in parameter

            if is_probability and not (0.0 <= value <= 1.0):
                await interaction.response.send_message(
                    ResponseFormatter.warning(
                        f"⚠️ Probability values must be between 0.0 and 1.0\n"
                        f"You provided: {value}"
                    ),
                    ephemeral=True,
                )
                return

            if is_int_param and (value < 0 or value != int(value)):
                await interaction.response.send_message(
                    ResponseFormatter.warning(
                        f"⚠️ This parameter requires a positive integer\n"
                        f"You provided: {value}"
                    ),
                    ephemeral=True,
                )
                return

            # Warn about extreme values
            warnings = []
            if parameter.endswith("_chance") or parameter.endswith("_factor"):
                if value > 0.5:
                    warnings.append(
                        f"⚠️ **High probability warning:** {value * 100:.1f}% is very aggressive"
                    )
                if value < 0.001 and value > 0:
                    warnings.append(
                        f"⚠️ **Low probability warning:** {value * 100:.3f}% may be barely noticeable"
                    )

            if parameter == "vowel_stretch_max_repeats" and value > 5:
                warnings.append(
                    f"⚠️ **High repeat warning:** {int(value)} repeats will create very long words"
                )

            # Load current profile (or create custom one)
            current_profile = user_prefs.get_degradation_profile(
                user_id, persona, "custom"
            )

            # Update the parameter
            if is_int_param:
                current_profile[parameter] = int(value)
            else:
                current_profile[parameter] = float(value)

            # Save as 'custom' profile
            user_prefs.save_degradation_profile(
                user_id, "custom", current_profile, persona_id=persona
            )

            scope = f"persona '{persona}'" if persona else "global"
            warning_text = "\n\n" + "\n".join(warnings) if warnings else ""

            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"✅ Updated **{parameter}** to `{value}` ({scope})\n\n"
                    f"Profile automatically switched to **custom**.{warning_text}"
                ),
                ephemeral=True,
            )

        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to set parameter: {str(e)}"),
                ephemeral=True,
            )

    @degradation_group.command(
        name="toggle",
        description="Enable or disable a degradation effect category",
    )
    @discord.app_commands.describe(
        effect="Effect category to toggle",
        persona="Optional: Apply to specific persona only",
    )
    @discord.app_commands.choices(
        effect=[
            discord.app_commands.Choice(name="Vowel Stretching", value="vowel_stretch"),
            discord.app_commands.Choice(name="Panic Effects", value="panic_effects"),
            discord.app_commands.Choice(
                name="Sedation Effects", value="sedation_effects"
            ),
        ]
    )
    async def degradation_toggle(
        interaction: discord.Interaction,
        effect: str,
        persona: Optional[str] = None,
    ):
        """Toggle a degradation effect category."""
        user_id = str(interaction.user.id)
        user_prefs = bot.agent_core.user_preferences

        try:
            # Load current profile
            current_profile = user_prefs.get_degradation_profile(
                user_id, persona, "custom"
            )

            # Toggle the effect
            enabled_key = f"{effect}_enabled"
            current_state = current_profile.get(enabled_key, True)
            new_state = not current_state
            current_profile[enabled_key] = new_state

            # Save profile
            user_prefs.save_degradation_profile(
                user_id, "custom", current_profile, persona_id=persona
            )

            scope = f"persona '{persona}'" if persona else "global"
            status = "**ENABLED** ✅" if new_state else "**DISABLED** ❌"

            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"{status} {effect.replace('_', ' ').title()} ({scope})"
                ),
                ephemeral=True,
            )

        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to toggle effect: {str(e)}"),
                ephemeral=True,
            )

    @degradation_group.command(
        name="preview",
        description="Preview current degradation settings with sample text",
    )
    @discord.app_commands.describe(
        text="Custom text to test (optional, defaults to sample)",
        dopamine="Simulated dopamine level (0.0-1.5, default 1.2 = high arousal)",
        cortisol="Simulated cortisol level (0.0-1.5, default 1.0 = panic)",
        gaba="Simulated GABA level (0.0-1.5, default 0.5 = normal)",
        persona="Optional: Use persona-specific profile",
    )
    async def degradation_preview(
        interaction: discord.Interaction,
        text: Optional[str] = None,
        dopamine: Optional[float] = 1.2,
        cortisol: Optional[float] = 1.0,
        gaba: Optional[float] = 0.5,
        persona: Optional[str] = None,
    ):
        """Preview degradation effects with sample text."""
        user_id = str(interaction.user.id)
        user_prefs = bot.agent_core.user_preferences

        try:
            # Use provided text or default sample
            sample_text = text or "I really love programming! This is amazing work."

            # Load current profile
            profile = user_prefs.get_degradation_profile(user_id, persona, "custom")

            # Create simulated limbic state
            limbic_state = {
                "DOPAMINE": dopamine,
                "CORTISOL": cortisol,
                "GABA": gaba,
                "OXYTOCIN": 0.5,
            }

            # Apply degradation
            degrader = bot.agent_core.cadence_degrader
            degraded_text = degrader.degrade(sample_text, limbic_state, profile)

            scope = f" (persona: {persona})" if persona else " (global)"

            await interaction.response.send_message(
                ResponseFormatter.info(
                    f"**Degradation Preview**{scope}\n\n"
                    f"**Limbic State:**\n"
                    f"• DOPAMINE: {dopamine:.2f} (arousal/desperation)\n"
                    f"• CORTISOL: {cortisol:.2f} (panic/terror)\n"
                    f"• GABA: {gaba:.2f} (sedation/drowsiness)\n\n"
                    f"**Original:**\n{sample_text}\n\n"
                    f"**Degraded:**\n{degraded_text}\n\n"
                    f"*Note: Results vary due to randomness. Run multiple times to see variation.*"
                ),
                ephemeral=True,
            )

        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to preview: {str(e)}"),
                ephemeral=True,
            )

    @degradation_group.command(
        name="save",
        description="Save current degradation settings as a named profile",
    )
    @discord.app_commands.describe(
        name="Name for the profile",
        persona="Optional: Save persona-specific profile",
    )
    async def degradation_save(
        interaction: discord.Interaction,
        name: str,
        persona: Optional[str] = None,
    ):
        """Save current settings as a named profile."""
        user_id = str(interaction.user.id)
        user_prefs = bot.agent_core.user_preferences

        try:
            # Prevent overwriting system presets
            if name in ["subtle", "moderate", "intense"]:
                await interaction.response.send_message(
                    ResponseFormatter.warning(
                        f"⚠️ Cannot overwrite system preset '{name}'\n"
                        f"Choose a different name for your custom profile."
                    ),
                    ephemeral=True,
                )
                return

            # Load current custom profile
            current_profile = user_prefs.get_degradation_profile(
                user_id, persona, "custom"
            )

            # Save with new name
            user_prefs.save_degradation_profile(
                user_id, name, current_profile, persona_id=persona
            )

            scope = f"persona '{persona}'" if persona else "global"
            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"✅ Saved degradation profile as **'{name}'** ({scope})\n\n"
                    f"Use `/degradation load {name}` to restore these settings later."
                ),
                ephemeral=True,
            )

        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to save profile: {str(e)}"),
                ephemeral=True,
            )

    @degradation_group.command(
        name="load",
        description="Load a saved degradation profile",
    )
    @discord.app_commands.describe(
        name="Name of the profile to load",
        persona="Optional: Load persona-specific profile",
    )
    async def degradation_load(
        interaction: discord.Interaction,
        name: str,
        persona: Optional[str] = None,
    ):
        """Load a saved profile."""
        user_id = str(interaction.user.id)
        user_prefs = bot.agent_core.user_preferences

        try:
            # Try to load the profile
            profile = user_prefs.get_degradation_profile(user_id, persona, name)

            # Save as current custom profile
            user_prefs.save_degradation_profile(
                user_id, "custom", profile, persona_id=persona
            )

            scope = f"persona '{persona}'" if persona else "global"
            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"✅ Loaded profile **'{name}'** ({scope})\n\n"
                    f"Active profile is now **custom** with '{name}' settings."
                ),
                ephemeral=True,
            )

        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(
                    f"Failed to load profile '{name}': {str(e)}\n\n"
                    f"Use `/degradation list` to see available profiles."
                ),
                ephemeral=True,
            )

    @degradation_group.command(
        name="list",
        description="List all your saved degradation profiles",
    )
    @discord.app_commands.describe(
        persona="Optional: List persona-specific profiles only",
    )
    async def degradation_list(
        interaction: discord.Interaction,
        persona: Optional[str] = None,
    ):
        """List saved profiles."""
        user_id = str(interaction.user.id)
        user_prefs = bot.agent_core.user_preferences

        try:
            profiles = user_prefs.list_degradation_profiles(user_id, persona)

            if not profiles:
                scope = f"persona '{persona}'" if persona else "globally"
                await interaction.response.send_message(
                    ResponseFormatter.info(
                        f"No saved profiles found {scope}.\n\n"
                        f"System presets available: subtle, moderate, intense"
                    ),
                    ephemeral=True,
                )
                return

            scope = f" (persona: {persona})" if persona else " (global)"
            profile_list = "\n".join([f"• {p}" for p in profiles])

            await interaction.response.send_message(
                ResponseFormatter.info(
                    f"**Saved Degradation Profiles**{scope}\n\n"
                    f"{profile_list}\n\n"
                    f"**System Presets:**\n"
                    f"• subtle (default)\n"
                    f"• moderate\n"
                    f"• intense"
                ),
                ephemeral=True,
            )

        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to list profiles: {str(e)}"),
                ephemeral=True,
            )

    @degradation_group.command(
        name="delete",
        description="Delete a saved degradation profile",
    )
    @discord.app_commands.describe(
        name="Name of the profile to delete",
        persona="Optional: Delete persona-specific profile",
    )
    async def degradation_delete(
        interaction: discord.Interaction,
        name: str,
        persona: Optional[str] = None,
    ):
        """Delete a saved profile."""
        user_id = str(interaction.user.id)
        user_prefs = bot.agent_core.user_preferences

        try:
            # Prevent deleting system presets
            if name in ["subtle", "moderate", "intense"]:
                await interaction.response.send_message(
                    ResponseFormatter.warning(
                        f"⚠️ Cannot delete system preset '{name}'"
                    ),
                    ephemeral=True,
                )
                return

            # Attempt deletion
            deleted = user_prefs.delete_degradation_profile(user_id, name, persona)

            if deleted:
                scope = f"persona '{persona}'" if persona else "global"
                await interaction.response.send_message(
                    ResponseFormatter.success(
                        f"✅ Deleted profile **'{name}'** ({scope})"
                    ),
                    ephemeral=True,
                )
            else:
                scope = f"persona '{persona}'" if persona else "globally"
                await interaction.response.send_message(
                    ResponseFormatter.warning(
                        f"⚠️ Profile '{name}' not found {scope}\n\n"
                        f"Use `/degradation list` to see available profiles."
                    ),
                    ephemeral=True,
                )

        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to delete profile: {str(e)}"),
                ephemeral=True,
            )

    @degradation_group.command(
        name="export",
        description="Export a degradation profile to JSON file for sharing",
    )
    @discord.app_commands.describe(
        name="Name of the profile to export",
        persona="Optional: Export persona-specific profile",
    )
    async def degradation_export(
        interaction: discord.Interaction,
        name: str,
        persona: Optional[str] = None,
    ):
        """Export a profile to JSON."""
        user_id = str(interaction.user.id)
        user_prefs = bot.agent_core.user_preferences

        try:
            # Export profile
            profile_data = user_prefs.export_degradation_profile(user_id, name, persona)

            # Create JSON file
            json_str = json.dumps(profile_data, indent=2)
            filename = f"degradation_profile_{name}.json"

            # Send as file attachment
            file = discord.File(
                fp=discord.utils._StringIO(json_str),
                filename=filename,
            )

            scope = f"persona '{persona}'" if persona else "global"
            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"✅ Exported profile **'{name}'** ({scope})\n\n"
                    f"Share this file with others to let them use your settings!"
                ),
                file=file,
                ephemeral=True,
            )

        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to export profile: {str(e)}"),
                ephemeral=True,
            )

    @degradation_group.command(
        name="import",
        description="Import a degradation profile from JSON file",
    )
    @discord.app_commands.describe(
        file="JSON file containing profile data",
        name="Optional: Custom name for imported profile (default: uses name from file)",
        persona="Optional: Import as persona-specific profile",
    )
    async def degradation_import(
        interaction: discord.Interaction,
        file: discord.Attachment,
        name: Optional[str] = None,
        persona: Optional[str] = None,
    ):
        """Import a profile from JSON."""
        user_id = str(interaction.user.id)
        user_prefs = bot.agent_core.user_preferences

        try:
            # Download and parse JSON
            json_bytes = await file.read()
            json_str = json_bytes.decode("utf-8")
            profile_data = json.loads(json_str)

            # Import profile
            imported_name = user_prefs.import_degradation_profile(
                user_id, profile_data, overwrite_name=name
            )

            scope = f"persona '{persona}'" if persona else "global"
            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"✅ Imported profile as **'{imported_name}'** ({scope})\n\n"
                    f"Use `/degradation load {imported_name}` to activate it."
                ),
                ephemeral=True,
            )

        except json.JSONDecodeError:
            await interaction.response.send_message(
                ResponseFormatter.error("Invalid JSON file format"),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to import profile: {str(e)}"),
                ephemeral=True,
            )

    @degradation_group.command(
        name="show",
        description="Show current degradation settings",
    )
    @discord.app_commands.describe(
        persona="Optional: Show persona-specific settings",
    )
    async def degradation_show(
        interaction: discord.Interaction,
        persona: Optional[str] = None,
    ):
        """Show current degradation settings."""
        user_id = str(interaction.user.id)
        user_prefs = bot.agent_core.user_preferences

        try:
            # Load current profile
            profile = user_prefs.get_degradation_profile(user_id, persona, "custom")

            scope = f" (persona: {persona})" if persona else " (global)"

            # Format enabled/disabled status
            def status(enabled):
                return "✅ Enabled" if enabled else "❌ Disabled"

            await interaction.response.send_message(
                ResponseFormatter.info(
                    f"**Current Degradation Settings**{scope}\n\n"
                    f"**Effect Toggles:**\n"
                    f"• Vowel Stretching: {status(profile['vowel_stretch_enabled'])}\n"
                    f"• Panic Effects: {status(profile['panic_effects_enabled'])}\n"
                    f"• Sedation Effects: {status(profile['sedation_effects_enabled'])}\n\n"
                    f"**Vowel Stretching (High Dopamine):**\n"
                    f"• Base chance: {profile['vowel_stretch_base_chance'] * 100:.1f}%\n"
                    f"• Scale factor: {profile['vowel_stretch_scale_factor'] * 100:.1f}%\n"
                    f"• Max at intensity 1.0: {(profile['vowel_stretch_base_chance'] + profile['vowel_stretch_scale_factor']) * 100:.1f}%\n"
                    f"• Min word length: {profile['vowel_stretch_min_word_length']}\n"
                    f"• Max repeats: {profile['vowel_stretch_max_repeats']}\n\n"
                    f"**Panic Effects (High Cortisol):**\n"
                    f"• Stutter base: {profile['panic_stutter_base_chance'] * 100:.1f}%\n"
                    f"• Stutter scale: {profile['panic_stutter_scale_factor'] * 100:.1f}%\n"
                    f"• Caps base: {profile['panic_caps_base_chance'] * 100:.1f}%\n"
                    f"• Caps scale: {profile['panic_caps_scale_factor'] * 100:.1f}%\n"
                    f"• Min word length: {profile['panic_min_word_length']}\n\n"
                    f"**Sedation Effects (High GABA):**\n"
                    f"• Ellipsis chance: {profile['sedation_ellipsis_chance'] * 100:.1f}%"
                ),
                ephemeral=True,
            )

        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to show settings: {str(e)}"),
                ephemeral=True,
            )

    @degradation_group.command(
        name="reset",
        description="Reset degradation settings to default (subtle preset)",
    )
    @discord.app_commands.describe(
        persona="Optional: Reset persona-specific settings only",
    )
    async def degradation_reset(
        interaction: discord.Interaction,
        persona: Optional[str] = None,
    ):
        """Reset to default settings."""
        user_id = str(interaction.user.id)
        user_prefs = bot.agent_core.user_preferences

        try:
            # Delete user's custom profile (falls back to system subtle)
            if persona:
                user_prefs.delete_degradation_profile(user_id, "custom", persona)
            else:
                user_prefs.delete_degradation_profile(user_id, "custom", None)

            scope = f"persona '{persona}'" if persona else "global"
            await interaction.response.send_message(
                ResponseFormatter.success(
                    f"✅ Reset degradation settings to **subtle** defaults ({scope})"
                ),
                ephemeral=True,
            )

        except Exception as e:
            await interaction.response.send_message(
                ResponseFormatter.error(f"Failed to reset settings: {str(e)}"),
                ephemeral=True,
            )

    # Add group to tree
    tree.add_command(degradation_group)
