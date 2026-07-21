"""Submission policy: static allow/deny gate for the submitted model.py.

Torch-free and unit-tested on CPU. Treat submission content as adversarial
(2.0 black-box safety). This is the *static* layer; runtime guards that the
scan cannot see (trained-from-scratch check, judge-owned loss, resource caps)
live in the runner/evaluator. See DESIGN.md §6–§7.
"""

from __future__ import annotations

from dataclasses import dataclass

MAX_BYTES = 256 * 1024  # 256 KB

# Substrings that must not appear in the submitted source. Deliberately broad;
# a legitimate architecture never needs any of these.
POLICY_DENY_TOKENS: tuple[str, ...] = (
    # --- escape / environment / network leakage ---
    "os.environ", "os.getenv", "getenv", "putenv",
    "subprocess", "socket", "requests", "urllib", "httpx", "http.client",
    "FRONTIER_", "JUDGE_", "HARBOR_", "MODAL_", "HF_TOKEN",
    "/judge", "/opt/", "/tests/",
    # --- pretrained-weight loading (must train from scratch) ---
    "from_pretrained", "torch.load", "load_state_dict", "safetensors",
    "hf_hub", "huggingface", "timm.create_model", "AutoModel",
    # --- filesystem reads (no data/weight/val access) ---
    "open(", "Path(", "np.load", "numpy.load", "np.fromfile", "mmap",
    "pickle.load", "joblib.load",
    # NOTE: metric/data names are NOT here -- see POLICY_DENY_TOKENS_CODE.
    # --- timer / control-flow short-circuits & concurrency tricks ---
    "time.time", "time.perf_counter", "perf_counter", "time.sleep",
    "while True", "threading", "multiprocessing", "os.fork", "ctypes",
    "exec(", "__import__",
    # NOTE: "eval(" and "compile(" are intentionally NOT banned so that the
    # legitimate `model.eval()` and `torch.compile()` idioms are allowed
    # (mirrors nanowm's allowlist). Sandboxing + judge-owned loss cover the rest.
)


# Scanned over CODE ONLY (comments and string literals stripped).
#
# These names exist to stop a submission from READING the metric or the held-out
# data, which takes executable code. Scanning them over prose rejected any
# submission that merely *documented its intent* -- "# should improve val_bpb"
# -- with a confusing "forbidden token" error. Both the reference and the locked
# baseline tripped it once their docstrings explained the task, which is how it
# was found. A submission should be able to say what it optimizes.
#
# Everything in POLICY_DENY_TOKENS above is still scanned over the FULL source:
# a judge path or an env var appearing in a comment is a leak signal in itself,
# whereas the word "perplexity" in a docstring reads nothing.
POLICY_DENY_TOKENS_CODE: tuple[str, ...] = (
    "val_ppl", "perplexity", "val_bpb", "bits_per_byte",
    "holdout", "hold_out", "val_data", "val.bin", "validation_bytes",
)


def _code_only(source: str) -> str:
    """Return `source` with comments and string literals removed.

    Fails CLOSED: if the source will not tokenize, return it unchanged so the
    scan still sees everything rather than waving a malformed file through.
    """
    import io
    import tokenize

    try:
        out, last = [], (1, 0)
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            (srow, scol), (erow, ecol) = tok.start, tok.end
            if srow != last[0]:
                out.append("\n")
                last = (srow, 0)
            out.append(" " * max(0, scol - last[1]))
            out.append(tok.string)
            last = (erow, ecol)
        return "".join(out)
    except Exception:
        return source


@dataclass
class PolicyResult:
    ok: bool
    reason: str = ""


def check_source(source: str, *, size_bytes: int | None = None) -> PolicyResult:
    """Validate submitted model.py source text against the static policy."""
    if size_bytes is None:
        size_bytes = len(source.encode("utf-8", errors="replace"))
    if size_bytes > MAX_BYTES:
        return PolicyResult(False, f"submission exceeds {MAX_BYTES} bytes")
    if not source.strip():
        return PolicyResult(False, "submission is empty")

    for tok in POLICY_DENY_TOKENS:
        if tok in source:
            return PolicyResult(False, f"forbidden token in submission: {tok!r}")

    # Metric/data names: code only, so docstrings and comments may name the
    # metric the submission is trying to improve.
    code = _code_only(source)
    for tok in POLICY_DENY_TOKENS_CODE:
        if tok in code:
            return PolicyResult(False, f"forbidden token in submission code: {tok!r}")

    # Must expose a model factory the harness can call.
    if ("def build_model" not in source) and ("class NanoSLM" not in source):
        return PolicyResult(
            False, "submission must define build_model(config) or class NanoSLM"
        )
    return PolicyResult(True, "policy ok")


def check_file(path: str) -> PolicyResult:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            source = fh.read()
    except OSError as exc:  # pragma: no cover - defensive
        return PolicyResult(False, f"cannot read submission: {exc.__class__.__name__}")
    return check_source(source)
