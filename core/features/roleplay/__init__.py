"""Roleplay feature package - all roleplay-centric components."""

from core.features.roleplay.roleplay_feature import RoleplayFeature
from core.features.roleplay.persona import PersonaLoader, PersonaCartridge
from core.features.roleplay.persona_manager import PersonaManager
from core.features.roleplay.limbic_engine import LimbicEngine
from core.features.roleplay.limbic_modifiers import DigitalPharmacy
from core.features.roleplay.cadence_degrader import CadenceDegrader
from core.features.roleplay.metacognition_engine import MetacognitionEngine
from core.features.roleplay.lives_engine import LivesEngine
from core.features.roleplay.save_states_engine import SaveStatesEngine
from core.features.roleplay.user_masks import UserMaskManager
from core.features.roleplay.scenario import ScenarioEngine
from core.features.roleplay.session_notes import SessionNotesManager

__all__ = [
    "RoleplayFeature",
    "PersonaLoader",
    "PersonaCartridge",
    "PersonaManager",
    "LimbicEngine",
    "DigitalPharmacy",
    "CadenceDegrader",
    "MetacognitionEngine",
    "LivesEngine",
    "SaveStatesEngine",
    "UserMaskManager",
    "ScenarioEngine",
    "SessionNotesManager",
]
