"""BFCL **memory** agentic workload (replaces the single-turn AST workload).

This is the second judged workload alongside the SWE-bench agentic run. Each
instance is a multi-turn agentic task from the Berkeley Function Calling
Leaderboard ``memory`` category: the model is given a key-value memory tool
suite (``MemoryAPI_kv``) pre-seeded with facts from a prior conversation, asked a
question, and must issue tool calls (retrieve / list / search across core and
archival memory) over several turns, then answer. Correctness is a deterministic
word-boundary match of the final answer against the ground truth.

Why memory (vs the old single-turn ``simple`` AST category): it gives a real,
multi-step agentic request path (so the scheduler optimization has long,
contended requests to act on) AND a non-zero, non-ceilinged accuracy signal (a
strong model gets ~70-90%, not a pinned 1.0), so the accuracy guardrail has
dynamic range.

Determinism/reproducibility: the per-scenario memory state is **pre-baked once**
(see build_memory_snapshots.py) into ``bfcl_data/memory_snapshots/<scenario>_final.json``
and loaded read-only here, so baseline and patched builds query an identical,
frozen memory — the prereq agent's behavior is a fixed fixture, not a per-run
variable. Self-contained: vendors the kv backend (``bfcl_vendor/``) + the data
slice; only needs stdlib + ``openai`` (+ optional ``rank-bm25`` for key-search).

Source: ShishirPatil/gorilla, bfcl-eval==2026.3.23 (Apache-2.0); see bfcl_data/NOTICE.
"""

from __future__ import annotations

import ast
import json
import os
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .bfcl_vendor.memory_kv import MemoryAPI_kv
from .settings import EvalSettings, parse_slice

BFCL_DATA_DIR = Path(os.environ.get("BFCL_DATA_DIR", str(Path(__file__).with_name("bfcl_data"))))
MEMORY_PROMPT_FILE = "BFCL_v4_memory.json"
MEMORY_ANSWER_FILE = "possible_answer/BFCL_v4_memory.json"
MEMORY_FUNCDOC_FILE = "multi_turn_func_doc/memory_kv.json"
MEMORY_SNAPSHOT_DIR = "memory_snapshots"
DEFAULT_MAX_STEPS = 20  # upstream MAXIMUM_STEP_LIMIT
SCENARIOS = ("customer", "healthcare", "finance", "student", "notetaker")

# Classic plaintext function-calling system prompt (verbatim from bfcl-eval).
_FUNC_CALLING_SYSPROMPT = (
    "You are an expert in composing functions.You are given a question and a set "
    "of possible functions. Based on the question, you will need to make one or "
    "more function/tool calls to achieve the purpose. If none of the functions "
    "can be used, point it out. If the given question lacks the parameters "
    "required by the function, also point it out.\n\n"
    "You should only return the function calls in your response.\n\n"
    "If you decide to invoke any of the function(s), you MUST put it in the "
    "format of [func_name1(params_name1=params_value1, params_name2=params_value2"
    "...), func_name2(params)].  You SHOULD NOT include any other text in the "
    "response.\n\n"
    "At each turn, you should try your best to complete the tasks requested by "
    "the user within the current turn. Continue to output functions to call "
    "until you have fulfilled the user's request to the best of your ability. "
    "Once you have no more functions to call, the system will consider the "
    "current turn complete and proceed to the next turn or task.\n\n"
    "Here is a list of functions in json format that you can invoke.\n"
)

# Memory scenario personas + backend instruction (verbatim from bfcl-eval).
MEMORY_AGENT_SETTINGS = {
    "student": "You are an academic-support assistant for college student. Remember key personal and academic details discussed across sessions, and draw on them to answer questions or give guidance.",
    "customer": "You are a general customer support assistant for an e-commerce platform. Your task is to understand and remember information that can be used to provide information about user inquiries, preferences, and offer consistent, helpful assistance over multiple interactions.",
    "finance": "You are a high-level executive assistant supporting a senior finance professional. Retain and synthesize both personal and professional information including facts, goals, prior decisions, and family life across sessions to provide strategic, context-rich guidance and continuity.",
    "healthcare": "You are a healthcare assistant supporting a patient across appointments. Retain essential medical history, treatment plans, and personal preferences to offer coherent, context-aware guidance and reminders.",
    "notetaker": "You are a personal organization assistant. Capture key information from conversations, like tasks, deadlines, and preferences, and use it to give reliable reminders and answers in future sessions.",
}
MEMORY_BACKEND_INSTRUCTION = """{scenario_setting}

You have access to an advanced memory system, consisting of two memory types 'Core Memory' and 'Archival Memory'. Both type of memory is persistent across multiple conversations with the user, and can be accessed in a later interactions. You should actively manage your memory data to keep track of important information, ensure that it is up-to-date and easy to retrieve to provide personalized responses to the user later.

The Core memory is limited in size, but always visible to you in context. The Archival Memory has a much larger capacity, but will be held outside of your immediate context due to its size.

Here is the content of your Core Memory from previous interactions:
{memory_content}
"""


@dataclass
class BfclResult:
    instance_id: str
    latency_seconds: float
    exit_status: str  # "ok" | "api_error" | "force_quit"
    correct: bool = False
    decoded_ok: bool = False
    output: str = ""
    error: str = ""
    per_call_seconds: list[float] = field(default_factory=list)
    n_steps: int = 0
    scenario: str = ""


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #

def bfcl_available() -> bool:
    if not (BFCL_DATA_DIR / MEMORY_PROMPT_FILE).exists():
        return False
    if not (BFCL_DATA_DIR / MEMORY_ANSWER_FILE).exists():
        return False
    if not (BFCL_DATA_DIR / MEMORY_FUNCDOC_FILE).exists():
        return False
    return all((BFCL_DATA_DIR / MEMORY_SNAPSHOT_DIR / f"{s}_final.json").exists() for s in SCENARIOS)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


_TOOLS_CACHE: list[dict[str, Any]] | None = None


def load_memory_tools() -> list[dict[str, Any]]:
    global _TOOLS_CACHE
    if _TOOLS_CACHE is None:
        _TOOLS_CACHE = _read_jsonl(BFCL_DATA_DIR / MEMORY_FUNCDOC_FILE)
    return _TOOLS_CACHE


def load_snapshot(scenario: str) -> dict[str, Any]:
    path = BFCL_DATA_DIR / MEMORY_SNAPSHOT_DIR / f"{scenario}_final.json"
    snap = json.loads(path.read_text(encoding="utf-8"))
    return {
        "core_memory": snap.get("core_memory", {}) or {},
        "archival_memory": snap.get("archival_memory", {}) or {},
    }


def load_memory_instances(settings: EvalSettings, role: str) -> list[dict[str, Any]]:
    prompts = _read_jsonl(BFCL_DATA_DIR / MEMORY_PROMPT_FILE)
    answers = {row["id"]: row for row in _read_jsonl(BFCL_DATA_DIR / MEMORY_ANSWER_FILE)}
    # Same deterministic fixed-seed sample as the SWE workload.
    prompts.sort(key=lambda row: row["id"])
    random.Random(settings.sample_seed).shuffle(prompts)
    chosen = list(parse_slice(settings.bfcl_slice_for_role(role), len(prompts)))
    tools = load_memory_tools()
    instances: list[dict[str, Any]] = []
    for index in chosen:
        row = prompts[index]
        answer = answers.get(row["id"])
        if answer is None:
            continue
        instances.append(
            {
                "id": row["id"],
                "scenario": row.get("scenario", ""),
                "question": row["question"],
                "ground_truth": answer.get("ground_truth", []),
                "functions": tools,
            }
        )
    return instances


# --------------------------------------------------------------------------- #
# Tool-call decode + execute (reuses the same AST decoding as the AST workload)
# --------------------------------------------------------------------------- #

def _literal(node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except Exception:
        try:
            return ast.unparse(node)
        except Exception:
            return None


def _resolve_call(node: ast.Call) -> tuple[str, dict[str, Any]]:
    func = node.func
    name = func.id if isinstance(func, ast.Name) else (
        ast.unparse(func) if hasattr(ast, "unparse") else getattr(func, "attr", "<call>")
    )
    kwargs: dict[str, Any] = {}
    for kw in node.keywords:
        if kw.arg is not None:
            kwargs[kw.arg] = _literal(kw.value)
    # positional args are unusual in prompt mode; map by the kw-less order is not
    # possible without the tool schema, so positionals are passed by index name.
    for i, positional in enumerate(node.args):
        kwargs[f"_arg{i}"] = _literal(positional)
    return name, kwargs


def _parse_call_list(expr: str) -> list[tuple[str, dict[str, Any]]]:
    """Parse a ``[func(a=b), ...]`` / ``func(a=b)`` expression into calls.

    Raises unless the expression is a function call (or list/tuple of calls).
    """
    parsed = ast.parse(expr, mode="eval").body
    calls: list[tuple[str, dict[str, Any]]] = []
    if isinstance(parsed, ast.Call):
        calls.append(_resolve_call(parsed))
    elif isinstance(parsed, (ast.List, ast.Tuple)):
        for elem in parsed.elts:
            if not isinstance(elem, ast.Call):
                raise ValueError("non-call element")
            calls.append(_resolve_call(elem))
    else:
        raise ValueError("not a function-call list")
    if not calls:
        raise ValueError("empty call list")
    return calls


def decode_tool_calls(text: str) -> list[tuple[str, dict[str, Any]]]:
    """Decode a prompt-mode ``[func(a=b), ...]`` response into (name, kwargs).

    Tolerant of a prose preamble or a ``` markdown fence around the call list
    (the served model sometimes prefixes e.g. "Sure, I'll store that." before the
    ``[...]``). Only a bracketed expression whose elements are *function calls* is
    accepted; a natural-language final answer — even one that happens to contain
    brackets — raises, so the agentic loop terminates.

    Raises if the text is not a function-call list (i.e. the model produced a
    final natural-language answer instead).
    """
    raw = text.strip()
    # Strip a leading ```/```python fence and matching trailing ```.
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1] if "\n" in raw else raw[3:]
        raw = raw.rstrip()
        if raw.endswith("```"):
            raw = raw[:-3]
    cleaned = raw.strip("`\n ")

    # Fast path: the whole response is the call list (optionally missing the
    # outer brackets / wrapped in stray quotes). Identical to the original strict
    # behavior, so a clean tool-call response decodes exactly as it did before.
    candidate = cleaned
    if not candidate.startswith("["):
        candidate = "[" + candidate
    if not candidate.endswith("]"):
        candidate = candidate + "]"
    candidate = candidate.strip().strip("'")
    try:
        return _parse_call_list(candidate)
    except Exception:
        pass

    # Tolerant path: extract a ``[ ... ]`` slice that parses as a call list,
    # ignoring any prose preamble/suffix. Try the widest span (first '[' .. last
    # ']') first, then the first balanced region.
    start = cleaned.find("[")
    if start != -1:
        spans: list[str] = []
        last = cleaned.rfind("]")
        if last > start:
            spans.append(cleaned[start:last + 1])
        depth = 0
        for j in range(start, len(cleaned)):
            if cleaned[j] == "[":
                depth += 1
            elif cleaned[j] == "]":
                depth -= 1
                if depth == 0:
                    spans.append(cleaned[start:j + 1])
                    break
        for span in spans:
            try:
                return _parse_call_list(span)
            except Exception:
                continue
    raise ValueError("not a function-call list")


_VALID_TOOLS = {
    "core_memory_add", "core_memory_remove", "core_memory_replace", "core_memory_clear",
    "core_memory_retrieve", "core_memory_list_keys", "core_memory_key_search",
    "core_memory_retrieve_all", "archival_memory_add", "archival_memory_remove",
    "archival_memory_replace", "archival_memory_clear", "archival_memory_retrieve",
    "archival_memory_list_keys", "archival_memory_key_search",
}


def _execute_one(api: MemoryAPI_kv, name: str, kwargs: dict[str, Any]) -> Any:
    if name not in _VALID_TOOLS:
        return {"error": f"Function '{name}' does not exist in the memory tool suite."}
    fn = getattr(api, name)
    clean = {k: v for k, v in kwargs.items() if not k.startswith("_arg")}
    try:
        return fn(**clean)
    except TypeError as exc:
        return {"error": f"Invalid arguments for {name}: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}


# --------------------------------------------------------------------------- #
# Scoring (verbatim agentic_checker / standardize_string from bfcl-eval)
# --------------------------------------------------------------------------- #

_PUNCT_RE = re.compile(r"[\,\.\/\-\_\*\^\(\)]")


def standardize_string(s: str) -> str:
    return _PUNCT_RE.sub("", str(s)).lower().replace("'", '"')


def memory_correct(final_text: Any, ground_truth: list[str]) -> bool:
    if isinstance(final_text, list):
        final_text = final_text[0] if final_text else ""
    resp = standardize_string(str(final_text))
    for ans in ground_truth:
        a = standardize_string(str(ans))
        if a and re.search(rf"\b{re.escape(a)}\b", resp):
            return True
    return False


# --------------------------------------------------------------------------- #
# Agentic loop
# --------------------------------------------------------------------------- #

def build_messages(instance: dict[str, Any], api: MemoryAPI_kv) -> list[dict[str, str]]:
    functions_json = json.dumps(instance["functions"], indent=4)
    scenario = instance["scenario"]
    memory_instruction = MEMORY_BACKEND_INSTRUCTION.format(
        scenario_setting=MEMORY_AGENT_SETTINGS.get(scenario, ""),
        memory_content=api._dump_core_memory_to_context(),
    )
    system_content = _FUNC_CALLING_SYSPROMPT + functions_json + "\n\n" + memory_instruction
    messages: list[dict[str, str]] = [{"role": "system", "content": system_content}]
    for turn in instance["question"][0]:
        messages.append({"role": turn.get("role", "user"), "content": turn.get("content", "")})
    return messages


def _openai_client(base_url: str):
    from openai import OpenAI

    return OpenAI(base_url=base_url, api_key="EMPTY", timeout=300.0)


def run_memory_instance(instance: dict[str, Any], *, base_url: str, settings: EvalSettings) -> BfclResult:
    client = _openai_client(base_url)
    # Fresh per-instance backend seeded read-only from the frozen snapshot.
    api = MemoryAPI_kv()
    snap = load_snapshot(instance["scenario"])
    api.core_memory = deepcopy(snap["core_memory"])
    api.archival_memory = deepcopy(snap["archival_memory"])

    messages = build_messages(instance, api)
    max_steps = int(getattr(settings, "memory_max_steps", DEFAULT_MAX_STEPS) or DEFAULT_MAX_STEPS)
    per_call: list[float] = []
    started = time.perf_counter()
    final_text = ""
    decoded_any = False
    steps = 0
    while True:
        t0 = time.perf_counter()
        try:
            completion = client.chat.completions.create(
                model=settings.model,
                messages=messages,
                temperature=settings.temperature,
                max_tokens=settings.bfcl_max_tokens,
                seed=0,
                extra_body={"vllm_xargs": {"job_id": str(instance["id"])}},
            )
        except Exception as exc:  # noqa: BLE001
            return BfclResult(
                instance_id=instance["id"], latency_seconds=time.perf_counter() - started,
                exit_status="api_error", error=type(exc).__name__,
                per_call_seconds=per_call, n_steps=steps, scenario=instance["scenario"],
            )
        per_call.append(time.perf_counter() - t0)
        text = completion.choices[0].message.content or ""

        try:
            calls = decode_tool_calls(text)
        except Exception:
            # Not a tool call -> the model produced its final answer.
            final_text = text
            return BfclResult(
                instance_id=instance["id"], latency_seconds=time.perf_counter() - started,
                exit_status="ok", correct=memory_correct(text, instance["ground_truth"]),
                decoded_ok=True, output=text, per_call_seconds=per_call,
                n_steps=steps, scenario=instance["scenario"],
            )
        decoded_any = True
        results = [_execute_one(api, name, kwargs) for name, kwargs in calls]
        messages.append({"role": "assistant", "content": text})
        feedback = [
            {"role": "tool", "name": name, "content": str(result)}
            for (name, _), result in zip(calls, results)
        ]
        messages.append({"role": "user", "content": repr(feedback)})

        steps += 1
        if steps >= max_steps:
            final_text = text
            return BfclResult(
                instance_id=instance["id"], latency_seconds=time.perf_counter() - started,
                exit_status="force_quit", correct=memory_correct(text, instance["ground_truth"]),
                decoded_ok=decoded_any, output=text, error="max_steps",
                per_call_seconds=per_call, n_steps=steps, scenario=instance["scenario"],
            )


def run_bfcl_workload(*, base_url: str, settings: EvalSettings, role: str) -> list[BfclResult]:
    instances = load_memory_instances(settings, role)
    results: list[BfclResult] = []
    lock = threading.Lock()

    def _record(r: BfclResult) -> None:
        with lock:
            results.append(r)

    def _run(instance: dict[str, Any]) -> None:
        try:
            r = run_memory_instance(instance, base_url=base_url, settings=settings)
        except Exception as exc:  # noqa: BLE001 - never drop an instance silently
            r = BfclResult(
                instance_id=str(instance.get("id", "unknown")), latency_seconds=0.0,
                exit_status="api_error", error=type(exc).__name__, scenario=instance.get("scenario", ""),
            )
        _record(r)

    bfcl_jps = float(getattr(settings, "bfcl_jps", settings.jps) or settings.jps)
    if settings.arrival_mode == "jps" and bfcl_jps > 0:
        # Poisson arrivals at the BFCL-specific rate (bfcl_jps, higher than the
        # SWE jps): each memory conversation arrives over time, so multi-step
        # instances overlap and queue. Seeded so the schedule is reproducible.
        rng = random.Random(20260605)
        schedule: list[float] = []
        clock = 0.0
        for _ in instances:
            clock += rng.expovariate(bfcl_jps)
            schedule.append(clock)
        origin = time.perf_counter()
        threads: list[threading.Thread] = []

        def _delayed(instance: dict[str, Any], when: float) -> None:
            delay = when - (time.perf_counter() - origin)
            if delay > 0:
                time.sleep(delay)
            _run(instance)

        for instance, when in zip(instances, schedule):
            t = threading.Thread(target=_delayed, args=(instance, when), daemon=True)
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
    else:
        # Fallback: fire all at once at high concurrency (a burst), capped by
        # bfcl_workers. Each instance has its own backend so there is no shared state.
        with ThreadPoolExecutor(max_workers=max(1, settings.bfcl_workers)) as pool:
            list(pool.map(_run, instances))
    return results


# --------------------------------------------------------------------------- #
# Aggregators (shapes consumed by measure.py / scoring.py)
# --------------------------------------------------------------------------- #

def per_instance_latency(results: list[BfclResult]) -> dict[str, float]:
    return {r.instance_id: r.latency_seconds for r in results}


def accuracy(results: list[BfclResult]) -> float:
    if not results:
        return 0.0
    return sum(1 for r in results if r.correct) / len(results)


def correctness_map(results: list[BfclResult]) -> dict[str, bool]:
    return {r.instance_id: bool(r.correct) for r in results}


def outputs(results: list[BfclResult]) -> dict[str, str]:
    return {r.instance_id: r.output for r in results}
