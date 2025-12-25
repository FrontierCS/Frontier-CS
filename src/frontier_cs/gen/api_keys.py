"""API key pool management for solution generation."""

import logging
import os
import threading
import time
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

PROVIDER_ENV_KEY_MAP: Dict[str, List[str]] = {
    "openai": ["OPENAI_API_KEY"],
    "google": ["GOOGLE_API_KEY"],
    "anthropic": ["ANTHROPIC_API_KEY"],
    "xai": ["XAI_API_KEY"],
    "deepseek": ["DEEPSEEK_API_KEY"],
    "openrouter": ["OPENROUTER_API_KEY"],
}


class APIKeyPool:
    """Thread-safe pool of API keys with backoff handling."""

    def __init__(self, keys: List[str], *, name: str):
        self.name = name
        self._states = [
            {
                "key": key,
                "failures": 0,
                "disabled": False,
                "backoff_until": 0.0,
            }
            for key in keys
        ]
        self._lock = threading.Lock()
        self._index = 0

    def acquire(self) -> Tuple[Optional[str], Optional[int]]:
        """Acquire an available API key from the pool."""
        with self._lock:
            if not self._states:
                return None, None
            now = time.time()
            for _ in range(len(self._states)):
                idx = self._index % len(self._states)
                self._index += 1
                state = self._states[idx]
                if state["disabled"]:
                    continue
                if state["backoff_until"] > now:
                    continue
                return state["key"], idx
            return None, None

    def report_success(self, idx: Optional[int]) -> None:
        """Report successful API call for a key."""
        if idx is None:
            return
        with self._lock:
            if 0 <= idx < len(self._states):
                state = self._states[idx]
                state["failures"] = 0
                state["backoff_until"] = 0.0

    def report_failure(self, idx: Optional[int], error: Optional[str]) -> None:
        """Report failed API call for a key."""
        if idx is None:
            return
        with self._lock:
            if not (0 <= idx < len(self._states)):
                return
            state = self._states[idx]
            state["failures"] += 1
            reason = (error or "").lower()
            fatal_markers = ("invalid", "unauthorized", "forbidden", "permission", "auth")
            if any(marker in reason for marker in fatal_markers):
                if not state["disabled"]:
                    logger.warning(f"Disabling API key for {self.name}: invalid/unauthorized")
                state["disabled"] = True
                state["backoff_until"] = float("inf")
                return

            delay: int = min(600, 60 * state["failures"])
            state["backoff_until"] = max(state["backoff_until"], time.time() + delay)
            logger.info(f"Backing off {delay:.0f}s for {self.name} key (failures={state['failures']})")

    def size(self) -> int:
        """Return the number of keys in the pool."""
        with self._lock:
            return len(self._states)


def _matches_env_base(key_name: str, base: str) -> bool:
    """Check if an environment variable name matches a base name pattern."""
    if key_name == base:
        return True
    if key_name.startswith(base):
        suffix = key_name[len(base):]
        if not suffix:
            return True
        if suffix.isdigit():
            return True
        if suffix.startswith(('_', '-')):
            return True
    return False


def _collect_provider_keys(provider: str, base_names: List[str]) -> List[str]:
    """Collect all API keys for a provider from environment variables."""
    keys: List[str] = []
    seen: set[str] = set()
    for env_name, value in os.environ.items():
        if not value:
            continue
        for base in base_names:
            if _matches_env_base(env_name, base):
                key_value = value.strip()
                if key_value and key_value not in seen:
                    seen.add(key_value)
                    keys.append(key_value)
    return keys


def build_key_pools() -> Dict[str, APIKeyPool]:
    """Build API key pools for all providers from environment variables."""
    pools: Dict[str, APIKeyPool] = {}
    for provider, bases in PROVIDER_ENV_KEY_MAP.items():
        keys = _collect_provider_keys(provider, bases)
        if keys:
            pools[provider] = APIKeyPool(keys, name=provider)
    return pools


def get_fallback_api_key(provider: str) -> Optional[str]:
    """Get an API key for a provider from environment variables."""
    env_var = PROVIDER_ENV_KEY_MAP.get(provider, [None])[0]
    if env_var:
        return os.getenv(env_var)
    return None
