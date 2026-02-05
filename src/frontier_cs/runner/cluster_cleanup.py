"""
Shared cluster cleanup registry for SkyPilot-based runners.
"""

from __future__ import annotations

import threading


class ActiveClusterRegistry:
    """Track active SkyPilot clusters for cleanup on exit."""

    _active_clusters: set[str] = set()
    _lock = threading.Lock()

    @classmethod
    def register(cls, name: str) -> None:
        with cls._lock:
            cls._active_clusters.add(name)

    @classmethod
    def unregister(cls, name: str) -> None:
        with cls._lock:
            cls._active_clusters.discard(name)

    @classmethod
    def snapshot(cls) -> list[str]:
        with cls._lock:
            return list(cls._active_clusters)
