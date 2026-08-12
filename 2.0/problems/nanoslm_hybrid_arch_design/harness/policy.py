"""Submission policy: static allow/deny gate for the submitted model.py.

Torch-free and unit-tested on CPU. Treat submission content as adversarial
(2.0 black-box safety). This is the *static* layer; runtime guards that the
scan cannot see (trained-from-scratch check, judge-owned loss, resource caps,
the bits-per-byte plausibility floor) live in the runner/evaluator.

Three layers, applied in order, each fails closed:

  1. Substring denylist over the full source (below). Catches dangerous words
     in ANY spelling that contains them -- including comments, where a judge
     path or an env var is a leak signal in itself.
  2. Metric/data-name denylist over code only (comments/strings stripped), so
     a submission may *document* what it optimizes without tripping the gate.
  3. AST scan with a STRICT IMPORT ALLOWLIST. The substring layer alone is
     evadable by construction -- ``getattr(os, 'envi' + 'ron')`` contains no
     denied token -- so the AST layer removes the primitives such evasion
     needs: only allowlisted module roots may be imported, and the
     dynamic-access builtins (bare ``eval``/``exec``/``getattr``/
     ``__import__``/``open``/...), dunder attributes (``__class__`` and
     friends are the classic sandbox-escape route), wildcard imports, and
     raw-file-reader attribute names (``fromfile``, ``from_file``,
     ``memmap``, ...) are rejected wherever they appear. ``model.eval()`` and
     ``torch.compile(...)`` are attribute accesses, not bare names, and remain
     allowed.

Static scanning of Turing-complete code is defense in depth, not proof; the
runtime plausibility floor (runner.run_arm) backstops it by rejecting any
result too good to be honest.
"""

from __future__ import annotations

import ast

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
    # Note: metric/data names are not here -- see POLICY_DENY_TOKENS_CODE.
    # --- timer / control-flow short-circuits & concurrency tricks ---
    "time.time", "time.perf_counter", "perf_counter", "time.sleep",
    "while True", "threading", "multiprocessing", "os.fork", "ctypes",
    "exec(", "__import__",
    # Note: "eval(" and "compile(" are intentionally not banned so that the
    # legitimate `model.eval()` and `torch.compile()` idioms are allowed
    # (mirrors nanowm's allowlist). Sandboxing + judge-owned loss cover the rest.
)


# Scanned over code only (comments and string literals stripped).
#
# These names exist to stop a submission from reading the metric or the held-out
# data, which takes executable code. Scanning them over prose rejected any
# submission that merely *documented its intent* -- "# should improve val_bpb"
# -- with a confusing "forbidden token" error. Both the reference and the locked
# baseline tripped it once their docstrings explained the task, which is how it
# was found. A submission should be able to say what it optimizes.
#
# Everything in POLICY_DENY_TOKENS above is still scanned over the full source:
# a judge path or an env var appearing in a comment is a leak signal in itself,
# whereas the word "perplexity" in a docstring reads nothing.
POLICY_DENY_TOKENS_CODE: tuple[str, ...] = (
    "val_ppl", "perplexity", "val_bpb", "bits_per_byte",
    "holdout", "hold_out", "val_data", "val.bin", "validation_bytes",
)


# --------------------------------------------------------------------------- #
# AST layer: strict import allowlist + dynamic-access primitives.
# --------------------------------------------------------------------------- #

# Module ROOTS a submission may import. Everything a legitimate architecture
# needs, nothing that touches the filesystem, the environment, processes or
# the network:
#   * torch / numpy / fla / einops / triton -- the modelling stack the Modal
#     image ships (einops is an fla dependency; triton is allowed because a
#     custom fused kernel is a legitimate architecture lever in this task --
#     fla itself exists for exactly that reason).
#   * a handful of pure-computation stdlib modules. `operator` is deliberately
#     absent: `operator.attrgetter("...")` is getattr-by-string, the exact
#     primitive the banned-names rule below removes. `os`/`sys`/`io`/
#     `pathlib`/`importlib`/... are absent for the obvious reasons;
#     `transformers` is absent because from_pretrained is a network/weights
#     path (train-from-scratch rule).
POLICY_ALLOWED_IMPORT_ROOTS: frozenset = frozenset({
    "__future__", "abc", "collections", "contextlib", "copy", "dataclasses",
    "enum", "functools", "itertools", "math", "typing", "warnings",
    "torch", "numpy", "fla", "einops", "triton",
})

# Bare names whose *appearance* (any context -- call, alias, argument) is
# rejected. These are the primitives that turn computed strings into imports,
# attribute walks, or file reads; without them, string concatenation has no
# sink. `eval`/`compile` here are the BARE builtins: `model.eval()` and
# `torch.compile()` are Attribute nodes and unaffected.
POLICY_BANNED_NAMES: frozenset = frozenset({
    "eval", "exec", "compile", "__import__", "getattr", "setattr", "delattr",
    "vars", "globals", "locals", "open", "input", "breakpoint", "exit",
    "quit", "__builtins__", "__loader__", "__spec__",
})

# Attribute / submodule names rejected wherever they appear -- as an attribute
# access (aliasing a module defeats substring checks: `q = numpy;
# q.fromfile(...)`), as a dotted-path segment in an import, or as a name
# imported via `from X import Y` (`from torch import load` would create a
# BARE `load` that no substring catches). Raw-binary readers and
# process/env/compiler escape hatches reachable through the allowlisted
# roots:
#   fromfile/from_file/memmap/open_memmap/... -- the readers that can open
#     val.bin's raw uint32 stream. (np.load/torch.load stay usable on paper
#     but require npy/pickle magic that a raw stream does not have, and the
#     literal spellings are substring-denied above.)
#   ctypeslib/f2py/distutils/cpp_extension/load_library -- compile-or-load-
#     native-code paths inside numpy/torch.
#   hub -- torch.hub downloads code and weights.
#   os/sys/environ/popen/system -- e.g. `torch.os` re-exports the os module.
POLICY_BANNED_ATTRS: frozenset = frozenset({
    "os", "sys", "environ", "popen", "system",
    "fromfile", "from_file", "tofile", "memmap", "open_memmap",
    "loadtxt", "genfromtxt", "fromregex", "DataSource",
    "ctypeslib", "f2py", "distutils", "cpp_extension", "load_library",
    "hub", "attrgetter",
})

# `from X import Y` names additionally rejected: importing these unqualified
# strips the module prefix every substring rule keys on.
_BANNED_IMPORT_NAMES: frozenset = POLICY_BANNED_ATTRS | {"load", "loads"}

# Dunder attributes allowed as Attribute access. Everything else dunder is
# rejected: `__class__`/`__globals__`/`__subclasses__`/`__dict__` are the
# standard object-graph escape routes. `__init__` is required by
# `super().__init__()`; `__version__` and `__name__` (the
# `type(exc).__name__` error-message idiom) are harmless strings that
# traverse nothing.
_ALLOWED_DUNDER_ATTRS: frozenset = frozenset(
    {"__init__", "__version__", "__name__"}
)


def _check_ast(source: str) -> str:
    """Return "" if the AST rules pass, else the (public) rejection reason."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return f"submission does not parse (line {exc.lineno})"

    def _module_path_ok(path: str) -> str:
        parts = path.split(".")
        if parts[0] not in POLICY_ALLOWED_IMPORT_ROOTS:
            return f"import of {parts[0]!r} is not in the import allowlist"
        for seg in parts[1:]:
            if seg in POLICY_BANNED_ATTRS:
                return f"import path segment {seg!r} is not allowed"
        return ""

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                why = _module_path_ok(alias.name)
                if why:
                    return why
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                return "relative imports are not allowed"
            why = _module_path_ok(node.module or "")
            if why:
                return why
            for alias in node.names:
                if alias.name == "*":
                    return "wildcard imports are not allowed"
                if alias.name in _BANNED_IMPORT_NAMES:
                    return f"importing the name {alias.name!r} is not allowed"
                if (alias.name.startswith("__") and alias.name.endswith("__")
                        and alias.name not in _ALLOWED_DUNDER_ATTRS):
                    return f"importing the name {alias.name!r} is not allowed"
        elif isinstance(node, ast.Name):
            if node.id in POLICY_BANNED_NAMES:
                return f"use of the name {node.id!r} is not allowed"
        elif isinstance(node, ast.Attribute):
            if node.attr in POLICY_BANNED_ATTRS:
                return f"attribute {node.attr!r} is not allowed"
            if (node.attr.startswith("__") and node.attr.endswith("__")
                    and node.attr not in _ALLOWED_DUNDER_ATTRS):
                return f"dunder attribute {node.attr!r} is not allowed"
    return ""


def _code_only(source: str) -> str:
    """Return `source` with comments and string literals removed.

    Fails closed: if the source will not tokenize, return it unchanged so the
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

    # AST layer: strict import allowlist + dynamic-access primitives.
    why = _check_ast(source)
    if why:
        return PolicyResult(False, why)

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
