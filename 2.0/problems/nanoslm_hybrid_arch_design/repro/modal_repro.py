"""Modal app to reproduce Olmo Hybrid Table 5 (190M Base-Easy BPB).

Two remote functions on one shared Volume:

  prep_data  (CPU)  stream the Olmo 3 mix as raw text, dolma2-tokenize it, and
                    write uint32 train.bin / val.bin (+ manifest with val_bytes)
                    to the Volume. Parameterized by target_tokens so a tiny
                    wiring test and a full 1x/8x-Chinchilla stage share code.

  train      (H100) load the tokenized bins, build the paper-faithful 190M
                    transformer or GDN-3:1 hybrid (repro.paper_models), train
                    with a WSD-S schedule (repro.wsd), log train + held-out CE,
                    and checkpoint to the Volume.

The DOWNSTREAM OlmoBaseEval-Easy bpb eval (the actual 0.950/0.891 metric) is a
separate stage (oe-eval) run on the produced checkpoints; this app produces the
checkpoints and a held-out-CE trajectory to sanity-check the training recipe.

Run (from the driver venv, with ~/.modal.toml authed):
    modal run repro/modal_repro.py::prep_data --target-tokens 20000000     # wiring
    modal run repro/modal_repro.py::train --arm transformer --target-tokens 20000000
"""

from __future__ import annotations

import os
import pathlib

import modal

APP_NAME = "nanoslm-repro"
DATA = "/data"
REPRO_REMOTE = "/root/repro"
_HERE = pathlib.Path(__file__).resolve().parent

VOL = modal.Volume.from_name("nanoslm-repro", create_if_missing=True)

# Same torch/fla/triton stack the benchmark's modal_app pins -- fla 0.5.1 needs
# Triton >= 3.2 (torch 2.6 ships it); 0.4.1's backward kernels predate it and
# hang/err. transformers carries the dolma2 tokenizer.
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.6.0", "numpy<2",
        "flash-linear-attention==0.5.1", "transformers==4.46.3",
        "huggingface_hub>=0.25", "tokenizers>=0.20", "zstandard>=0.22",
        "hf_transfer>=0.1.6",   # HF_HUB_ENABLE_HF_TRANSFER=1 needs this present
    )
    .add_local_dir(str(_HERE), REPRO_REMOTE, copy=True,
                   ignore=["__pycache__", "*.pyc"])
    .env({
        "CUBLAS_WORKSPACE_CONFIG": ":4096:8",
        "TRITON_CACHE_DIR": "/tmp/triton-cache",
        "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
        "PYTHONPATH": "/root",
    })
)

app = modal.App(APP_NAME)

TOKENIZER = "allenai/dolma2-tokenizer"          # vocab 100278 (padded to 100352)
VOCAB_PADDED = 100352
DEFAULT_DATASET = "allenai/dolma3_mix-150B-1025"  # 150B sample of the Olmo 3 mix


# --------------------------------------------------------------------------- #
# Data prep: stream raw text -> dolma2 token ids -> uint32 bins on the Volume.
# --------------------------------------------------------------------------- #
@app.function(image=image, cpu=16.0, memory=32768, timeout=6 * 60 * 60,
              volumes={DATA: VOL})
def prep_data(target_tokens: int, val_tokens: int = 8_000_000,
              dataset: str = DEFAULT_DATASET, text_field: str = "text",
              tag: str = "smoke", seed: int = 0) -> dict:
    """Tokenize `target_tokens` (+ val) tokens of `dataset` into the Volume.

    The dataset is 6k+ ``.jsonl.zst`` shards grouped by domain; the per-domain
    shard COUNT already encodes the Olmo 3 mixture proportions. We list every
    shard, DETERMINISTICALLY SHUFFLE it (so a small subset stays mixture-
    representative rather than all-one-domain), then read shards via zstandard
    until the token target is met. Train and val come from DISJOINT shards.

    Writes {DATA}/{tag}/train.bin, val.bin, manifest.json. manifest carries
    val_bytes (UTF-8 length of the decoded val span) so bpb is normalized by
    BYTES, not tokens.
    """
    import io
    import json
    import time

    import numpy as np
    import zstandard
    from huggingface_hub import HfApi, hf_hub_download
    from transformers import AutoTokenizer

    outdir = pathlib.Path(DATA) / tag
    outdir.mkdir(parents=True, exist_ok=True)
    tok = AutoTokenizer.from_pretrained(TOKENIZER)
    eos = tok.eos_token_id if tok.eos_token_id is not None else 0

    api = HfApi()
    shards = sorted(f.rfilename for f in api.dataset_info(dataset).siblings
                    if f.rfilename.endswith(".jsonl.zst"))
    order = np.random.default_rng(seed).permutation(len(shards))
    shards = [shards[i] for i in order]
    print(f"{len(shards)} shards; shuffled seed={seed}")

    need = int(target_tokens) + int(val_tokens)
    buf = np.empty(need + 4_000_000, dtype=np.uint32)
    n = 0
    dctx = zstandard.ZstdDecompressor()
    t0 = time.time()

    def append(texts):
        nonlocal n
        enc = tok(texts, add_special_tokens=False)["input_ids"]
        for ids in enc:
            m = len(ids) + 1
            if n + m > buf.shape[0]:
                m = buf.shape[0] - n
                if m <= 0:
                    return
            buf[n:n + m - 1] = np.asarray(ids[:m - 1], dtype=np.uint32)
            buf[n + m - 1] = eos
            n += m

    shards_used = 0
    for path in shards:
        if n >= need:
            break
        local = hf_hub_download(dataset, path, repo_type="dataset")
        batch = []
        with open(local, "rb") as fh:
            reader = io.TextIOWrapper(dctx.stream_reader(fh), encoding="utf-8")
            for line in reader:
                if not line.strip():
                    continue
                try:
                    t = json.loads(line).get(text_field)
                except Exception:
                    continue
                if not t:
                    continue
                batch.append(t)
                if len(batch) >= 1000:
                    append(batch); batch = []
                    if n >= need:
                        break
            if batch and n < need:
                append(batch)
        os.remove(local)  # keep container disk bounded
        shards_used += 1
        if shards_used % 10 == 0:
            print(f"  {shards_used} shards, {n/1e6:.1f}M/{need/1e6:.1f}M tok, "
                  f"{n/max(1e-9,time.time()-t0)/1e3:.0f}k tok/s")

    n = min(n, need)
    ids = buf[:n]
    hi = int(ids.max()) if n else 0
    assert hi < 100278, f"token id {hi} out of dolma2 vocab"

    val_ids = ids[-val_tokens:]
    train_ids = ids[:-val_tokens]
    train_ids.tofile(outdir / "train.bin")
    val_ids.tofile(outdir / "val.bin")

    val_text = tok.decode(val_ids.tolist(), skip_special_tokens=True)
    val_bytes = len(val_text.encode("utf-8"))
    manifest = {
        "tag": tag, "dataset": dataset, "tokenizer": TOKENIZER,
        "shards_used": shards_used, "seed": seed,
        "train_tokens": int(train_ids.size), "val_tokens": int(val_ids.size),
        "val_bytes": int(val_bytes),
        "val_bytes_per_token": val_bytes / max(1, val_ids.size),
        "seconds": round(time.time() - t0, 1),
    }
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    VOL.commit()
    print("prep_data done:", manifest)
    return manifest


# --------------------------------------------------------------------------- #
# Training: paper-faithful 190M model, WSD-S schedule, checkpoint to Volume.
# --------------------------------------------------------------------------- #
@app.function(image=image, cpu=8.0, memory=16384, timeout=6 * 60 * 60,
              volumes={DATA: VOL})
def _tokenize_shards(args) -> dict:
    """Worker: tokenize a list of shards -> one part_{idx}.bin on the Volume."""
    import io
    import json
    import time

    import numpy as np
    import zstandard
    from huggingface_hub import hf_hub_download
    from transformers import AutoTokenizer

    idx, paths, dataset, text_field, tag = args
    tok = AutoTokenizer.from_pretrained(TOKENIZER)
    eos = tok.eos_token_id if tok.eos_token_id is not None else 0
    dctx = zstandard.ZstdDecompressor()
    parts = pathlib.Path(DATA) / tag / "parts"
    parts.mkdir(parents=True, exist_ok=True)

    chunks, ntok, t0 = [], 0, time.time()
    for path in paths:
        local = hf_hub_download(dataset, path, repo_type="dataset")
        texts = []
        with open(local, "rb") as fh:
            reader = io.TextIOWrapper(dctx.stream_reader(fh), encoding="utf-8")
            for line in reader:
                if not line.strip():
                    continue
                try:
                    t = json.loads(line).get(text_field)
                except Exception:
                    continue
                if t:
                    texts.append(t)
                if len(texts) >= 1000:
                    enc = tok(texts, add_special_tokens=False)["input_ids"]
                    for ids in enc:
                        a = np.asarray(ids + [eos], dtype=np.uint32); chunks.append(a); ntok += a.size
                    texts = []
            if texts:
                enc = tok(texts, add_special_tokens=False)["input_ids"]
                for ids in enc:
                    a = np.asarray(ids + [eos], dtype=np.uint32); chunks.append(a); ntok += a.size
        os.remove(local)
    arr = np.concatenate(chunks) if chunks else np.empty(0, dtype=np.uint32)
    hi = int(arr.max()) if arr.size else 0
    assert hi < 100278, f"token id {hi} out of dolma2 vocab"
    outp = parts / f"part_{idx:04d}.bin"
    arr.tofile(outp)
    VOL.commit()
    return {"idx": idx, "tokens": int(arr.size), "shards": len(paths),
            "seconds": round(time.time() - t0, 1)}


@app.function(image=image, cpu=32.0, memory=65536, timeout=6 * 60 * 60,
              volumes={DATA: VOL})
def prep_data_parallel(target_tokens: int, val_tokens: int = 8_000_000,
                       dataset: str = DEFAULT_DATASET, tag: str = "run",
                       n_workers: int = 32, tokens_per_shard_est: int = 22_000_000,
                       headroom: float = 1.35, seed: int = 0) -> dict:
    """Fan-out tokenization: split a shuffled shard subset across workers, then
    concatenate the parts into train.bin / val.bin (+ manifest)."""
    import json
    import time

    import numpy as np
    from huggingface_hub import HfApi
    from transformers import AutoTokenizer

    outdir = pathlib.Path(DATA) / tag
    outdir.mkdir(parents=True, exist_ok=True)
    api = HfApi()
    shards = sorted(f.rfilename for f in api.dataset_info(dataset).siblings
                    if f.rfilename.endswith(".jsonl.zst"))
    order = np.random.default_rng(seed).permutation(len(shards))
    shards = [shards[i] for i in order]

    need = int(target_tokens) + int(val_tokens)
    n_shards = min(len(shards), int(np.ceil(need / tokens_per_shard_est * headroom)))
    picked = shards[:n_shards]
    # Round-robin assign so each worker gets a mixture-representative slice.
    buckets = [[] for _ in range(n_workers)]
    for i, p in enumerate(picked):
        buckets[i % n_workers].append(p)
    jobs = [(i, b, dataset, "text", tag) for i, b in enumerate(buckets) if b]
    print(f"{len(picked)} shards over {len(jobs)} workers (need {need/1e6:.0f}M tok)")

    t0 = time.time()
    results = sorted(_tokenize_shards.map(jobs), key=lambda r: r["idx"])
    total = sum(r["tokens"] for r in results)
    print(f"tokenized {total/1e6:.0f}M tok in {(time.time()-t0)/60:.1f}m across workers")
    if total < need:
        print(f"WARNING: only {total/1e6:.0f}M < need {need/1e6:.0f}M; increase headroom")

    # Concatenate parts in worker order into train.bin, then val.bin.
    VOL.reload()
    parts = sorted((outdir / "parts").glob("part_*.bin"))
    train_target = int(target_tokens)
    written_train = 0
    ftrain = open(outdir / "train.bin", "wb")
    val_arrs, val_have = [], 0
    for pf in parts:
        a = np.fromfile(pf, dtype=np.uint32)
        if written_train < train_target:
            take = min(a.size, train_target - written_train)
            a[:take].tofile(ftrain); written_train += take
            rest = a[take:]
        else:
            rest = a
        if rest.size and val_have < val_tokens:
            need_v = val_tokens - val_have
            val_arrs.append(rest[:need_v]); val_have += min(rest.size, need_v)
    ftrain.close()
    val_ids = np.concatenate(val_arrs) if val_arrs else np.empty(0, dtype=np.uint32)
    val_ids.tofile(outdir / "val.bin")

    tok = AutoTokenizer.from_pretrained(TOKENIZER)
    val_text = tok.decode(val_ids.tolist(), skip_special_tokens=True)
    val_bytes = len(val_text.encode("utf-8"))
    for pf in parts:  # free part files
        pf.unlink()
    manifest = {
        "tag": tag, "dataset": dataset, "tokenizer": TOKENIZER,
        "shards_used": len(picked), "n_workers": len(jobs), "seed": seed,
        "train_tokens": int(written_train), "val_tokens": int(val_ids.size),
        "val_bytes": int(val_bytes),
        "val_bytes_per_token": val_bytes / max(1, val_ids.size),
        "prep_minutes": round((time.time() - t0) / 60, 1),
    }
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    VOL.commit()
    print("prep_data_parallel done:", manifest)
    return manifest


@app.function(image=image, gpu="H100", memory=32768, timeout=12 * 60 * 60,
              volumes={DATA: VOL})
def train(arm: str = "transformer", target_tokens: int = 20_000_000,
          tag: str = "smoke", seq_len: int = 4096,
          # micro_batch defaults are ARM-AWARE (0 = auto): the transformer fits
          # mb=8 (fp32 logits ~13GB), but the hybrid's fla GDN autotuner needs
          # more headroom and OOMs at mb=8, so it uses mb=4. Effective batch is
          # held at 128 sequences via grad_accum = 128 // micro_batch.
          micro_batch: int = 0, grad_accum: int = 0,
          peak_lr: float = 2.0e-3, warmup_frac: float = 0.02,
          weight_decay: float = 0.1, beta1: float = 0.9, beta2: float = 0.95,
          grad_clip: float = 1.0, log_every: int = 25, seed: int = 1337) -> dict:
    """Train one arm for ~target_tokens tokens with WSD-S; log held-out CE."""
    import json
    import sys
    import time

    import numpy as np
    import torch
    import torch.nn.functional as F

    sys.path.insert(0, "/root")
    from repro import paper_models, wsd

    torch.manual_seed(seed)
    dev = "cuda"
    ddir = pathlib.Path(DATA) / tag
    # memmap the 15GB train stream (read-only) so it isn't loaded into RAM.
    train_ids = np.memmap(ddir / "train.bin", dtype=np.uint32, mode="r")
    val_ids = np.fromfile(ddir / "val.bin", dtype=np.uint32)  # small (~32MB)
    manifest = json.loads((ddir / "manifest.json").read_text())
    bytes_per_tok = float(manifest["val_bytes_per_token"])

    class Cfg:
        vocab_size = VOCAB_PADDED
        block_size = seq_len
        eval_block_size = seq_len

    build = paper_models.build_transformer if arm == "transformer" else paper_models.build_hybrid
    model = build(Cfg()).to(dev)
    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    n_non_emb = n_params - model.wte.weight.numel()

    if not micro_batch:
        micro_batch = 4 if arm == "hybrid" else 8
    if not grad_accum:
        grad_accum = max(1, 128 // micro_batch)
    tokens_per_step = micro_batch * grad_accum * seq_len
    total_steps = max(1, int(target_tokens) // tokens_per_step)
    warmup_steps = max(1, int(warmup_frac * total_steps))

    decay, no_decay = [], []
    for p in model.parameters():
        (decay if p.dim() >= 2 else no_decay).append(p)
    opt = torch.optim.AdamW(
        [{"params": decay, "weight_decay": weight_decay},
         {"params": no_decay, "weight_decay": 0.0}],
        lr=peak_lr, betas=(beta1, beta2),
    )

    rng = np.random.default_rng(seed)
    hi = train_ids.size - seq_len - 1

    def get_batch(nseq):
        ix = rng.integers(0, hi, size=nseq)
        x = np.stack([train_ids[i:i + seq_len] for i in ix]).astype(np.int64)
        y = np.stack([train_ids[i + 1:i + 1 + seq_len] for i in ix]).astype(np.int64)
        return (torch.from_numpy(x).pin_memory().to(dev, non_blocking=True),
                torch.from_numpy(y).pin_memory().to(dev, non_blocking=True))

    @torch.no_grad()
    def eval_ce(max_windows=24):
        model.eval()
        n = min(val_ids.size - 1, max_windows * seq_len)
        nw = n // seq_len
        tot_ce, tot_tok = 0.0, 0
        for w in range(nw):
            s = w * seq_len
            x = torch.from_numpy(val_ids[s:s + seq_len][None].astype(np.int64)).to(dev)
            y = torch.from_numpy(val_ids[s + 1:s + 1 + seq_len][None].astype(np.int64)).to(dev)
            logits = model(x).float()
            tot_ce += float(F.cross_entropy(logits.reshape(-1, logits.size(-1)),
                                            y.reshape(-1), reduction="sum"))
            tot_tok += y.numel()
        model.train()
        mean_ce = tot_ce / max(1, tot_tok)
        val_bpb = tot_ce / (tot_tok * bytes_per_tok * np.log(2))
        return mean_ce, val_bpb

    logpath = ddir / f"train_{arm}.log"
    log_lines = []

    def log(msg):
        print(msg, flush=True)
        log_lines.append(msg)

    log(f"[{arm}] non_emb={n_non_emb/1e6:.1f}M total={n_params/1e6:.1f}M "
        f"tokens/step={tokens_per_step} total_steps={total_steps} warmup={warmup_steps} "
        f"target_tokens={target_tokens}")

    t0 = time.time()
    for step in range(total_steps):
        lr = wsd.lr_wsd(step, peak_lr=peak_lr, total_steps=total_steps,
                        warmup_steps=warmup_steps)
        for pg in opt.param_groups:
            pg["lr"] = lr
        opt.zero_grad(set_to_none=True)
        loss_acc = 0.0
        for _ in range(grad_accum):
            x, y = get_batch(micro_batch)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                logits = model(x)
                loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)).float(),
                                       y.reshape(-1)) / grad_accum
            loss.backward()
            loss_acc += float(loss) * grad_accum
        torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
        opt.step()

        if step % log_every == 0 or step == total_steps - 1:
            toks = (step + 1) * tokens_per_step
            dt = time.time() - t0
            tps = toks / max(1e-9, dt)
            log(f"[{arm}] step {step:5d}/{total_steps} lr={lr:.2e} "
                f"train_ce={loss_acc/grad_accum:.4f} tok={toks/1e6:.1f}M "
                f"{tps/1e3:.0f}k tok/s wall={dt/60:.1f}m")
            # Flush progress to the Volume so DETACHED runs are observable
            # without a live client (see modal run --detach).
            logpath.write_text("\n".join(log_lines))
            VOL.commit()

    mean_ce, val_bpb = eval_ce()
    wall = time.time() - t0
    ckpt = ddir / f"ckpt_{arm}.pt"
    torch.save({"model": model.state_dict(), "arm": arm, "cfg_vocab": VOCAB_PADDED,
                "seq_len": seq_len, "target_tokens": target_tokens}, ckpt)
    logpath.write_text("\n".join(log_lines))
    VOL.commit()
    result = {
        "arm": arm, "n_non_emb_M": round(n_non_emb / 1e6, 1),
        "total_steps": total_steps, "tokens_trained_M": round(total_steps * tokens_per_step / 1e6, 1),
        "final_train_ce": round(loss_acc / grad_accum, 4),
        "val_ce_nats": round(mean_ce, 4), "val_bpb_lm": round(val_bpb, 4),
        "wall_min": round(wall / 60, 1),
        "tok_per_s_k": round(total_steps * tokens_per_step / wall / 1e3, 1),
        "gpu": torch.cuda.get_device_name(0),
    }
    log(f"[{arm}] DONE {result}")
    return result


@app.local_entrypoint()
def main(action: str = "prep", arm: str = "transformer",
         target_tokens: int = 20_000_000, tag: str = "smoke"):
    if action == "prep":
        print(prep_data.remote(target_tokens=target_tokens, tag=tag))
    elif action == "prep_par":
        print(prep_data_parallel.remote(target_tokens=target_tokens, tag=tag))
    elif action == "train":
        print(train.remote(arm=arm, target_tokens=target_tokens, tag=tag))
    else:
        raise SystemExit(f"unknown action {action!r}")
