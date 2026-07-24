"""Evaluator for nanoslm_hybrid_arch_design (Frontier-CS 2.0).

Contract: ``evaluate(solution_path) -> (score, score_unbounded, message, metrics)``.
The submission is a single ``model.py`` (full architecture freedom). The judge
trains it from scratch for a fixed wall-clock budget on a single H100 and scores
held-out validation perplexity against a locked baseline architecture trained
under the identical budget.

Top-level imports are torch-free so this module loads (and self-tests) without a
GPU; the training/eval path is lazy-imported inside :func:`evaluate`.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import traceback
from pathlib import Path

# Torch-free harness layers (safe to import anywhere).
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from harness import policy, scoring, settings  # noqa: E402

# cuBLAS determinism must be configured before the first CUDA call, which means
# before torch is imported anywhere. This module's top-level imports are
# deliberately torch-free (see the docstring), so setting it here is early
# enough on every path -- Modal, judge container, or a local GPU box.
#
# TaskConfig has carried `cublas_workspace_config` (CUBLAS_WORKSPACE_CONFIG=
# :4096:8) since the problem was written, as part of the determinism story, but
# nothing read it. So every run so far had
# torch.use_deterministic_algorithms(True) set while cuBLAS remained free to be
# non-deterministic -- which showed up as a UserWarning in the first GPU run and
# quietly weakened the CRN pairing the score depends on.
# `setdefault`, so an operator can still override from outside.
os.environ.setdefault(
    "CUBLAS_WORKSPACE_CONFIG", settings.DEFAULT.cublas_workspace_config
)


def _protect_evaluator_source() -> None:
    """Hide evaluator source from unprivileged submitted code in containers."""
    try:
        p = Path(__file__).resolve()
        if str(p).startswith(("/judge/", "/tests/")) and os.geteuid() == 0:
            p.chmod(0o600)
    except Exception:
        pass


_protect_evaluator_source()


def _backend() -> str:
    """MODAL (CPU judge -> Modal GPU) or local (directly-attached GPU).

    The design specifies a CPU judge with the H100 served on Modal, the same
    shape as nanowm_rollout_* and vllm_llm_serving_optimization -- but until
    now nothing implemented it: `evaluate()` only called `_select_device()`,
    which in a CPU-only judge container returns "cpu" and would try to train a
    ~190M model at ctx 8192 on CPU. Harbor invokes this module, not the manual
    `modal_app.evaluate_remote` wrapper, so without this the problem is not
    runnable under Harbor at all.

    Explicit env wins so either path can be forced in testing; otherwise a
    Modal token implies Modal, and a local CUDA device implies local.
    """
    b = os.environ.get("FRONTIER_NANOSLM_BACKEND", "").strip().lower()
    if b in ("modal", "local"):
        return b
    if os.environ.get("MODAL_TOKEN_ID") or os.environ.get("MODAL_TOKEN_SECRET"):
        return "modal"
    return "local"


def _run_pair_modal(solution_path: str, role: str):
    """Run both arms on a Modal GPU; score judge-side.

    Only arm metrics cross the boundary -- scoring stays in the judge, so a
    GPU worker never hands back a score the judge did not compute.
    """
    from harness.modal_app import app, run_pair_remote

    source = Path(solution_path).read_text(encoding="utf-8", errors="replace")
    with app.run():
        res = run_pair_remote.remote(solution_source=source, role=role)
    return res


def _select_device() -> str:
    try:
        import torch
    except Exception as exc:  # torch not installed (dev box)
        raise RuntimeError(f"torch unavailable: {type(exc).__name__}")
    return "cuda" if torch.cuda.is_available() else "cpu"


def _role() -> str:
    """'agent' (cheap iterative feedback, cached baseline) or 'final' (fresh CRN)."""
    r = os.environ.get("FRONTIER_NANOSLM_ROLE", "final").strip().lower()
    return "agent" if r == "agent" else "final"


def _baseline_cache_file(cfg) -> str:
    return os.environ.get("FRONTIER_NANOSLM_BASELINE_CACHE", cfg.baseline_cache_path)


def _baseline_cache_get(cfg, fingerprint: str):
    """Return cached baseline perplexity for this fingerprint, or None."""
    try:
        with open(_baseline_cache_file(cfg), "r", encoding="utf-8") as fh:
            return float(json.load(fh).get(fingerprint))
    except Exception:
        return None


def _baseline_cache_put(cfg, fingerprint: str, ppl: float) -> None:
    """Best-effort write of the baseline perplexity (path may be read-only)."""
    path = _baseline_cache_file(cfg)
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            data = {}
        data[fingerprint] = ppl
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
    except Exception:
        pass


def _load_submission_module(path: str):
    """Import the submitted model.py after the static policy gate has passed."""
    spec = importlib.util.spec_from_file_location("submission_model", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load submission module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evaluate(solution_path: str):
    cfg = settings.active_config()
    fp = settings.config_fingerprint(cfg)

    # 1) Static policy gate (torch-free, adversarial-safe).
    pol = policy.check_file(solution_path)
    if not pol.ok:
        return (scoring.FAILURE_SCORE, scoring.FAILURE_SCORE,
                f"policy_rejected: {pol.reason}", {"config_fingerprint": fp})

    # 2) Backend. On MODAL the judge never imports torch -- the arms run in a
    #    Modal GPU container and only plain metrics come back.
    role = _role()
    if _backend() == "modal":
        try:
            res = _run_pair_modal(solution_path, role)
        except Exception as exc:  # noqa: BLE001 - classify, never leak
            return (scoring.FAILURE_SCORE, scoring.FAILURE_SCORE,
                    f"environment_error: modal dispatch failed "
                    f"({type(exc).__name__})", {"config_fingerprint": fp})
        # Guard rejections travel as a field, not an exception: GuardError is
        # defined in harness.runner (which imports torch), so this CPU-only
        # judge could not deserialize the raised form. The message is the
        # public, classified reason -- same wording as the local path's.
        if res.get("guard_error"):
            return scoring.FAILURE_SCORE, scoring.FAILURE_SCORE, f"guard: {res['guard_error']}", {
                "config_fingerprint": fp, "role": role,
                "stack": res.get("stack"),
            }
        b, c = res["baseline"], res["submission"]
        sr = scoring.score_from_bpb(b["val_bpb"], c["val_bpb"])
        note = []
        if role == "agent":
            # Mirrors the local path's note: says whether this feedback run
            # paid ~T (cached baseline) or ~2T (fresh pair, cache populated).
            note.append("iterative(cached-baseline)"
                        if res.get("baseline_cached") else "iterative")
        message = scoring.format_message(
            b["val_bpb"], c["val_bpb"], sr,
            steps=c["steps"], wall_seconds=c["wall_seconds"],
            extra=",".join(note),
        )
        return sr.score, sr.score_unbounded, message, {
            "base_val_bpb": b["val_bpb"], "sub_val_bpb": c["val_bpb"],
            "abs_bpb_delta": sr.abs_bpb_delta, "sub_val_ppl": c["val_ppl"],
            # abs_bpb_delta is the scored quantity; rel_improvement is kept
            # alongside it so an operator never has to recompute it.
            "rel_improvement": sr.rel_improvement,
            "sub_steps": c["steps"], "base_steps": b["steps"],
            "sub_params": c["n_params"], "sub_wall_seconds": c["wall_seconds"],
            "sub_train_block_size": c.get("train_block_size"),
            "base_train_block_size": b.get("train_block_size"),
            "eval_block_size": cfg.eval_block_size,
            "role": role, "device": "modal:H100",
            "config_fingerprint": fp, "stack": res.get("stack"),
        }

    # Local backend: torch + a directly-attached GPU.
    try:
        device = _select_device()
    except RuntimeError as exc:
        return (
            scoring.FAILURE_SCORE,
            scoring.FAILURE_SCORE,
            f"environment_error: {exc} (training path requires torch + GPU)",
            {"config_fingerprint": fp},
        )

    # 3) Train + eval; score perplexity vs the locked baseline.
    #    agent role: train submission only (~T), reuse fingerprint-cached baseline.
    #    final role: fresh baseline+submission CRN pair (~2T) — authoritative.
    try:
        from harness import runner  # lazy: imports torch
        from harness.data import TokenData

        module = _load_submission_module(solution_path)

        if role == "agent":
            data = TokenData(cfg)
            # Range-guarded before anything expensive runs.
            sub_block = runner.resolve_train_block_size(module, cfg)
            base_bpb = _baseline_cache_get(cfg, fp)
            base_steps = None
            if base_bpb is None:
                base_arm = runner.run_arm(
                    runner.baseline_factory(), data, cfg, device,
                    runner.baseline_block_size(cfg),
                )
                base_bpb = base_arm.val_bpb
                base_steps = base_arm.steps
                _baseline_cache_put(cfg, fp, base_bpb)
            sub = runner.run_arm(
                runner.load_factory(module), data, cfg, device, sub_block
            )
        else:
            base_arm, sub = runner.run_pair(module, cfg, device)
            base_bpb = base_arm.val_bpb
            base_steps = base_arm.steps
    except Exception as exc:
        from harness.runner import GuardError

        if isinstance(exc, GuardError):
            return (scoring.FAILURE_SCORE, scoring.FAILURE_SCORE,
                    f"guard: {exc}", {"config_fingerprint": fp, "role": role})
        # Never leak submission tracebacks/stdout (2.0 black-box safety).
        return (
            scoring.FAILURE_SCORE,
            scoring.FAILURE_SCORE,
            f"submission_error: {type(exc).__name__}",
            {"config_fingerprint": fp, "role": role},
        )

    sr = scoring.score_from_bpb(base_bpb, sub.val_bpb)
    note = []
    if role == "agent":
        note.append("iterative(cached-baseline)" if base_steps is None else "iterative")
    message = scoring.format_message(
        base_bpb,
        sub.val_bpb,
        sr,
        steps=sub.steps,
        wall_seconds=sub.wall_seconds,
        extra=",".join(note),
    )
    metrics = {
        "base_val_bpb": base_bpb,
        "sub_val_bpb": sub.val_bpb,
        "abs_bpb_delta": sr.abs_bpb_delta,
        "sub_val_ppl": sub.val_ppl,   # derived, readability only
        "rel_improvement": sr.rel_improvement,
        "sub_steps": sub.steps,
        "base_steps": base_steps,
        "sub_params": sub.n_params,
        "sub_wall_seconds": sub.wall_seconds,
        # Agent-controlled training context vs the fixed scoring window, both
        # reported so a submission can see the steps-vs-extrapolation trade it
        # actually made rather than inferring it.
        "sub_train_block_size": sub.train_block_size,
        "eval_block_size": cfg.eval_block_size,
        "role": role,
        "device": device,
        "config_fingerprint": fp,
    }
    return sr.score, sr.score_unbounded, message, metrics


def prepare() -> dict:
    """Warm assets + cache the baseline perplexity for the iterative feedback path.

    Best-effort: if torch/GPU is unavailable (dev box) we still return the
    fingerprint so the judge readiness log is meaningful.
    """
    cfg = settings.active_config()
    info = {"config_fingerprint": settings.config_fingerprint(cfg)}
    try:
        device = _select_device()
        from harness import runner
        from harness.data import TokenData

        data = TokenData(cfg)
        base = runner.run_arm(
            runner.baseline_factory(), data, cfg, device,
            runner.baseline_block_size(cfg),
        )
        info["base_val_bpb"] = base.val_bpb
        info["base_steps"] = base.steps
        info["device"] = device
        _baseline_cache_put(cfg, info["config_fingerprint"], base.val_bpb)
        info["baseline_cached"] = True
    except Exception as exc:
        info["warm_skipped"] = f"{type(exc).__name__}"
    return info


# --------------------------------------------------------------------------- #
# Torch-free self-test: exercises policy + scoring + fingerprint without a GPU.
# --------------------------------------------------------------------------- #
def _write_selftest_bin(dirpath: str, name: str, vocab_size: int, n: int, seed: int) -> str:
    """Write a tiny real uint32 token stream for the self-test.

    The harness has no synthetic fallback, so the self-test manufactures its own
    small real corpus (in-range ids, on disk) rather than relying on the loader
    to fabricate one -- the same load path the judge uses, just tiny.
    """
    import numpy as _np

    rng = _np.random.default_rng(seed)
    arr = rng.integers(0, vocab_size, size=n).astype(_np.uint32)
    path = os.path.join(dirpath, name)
    arr.tofile(path)
    return path


def _selftest() -> int:
    ok = True

    def check(name, cond):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"[{'pass' if cond else 'fail'}] {name}", file=sys.stderr)

    # --- policy: accept reference + baseline, reject malicious variants ---
    ref_src = (_HERE / "reference.py").read_text()
    base_src = (_HERE / "harness" / "baseline_model.py").read_text()
    check("policy accepts reference.py", policy.check_source(ref_src).ok)
    check("policy accepts baseline_model.py", policy.check_source(base_src).ok)

    malicious = {
        "env leak": "import os\ndef build_model(c):\n x=os.environ['HF_TOKEN']\n class NanoSLM: pass\n",
        "torch.load": "def build_model(c):\n import torch; torch.load('/opt/x'); return None\n",
        "timer peek": "import time\ndef build_model(c):\n time.time()\n class NanoSLM: pass\n",
        "metric peek": "def build_model(c):\n val_ppl=1.0\n class NanoSLM: pass\n",
        "no factory": "x = 1\n",
        "empty": "   ",
    }
    for name, src in malicious.items():
        check(f"policy rejects {name}", not policy.check_source(src).ok)

    # AST layer: substring evasions that motivated the strict allowlist. None
    # of these contain a denied substring; all must die on the AST rules.
    evasive = {
        "import os (allowlist)": "import os\nclass NanoSLM: pass\n",
        "bare getattr": "import torch\ng = getattr\nclass NanoSLM: pass\n",
        "bare eval": "class NanoSLM: pass\ndef build_model(c):\n return eval('1')\n",
        "dunder walk": "class NanoSLM: pass\ndef build_model(c):\n return ().__class__\n",
        "aliased fromfile": "import numpy as q\nclass NanoSLM: pass\ndef build_model(c):\n return q.fromfile('x')\n",
        "from-import load": "from torch import load\nclass NanoSLM: pass\n",
        "wildcard import": "from torch import *\nclass NanoSLM: pass\n",
        "relative import": "from . import secrets\nclass NanoSLM: pass\n",
        "banned import segment (torch.hub)": "import torch.hub as h\nclass NanoSLM: pass\n",
        "operator (attrgetter-by-string)": "import operator\nclass NanoSLM: pass\n",
        "unparseable source": "def build_model(:\n",
    }
    for name, src in evasive.items():
        check(f"policy rejects {name}", not policy.check_source(src).ok)

    # legitimate idioms must survive
    check(
        "policy allows model.eval()/torch.compile()",
        policy.check_source(
            "class NanoSLM:\n def forward(self,x):\n  self.eval(); return x\n"
        ).ok,
    )
    check(
        "policy allows super().__init__ / torch.__version__ / triton",
        policy.check_source(
            "import torch\nimport triton\nimport triton.language as tl\n"
            "class NanoSLM(torch.nn.Module):\n"
            " def __init__(self):\n"
            "  super().__init__()\n"
            "  self.v = torch.__version__\n"
        ).ok,
    )

    # --- scoring: the score IS the submission's raw val_bpb, lower is better ---
    base_bpb = 4.0
    s_tie = scoring.score_from_bpb(base_bpb, base_bpb)
    s_worse = scoring.score_from_bpb(base_bpb, base_bpb + 0.10)
    s_better = scoring.score_from_bpb(base_bpb, base_bpb - 0.05)
    check("score is exactly the submission's val_bpb",
          abs(s_better.score - (base_bpb - 0.05)) < 1e-12
          and abs(s_tie.score - base_bpb) < 1e-12
          and abs(s_worse.score - (base_bpb + 0.10)) < 1e-12)
    check("score is unscaled and un-clipped (no [0,100] mapping)",
          abs(s_worse.score - s_worse.score_unbounded) < 1e-12
          and 0.0 < s_better.score < 100.0 / 25.0)  # a bpb, not a percentage
    check("lower is better (worse model -> higher score value)",
          s_worse.score > s_tie.score > s_better.score)
    check("degenerate bpb maps to the failure sentinel, never a good score",
          scoring.score_from_bpb(base_bpb, 0.0).score == scoring.FAILURE_SCORE
          and scoring.score_from_bpb(base_bpb, float("inf")).score
          == scoring.FAILURE_SCORE)
    # The baseline comparison is still reported alongside, for context only.
    check("gain figures still reported",
          abs(s_better.abs_bpb_delta - 0.05) < 1e-12
          and abs(s_better.rel_improvement - (0.05 / base_bpb)) < 1e-12)
    check("legacy scoring constants stay out of the fingerprint",
          "bpb_score_scale" not in settings._FINGERPRINT_KEYS
          and "r_target" not in settings._FINGERPRINT_KEYS)
    # Same for the plausibility floor (a guard constant), which must exist and
    # sit far below any honest result at this scale.
    check("min_plausible_bpb set, sane, and not fingerprinted",
          0.0 < settings.DEFAULT.min_plausible_bpb <= 0.5
          and "min_plausible_bpb" not in settings._FINGERPRINT_KEYS)

    # --- fingerprint: stable, and changes iff a locked knob changes ---
    from dataclasses import replace

    fp0 = settings.config_fingerprint(settings.DEFAULT)
    fp_same = settings.config_fingerprint(settings.DEFAULT)
    fp_diff = settings.config_fingerprint(replace(settings.DEFAULT, learning_rate=1e-3))
    check("fingerprint stable", fp0 == fp_same)
    check("fingerprint changes on locked-knob change", fp0 != fp_diff)

    # The eval window is fingerprinted (changing it changes what val_bpb means,
    # so a cached baseline must not be reused) ...
    check(
        "fingerprint changes on eval_block_size change",
        fp0 != settings.config_fingerprint(
            replace(settings.DEFAULT, eval_block_size=4096)
        ),
    )
    # ... while the training context is not. It varies per submission now, so
    # fingerprinting it would give every submission a unique key and the cached
    # baseline would never hit -- doubling the cost of the agent-role path.
    check(
        "fingerprint ignores the default training block_size",
        fp0 == settings.config_fingerprint(
            replace(settings.DEFAULT, block_size=2048)
        ),
    )

    # --- agent-controlled training context: resolution + bounds ---
    # Imported lazily: harness.runner pulls in torch, which the CPU dev box and
    # the CPU judge container may not have. The selftest must still run there,
    # so an absent torch skips these rather than failing them.
    try:
        from harness import runner as _runner
    except Exception as exc:  # pragma: no cover - torch-free host
        print(f"[SKIP] BLOCK_SIZE checks ({type(exc).__name__})", file=sys.stderr)
        _runner = None

    if _runner is not None:
        import types

        cfg = settings.DEFAULT

        def _mod(**attrs):
            m = types.ModuleType("sub")
            for k, v in attrs.items():
                setattr(m, k, v)
            return m

        check(
            "absent BLOCK_SIZE -> cfg default",
            _runner.resolve_train_block_size(_mod(), cfg) == cfg.block_size,
        )
        check(
            "BLOCK_SIZE=2048 accepted",
            _runner.resolve_train_block_size(_mod(BLOCK_SIZE=2048), cfg) == 2048,
        )
        check(
            "baseline declares 8192 explicitly",
            _runner.baseline_block_size(cfg) == cfg.eval_block_size == 8192,
        )
        for bad in (128, 16384, 3000, -1, 0, "2048", 2048.0, True):
            try:
                _runner.resolve_train_block_size(_mod(BLOCK_SIZE=bad), cfg)
                rejected = False
            except _runner.GuardError:
                rejected = True
            check(f"BLOCK_SIZE={bad!r} rejected", rejected)

        # A model that sizes a positional table off the training context trains
        # fine and then fails at the 8192 eval -- the characteristic new failure
        # mode of the split contexts. It must come back as a GuardError naming
        # Both contexts, not as a bare RuntimeError/IndexError. (torch raises
        # IndexError here, which an earlier `except RuntimeError` missed.)
        import torch
        import torch.nn as nn

        from harness.data import TokenData as _TD

        class _BadPos(nn.Module):
            def __init__(self, config):
                super().__init__()
                self.emb = nn.Embedding(config.vocab_size, 8)
                # Wrong on purpose: should be config.eval_block_size.
                self.pos = nn.Embedding(config.block_size, 8)
                self.lin = nn.Linear(8, config.vocab_size)

            def forward(self, idx):
                p = self.pos(torch.arange(idx.shape[1], device=idx.device))
                return self.lin(self.emb(idx) + p)

        import tempfile as _tempfile

        with _tempfile.TemporaryDirectory() as _cdir:
            _tp = _write_selftest_bin(_cdir, "train.bin", 256, 16384, 1)
            _vp = _write_selftest_bin(_cdir, "val.bin", 256, 16384, 2)
            tiny = replace(
                settings.DEFAULT, vocab_size=256, eval_block_size=512, batch_size=2,
                train_seconds=0.5, max_train_seconds=10.0, val_tokens=1024,
                train_tokens_path=_tp, val_tokens_path=_vp, manifest_path="",
                val_bytes=1024 * 4,
            )
            try:
                _runner.run_arm(
                    _runner.load_factory(_mod(build_model=_BadPos)),
                    _TD(tiny), tiny, "cpu", 256,
                )
                got = "no error"
            except _runner.GuardError as exc:
                got = str(exc)
        check(
            "eval-context failure -> GuardError naming both contexts",
            "evaluation failed at context 512" in got and "trained at 256" in got,
        )

        # --- plausibility floor: a too-good bpb is rejected as leakage. The
        # eval is stubbed to return an impossibly low bpb; run_arm must refuse
        # it rather than score it. (Backstop for the static gate -- see
        # settings.min_plausible_bpb.) ---
        from harness.eval_ppl import EvalOutput as _EO

        class _TinyOK(nn.Module):
            def __init__(self, config):
                super().__init__()
                self.emb = nn.Embedding(config.vocab_size, 8)
                self.lin = nn.Linear(8, config.vocab_size)

            def forward(self, idx):
                return self.lin(self.emb(idx))

        with _tempfile.TemporaryDirectory() as _cdir:
            _tp = _write_selftest_bin(_cdir, "train.bin", 256, 16384, 5)
            _vp = _write_selftest_bin(_cdir, "val.bin", 256, 16384, 6)
            tiny2 = replace(
                settings.DEFAULT, vocab_size=256, eval_block_size=512, batch_size=2,
                train_seconds=0.5, max_train_seconds=10.0, val_tokens=1024,
                train_tokens_path=_tp, val_tokens_path=_vp, manifest_path="",
                val_bytes=1024 * 4,
            )
            _real_eval = _runner.evaluate_perplexity
            _runner.evaluate_perplexity = (
                lambda *a, **k: _EO(0.01, 1.0, 0.01, 1024, 1.0, 4096.0)
            )
            try:
                _runner.run_arm(
                    _runner.load_factory(_mod(build_model=_TinyOK)),
                    _TD(tiny2), tiny2, "cpu", 256,
                )
                floor_msg = "no error"
            except _runner.GuardError as exc:
                floor_msg = str(exc)
            finally:
                _runner.evaluate_perplexity = _real_eval
        check("implausibly low bpb -> GuardError (leakage floor)",
              "plausibility floor" in floor_msg)

    # --- The crux: eval windows are 8192 whatever the training context is ---
    # Numpy-only, no torch: exercise the window arithmetic val_windows uses.
    try:
        import numpy as np

        from harness.data import TokenData
    except Exception as exc:  # pragma: no cover
        print(f"[SKIP] val_windows checks ({type(exc).__name__})", file=sys.stderr)
        TokenData = None

    if TokenData is not None:
        import tempfile as _tempfile

        with _tempfile.TemporaryDirectory() as _cdir:
            _vocab = settings.DEFAULT.vocab_size
            _tp = _write_selftest_bin(_cdir, "train.bin", _vocab, 16384, 3)
            # val must hold > val_tokens ids so the window count is exercised.
            _vp = _write_selftest_bin(_cdir, "val.bin", _vocab, 40_000, 4)
            tiny_cfg = replace(
                settings.DEFAULT, val_tokens=32_768,
                train_tokens_path=_tp, val_tokens_path=_vp, manifest_path="",
                val_bytes=32_768 * 4,
            )
            widths, denoms = set(), set()
            for train_ctx in (8192, 2048, 256):
                d = TokenData(replace(tiny_cfg, block_size=train_ctx))
                # val_windows yields torch tensors, so replicate its slicing here
                # rather than importing torch: same expression, no device.
                eb = d.cfg.eval_block_size
                n = min(d.val.size - 1, d.cfg.val_tokens)
                n_windows = n // eb
                widths.add((eb, n_windows))
                denoms.add(round(d.val_bytes_for(n_windows * eb), 6))
                # ... and the training batch really does follow the training ctx.
                x = np.stack([d.train[i: i + train_ctx] for i in (0, 1)])
                check(f"train batch width == {train_ctx}", x.shape[1] == train_ctx)
            check("eval window width/count independent of training ctx", len(widths) == 1)
            check("bpb denominator independent of training ctx", len(denoms) == 1)
            check("eval window width is 8192", widths.pop() == (8192, 4))

    # --- baseline cache hits across submissions with different train contexts ---
    # This is the reason block_size left the fingerprint. The key is derived
    # from the config only; a submission's BLOCK_SIZE is resolved per-arm inside
    # run_arm and never reaches the key, so one cached baseline serves both.
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        cache = os.path.join(td, "baseline_ppl.json")
        prev = os.environ.get("FRONTIER_NANOSLM_BASELINE_CACHE")
        os.environ["FRONTIER_NANOSLM_BASELINE_CACHE"] = cache
        try:
            cfg_c = settings.DEFAULT
            key = settings.config_fingerprint(cfg_c)
            _baseline_cache_put(cfg_c, key, 1.2345)
            # Two submissions, training at 8192 and at 2048, both look the
            # baseline up under the same config -> the same key -> a hit.
            hits = [
                _baseline_cache_get(cfg_c, settings.config_fingerprint(cfg_c))
                for _ in (8192, 2048)
            ]
            check("baseline cache hits for both training contexts",
                  hits == [1.2345, 1.2345])
            check(
                "cache misses when the eval window changes",
                _baseline_cache_get(
                    cfg_c,
                    settings.config_fingerprint(
                        replace(cfg_c, eval_block_size=4096)),
                ) is None,
            )
        finally:
            if prev is None:
                os.environ.pop("FRONTIER_NANOSLM_BASELINE_CACHE", None)
            else:
                os.environ["FRONTIER_NANOSLM_BASELINE_CACHE"] = prev

    print(("selftest OK" if ok else "selftest failed"), file=sys.stderr)
    return 0 if ok else 1


def main(argv) -> int:
    if len(argv) == 2 and argv[1] == "--selftest":
        return _selftest()
    if len(argv) != 2:
        print("usage: evaluator.py /path/to/model.py | --selftest", file=sys.stderr)
        return 1
    try:
        result = evaluate(argv[1])
        score, score_unbounded, message = result[0], result[1], result[2]
        print(message, file=sys.stderr)
        print(f"{score:.12f} {score_unbounded:.12f}")
        return 0
    except Exception:
        print(traceback.format_exc(), file=sys.stderr)
        print("0.0 0.0")
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
