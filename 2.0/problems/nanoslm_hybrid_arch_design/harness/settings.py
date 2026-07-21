"""Locked task settings + config fingerprint (torch-free).

All numbers here are read by the judge only. The agent never sees this file at
scoring time. Values tagged ``CALIBRATE`` are placeholders pending the
single-H100 calibration described in DESIGN.md §3 and must be frozen before the
task ships.
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
    # dolma2 BPE (allenai/dolma2-tokenizer), the OLMo-3 tokenizer. UNGATED --
    # no HF token is needed to download it, unlike lm_arch_discovery's Llama-2
    # tokenizer. 100278 ids > 65535, so token streams are uint32 on disk; uint16
    # would silently wrap the upper ~35k of the vocabulary.
    vocab_size: int = 100278
    # HYBRID-DISCOVERY SETTING. 8192, not 1024: hybrids exist to escape
    # attention's O(L^2), and at ctx 1024 attention is only ~31-40% of layer
    # FLOPs, so a cheaper sequence mixer has little to win and the fixed
    # wall-clock budget barely rewards it. At 8192 attention is ~78-84% of
    # layer FLOPs, so the attention/recurrence trade is the dominant design
    # question -- which is the point of this task.
    #
    # TWO CONTEXT LENGTHS, AND THE DISTINCTION IS LOAD-BEARING.
    #
    #   eval_block_size  FIXED, judge-owned. Every submission is scored on
    #                    non-overlapping windows of exactly this width, so
    #                    val_bpb stays comparable across submissions. NEVER
    #                    derive this from anything a submission controls.
    #   block_size       DEFAULT training context. A submission may override it
    #                    with a module-level ``BLOCK_SIZE`` int in model.py
    #                    (runner.resolve_train_block_size), because trading
    #                    context length for optimizer steps inside the fixed
    #                    wall-clock budget is now part of the design space --
    #                    at the cost of having to extrapolate to 8192 at eval.
    block_size: int = 8192         # DEFAULT training context (agent may override)
    eval_block_size: int = 8192    # FIXED scoring window -- judge-owned

    # --- fixed optimization recipe (locked; agent designs architecture only) ---
    # 8x4 rather than 32x1: at ctx 8192 a 32-sequence micro-batch is 262k tokens
    # of activations per forward. Accumulating keeps the EFFECTIVE batch at 32
    # sequences (unchanged from the ctx-1024 recipe, so the optimization recipe
    # is still locked and comparable) while bounding peak memory.
    batch_size: int = 8            # sequences per micro-batch (per device)
    grad_accum: int = 4            # -> effective batch 32 sequences
    learning_rate: float = 3.0e-3  # AdamW peak LR (nanoGPT-speedrun class)
    min_lr: float = 3.0e-4
    weight_decay: float = 0.1
    beta1: float = 0.9
    beta2: float = 0.95
    grad_clip: float = 1.0
    warmup_steps: int = 100

    # --- iso-wallclock budget (CALIBRATE: pick largest T leaving >=15min headroom) ---
    train_seconds: float = 1800.0  # CALIBRATE  wall-clock T per training run (30 min)
    max_train_seconds: float = 3300.0  # hard cap (< 1h) — abort if exceeded

    # --- data / tokenizer (locked; hidden tokens live in the judge image) ---
    dataset_name: str = "HuggingFaceFW/fineweb-edu:sample-10BT"  # provenance; matches config.yaml
    tokenizer_name: str = "allenai/dolma2-tokenizer"
    token_dtype: str = "uint32"    # vocab 100278 > 65535 -> uint16 is WRONG
    train_tokens_path: str = "/opt/nanoslm_arch/data/train.bin"
    val_tokens_path: str = "/opt/nanoslm_arch/data/val.bin"  # HELD OUT — never in /app
    # Written by docker/prep_assets.py next to the streams; carries val_bytes.
    manifest_path: str = "/opt/nanoslm_arch/data/manifest.json"
    val_tokens: int = 1_048_576    # held-out TOKENS scored (non-overlapping windows)
    # BYTE length of the held-out text that `val_tokens` target tokens cover.
    # 0 means "resolve from the manifest / FRONTIER_NANOSLM_VAL_BYTES at load
    # time" -- see resolve_val_bytes(). This must NEVER silently become a token
    # count: bpb is normalized by BYTES so that it stays comparable across
    # architectures the way the byte-level tokenizer used to make it by
    # construction.
    val_bytes: int = 0

    # --- iterative-role cached baseline (GPU via Modal; judge container CPU-only) ---
    # Mirrors nanowm's `baseline_cache`. The cheap agent-role feedback path trains
    # only the submission (~T on a Modal H100) and reuses a baseline perplexity
    # cached by config fingerprint; the final/verifier path recomputes a fresh
    # baseline+submission CRN pair (~2T) on one Modal GPU/process. In local testing
    # mode the judge can use a directly-attached H100 instead of Modal.
    baseline_cache_path: str = "/opt/nanoslm_arch/baseline/baseline_ppl.json"

    # --- scoring ---
    # ABSOLUTE bits-per-byte gain is the scored measurement:
    #     gain  = base_bpb - sub_bpb
    #     score = clip(100 * gain / bpb_score_scale, 0, 100)
    #
    # NOT A CALIBRATION TARGET, AND DELIBERATELY NOT LISTED AS ONE.
    # `bpb_score_scale` is a DISPLAY CONVENTION whose only necessary job is to
    # map bpb into the 0-100 range Harbor wants: Harbor computes
    # `reward = score / 100`, so a raw gain of 0.05 bpb would arrive as reward
    # 0.0005 -- zero, for every submission. It does NOT define "what counts as a
    # full win"; no such number has been measured, and dressing an arbitrary
    # constant as a measured target would put the score's meaning on a figure
    # nobody determined. The only real requirement is DISCRIMINATION (too coarse
    # and everyone pins at 0, too fine and everyone pins at 100), which is far
    # weaker than calibration and settable from one real-corpus run.
    # `score_unbounded` stays un-clipped so strong submissions remain visible.
    #
    # NOTE this replaced a RELATIVE `r_target` of the same numeric value, and
    # the two are NOT equivalent: 0.05 relative was ~0.145 bpb absolute at the
    # synthetic operating point (base_bpb ~2.9) and would be ~0.075-0.10 bpb
    # once a real corpus puts the baseline nearer 1.5-2.0. So 0.05 ABSOLUTE is a
    # STRICTER bar on real data than the relative form it replaced.
    bpb_score_scale: float = 0.05  # bpb gain that saturates the bounded score

    # --- guards / resource caps ---
    param_cap: int = 400_000_000   # max trainable params (over-cap -> score 0)
    min_param_delta: float = 1e-6  # trained-from-scratch guard: mean|Δparam| threshold
    seed: int = 1337
    # OFF pending validation -- see runner.run_arm. Closing the "compile the
    # baseline architecture and win on wall-clock" loophole still needs doing.
    compile_model: bool = False

    # --- determinism knobs applied on the GPU path ---
    cublas_workspace_config: str = ":4096:8"


DEFAULT = TaskConfig()


# --------------------------------------------------------------------------- #
# Byte accounting for the held-out stream.
#
# THIS IS THE SUBTLE PART OF THE BPE MIGRATION. At byte level 1 token == 1 byte,
# so `mean per-token CE / ln2` WAS bits-per-byte and dividing the total NLL by
# the token count happened to be right. With a BPE tokenizer the two diverge by
# the compression ratio (~4.4 bytes/token for dolma2 on English), and per-token
# CE/ln2 is a TOKENIZER-DEPENDENT quantity -- it is not comparable across setups
# and it is not bits per byte. The whole reason bpb was chosen as the scored
# metric (DESIGN.md §2) is that it is tokenizer-independent, so the
# denominator must be BYTES.
#
# The byte count is produced at corpus-prep time (docker/prep_assets.py decodes
# the scored token span and measures its UTF-8 length) and travels in
# manifest.json. eval_ppl.py ASSERTS it is available rather than falling back.
# --------------------------------------------------------------------------- #

# Only used when no real corpus is staged (synthetic smoke stream). Roughly the
# measured dolma2 compression ratio on English web text, so a smoke bpb lands in
# a plausible range instead of being off by ~4.4x.
SYNTHETIC_BYTES_PER_TOKEN = 4.4


def resolve_val_bytes_per_token(cfg: TaskConfig | None = None) -> float | None:
    """Bytes of held-out TEXT per scored target token, or ``None`` if unknown.

    A RATIO rather than a bare total, because the number of tokens actually
    scored is ``min(len(val)-1, cfg.val_tokens)`` rounded down to whole windows
    -- the smoke config scores far fewer than the corpus contains. The ratio is
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


# --------------------------------------------------------------------------- #
# Smoke overrides: tiny, fast, CPU-friendly. Enabled by FRONTIER_NANOSLM_SMOKE=1.
# Used only to prove the harness wiring end-to-end without a GPU; never scored.
# --------------------------------------------------------------------------- #
def smoke_enabled() -> bool:
    return os.environ.get("FRONTIER_NANOSLM_SMOKE", "") == "1"


def active_config() -> TaskConfig:
    if not smoke_enabled():
        return DEFAULT
    # SMOKE SHRINKS THE BUDGET, NOT THE SHAPE.
    #
    # The obvious smoke config (block_size=64) is actively harmful here: fla's
    # Triton kernels autotune per shape, and a 64-token sequence is far outside
    # the regime they are tuned for. Measured on an H100, GatedDeltaNet's first
    # forward costs 74.5s at T=64 but only 15.5s at T=8192 -- the tiny sequence
    # is ~5x SLOWER to compile. A block_size=64 smoke therefore appears to hang
    # for tens of minutes while compiling kernels no scored run will ever use.
    #
    # So the smoke keeps the REAL sequence length and cuts batch size, steps and
    # eval tokens instead. It is slower than a toy config but it exercises the
    # kernels the scored run actually uses, which is the point of a smoke test.
    return TaskConfig(
        block_size=8192,           # REAL shape -- see above
        eval_block_size=8192,      # scoring window is NEVER shrunk by the smoke
        batch_size=1,
        grad_accum=1,
        warmup_steps=1,
        # 45s, not 3s. The score is a function of THROUGHPUT, so a smoke that
        # yields one optimizer step per arm cannot validate the thing being
        # measured -- at train_seconds=3.0 both arms did exactly 1 step and the
        # reported +4.2% was noise. 45s gives tens of steps and a real
        # steps-per-arm comparison, at the cost of a slower smoke.
        train_seconds=45.0,
        max_train_seconds=900.0,
        val_tokens=32_768,
        param_cap=400_000_000,
    )


# --------------------------------------------------------------------------- #
# Config fingerprint: the cache key for the iterative-role cached baseline.
# A change to ANY locked knob invalidates a cached baseline rather than
# mispairing it (mirrors nanowm settings.config_fingerprint()).
# --------------------------------------------------------------------------- #
#
# NOTE `block_size` IS DELIBERATELY ABSENT, and `eval_block_size` replaces it.
# `block_size` is now only the DEFAULT training context: each submission may
# pick its own (runner.resolve_train_block_size). Fingerprinting a per-arm value
# would give every submission a distinct key, so the cached baseline would never
# hit and the agent-role feedback path would silently cost ~2T instead of ~T --
# the exact thing the cache exists to avoid. The BASELINE always trains at 8192
# (baseline_model.BLOCK_SIZE) and is always scored at `eval_block_size`, so
# neither of those depends on the submission and the cached number stays valid.
# `eval_block_size` DOES belong here: changing the scoring window changes what
# val_bpb means, so a baseline cached under the old one must not be reused.
_FINGERPRINT_KEYS = (
    "vocab_size", "eval_block_size", "batch_size", "grad_accum",
    "learning_rate", "min_lr", "weight_decay", "beta1", "beta2",
    "grad_clip", "warmup_steps", "train_seconds", "dataset_name",
    # tokenizer_name is fingerprinted alongside vocab_size: changing the
    # tokenizer changes what val_bpb MEANS, so a baseline cached under the old
    # one must not be reused.
    "tokenizer_name", "val_tokens", "seed",
)


def config_fingerprint(cfg: TaskConfig | None = None) -> str:
    cfg = cfg or active_config()
    d = asdict(cfg)
    payload = {k: d[k] for k in _FINGERPRINT_KEYS}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]
