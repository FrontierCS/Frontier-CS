"""Locked task settings + config fingerprint (torch-free).

All numbers here are read by the judge only; the agent never sees this file at
scoring time.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass


# --------------------------------------------------------------------------- #
# Locked training / evaluation configuration.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class TaskConfig:
    # --- fixed model I/O contract (agent must honor these) ---
    # dolma2 BPE (allenai/dolma2-tokenizer), the OLMo-3 tokenizer. Ungated --
    # no HF token is needed to download it, unlike lm_arch_discovery's Llama-2
    # tokenizer.
    #
    # 100352 = the tokenizer's 100278 real ids PADDED up (Olmo 3's own
    # convention, "padded for efficient embedding lookups"). The corpus is
    # unaffected: ids on disk are always < 100278, the extra 74 embedding rows
    # and logit columns are simply never indexed by data. Models must still
    # produce logits over the full padded width. > 65535 either way, so token
    # streams are uint32 on disk; uint16 would silently wrap the upper ~35k of
    # the vocabulary.
    vocab_size: int = 100352
    # 8192, not 1024: hybrids exist to escape attention's O(L^2), and attention
    # only dominates layer FLOPs at long context, so the attention/recurrence
    # trade is the dominant design question here -- the point of the task.
    #
    # Two context lengths, and the distinction is load-bearing.
    #
    #   eval_block_size  fixed, judge-owned. Every submission is scored on
    #                    non-overlapping windows of exactly this width, so
    #                    val_bpb stays comparable across submissions. Never
    #                    derive this from anything a submission controls.
    #   block_size       default training context. A submission may override it
    #                    with a module-level ``BLOCK_SIZE`` int in model.py
    #                    (runner.resolve_train_block_size), because trading
    #                    context length for optimizer steps inside the fixed
    #                    wall-clock budget is now part of the design space --
    #                    at the cost of having to extrapolate to 8192 at eval.
    block_size: int = 8192         # Default training context (agent may override)
    eval_block_size: int = 8192    # Fixed scoring window -- judge-owned

    # --- fixed optimization recipe (locked; agent designs architecture only) ---
    # micro-batch 2 so the fp32 cross-entropy logits at ctx 8192 fit on one H100;
    # grad_accum 16 holds the effective batch at 32 so the recipe stays
    # comparable. (micro-batch 8 OOMs; a fused CE would let it grow again.)
    batch_size: int = 2            # sequences per micro-batch (per device)
    grad_accum: int = 16           # -> effective batch 32 sequences
    learning_rate: float = 3.0e-3  # AdamW peak LR (nanoGPT-speedrun class)
    min_lr: float = 3.0e-4
    weight_decay: float = 0.1
    beta1: float = 0.9
    beta2: float = 0.95
    grad_clip: float = 1.0
    warmup_steps: int = 100

    # --- iso-wallclock budget (matches config.yaml) ---
    train_seconds: float = 21600.0  # wall-clock T per training run (6 h)
    # Infrastructure backstop, enforced by the Modal function timeout (and the
    # orchestrator), not by the training loop -- a between-step check could
    # never fire before train_seconds and cannot interrupt a hung step.
    max_train_seconds: float = 43200.0  # hard cap (12 h)

    # --- data / tokenizer (locked; hidden tokens live in the judge image) ---
    dataset_name: str = "HuggingFaceFW/fineweb-edu:sample-10BT"  # provenance; matches config.yaml
    tokenizer_name: str = "allenai/dolma2-tokenizer"
    token_dtype: str = "uint32"    # ids up to 100277 > 65535 -> uint16 is wrong
    train_tokens_path: str = "/opt/nanoslm_arch/data/train.bin"
    val_tokens_path: str = "/opt/nanoslm_arch/data/val.bin"  # Held out — never in /app
    # Written by docker/prep_assets.py next to the streams; carries val_bytes.
    manifest_path: str = "/opt/nanoslm_arch/data/manifest.json"
    val_tokens: int = 1_048_576    # held-out tokens scored (non-overlapping windows)
    # Byte length of the held-out text that `val_tokens` target tokens cover.
    # 0 means "resolve from the manifest / FRONTIER_NANOSLM_VAL_BYTES at load
    # time" -- see resolve_val_bytes(). This must never silently become a token
    # count: bpb is normalized by bytes so that it stays comparable across
    # architectures the way the byte-level tokenizer used to make it by
    # construction.
    val_bytes: int = 0

    # --- iterative-role cached baseline (GPU via Modal; judge container CPU-only) ---
    # Mirrors nanowm's `baseline_cache`. The cheap agent-role feedback path trains
    # only the submission (~T on a Modal H100) and reuses a baseline result
    # cached by config fingerprint; the final/verifier path recomputes a fresh
    # baseline+submission CRN pair (~2T) on one Modal GPU/process.
    #
    # On the Modal backend (production) the cache lives on the nanoslm-corpus
    # Volume so it survives containers, and is keyed by fingerprint AND the
    # staged train.bin's byte size AND the modal_app CODE_VERSION -- the
    # fingerprint only hashes config values, so a harness behavior change
    # (e.g. the LR schedule) must bump CODE_VERSION, and a corpus restage
    # changes the size stamp automatically. See modal_app.run_pair_remote.
    # The path below is only the local-backend (dev/testing) location.
    baseline_cache_path: str = "/opt/nanoslm_arch/baseline/baseline_ppl.json"

    # --- scoring ---
    # Absolute bits-per-byte gain is the scored measurement:
    #     gain  = base_bpb - sub_bpb
    #     score = clip(100 * gain / bpb_score_scale, 0, 100)
    # `bpb_score_scale` is a display convention that maps the gain into Harbor's
    # 0-100 reward, not a calibrated "full win" target; its only
    # real requirement is discrimination, and `score_unbounded` stays un-clipped.
    # 0.5 comes from a real-corpus run and is due a re-check at the 6 h budget.
    bpb_score_scale: float = 0.5   # bpb gain that saturates the bounded score

    # --- guards / resource caps ---
    param_cap: int = 400_000_000   # max trainable params (over-cap -> score 0)
    min_param_delta: float = 1e-6  # trained-from-scratch guard: mean|Δparam| threshold
    # Plausibility floor on the scored bits-per-byte. The static policy gate
    # scans Turing-complete code and is defense in depth, not proof; a
    # submission that evaded it and read the held-out stream at runtime would
    # score a near-zero bpb. No honest result can approach this floor: the
    # strongest published LLMs sit near ~0.55 bpb on web text, and a <=400M
    # model trained 6 h from scratch lands far above that. A measurement below
    # it is therefore treated as held-out leakage, not brilliance -> GuardError
    # (score 0, public reason). A scoring/guard constant like bpb_score_scale,
    # so it is deliberately NOT fingerprinted.
    min_plausible_bpb: float = 0.4
    seed: int = 1337
    # Off by default (see runner.run_arm): compiling the chunkwise mixer measured
    # worse than eager, and the fairness argument for compiling both arms is real
    # but unresolved.
    compile_model: bool = False

    # --- determinism knobs applied on the GPU path ---
    cublas_workspace_config: str = ":4096:8"


DEFAULT = TaskConfig()


# --------------------------------------------------------------------------- #
# Byte accounting for the held-out stream.
#
# This is the subtle part of the BPE migration. At byte level 1 token == 1 byte,
# so `mean per-token CE / ln2` was bits-per-byte and dividing the total NLL by
# the token count happened to be right. With a BPE tokenizer the two diverge by
# the compression ratio (~4.4 bytes/token for dolma2 on English), and per-token
# CE/ln2 is a tokenizer-dependent quantity -- it is not comparable across setups
# and it is not bits per byte. The whole reason bpb was chosen as the scored
# metric is that it is tokenizer-independent, so the
# denominator must be bytes.
#
# The byte count is produced at corpus-prep time (docker/prep_assets.py decodes
# the scored token span and measures its UTF-8 length) and travels in
# manifest.json. eval_ppl.py asserts it is available rather than falling back;
# with no real corpus the harness raises DataError instead of estimating a ratio.
# --------------------------------------------------------------------------- #


def resolve_val_bytes_per_token(cfg: TaskConfig | None = None) -> float | None:
    """Bytes of held-out text per scored target token, or ``None`` if unknown.

    A ratio rather than a bare total, because the number of tokens actually
    scored is ``min(len(val)-1, cfg.val_tokens)`` rounded down to whole windows
    -- a test config may score fewer than the corpus contains. The ratio is
    exact for the production config (which scores the whole staged stream) and
    proportional otherwise, and it can never be confused for a token count.

    Resolution order (first hit wins):
      1. ``FRONTIER_NANOSLM_VAL_BYTES`` (+ optional ``..._VAL_BYTES_TOKENS``) --
         operator / Modal-image override.
      2. ``cfg.val_bytes`` when frozen to a non-zero literal (paired with
         ``cfg.val_tokens``).
      3. ``val_bytes`` / ``val_target_tokens`` from the manifest that
         ``docker/prep_assets.py`` writes next to the token streams.
    """
    cfg = cfg or active_config()

    def _ratio(nbytes, ntok) -> float | None:
        try:
            nbytes, ntok = int(nbytes), int(ntok)
        except (TypeError, ValueError):
            return None
        return nbytes / ntok if nbytes > 0 and ntok > 0 else None

    env = os.environ.get("FRONTIER_NANOSLM_VAL_BYTES", "").strip()
    if env:
        r = _ratio(env, os.environ.get("FRONTIER_NANOSLM_VAL_BYTES_TOKENS")
                   or cfg.val_tokens)
        if r:
            return r

    if cfg.val_bytes > 0:
        r = _ratio(cfg.val_bytes, cfg.val_tokens)
        if r:
            return r

    for path in (os.environ.get("FRONTIER_NANOSLM_MANIFEST", ""), cfg.manifest_path):
        if not path:
            continue
        try:
            with open(path, "r", encoding="utf-8") as fh:
                man = json.load(fh)
        except Exception:
            continue
        r = _ratio(man.get("val_bytes"), man.get("val_target_tokens"))
        if r:
            return r
    return None


def active_config() -> TaskConfig:
    """The one production configuration.

    (A FRONTIER_NANOSLM_SMOKE budget-shrinking mode used to live here for
    cheap wiring checks; it was removed deliberately -- the harness runs one
    configuration, the scored one. Ad-hoc testing configs belong in tests,
    built with ``dataclasses.replace`` on ``DEFAULT``, as the evaluator
    selftest does.)
    """
    return DEFAULT


# --------------------------------------------------------------------------- #
# Config fingerprint: the cache key for the iterative-role cached baseline.
# A change to any locked knob invalidates a cached baseline rather than
# mispairing it (mirrors nanowm settings.config_fingerprint()).
# --------------------------------------------------------------------------- #
#
# Note `block_size` is deliberately absent, and `eval_block_size` replaces it.
# `block_size` is now only the default training context: each submission may
# pick its own (runner.resolve_train_block_size). Fingerprinting a per-arm value
# would give every submission a distinct key, so the cached baseline would never
# hit and the agent-role feedback path would silently cost ~2T instead of ~T --
# the exact thing the cache exists to avoid. The baseline always trains at 8192
# (baseline_model.BLOCK_SIZE) and is always scored at `eval_block_size`, so
# neither of those depends on the submission and the cached number stays valid.
# `eval_block_size` does belong here: changing the scoring window changes what
# val_bpb means, so a baseline cached under the old one must not be reused.
_FINGERPRINT_KEYS = (
    "vocab_size", "eval_block_size", "batch_size", "grad_accum",
    "learning_rate", "min_lr", "weight_decay", "beta1", "beta2",
    "grad_clip", "warmup_steps", "train_seconds", "dataset_name",
    # tokenizer_name is fingerprinted alongside vocab_size: changing the
    # tokenizer changes what val_bpb means, so a baseline cached under the old
    # one must not be reused.
    "tokenizer_name", "val_tokens", "seed",
    # compile_model changes both arms' throughput, hence the baseline's step
    # count and val_bpb -- flipping it must invalidate a cached baseline.
    "compile_model",
)


def config_fingerprint(cfg: TaskConfig | None = None) -> str:
    cfg = cfg or active_config()
    d = asdict(cfg)
    payload = {k: d[k] for k in _FINGERPRINT_KEYS}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]
