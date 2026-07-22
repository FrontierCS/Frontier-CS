"""Token-level data loading (torch path).

Train/val data are flat ``uint32`` token-ID streams (``.bin``) baked into the
judge image by ``docker/prep_assets.py`` using the dolma2 BPE tokenizer
(``allenai/dolma2-tokenizer``, 100278 real ids; the model vocabulary is padded
to 100352, so streams never index the top 74 rows). The validation stream is held out
and never mounted in ``/app``. The corpus is required: when the ``.bin`` files
are absent or unusable the harness raises ``DataError`` rather than fabricating
tokens, so a run never reports a bits-per-byte computed from synthetic data.

Byte accounting
---------------
``val_bytes_for(n)`` reports how many bytes of text ``n`` scored target tokens
cover. ``eval_ppl`` divides by that, not by the token count -- see
``settings.resolve_val_bytes_per_token`` for why that distinction is the whole
point of the metric.

Data order is fixed by the harness (common random numbers across the baseline
and the submission), so the two arms see identical batches.
"""

from __future__ import annotations

import numpy as np

from .settings import (
    TaskConfig,
    resolve_val_bytes_per_token,
)

TOKEN_DTYPE = np.uint32


class DataError(RuntimeError):
    """Corpus is absent or unusable (missing/empty file, bad dtype, out-of-range ids, no byte count)."""


def _load_bin(path: str, *, vocab_size: int, label: str) -> np.ndarray:
    """Load a ``uint32`` token stream, raising ``DataError`` if it is missing or unusable."""
    try:
        arr = np.fromfile(path, dtype=TOKEN_DTYPE)
    except OSError as exc:
        raise DataError(
            f"{label} corpus not found at {path!r} ({type(exc).__name__}). Stage the "
            "train.bin/val.bin (docker/prep_assets.py, or mount the Modal corpus "
            "volume)."
        ) from exc
    if arr.size == 0:
        raise DataError(
            f"{label} corpus at {path!r} is empty -- re-run docker/prep_assets.py."
        )
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
    return arr


class TokenData:
    """Holds train/val token arrays and yields fixed-order training batches.

    Two context lengths -- Read before editing
    ---------------------------------------------------------
    ``val_windows`` is cut at ``cfg.eval_block_size`` (8192, judge-owned) and
    Nothing here may make it depend on the training context: the scored
    bits-per-byte is only comparable across submissions because every arm is
    evaluated on the identical windows of the identical held-out stream. The
    Training path (``batch``) uses the per-arm training context instead, which a
    submission may set below 8192 to buy optimizer steps.
    """

    def __init__(self, cfg: TaskConfig):
        self.cfg = cfg
        # Longest window this data object will ever have to serve: the eval
        # window is fixed at 8192 and the training context is capped there too
        # (runner.MAX_TRAIN_BLOCK), so sizing off the max keeps both paths safe
        # no matter what a submission asks for.
        self.max_block = max(cfg.block_size, cfg.eval_block_size)
        self.train = _load_bin(
            cfg.train_tokens_path, vocab_size=cfg.vocab_size, label="train",
        )
        self.val = _load_bin(
            cfg.val_tokens_path, vocab_size=cfg.vocab_size, label="val",
        )
        if self.train.size < self.max_block + 1:
            raise DataError(
                f"train corpus at {cfg.train_tokens_path!r} has only "
                f"{self.train.size} tokens; needs > {self.max_block} to fill one "
                "window -- stage the full shard (docker/prep_assets.py)."
            )

        # Bytes of text per scored target token. Asserted, never defaulted to 1:
        # a ratio of 1 would silently turn val_bpb back into per-token CE/ln2.
        ratio = resolve_val_bytes_per_token(cfg)
        if ratio is None:
            raise DataError(
                "held-out byte count unavailable: no val_bytes in "
                f"{cfg.manifest_path!r}, no FRONTIER_NANOSLM_VAL_BYTES, and "
                "TaskConfig.val_bytes is 0. bits-per-byte cannot be computed "
                "from a token count -- re-run docker/prep_assets.py."
            )
        self.bytes_per_token = float(ratio)

    def val_bytes_for(self, n_target_tokens: int) -> float:
        """Bytes of held-out text covered by ``n_target_tokens`` target tokens."""
        return self.bytes_per_token * float(n_target_tokens)

    def batch(self, step: int, device: str, block_size: int | None = None):
        """Deterministic (step-keyed) training batch of token windows.

        ``block_size`` is the training context of the arm being trained, which
        may differ per submission; it defaults to the config's. The window start
        Indices are drawn against ``self.max_block`` rather than against the
        requested width, so two arms with different training contexts still
        begin their windows at the same offsets -- a short-context arm reads a
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

        Always ``cfg.eval_block_size`` wide. A submission that trained at 2048 
        is still scored on 8192-wide windows and must extrapolate to those 
        positions; that is the deliberate trade described above, and the reason 
        the bpb denominator (bytes per scored target token x number of target 
        tokens) is unaffected by the training context.
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
