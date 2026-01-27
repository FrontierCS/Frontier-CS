"""Concurrent execution utilities for solution generation."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

from .api_keys import APIKeyPool


@dataclass
class ExecutionResult:
    """Result of a single task execution."""

    status: str  # "generated" | "failed" | "skipped"
    solution_name: str
    error: Optional[str]
    provider: str
    pool_token: Optional[int]


T = TypeVar("T")


def run_with_pool(
    tasks: List[T],
    execute_fn: Callable[[T], ExecutionResult],
    provider_key_pools: Dict[str, APIKeyPool],
    concurrency: int,
    on_complete: Optional[Callable[[ExecutionResult], None]] = None,
) -> Tuple[List[str], List[str]]:
    """Run tasks concurrently with key pool management.

    Args:
        tasks: List of tasks to execute
        execute_fn: Function that executes a single task and returns ExecutionResult
        provider_key_pools: Dict mapping provider name to APIKeyPool
        concurrency: Maximum number of concurrent workers
        on_complete: Optional callback called after each task completes

    Returns:
        Tuple of (generated solution names, failed solution names with errors)
    """
    generated: List[str] = []
    failed: List[str] = []

    if not tasks:
        return generated, failed

    max_workers = min(concurrency, len(tasks))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {executor.submit(execute_fn, task): task for task in tasks}
        for future in as_completed(future_to_task):
            result = future.result()

            # Report to key pool
            pool = provider_key_pools.get(result.provider)
            if pool and result.pool_token is not None:
                if result.status == "generated":
                    pool.report_success(result.pool_token)
                else:
                    pool.report_failure(result.pool_token, result.error)

            # Accumulate results
            if result.status == "generated":
                generated.append(result.solution_name)
            elif result.status == "failed":
                if result.error:
                    failed.append(f"{result.solution_name} ({result.error})")
                else:
                    failed.append(result.solution_name)

            # Callback
            if on_complete:
                on_complete(result)

    return generated, failed


def acquire_key_for_provider(
    provider: str,
    provider_key_pools: Dict[str, APIKeyPool],
) -> Tuple[Optional[str], Optional[int]]:
    """Acquire an API key from the pool for a given provider.

    Args:
        provider: Provider name (e.g., "openai", "anthropic")
        provider_key_pools: Dict mapping provider name to APIKeyPool

    Returns:
        Tuple of (api_key, pool_token) or (None, None) if no key available
    """
    pool = provider_key_pools.get(provider)
    if pool:
        return pool.acquire()
    return None, None
