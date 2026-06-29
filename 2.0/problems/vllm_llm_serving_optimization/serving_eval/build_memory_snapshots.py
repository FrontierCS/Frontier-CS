"""One-time bootstrap: bake the 5 per-scenario memory snapshots.

The BFCL ``memory`` query instances are answerable only against a memory state
built by that scenario's "prereq" conversations (the model is fed user turns that
contain the facts and is expected to store them via the memory tools). Running
that prereq agent live on every eval is wrong (huge latency, model-dependent and
non-deterministic state, breaks baseline-vs-patched comparability), so we run it
ONCE here against the target model and freeze the result into
``bfcl_data/memory_snapshots/<scenario>_final.json``. Commit those fixtures.

Usage (needs Modal + HF creds; serves the model on its own):
    python3 -m serving_eval.build_memory_snapshots [--gpu H100] [--scenarios customer,...]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from copy import deepcopy
from pathlib import Path

from . import bfcl
from .bfcl_vendor.memory_kv import MemoryAPI_kv
from .serving import ServingError, deploy_server, stop_server, wait_healthy
from .settings import EvalSettings

PREREQ_DIR = bfcl.BFCL_DATA_DIR / "memory_prereq_conversation"
SNAPSHOT_DIR = bfcl.BFCL_DATA_DIR / bfcl.MEMORY_SNAPSHOT_DIR

# The prereq agent is told to STORE, not just answer (the query system prompt
# tells it to retrieve). Same tool suite + scenario persona + live core dump.
_STORE_INSTRUCTION = (
    "{scenario_setting}\n\n"
    "You have a persistent key-value memory with a small always-visible Core "
    "Memory and a large Archival Memory. As the user shares information across "
    "this conversation, ACTIVELY STORE the important, durable facts so you can "
    "recall them in future sessions: use core_memory_add for the most important, "
    "frequently-needed facts (snake_case keys), and archival_memory_add for "
    "everything else worth keeping. Keep keys meaningful and unique. Only return "
    "function calls; when you have stored what matters for a message, stop.\n\n"
    "Here is the current content of your Core Memory:\n{memory_content}\n"
)


def _client(base_url):
    from openai import OpenAI

    return OpenAI(base_url=base_url, api_key="EMPTY", timeout=300.0)


def _run_prereq_for_scenario(scenario: str, *, base_url: str, settings: EvalSettings,
                             max_steps_per_turn: int = 8) -> dict:
    entries = bfcl._read_jsonl(PREREQ_DIR / f"memory_{scenario}.json")
    # Order by the trailing numeric index (memory_prereq_<n>-...).
    entries.sort(key=lambda e: int(str(e["id"]).split("_prereq_")[1].split("-")[0]))
    tools_json = json.dumps(bfcl.load_memory_tools(), indent=4)
    persona = bfcl.MEMORY_AGENT_SETTINGS.get(scenario, "")
    api = MemoryAPI_kv()  # persists across all entries of this scenario
    client = _client(base_url)

    for entry in entries:
        system = (
            bfcl._FUNC_CALLING_SYSPROMPT + tools_json + "\n\n"
            + _STORE_INSTRUCTION.format(scenario_setting=persona,
                                        memory_content=api._dump_core_memory_to_context())
        )
        messages = [{"role": "system", "content": system}]
        for turn in entry["question"]:
            messages.append({"role": turn[0].get("role", "user"), "content": turn[0].get("content", "")})
            steps = 0
            nudged = False
            while True:
                try:
                    text = client.chat.completions.create(
                        model=settings.model, messages=messages,
                        temperature=settings.temperature, max_tokens=settings.bfcl_max_tokens, seed=0,
                    ).choices[0].message.content or ""
                except Exception as exc:  # noqa: BLE001
                    print(f"  [{scenario}] api_error on a prereq turn: {type(exc).__name__}", flush=True)
                    break
                try:
                    calls = bfcl.decode_tool_calls(text)
                except Exception:
                    messages.append({"role": "assistant", "content": text})
                    # Some note-style turns make the model acknowledge in prose
                    # instead of emitting store calls. Nudge once to force
                    # function-call-only output before giving up on the turn.
                    if not nudged and steps == 0:
                        nudged = True
                        messages.append({"role": "user", "content": (
                            "Respond with ONLY function call(s) that STORE the durable "
                            "facts from my previous message, e.g. [core_memory_add("
                            "key='...', value='...'), archival_memory_add(content='...')]. "
                            "No prose.")})
                        continue
                    break  # model finished storing for this user turn
                results = [bfcl._execute_one(api, n, kw) for n, kw in calls]
                messages.append({"role": "assistant", "content": text})
                messages.append({"role": "user", "content": repr(
                    [{"role": "tool", "name": n, "content": str(r)} for (n, _), r in zip(calls, results)])})
                steps += 1
                if steps >= max_steps_per_turn:
                    break
        print(f"  [{scenario}] entry {entry['id']} done | core={len(api.core_memory)} archival={len(api.archival_memory)}", flush=True)
    return {"core_memory": api.core_memory, "archival_memory": api.archival_memory}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gpu", default="H100")  # single card is plenty for bootstrapping
    ap.add_argument("--scenarios", default=",".join(bfcl.SCENARIOS))
    ap.add_argument("--clean-source", default="/tmp/vllm-clean")
    args = ap.parse_args(argv)
    scenarios = [s for s in args.scenarios.split(",") if s]

    settings = EvalSettings()
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    app = f"vllm-memory-bootstrap-{int(time.time()) % 100000}"
    print(f"[{time.strftime('%H:%M:%S')}] deploying {settings.model} on {args.gpu} for bootstrap...", flush=True)
    handle = deploy_server(src_path=args.clean_source, model=settings.model, gpu=args.gpu,
                           app_name=app, label=app, scaledown_seconds=600,
                           startup_timeout_seconds=2400, build_timeout_seconds=5400, deploy_retries=2)
    try:
        wait_healthy(handle, model=settings.model, timeout_seconds=2700)
        print(f"[{time.strftime('%H:%M:%S')}] healthy at {handle.base_url}", flush=True)
        for scenario in scenarios:
            t0 = time.time()
            print(f"[{time.strftime('%H:%M:%S')}] baking '{scenario}'...", flush=True)
            snap = _run_prereq_for_scenario(scenario, base_url=handle.base_url, settings=settings)
            out = SNAPSHOT_DIR / f"{scenario}_final.json"
            out.write_text(json.dumps(snap, indent=2), encoding="utf-8")
            print(f"[{time.strftime('%H:%M:%S')}] '{scenario}' -> {out.name} "
                  f"(core={len(snap['core_memory'])}, archival={len(snap['archival_memory'])}) in {time.time()-t0:.0f}s", flush=True)
    finally:
        stop_server(app)
        print(f"[{time.strftime('%H:%M:%S')}] stopped {app}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
