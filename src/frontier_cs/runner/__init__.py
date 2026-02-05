"""
Runner module for executing evaluations.

Provides different backends for running evaluations:
- ResearchDockerRunner: Local Docker evaluation for research
- ResearchSkyPilotRunner: Cloud evaluation via SkyPilot for research
- AlgorithmicLocalRunner: Judge server for algorithmic problems
"""

from .base import Runner, ResearchRunner, EvaluationResult
from .research_docker import ResearchDockerRunner
from .algorithmic_local import AlgorithmicLocalRunner

__all__ = [
    "Runner",
    "ResearchRunner",
    "EvaluationResult",
    "ResearchDockerRunner",
    "AlgorithmicLocalRunner",
]

# ResearchSkyPilotRunner is optional (requires skypilot)
try:
    from .research_skypilot import ResearchSkyPilotRunner
    from .algorithmic_skypilot import AlgorithmicSkyPilotRunner
    __all__.append("ResearchSkyPilotRunner")
    __all__.append("AlgorithmicSkyPilotRunner")
except ImportError:
    pass
