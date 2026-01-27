"""API key pool management for solution generation."""

import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def ensure_env_loaded() -> bool:
    """Load .env file, overriding existing env vars. Returns True if file was found."""
    return load_dotenv(override=True)


@dataclass
class KeyCheckResult:
    """Result of an API key validation check."""
    provider: str
    key: str  # Full key
    key_hint: str  # Last 6 chars for display
    valid: bool
    error: Optional[str] = None
    org_id: Optional[str] = None  # Organization/project ID if available
    rpm_limit: Optional[int] = None  # Requests per minute limit
    tpm_limit: Optional[int] = None  # Tokens per minute limit

PROVIDER_ENV_KEY_MAP: Dict[str, List[str]] = {
    "openai": ["OPENAI_API_KEY"],
    "google": ["GOOGLE_API_KEY"],
    "anthropic": ["ANTHROPIC_API_KEY"],
    "xai": ["XAI_API_KEY"],
    "deepseek": ["DEEPSEEK_API_KEY"],
    "openrouter": ["OPENROUTER_API_KEY"],
}


@dataclass
class KeyInfo:
    """Info for a key in the pool."""
    key: str
    weight: int = 1  # Higher weight = more requests
    org_id: Optional[str] = None


class APIKeyPool:
    """Thread-safe pool of API keys with weighted load balancing."""

    def __init__(self, keys: List[KeyInfo], *, name: str):
        self.name = name
        self._states = [
            {
                "key": info.key,
                "weight": info.weight,
                "org_id": info.org_id,
                "failures": 0,
                "disabled": False,
                "backoff_until": 0.0,
                "usage_count": 0,  # Track usage for weighted selection
            }
            for info in keys
        ]
        self._lock = threading.Lock()
        self._total_weight = sum(s["weight"] for s in self._states)

    def acquire(self) -> Tuple[Optional[str], Optional[int]]:
        """Acquire an API key using weighted selection."""
        with self._lock:
            if not self._states:
                return None, None

            now = time.time()
            available = []
            for idx, state in enumerate(self._states):
                if state["disabled"]:
                    continue
                if state["backoff_until"] > now:
                    continue
                available.append((idx, state))

            if not available:
                return None, None

            # Weighted selection: prefer keys with lower usage/weight ratio
            # This naturally balances load according to weights
            best_idx = None
            best_ratio = float("inf")
            for idx, state in available:
                ratio = state["usage_count"] / state["weight"]
                if ratio < best_ratio:
                    best_ratio = ratio
                    best_idx = idx

            if best_idx is not None:
                self._states[best_idx]["usage_count"] += 1
                return self._states[best_idx]["key"], best_idx
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


def build_key_pools(
    valid_keys: Optional[Dict[str, List[str]]] = None,
    key_info: Optional[Dict[str, List[KeyCheckResult]]] = None,
) -> Dict[str, APIKeyPool]:
    """Build API key pools for all providers.

    Args:
        valid_keys: If provided, use only these pre-validated keys.
                   If None, collect all keys from environment variables.
        key_info: Optional KeyCheckResult list per provider for RPM weights.
    """
    pools: Dict[str, APIKeyPool] = {}

    if valid_keys is not None:
        for provider, keys in valid_keys.items():
            if not keys:
                continue

            # Build KeyInfo list with weights from key_info if available
            key_infos: List[KeyInfo] = []
            provider_results = key_info.get(provider, []) if key_info else []
            result_map = {r.key: r for r in provider_results if r.valid}

            for key in keys:
                result = result_map.get(key)
                if result:
                    # Use RPM as weight, default to 100 if unknown
                    weight = result.rpm_limit or 100
                    key_infos.append(KeyInfo(key, weight, result.org_id))
                else:
                    key_infos.append(KeyInfo(key, 100, None))

            pools[provider] = APIKeyPool(key_infos, name=provider)
    else:
        # Collect from environment (legacy behavior, equal weights)
        for provider, bases in PROVIDER_ENV_KEY_MAP.items():
            keys = _collect_provider_keys(provider, bases)
            if keys:
                key_infos = [KeyInfo(key, 100, None) for key in keys]
                pools[provider] = APIKeyPool(key_infos, name=provider)
    return pools


def get_fallback_api_key(provider: str) -> Optional[str]:
    """Get an API key for a provider from environment variables."""
    env_var = PROVIDER_ENV_KEY_MAP.get(provider, [None])[0]
    if env_var:
        return os.getenv(env_var)
    return None


@dataclass
class _CheckResult:
    """Internal result from key checker."""
    valid: bool
    error: Optional[str] = None
    org_id: Optional[str] = None
    rpm_limit: Optional[int] = None
    tpm_limit: Optional[int] = None


def _parse_rate_limit_headers(headers) -> Tuple[Optional[int], Optional[int]]:
    """Extract RPM and TPM limits from response headers."""
    rpm = headers.get("x-ratelimit-limit-requests")
    tpm = headers.get("x-ratelimit-limit-tokens")
    return (int(rpm) if rpm else None, int(tpm) if tpm else None)


def _check_openai_key(api_key: str, base_url: Optional[str] = None) -> _CheckResult:
    """Check if an OpenAI API key is valid."""
    import httpx
    base = (base_url or "https://api.openai.com/v1").rstrip("/")
    org_id = None
    rpm_limit = None
    tpm_limit = None

    # Try /me endpoint first (OpenAI only) to get org info
    if "api.openai.com" in base:
        try:
            resp = httpx.get(f"{base}/me", headers={"Authorization": f"Bearer {api_key}"}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                orgs = data.get("orgs", {}).get("data", [])
                if orgs:
                    org_id = orgs[0].get("id")
        except Exception:
            pass

    # Use /models endpoint to validate and get rate limits
    try:
        resp = httpx.get(f"{base}/models", headers={"Authorization": f"Bearer {api_key}"}, timeout=10)
        if resp.status_code == 200:
            rpm_limit, tpm_limit = _parse_rate_limit_headers(resp.headers)
            return _CheckResult(True, None, org_id, rpm_limit, tpm_limit)
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        err = data.get("error", {}).get("message", resp.text[:100])
        return _CheckResult(False, err)
    except Exception as e:
        return _CheckResult(False, str(e))


def _check_google_key(api_key: str) -> _CheckResult:
    """Check if a Google API key is valid."""
    import httpx
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        resp = httpx.get(url, timeout=10)
        if resp.status_code == 200:
            # Google: same key = same project, use key prefix as pseudo-org
            # Free tier: ~5 RPM, Paid tier 1: ~300 RPM (can't detect from headers)
            org_id = f"gcp-{api_key[:8]}"
            return _CheckResult(True, None, org_id)
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        err = data.get("error", {}).get("message", resp.text[:100])
        return _CheckResult(False, err)
    except Exception as e:
        return _CheckResult(False, str(e))


def _check_anthropic_key(api_key: str) -> _CheckResult:
    """Check if an Anthropic API key is valid."""
    import httpx
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    try:
        resp = httpx.post(url, headers=headers, json={}, timeout=10)
        org_id = resp.headers.get("anthropic-organization-id")
        rpm_limit, tpm_limit = _parse_rate_limit_headers(resp.headers)
        if resp.status_code == 400:  # Bad request = auth OK
            return _CheckResult(True, None, org_id, rpm_limit, tpm_limit)
        if resp.status_code == 401:
            data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            err = data.get("error", {}).get("message", "Unauthorized")
            return _CheckResult(False, err)
        return _CheckResult(True, None, org_id, rpm_limit, tpm_limit)
    except Exception as e:
        return _CheckResult(False, str(e))


def _check_xai_key(api_key: str) -> _CheckResult:
    """Check if an xAI API key is valid."""
    result = _check_openai_key(api_key, base_url="https://api.x.ai/v1")
    if result.valid:
        result.org_id = f"xai-{api_key[:8]}"
    return result


def _check_deepseek_key(api_key: str) -> _CheckResult:
    """Check if a DeepSeek API key is valid."""
    result = _check_openai_key(api_key, base_url="https://api.deepseek.com")
    if result.valid:
        result.org_id = f"deepseek-{api_key[:8]}"
    return result


def _check_openrouter_key(api_key: str) -> _CheckResult:
    """Check if an OpenRouter API key is valid."""
    result = _check_openai_key(api_key, base_url="https://openrouter.ai/api/v1")
    if result.valid:
        result.org_id = f"openrouter-{api_key[:8]}"
    return result


_PROVIDER_CHECKERS = {
    "openai": _check_openai_key,
    "google": _check_google_key,
    "anthropic": _check_anthropic_key,
    "xai": _check_xai_key,
    "deepseek": _check_deepseek_key,
    "openrouter": _check_openrouter_key,
}


def precheck_api_keys(
    providers: Optional[List[str]] = None,
    *,
    verbose: bool = True,
) -> Dict[str, List[KeyCheckResult]]:
    """
    Validate API keys for specified providers.

    Args:
        providers: List of providers to check. If None, checks all with keys.
        verbose: Print results to stdout.

    Returns:
        Dict mapping provider to list of KeyCheckResult.
    """
    ensure_env_loaded()
    results: Dict[str, List[KeyCheckResult]] = {}

    providers_to_check = providers or list(PROVIDER_ENV_KEY_MAP.keys())

    for provider in providers_to_check:
        bases = PROVIDER_ENV_KEY_MAP.get(provider, [])
        keys = _collect_provider_keys(provider, bases)
        if not keys:
            continue

        checker = _PROVIDER_CHECKERS.get(provider)
        if not checker:
            continue

        results[provider] = []
        for key in keys:
            key_hint = f"***{key[-6:]}" if len(key) > 6 else "***"
            check = checker(key)
            result = KeyCheckResult(
                provider=provider,
                key=key,
                key_hint=key_hint,
                valid=check.valid,
                error=check.error,
                org_id=check.org_id,
                rpm_limit=check.rpm_limit,
                tpm_limit=check.tpm_limit,
            )
            results[provider].append(result)

            if verbose:
                parts = []
                if check.org_id:
                    parts.append(f"org={check.org_id}")
                if check.rpm_limit:
                    parts.append(f"rpm={check.rpm_limit}")
                extra = " " + " ".join(parts) if parts else ""
                status = f"OK{extra}" if check.valid else f"FAILED: {check.error}"
                print(f"  {provider} ({key_hint}): {status}")

    return results


@dataclass
class ValidKeyInfo:
    """Info about a validated API key."""
    key: str
    org_id: Optional[str]


def precheck_required_providers(
    providers: List[str],
    *,
    exit_on_failure: bool = True,
) -> Tuple[Dict[str, List[str]], Dict[str, List[KeyCheckResult]]]:
    """
    Check that all required providers have at least one valid key.

    Args:
        providers: List of required providers.
        exit_on_failure: Exit with code 1 if any provider fails.

    Returns:
        Tuple of (valid_keys dict, check_results dict for RPM weights).
    """
    print("Validating API keys...")
    results = precheck_api_keys(providers, verbose=True)

    valid_keys: Dict[str, List[str]] = {}
    org_counts: Dict[str, Dict[str, int]] = {}  # provider -> org_id -> count
    failed_providers = []

    for provider in providers:
        provider_results = results.get(provider, [])
        if not provider_results:
            print(f"  {provider}: NO KEYS FOUND")
            failed_providers.append(provider)
            continue

        # Collect valid keys and count orgs
        provider_valid = []
        org_counts[provider] = {}
        for r in provider_results:
            if r.valid:
                provider_valid.append(r.key)
                org = r.org_id or "unknown"
                org_counts[provider][org] = org_counts[provider].get(org, 0) + 1

        if not provider_valid:
            failed_providers.append(provider)
        else:
            valid_keys[provider] = provider_valid

    if failed_providers:
        print(f"\nAPI key validation failed for: {', '.join(failed_providers)}")
        if exit_on_failure:
            import sys
            sys.exit(1)
        return {}, {}

    # Print summary with org and rate limit info
    print("\nSummary:")
    valid_count = sum(len(keys) for keys in valid_keys.values())
    for provider in providers:
        if provider not in valid_keys:
            continue
        keys = valid_keys[provider]
        provider_results = results.get(provider, [])
        valid_results = [r for r in provider_results if r.valid]

        # Count unique orgs
        orgs = org_counts.get(provider, {})
        n_orgs = len(orgs)

        # Get total RPM across all orgs (same org shares limit)
        total_rpm = None
        org_rpms: Dict[str, int] = {}
        for r in valid_results:
            if r.rpm_limit and r.org_id:
                # Only count highest RPM per org (they share the limit)
                org_rpms[r.org_id] = max(org_rpms.get(r.org_id, 0), r.rpm_limit)
        if org_rpms:
            total_rpm = sum(org_rpms.values())

        # Build status line
        parts = [f"{len(keys)} key(s)"]
        if n_orgs == 1:
            parts.append(f"1 org")
        else:
            parts.append(f"{n_orgs} orgs")
        if total_rpm:
            # Suggest concurrent: RPM/10, capped at 20 per org
            # (LLM generation takes minutes, so conservative estimate)
            suggested_concurrent = min(n_orgs * 20, max(1, total_rpm // 10))
            parts.append(f"~{total_rpm} RPM")
            parts.append(f"suggest ~{suggested_concurrent} concurrent")
        print(f"  {provider}: {', '.join(parts)}")

    print(f"\nAPI key validation complete. {valid_count} valid key(s).\n")
    return valid_keys, results
