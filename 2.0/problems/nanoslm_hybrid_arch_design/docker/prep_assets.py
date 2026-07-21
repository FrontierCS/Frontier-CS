"""Stage the tokenized corpus for nanoslm_hybrid_arch_design. Judge/operator side only.

Idempotent. Writes two flat uint32 TOKEN-ID streams plus a manifest:

    $NANOSLM_ARCH_ASSETS/train.bin      ~512M tokens   training ids
    $NANOSLM_ARCH_ASSETS/val.bin        1M+1 tokens    HELD OUT, judge image only
    $NANOSLM_ARCH_ASSETS/manifest.json  provenance + THE HELD-OUT BYTE COUNT

TOKENIZER
---------
`allenai/dolma2-tokenizer` (vocab 100278) -- the OLMo-3 tokenizer. UNGATED: it
downloads with no HF token, unlike lm_arch_discovery's license-gated Llama-2
tokenizer. Pinned in `harness/settings.py` as `TaskConfig.tokenizer_name` and
fingerprinted, so changing it invalidates any cached baseline.

DTYPE: uint32, NOT uint16
-------------------------
100278 ids do not fit in uint16 (max 65535). A uint16 stream would wrap the
upper ~35k of the vocabulary into low ids -- a corpus that still loads, still
trains, and shows up only as an unexplained floor on val_bpb. `harness/data.py`
reads `np.fromfile(path, dtype=np.uint32)` and asserts `max(id) < vocab_size`.

THE HELD-OUT BYTE COUNT -- WHY THIS FILE COMPUTES IT
----------------------------------------------------
The scored metric is bits per BYTE:

    val_bpb = total_nll_nats / (val_bytes * ln 2)

While the tokenizer was byte-level, 1 token == 1 byte and normalizing by the
token count was accidentally identical. Under BPE it is not: per-token CE/ln2 is
a tokenizer-dependent quantity that is no longer comparable across setups, which
would destroy the reason bpb was chosen (DESIGN.md §2). Nothing at
eval time can recover the byte count from a token stream, so it is measured HERE
-- by decoding the exact span of target tokens the harness scores and taking its
UTF-8 length -- and recorded in the manifest as `val_bytes` alongside
`val_target_tokens`. `harness/settings.resolve_val_bytes_per_token()` reads it
and `harness/data.TokenData` raises rather than falling back to a token count.

DISJOINTNESS
------------
`val.bin` is filled FIRST from the head of the document stream; the document
that straddles the boundary is then DISCARDED; training fills from what
follows. So no document contributes to both, structurally rather than by
sampling. Asserted at write time.

SIZING
------
`val.bin` holds `TaskConfig.val_tokens + 1` ids: the harness scores
`val_tokens` TARGET tokens over non-overlapping windows, and the last target
needs one more input token behind it.

`train.bin` defaults to 512M tokens (~2 GB on disk at uint32). A 30-minute H100
run at batch 8 x ctx 8192 touches on the order of 10^7-10^8 tokens, so this
leaves ample headroom without the sampler ever exhausting the stream.

Usage:
    NANOSLM_ARCH_ASSETS=./assets python3 docker/prep_assets.py
    NANOSLM_ARCH_ASSETS=./assets python3 docker/prep_assets.py --train-tokens 2000000
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

import numpy as np

# HuggingFaceFW/fineweb-edu, sample-10BT: public, ungated, English, and the
# `dataset_name` recorded in TaskConfig is derived from it.
CORPUS = "HuggingFaceFW/fineweb-edu"
CORPUS_CONFIG = "sample-10BT"

TOKENIZER = "allenai/dolma2-tokenizer"   # matches TaskConfig.tokenizer_name
VOCAB_SIZE = 100278                      # matches TaskConfig.vocab_size
TOKEN_DTYPE = np.uint32                  # matches harness/data.TOKEN_DTYPE

VAL_TOKENS = 1 << 20                     # matches TaskConfig.val_tokens
TRAIN_TOKENS = 512_000_000
DOC_BATCH = 256                          # docs per tokenizer call


def _stream_docs():
    from datasets import load_dataset

    ds = load_dataset(CORPUS, CORPUS_CONFIG, split="train", streaming=True)
    for rec in ds:
        text = rec.get("text") or rec.get("content")
        if text:
            yield text


def _load_tokenizer():
    import logging

    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(TOKENIZER)
    # "Token indices sequence length is longer than the specified maximum
    # sequence length for this model (15040 > 8192)" fires on nearly every batch
    # and is IRRELEVANT here: we are building a flat corpus stream, not feeding
    # documents to a model. The harness slices its own block_size windows out of
    # it later. Silenced so a real error is not buried in thousands of lines.
    tok.model_max_length = int(1e12)
    logging.getLogger("transformers.tokenization_utils_base").setLevel(logging.ERROR)
    if len(tok) > VOCAB_SIZE:
        raise SystemExit(
            f"FATAL: tokenizer has {len(tok)} ids but VOCAB_SIZE is {VOCAB_SIZE}; "
            "harness/settings.py TaskConfig.vocab_size must be raised to match"
        )
    return tok


def _encode_batched(tok, docs, quota: int):
    """Yield uint32 id chunks from `docs` until `quota` ids are produced.

    Documents are concatenated with NO separator token, exactly as the
    byte-level version concatenated raw text. A separator would carry zero bytes
    of text while still consuming a token, biasing the byte accounting.
    """
    produced, used, buf = 0, 0, []

    def _flush():
        nonlocal produced, buf
        if not buf:
            return None
        enc = tok(buf, add_special_tokens=False)["input_ids"]
        buf = []
        flat = np.fromiter(
            (i for seq in enc for i in seq), dtype=np.int64,
        )
        if produced + flat.size > quota:
            flat = flat[: quota - produced]
        produced += flat.size
        return flat.astype(TOKEN_DTYPE)

    for text in docs:
        buf.append(text)
        used += 1
        if len(buf) >= DOC_BATCH:
            chunk = _flush()
            if chunk is not None and chunk.size:
                yield chunk, used
            if produced >= quota:
                return
    chunk = _flush()
    if chunk is not None and chunk.size:
        yield chunk, used


def _fill(path: pathlib.Path, quota: int, docs, tok, *, keep: bool):
    """Write `quota` token ids to `path`; return (written, docs_used, ids|None)."""
    written, used, kept = 0, 0, []
    with open(path, "wb") as fh:
        for chunk, used in _encode_batched(tok, docs, quota):
            fh.write(chunk.tobytes())
            written += chunk.size
            if keep:
                kept.append(chunk)
            if written >= quota:
                break
    ids = np.concatenate(kept) if (keep and kept) else None
    return written, used, ids


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--assets", default=os.environ.get("NANOSLM_ARCH_ASSETS", "./assets"))
    ap.add_argument("--train-tokens", type=int, default=TRAIN_TOKENS)
    ap.add_argument("--val-tokens", type=int, default=VAL_TOKENS,
                    help="TARGET tokens scored; val.bin holds this many + 1")
    args = ap.parse_args()

    out = pathlib.Path(args.assets)
    out.mkdir(parents=True, exist_ok=True)
    train_p, val_p = out / "train.bin", out / "val.bin"
    man_p = out / "manifest.json"

    itemsize = np.dtype(TOKEN_DTYPE).itemsize
    val_ids_needed = args.val_tokens + 1
    if (train_p.exists() and val_p.exists() and man_p.exists()
            and train_p.stat().st_size >= args.train_tokens * itemsize
            and val_p.stat().st_size >= val_ids_needed * itemsize):
        print(f"[prep] cached: train={train_p.stat().st_size // itemsize:,} tok "
              f"val={val_p.stat().st_size // itemsize:,} tok")
        return 0

    tok = _load_tokenizer()
    docs = _stream_docs()

    # HELD-OUT FIRST, then discard the straddling document, then train.
    v_written, v_docs, v_ids = _fill(val_p, val_ids_needed, docs, tok, keep=True)
    straddler = next(docs, None)
    t_written, t_docs, _ = _fill(train_p, args.train_tokens, docs, tok, keep=False)

    # CLOSE THE STREAM EXPLICITLY, or this script hangs after finishing its work.
    # `_stream_docs` wraps a `datasets` STREAMING iterator, and every quota above
    # is satisfied by breaking out early -- so the generator is left suspended
    # mid-iteration with its HTTP/fsspec resources open. Measured: the script
    # wrote train.bin, val.bin and manifest.json correctly and then sat for 14+
    # minutes at interpreter shutdown waiting on those non-daemon threads.
    # docker/build_images.sh calls this on a cold cache and would hang with it.
    docs.close()

    if v_written < val_ids_needed:
        print(f"FATAL: val short ({v_written} < {val_ids_needed})", file=sys.stderr)
        return 1
    if t_written < args.train_tokens:
        print(f"FATAL: train short ({t_written} < {args.train_tokens})", file=sys.stderr)
        return 1
    # STRUCTURAL disjointness assertion, unchanged in intent from the byte-level
    # version: the boundary document is consumed and thrown away, so the last
    # document in val and the first in train are different documents.
    if straddler is None:
        print("FATAL: corpus exhausted at the val/train boundary", file=sys.stderr)
        return 1

    hi = int(v_ids.max())
    if hi >= VOCAB_SIZE:
        print(f"FATAL: token id {hi} >= vocab {VOCAB_SIZE}", file=sys.stderr)
        return 1

    # THE BYTE COUNT. Decode exactly the span the harness scores -- the TARGET
    # tokens, ids[1 : val_tokens+1], since the model predicts token i+1 from
    # token i -- and measure its UTF-8 length.
    target_ids = v_ids[1 : args.val_tokens + 1]
    val_text = tok.decode(target_ids.tolist())
    val_bytes = len(val_text.encode("utf-8"))
    if val_bytes <= 0:
        print("FATAL: decoded held-out span is empty", file=sys.stderr)
        return 1
    # CORRECTNESS CHECK: the decode must be byte-ADDITIVE across the input/target
    # split, i.e. decode(ids[:1]) + decode(ids[1:]) reproduces decode(ids)
    # exactly. That is what makes `val_bytes` the true byte length of the span
    # the model is scored on rather than an approximation.
    #
    # NOT a re-encode check. `tok(decode(span)) == span` is the obvious test and
    # it is WRONG here: BPE re-merges greedily, so a span that begins or ends
    # mid-document re-tokenizes differently at its boundaries while decoding to
    # byte-identical text. Measured on a real FineWeb-Edu val span, the re-encode
    # test fails and the additivity test passes -- the byte count is fine, the
    # test was not.
    full_bytes = len(tok.decode(v_ids.tolist()).encode("utf-8"))
    head_bytes = len(tok.decode(v_ids[:1].tolist()).encode("utf-8"))
    byte_additive = (head_bytes + val_bytes == full_bytes)
    if not byte_additive:
        print(f"FATAL: decode is not byte-additive across the target split "
              f"({head_bytes} + {val_bytes} != {full_bytes}); val_bytes would "
              f"not describe the scored span", file=sys.stderr)
        return 1

    man_p.write_text(json.dumps({
        "corpus": f"{CORPUS}:{CORPUS_CONFIG}",
        "tokenizer": TOKENIZER,
        "vocab_size": VOCAB_SIZE,
        "format": "flat uint32 token ids, no header (np.fromfile dtype=uint32)",
        "val_ids": int(v_written), "val_docs": int(v_docs),
        # THE FIELD THE HARNESS READS. bpb = nll / (val_bytes * ln2), scaled by
        # val_target_tokens when a run scores fewer tokens than were staged.
        "val_target_tokens": int(target_ids.size),
        "val_bytes": int(val_bytes),
        "val_bytes_per_token": round(val_bytes / target_ids.size, 4),
        "val_decode_byte_additive": byte_additive,
        "train_tokens": int(t_written), "train_docs": int(t_docs),
        "disjoint": "val filled first; straddling document discarded; train follows",
    }, indent=2))

    print(f"[prep] val   {v_written:,} ids from {v_docs:,} docs -> {val_p}")
    print(f"[prep] val   {val_bytes:,} BYTES over {target_ids.size:,} target tokens "
          f"({val_bytes / target_ids.size:.2f} B/tok, byte-additive={byte_additive})")
    print(f"[prep] train {t_written:,} ids from {t_docs:,} docs -> {train_p}")
    print("[prep] disjoint by construction (straddling document discarded)")
    return 0


if __name__ == "__main__":
    # os._exit, NOT SystemExit, and this is load-bearing rather than a style
    # choice. `datasets` streaming leaves non-daemon fsspec/aiohttp threads
    # alive; even after `docs.close()` above, normal interpreter shutdown blocks
    # joining them. MEASURED: this script wrote train.bin, val.bin and
    # manifest.json correctly within a minute and then hung for 14+ minutes
    # doing nothing. docker/build_images.sh runs it on a cold asset cache and
    # would hang with it, with no output to explain why.
    #
    # Everything this script produces is already durable at this point -- the
    # .bin files are written and closed by _fill(), and manifest.json by
    # pathlib.write_text -- so skipping teardown costs nothing. The explicit
    # flush is required because os._exit does NOT flush Python's stdio buffers.
    _rc = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(_rc)
