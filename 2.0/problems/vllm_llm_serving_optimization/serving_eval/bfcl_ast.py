"""BFCL (Berkeley Function Calling Leaderboard) serving workload + correctness.

This is the *second* judged workload alongside the SWE-bench agentic run. Where
SWE-bench gives a latency signal but a ~0 task-solving rate for an 8B model (so
its accuracy guardrail is effectively dead), BFCL gives a **real, deterministic,
non-zero** correctness signal: each instance is a single-turn function-calling
query whose answer is checked by AST equality against a ground-truth call. That
makes a live accuracy guardrail possible and gives a per-sample greedy gate that
actually catches generation corruption.

The module is intentionally self-contained: it vendors a fixed slice of the BFCL
``simple`` (Python) category under ``bfcl_data/`` and reimplements the prompt
construction, the answer decoder, and the AST checker for that category — no
``bfcl_eval`` install, no run-time network. The checker is cross-validated
against the upstream ``bfcl_eval.eval_checker`` on all vendored records.

Source: ShishirPatil/gorilla, bfcl-eval==2026.3.23 (Apache-2.0); see
``bfcl_data/NOTICE``. Served in *prompt mode* (plain chat, the leaderboard's
``(Prompt)`` setting) so the request path matches the SWE-bench runner exactly.
"""

from __future__ import annotations

import ast
import json
import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .settings import EvalSettings, parse_slice

# The vendored slice ships next to this module; an env override lets the judge
# point at a baked path. No network / datasets.load_dataset at run time.
BFCL_DATA_DIR = Path(os.environ.get("BFCL_DATA_DIR", str(Path(__file__).with_name("bfcl_data"))))
BFCL_PROMPT_FILE = "BFCL_v4_simple_python.json"
BFCL_ANSWER_FILE = "possible_answer/BFCL_v4_simple_python.json"
BFCL_CATEGORY = "simple"  # single-turn, AST-checkable, highest/most-stable accuracy

# The canonical BFCL prompt-mode system prompt (plaintext/classic format), kept
# verbatim from bfcl-eval so the served distribution matches the leaderboard.
_BFCL_SYSTEM_PROMPT = (
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


@dataclass
class BfclResult:
    instance_id: str
    latency_seconds: float
    exit_status: str  # "ok" | "api_error" | "decode_error"
    correct: bool = False
    decoded_ok: bool = False
    output: str = ""
    error: str = ""
    per_call_seconds: list[float] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #

def bfcl_available() -> bool:
    return (BFCL_DATA_DIR / BFCL_PROMPT_FILE).exists() and (BFCL_DATA_DIR / BFCL_ANSWER_FILE).exists()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def load_bfcl_instances(settings: EvalSettings, role: str) -> list[dict[str, Any]]:
    prompts = _read_jsonl(BFCL_DATA_DIR / BFCL_PROMPT_FILE)
    answers = {row["id"]: row for row in _read_jsonl(BFCL_DATA_DIR / BFCL_ANSWER_FILE)}
    # Same deterministic fixed-seed sample as the SWE workload (sort for a stable
    # base order, then shuffle with sample_seed); public slice stays a subset.
    prompts.sort(key=lambda row: row["id"])
    random.Random(settings.sample_seed).shuffle(prompts)
    chosen = list(parse_slice(settings.bfcl_slice_for_role(role), len(prompts)))
    instances: list[dict[str, Any]] = []
    for index in chosen:
        row = prompts[index]
        answer = answers.get(row["id"])
        if answer is None:
            continue
        instances.append(
            {
                "id": row["id"],
                "question": row["question"],
                "function": row["function"],
                "ground_truth": answer["ground_truth"],
            }
        )
    return instances


def _build_messages(instance: dict[str, Any]) -> list[dict[str, str]]:
    functions_json = json.dumps(instance["function"], indent=4)
    system_content = _BFCL_SYSTEM_PROMPT + functions_json
    # ``question`` is a list of turns; the AST categories are single-turn.
    turns = list(instance["question"][0])
    messages: list[dict[str, str]] = [{"role": "system", "content": system_content}]
    for turn in turns:
        if turn.get("role") == "system":
            messages[0]["content"] = system_content + "\n\n" + turn.get("content", "")
        else:
            messages.append({"role": turn.get("role", "user"), "content": turn.get("content", "")})
    return messages


# --------------------------------------------------------------------------- #
# Answer decoding + AST checking (self-contained, faithful to BFCL ``simple``)
# --------------------------------------------------------------------------- #

def _literal(node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except Exception:
        try:
            return ast.unparse(node)
        except Exception:
            return None


def _resolve_call(node: ast.Call, param_order: list[str]) -> dict[str, dict[str, Any]]:
    func = node.func
    if isinstance(func, ast.Name):
        name = func.id
    elif isinstance(func, ast.Attribute):
        # underscore_to_dot is False for Llama; keep the dotted text as-is.
        try:
            name = ast.unparse(func)
        except Exception:
            name = func.attr
    else:
        name = ast.unparse(func) if hasattr(ast, "unparse") else "<call>"
    args: dict[str, Any] = {}
    for i, positional in enumerate(node.args):
        if i < len(param_order):
            args[param_order[i]] = _literal(positional)
    for kw in node.keywords:
        if kw.arg is not None:
            args[kw.arg] = _literal(kw.value)
    return {name: args}


def decode_calls(text: str, param_order: list[str]) -> list[dict[str, dict[str, Any]]]:
    """Decode a BFCL prompt-mode response ``[func(a=b, ...)]`` into call dicts.

    Mirrors ``bfcl_eval.model_handler.utils.default_decode_ast_prompting`` +
    ``ast_parse`` for the Python return format. Raises on non-call prose.
    """
    cleaned = text.strip("`\n ")
    if not cleaned.startswith("["):
        cleaned = "[" + cleaned
    if not cleaned.endswith("]"):
        cleaned = cleaned + "]"
    cleaned = cleaned.strip().strip("'")
    parsed = ast.parse(cleaned, mode="eval")
    body = parsed.body
    calls: list[dict[str, dict[str, Any]]] = []
    if isinstance(body, ast.Call):
        calls.append(_resolve_call(body, param_order))
    elif isinstance(body, (ast.List, ast.Tuple)):
        for elem in body.elts:
            if not isinstance(elem, ast.Call):
                raise ValueError("non-call element in function-call list")
            calls.append(_resolve_call(elem, param_order))
    else:
        raise ValueError("decoded output is not a function-call list")
    return calls


def _norm_scalar(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return value.strip().strip("'\"").casefold()
    if isinstance(value, (list, tuple)):
        return [_norm_scalar(v) for v in value]
    if isinstance(value, dict):
        return {str(k).casefold(): _norm_scalar(v) for k, v in value.items()}
    return value


def _value_matches(model_value: Any, accepted: list[Any]) -> bool:
    norm_model = _norm_scalar(model_value)
    for candidate in accepted:
        if candidate == "":
            continue  # "" marks an optional/omittable param, handled by the caller
        if _norm_scalar(candidate) == norm_model:
            return True
        # numeric/string cross-type leniency (e.g. model "5" vs gt 5)
        try:
            if isinstance(norm_model, float) and float(str(candidate)) == norm_model:
                return True
            if isinstance(_norm_scalar(candidate), float) and float(str(model_value)) == _norm_scalar(candidate):
                return True
        except Exception:
            pass
    return False


def check_simple(decoded: list[dict[str, dict[str, Any]]], ground_truth: list[dict[str, Any]]) -> bool:
    """AST-match for the ``simple`` category: exactly one call, name + args match."""
    if not decoded or len(decoded) != 1 or not ground_truth:
        return False
    gt_entry = ground_truth[0]
    (gt_func, gt_args), = gt_entry.items()
    if len(decoded[0]) != 1:
        return False
    (model_func, model_args), = decoded[0].items()
    if str(model_func).strip().casefold() != str(gt_func).strip().casefold():
        return False
    for arg, accepted in gt_args.items():
        if arg in model_args:
            if not _value_matches(model_args[arg], accepted):
                return False
        elif "" not in accepted:
            return False  # required arg missing
    for arg in model_args:
        if arg not in gt_args:
            return False  # hallucinated argument
    return True


def score_response(instance: dict[str, Any], text: str) -> tuple[bool, bool]:
    """Return (decoded_ok, correct) for one model response."""
    function = instance["function"]
    param_order: list[str] = []
    if function:
        props = function[0].get("parameters", {}).get("properties", {})
        param_order = list(props.keys())
    try:
        decoded = decode_calls(text, param_order)
    except Exception:
        return False, False
    try:
        return True, check_simple(decoded, instance["ground_truth"])
    except Exception:
        return True, False


# --------------------------------------------------------------------------- #
# Workload runner (mirrors agent_runner: client-side per-instance latency)
# --------------------------------------------------------------------------- #

def _openai_client(base_url: str):
    from openai import OpenAI

    return OpenAI(base_url=base_url, api_key="EMPTY", timeout=300.0)


def run_instance(instance: dict[str, Any], *, base_url: str, settings: EvalSettings) -> BfclResult:
    client = _openai_client(base_url)
    messages = _build_messages(instance)
    started = time.perf_counter()
    try:
        completion = client.chat.completions.create(
            model=settings.model,
            messages=messages,
            temperature=settings.temperature,
            max_tokens=settings.bfcl_max_tokens,
            seed=0,
            # Per-instance job id (single-turn here). Forwarded via vllm_xargs ->
            # sampling_params.extra_args["job_id"] for job-aware scheduling;
            # vanilla vLLM ignores it. Does not change generated tokens.
            extra_body={"vllm_xargs": {"job_id": str(instance["id"])}},
        )
    except Exception as exc:  # noqa: BLE001
        return BfclResult(
            instance_id=instance["id"],
            latency_seconds=time.perf_counter() - started,
            exit_status="api_error",
            error=type(exc).__name__,
        )
    latency = time.perf_counter() - started
    text = completion.choices[0].message.content or ""
    decoded_ok, correct = score_response(instance, text)
    return BfclResult(
        instance_id=instance["id"],
        latency_seconds=latency,
        exit_status="ok" if decoded_ok else "decode_error",
        correct=correct,
        decoded_ok=decoded_ok,
        output=text,
        per_call_seconds=[latency],
    )


def run_bfcl_workload(*, base_url: str, settings: EvalSettings, role: str) -> list[BfclResult]:
    instances = load_bfcl_instances(settings, role)
    results: list[BfclResult] = []
    lock = threading.Lock()

    def _record(result: BfclResult) -> None:
        with lock:
            results.append(result)

    def _run(instance: dict[str, Any]) -> None:
        try:
            result = run_instance(instance, base_url=base_url, settings=settings)
        except Exception as exc:  # noqa: BLE001 - never drop an instance silently
            result = BfclResult(
                instance_id=str(instance.get("id", "unknown")),
                latency_seconds=0.0,
                exit_status="api_error",
                error=type(exc).__name__,
            )
        _record(result)

    # Fire BFCL at HIGH concurrency rather than the SWE Poisson schedule. Short
    # single-turn requests under a low arrival rate never queue, so there is no
    # contention and the scheduler policy has nothing to act on (BFCL stayed
    # ~1.0x). A large worker pool submits many at once -> real queueing/batching
    # pressure -> scheduling differences become observable.
    with ThreadPoolExecutor(max_workers=max(1, settings.bfcl_workers)) as pool:
        list(pool.map(_run, instances))

    return results


# --------------------------------------------------------------------------- #
# Aggregators (shape matches what measure.py / scoring.py consume)
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
