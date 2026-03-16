"""
Scenario management module for Project Myriad.

This module manages hierarchical environmental contexts stored as folder-based scenarios,
allowing the AI to understand nested locations and world states.
"""

from .scenario_models import Scenario
from .scenario_manager import ScenarioEngine

__all__ = ["Scenario", "ScenarioEngine"]
