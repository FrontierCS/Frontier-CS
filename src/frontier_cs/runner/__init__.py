"""
Runner module for executing evaluations.

Provides different backends for running evaluations:
- DockerRunner: Local Docker evaluation
- SkyPilotRunner: Cloud evaluation via SkyPilot
- AlgorithmicRunner: Judge server for algorithmic problems
"""

from .base import Runner, EvaluationResult
from .docker import DockerRunner
from .algorithmic import AlgorithmicRunner

__all__ = [
    "Runner",
    "EvaluationResult",
    "DockerRunner",
    "AlgorithmicRunner",
]

# SkyPilotRunner is optional (requires skypilot)
try:
    from .skypilot import SkyPilotRunner
    from .algorithmic_skypilot import AlgorithmicSkyPilotRunner
    __all__.append("SkyPilotRunner")
    __all__.append("AlgorithmicSkyPilotRunner")
except ImportError:
    pass
