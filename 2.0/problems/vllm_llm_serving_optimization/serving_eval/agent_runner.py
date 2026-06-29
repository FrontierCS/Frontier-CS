"""A compact, mini-swe-agent-style agentic workload runner.

This drives the served model through multi-turn, tool-using conversations over a
slice of SWE-bench instances, exactly the long shared-prefix workload the task
optimizes. It is intentionally a small, self-contained re-implementation of the
mini-swe-agent loop so that per-instance end-to-end latency can be measured
cleanly on the client side (no dependence on any server-side instrumentation).

For each instance:
  * messages start with a system prompt + the problem statement,
  * the model replies with one ```bash``` action,
  * the action runs in the instance sandbox, and its output is fed back,
  * the loop ends when the model submits (a sentinel command) or hits a limit.

Instances arrive over time as a Poisson process (``jps``) or under fixed
concurrency (``workers``), so many conversations are in flight at once.
"""

from __future__ import annotations

import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from .settings import EvalSettings, parse_slice
from .sandbox import make_sandbox

SUBMIT_SENTINEL = "VLLM_SERVING_OPT_SUBMIT"

SYSTEM_PROMPT = (
    "You are a software engineering agent fixing a bug in a code repository.\n"
    "Your working directory is the repository root.\n"
    "At each step, reply with exactly ONE shell command inside a single fenced\n"
    "```bash\n...\n``` block. Do not include any other text.\n"
    "Inspect files, make edits, and run any checks you need.\n"
    f"When the fix is complete, run: echo {SUBMIT_SENTINEL}\n"
    "and nothing else, to submit your changes."
)

INSTANCE_TEMPLATE = (
    "Resolve the following issue in the repository.\n\n"
    "<issue>\n{problem_statement}\n</issue>\n\n"
    "Begin by exploring the repository. Respond with one ```bash``` command."
)

BASH_BLOCK_RE = re.compile(r"```bash\s*\n(.*?)\n```", re.DOTALL)


@dataclass
class InstanceResult:
    instance_id: str
    latency_seconds: float
    n_calls: int
    exit_status: str
    patch: str = ""
    error: str = ""
    per_call_seconds: list[float] = field(default_factory=list)


def load_instances(settings: EvalSettings, role: str) -> list[dict[str, Any]]:
    import random

    from datasets import load_dataset

    dataset = load_dataset(settings.dataset, split=settings.dataset_split)
    # Deterministic, fixed-seed RANDOM sample across all repos (sorted first for a
    # machine-independent base order, then shuffled with sample_seed). This avoids
    # the contiguous "sorted prefix" slice, which clusters by repo (e.g. all
    # astropy+django) and is not representative. The public slice is the first
    # rows of the same shuffled order, so it stays a strict subset of the final.
    ids = sorted(range(len(dataset)), key=lambda i: dataset[i]["instance_id"])
    random.Random(settings.sample_seed).shuffle(ids)
    chosen = list(parse_slice(settings.slice_for_role(role), len(ids)))
    instances: list[dict[str, Any]] = []
    for index in chosen:
        row = dataset[ids[index]]
        instances.append(
            {
                "instance_id": row["instance_id"],
                "problem_statement": row.get("problem_statement", ""),
            }
        )
    return instances


def _openai_client(base_url: str):
    from openai import OpenAI

    return OpenAI(base_url=base_url, api_key="EMPTY", timeout=900.0)


def _parse_action(text: str) -> str | None:
    match = BASH_BLOCK_RE.search(text or "")
    if not match:
        return None
    return match.group(1).strip()


def run_instance(
    instance: dict[str, Any],
    *,
    base_url: str,
    settings: EvalSettings,
    prefer_docker: bool,
) -> InstanceResult:
    instance_id = instance["instance_id"]
    client = _openai_client(base_url)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": INSTANCE_TEMPLATE.format(problem_statement=instance["problem_statement"])},
    ]
    per_call: list[float] = []
    exit_status = "incomplete"
    sandbox = None
    started = time.perf_counter()
    try:
        sandbox = make_sandbox(instance_id, prefer_docker=prefer_docker)
        for _ in range(max(1, settings.step_limit)):
            call_start = time.perf_counter()
            try:
                completion = client.chat.completions.create(
                    model=settings.model,
                    messages=messages,
                    temperature=settings.temperature,
                    max_tokens=settings.max_completion_tokens,
                    # Stable per-conversation job id (every turn of this instance
                    # shares it). Forwarded via vllm_xargs -> sampling_params.
                    # extra_args["job_id"], which vanilla vLLM ignores but a
                    # job-aware scheduler can use for job-level FCFS. Does not
                    # change generated tokens.
                    extra_body={"vllm_xargs": {"job_id": str(instance_id)}},
                )
            except Exception as exc:  # noqa: BLE001
                # An API error (e.g. the growing conversation exceeding the model's
                # context window) ends the loop, but any edits the agent already
                # made to the sandbox are real work — capture the patch-so-far
                # instead of discarding it.
                exit_status = "api_error"
                partial_patch = ""
                try:
                    partial_patch = sandbox.read_patch() if sandbox is not None else ""
                except Exception:  # noqa: BLE001
                    partial_patch = ""
                return InstanceResult(
                    instance_id=instance_id,
                    latency_seconds=time.perf_counter() - started,
                    n_calls=len(per_call),
                    exit_status="limit_with_patch" if partial_patch.strip() else exit_status,
                    patch=partial_patch,
                    error=type(exc).__name__,
                    per_call_seconds=per_call,
                )
            per_call.append(time.perf_counter() - call_start)
            content = completion.choices[0].message.content or ""
            messages.append({"role": "assistant", "content": content})

            action = _parse_action(content)
            if action is None:
                messages.append(
                    {
                        "role": "user",
                        "content": "Reply with exactly one ```bash``` command block.",
                    }
                )
                continue
            if SUBMIT_SENTINEL in action:
                exit_status = "submitted"
                break

            code, output = sandbox.run(action, timeout=60)
            output = output[-4000:]
            messages.append(
                {"role": "user", "content": f"(exit={code})\n{output}"}
            )
        patch = sandbox.read_patch() if sandbox is not None else ""
        if exit_status == "incomplete" and patch.strip():
            exit_status = "limit_with_patch"
        return InstanceResult(
            instance_id=instance_id,
            latency_seconds=time.perf_counter() - started,
            n_calls=len(per_call),
            exit_status=exit_status,
            patch=patch,
            per_call_seconds=per_call,
        )
    finally:
        if sandbox is not None:
            sandbox.close()


def run_workload(
    *,
    base_url: str,
    settings: EvalSettings,
    role: str,
    prefer_docker: bool,
) -> list[InstanceResult]:
    instances = load_instances(settings, role)
    results: list[InstanceResult] = []
    results_lock = threading.Lock()

    def _record(result: InstanceResult) -> None:
        with results_lock:
            results.append(result)

    def _run(instance: dict[str, Any]) -> None:
        # Never let an instance vanish: if run_instance raises (e.g. sandbox
        # creation failed), record an explicit failure result so the instance is
        # counted (as a regression by the scorer) instead of silently dropped.
        try:
            result = run_instance(
                instance, base_url=base_url, settings=settings, prefer_docker=prefer_docker
            )
        except Exception as exc:  # noqa: BLE001
            result = InstanceResult(
                instance_id=str(instance.get("instance_id", "unknown")),
                latency_seconds=0.0,
                n_calls=0,
                exit_status="api_error",
                error=type(exc).__name__,
            )
        _record(result)

    if settings.arrival_mode == "jps" and settings.jps > 0:
        # Deterministic Poisson schedule (seeded) so arrivals are reproducible.
        import random

        rng = random.Random(20260604)
        schedule: list[float] = []
        clock = 0.0
        for _ in instances:
            clock += rng.expovariate(settings.jps)
            schedule.append(clock)
        threads: list[threading.Thread] = []
        origin = time.perf_counter()

        def _delayed(instance: dict[str, Any], when: float) -> None:
            delay = when - (time.perf_counter() - origin)
            if delay > 0:
                time.sleep(delay)
            _run(instance)

        for instance, when in zip(instances, schedule):
            thread = threading.Thread(target=_delayed, args=(instance, when), daemon=True)
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join()
    else:
        with ThreadPoolExecutor(max_workers=max(1, settings.workers)) as pool:
            list(pool.map(_run, instances))

    return results
