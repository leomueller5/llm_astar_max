"""Offline-first strategic guidance research. No provider performs network calls."""
from .schema import StrategicGuidance,Strategy,Bypass,parse_guidance
from .providers import StaticProvider,ScriptedProvider,GuidanceContext
