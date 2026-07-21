"""Token-level data loading (torch path).

Train/val data are flat ``uint32`` TOKEN-ID streams (``.bin``) baked into the
judge image by ``docker/prep_assets.py`` using the dolma2 BPE tokenizer
(``allenai/dolma2-tokenizer``, vocab 100278). The validation stream is HELD OUT
and never mounted in ``/app``. When the files are absent (CPU smoke / local dev)
a deterministic synthetic token stream is generated so the harness wiring runs
end-to-end without baked assets.

WHY uint32 AND NOT uint16
-------------------------
The dolma2 vocabulary is 100278 ids. ``uint16`` tops out at 65535, so the upper
~35k of the vocabulary would wrap silently into low ids -- a corrupted corpus
that still loads, still trains, and only shows up as an unexplained bpb floor.
The stream is therefore uint32 and ``_load_bin`` asserts every id is in range.

BYTE ACCOUNTING
---------------
``val_bytes_for(n)`` reports how many BYTES OF TEXT ``n`` scored target tokens
cover. ``eval_ppl`` divides by that, not by the token count -- see
``settings.resolve_val_bytes_per_token`` for why that distinction is the whole
point of the metric.

Data order is fixed by the harness (common random numbers across the baseline
and the submission), so the two arms see identical batches.
"""

from __future__ import annotations

import numpy as np

from .settings import (
    SYNTHETIC_BYTES_PER_TOKEN,
    TaskConfig,
    resolve_val_bytes_per_token,
)

TOKEN_DTYPE = np.uint32


class DataError(RuntimeError):
    """Corpus is present but unusable (bad dtype, out-of-range ids, no byte count)."""


def _synthetic_tokens(n: int, seed: int, vocab_size: int) -> np.ndarray:
    """Deterministic pseudo-text token stream for smoke runs (no baked data).

    Emits plausible BPE ids: a repeating "vocabulary" of a few thousand common
    ids (real text is heavily Zipfian, so a smoke model can actually reduce
    perplexity below uniform) plus occasional rare ids from the full range, so
    the embedding table is exercised beyond its first rows.
    """
    rng = np.random.default_rng(seed)
    common = rng.integers(0, min(4096, vocab_size), size=max(1024, n // 8))
    stream = np.tile(common, (n // common.size) + 1)[:n].astype(np.int64)
    rare_mask = rng.random(n) < 0.02
    stream[rare_mask] = rng.integers(0, vocab_size, size=int(rare_mask.sum()))
    return stream.astype(TOKEN_DTYPE)


def _load_bin(path: str, *, fallback_n: int, seed: int, vocab_size: int) -> tuple[np.ndarray, bool]:
    """Return ``(tokens, is_real)``; synthesize when the file is absent."""
    try:
        arr = np.fromfile(path, dtype=TOKEN_DTYPE)
    except OSError:
        return _synthetic_tokens(fallback_n, seed, vocab_size), False
    if arr.size == 0:
        return _synthetic_tokens(fallback_n, seed, vocab_size), False
    # A uint8 stream left over from the byte-level era reads as uint32 without
    # error -- it just produces garbage ids. Catch it here rather than as a
    # mystery bpb. (An out-of-range id would also index past the embedding
    # table and raise a device-side assert deep inside the model.)
    hi = int(arr.max())
    if hi >= vocab_size:
        raise DataError(
            f"{path}: token id {hi} >= vocab_size {vocab_size} "
            f"(stale corpus, or written with the wrong dtype)"
        )
    return arr, True


class TokenData:
    """Holds train/val token arrays and yields fixed-order training batches.

    TWO CONTEXT LENGTHS -- READ BEFORE EDITING
    ---------------------------------------------------------
    ``val_windows`` is cut at ``cfg.eval_block_size`` (8192, judge-owned) and
    NOTHING here may make it depend on the training context: the scored
    bits-per-byte is only comparable across submissions because every arm is
    evaluated on the identical windows of the identical held-out stream. The
    TRAINING path (``batch``) uses the per-arm training context instead, which a
    submission may set below 8192 to buy optimizer steps.
    """

    def __init__(self, cfg: TaskConfig):
        self.cfg = cfg
        # Longest window this data object will ever have to serve: the eval
        # window is fixed at 8192 and the training context is capped there too
        # (runner.MAX_TRAIN_BLOCK), so sizing off the max keeps both paths safe
        # no matter what a submission asks for.
        self.max_block = max(cfg.block_size, cfg.eval_block_size)
        self.train, train_real = _load_bin(
            cfg.train_tokens_path, fallback_n=1 << 20,
            seed=cfg.seed, vocab_size=cfg.vocab_size,
        )
        self.val, self.val_is_real = _load_bin(
            cfg.val_tokens_path, fallback_n=cfg.val_tokens + cfg.eval_block_size + 1,
            seed=cfg.seed + 999, vocab_size=cfg.vocab_size,
        )
        if self.train.size < self.max_block + 1:
            self.train = _synthetic_tokens(1 << 20, cfg.seed, cfg.vocab_size)
            train_real = False
        self.train_is_real = train_real

        # Bytes of text per scored target token. ASSERTED, never defaulted to 1:
        # a ratio of 1 would silently turn val_bpb back into per-token CE/ln2.
        ratio = resolve_val_bytes_per_token(cfg)
        if ratio is None:
            if self.val_is_real:
                raise DataError(
                    "held-out byte count unavailable: no val_bytes in "
                    f"{cfg.manifest_path!r}, no FRONTIER_NANOSLM_VAL_BYTES, and "
                    "TaskConfig.val_bytes is 0. bits-per-byte cannot be "
                    "computed from a token count -- re-run docker/prep_assets.py."
                )
            # Synthetic stream: there is no underlying text, so use the measured
            # dolma2 compression ratio to keep smoke bpb in a plausible range.
            ratio = SYNTHETIC_BYTES_PER_TOKEN
            self.val_bytes_estimated = True
        else:
            self.val_bytes_estimated = not self.val_is_real
        self.bytes_per_token = float(ratio)

    def val_bytes_for(self, n_target_tokens: int) -> float:
        """Bytes of held-out text covered by ``n_target_tokens`` target tokens."""
        return self.bytes_per_token * float(n_target_tokens)

    def batch(self, step: int, device: str, block_size: int | None = None):
        """Deterministic (step-keyed) training batch of token windows.

        ``block_size`` is the TRAINING context of the arm being trained, which
        may differ per submission; it defaults to the config's. The window START
        INDICES are drawn against ``self.max_block`` rather than against the
        requested width, so two arms with different training contexts still
        begin their windows at the SAME offsets -- a short-context arm reads a
        prefix of what a long-context arm reads, instead of an unrelated slice.
        That keeps common random numbers as close to intact as differing window
        widths permit.
        """
        import torch

        cfg = self.cfg
        bs = int(block_size or cfg.block_size)
        # Common random numbers: batch content depends only on (seed, step), so
        # baseline and submission arms train on identical data.
        g = np.random.default_rng(cfg.seed * 1_000_003 + step)
        hi = max(1, self.train.size - self.max_block - 1)
        ix = g.integers(0, hi, size=cfg.batch_size)
        x = np.stack([self.train[i : i + bs] for i in ix])
        y = np.stack([self.train[i + 1 : i + 1 + bs] for i in ix])
        xt = torch.from_numpy(x.astype(np.int64))
        yt = torch.from_numpy(y.astype(np.int64))
        if device.startswith("cuda"):
            xt = xt.pin_memory().to(device, non_blocking=True)
            yt = yt.pin_memory().to(device, non_blocking=True)
        else:
            xt, yt = xt.to(device), yt.to(device)
        return xt, yt

    def val_windows(self, device: str):
        """Yield non-overlapping (x, y) windows over the held-out token stream.

        ALWAYS ``cfg.eval_block_size`` wide -- never the training context. A
        submission that trained at 2048 is still scored on 8192-wide windows and
        must extrapolate to those positions; that is the deliberate trade
        described above, and the reason the bpb denominator (bytes per
        scored target token x number of target tokens) is unaffected by the
        training context.
        """
        import torch

        cfg = self.cfg
        eb = cfg.eval_block_size
        n = min(self.val.size - 1, cfg.val_tokens)
        n_windows = n // eb
        for w in range(n_windows):
            s = w * eb
            x = self.val[s : s + eb][None, :]
            y = self.val[s + 1 : s + 1 + eb][None, :]
            xt = torch.from_numpy(x.astype(np.int64)).to(device)
            yt = torch.from_numpy(y.astype(np.int64)).to(device)
            yield xt, yt


# The class was ``ByteData`` while the tokenizer was byte-level. Kept as an
# alias so any out-of-tree caller keeps working; new code uses TokenData.
ByteData = TokenData
