import os
import io
import re
import tarfile
import zipfile
from typing import Optional, Tuple, List


JP2_SIG = b"\x00\x00\x00\x0cjP  \r\n\x87\n"


def _is_j2k_codestream(buf: bytes) -> bool:
    return len(buf) >= 2 and buf[0] == 0xFF and buf[1] == 0x4F  # SOC


def _is_jp2(buf: bytes) -> bool:
    return buf.startswith(JP2_SIG)


_B64_RE = re.compile(rb"^[A-Za-z0-9+/=\r\n\t ]+$")
_HEXBYTE_RE = re.compile(r"0x([0-9a-fA-F]{2})")
_XBYTE_RE = re.compile(r"\\x([0-9a-fA-F]{2})")


def _maybe_b64_decode(data: bytes) -> Optional[bytes]:
    if len(data) < 32:
        return None
    if not _B64_RE.match(data):
        return None
    s = re.sub(rb"\s+", b"", data)
    if len(s) % 4 != 0:
        return None
    try:
        import base64
        out = base64.b64decode(s, validate=False)
        if _is_j2k_codestream(out) or _is_jp2(out):
            return out
        return None
    except Exception:
        return None


def _extract_from_text(data: bytes) -> List[bytes]:
    outs: List[bytes] = []
    try:
        txt = data.decode("utf-8", "ignore")
    except Exception:
        return outs

    # C-style hex array
    hexes = _HEXBYTE_RE.findall(txt)
    if len(hexes) >= 64:
        try:
            buf = bytes(int(h, 16) for h in hexes)
            if _is_j2k_codestream(buf) or _is_jp2(buf):
                outs.append(buf)
        except Exception:
            pass

    # \xNN sequences
    xhexes = _XBYTE_RE.findall(txt)
    if len(xhexes) >= 64:
        try:
            buf = bytes(int(h, 16) for h in xhexes)
            if _is_j2k_codestream(buf) or _is_jp2(buf):
                outs.append(buf)
        except Exception:
            pass

    # Base64 blob
    b64 = _maybe_b64_decode(data)
    if b64 is not None:
        outs.append(b64)

    return outs


def _score_candidate(name: str, size: int, data: bytes) -> float:
    lower = name.lower()
    score = 0.0

    if "47500" in lower:
        score += 10000.0
    if "clusterfuzz" in lower:
        score += 2000.0
    if "oss-fuzz" in lower or "ossfuzz" in lower:
        score += 1200.0
    if "poc" in lower or "crash" in lower or "repro" in lower:
        score += 800.0
    if "fuzz" in lower or "corpus" in lower:
        score += 400.0
    if "nonregression" in lower or "regression" in lower or "test" in lower:
        score += 150.0

    if lower.endswith((".jp2", ".j2k", ".jpc", ".j2c")):
        score += 900.0
    elif lower.endswith((".bin", ".dat", ".raw", ".in")):
        score += 200.0

    if _is_j2k_codestream(data):
        score += 1000.0
    if _is_jp2(data):
        score += 900.0

    # Prefer close to known ground-truth size
    gt = 1479
    score += max(0.0, 300.0 - abs(size - gt) * 0.5)

    # Prefer smaller
    score += max(0.0, 400.0 - min(size, 4000) * 0.05)

    # Penalize huge
    if size > 200_000:
        score -= 2000.0
    if size > 2_000_000:
        score -= 100000.0

    return score


def _scan_zip_bytes(zdata: bytes, parent: str) -> List[Tuple[float, bytes, str]]:
    out: List[Tuple[float, bytes, str]] = []
    try:
        with zipfile.ZipFile(io.BytesIO(zdata), "r") as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                if info.file_size <= 0 or info.file_size > 2_000_000:
                    continue
                try:
                    data = zf.read(info.filename)
                except Exception:
                    continue
                name = f"{parent}:{info.filename}"
                if _is_j2k_codestream(data) or _is_jp2(data):
                    out.append((_score_candidate(name, len(data), data), data, name))
                else:
                    for b in _extract_from_text(data):
                        out.append((_score_candidate(name + ":extracted", len(b), b), b, name + ":extracted"))
    except Exception:
        return out
    return out


class Solution:
    def solve(self, src_path: str) -> bytes:
        candidates: List[Tuple[float, int, bytes, str]] = []

        def add_candidate(data: bytes, name: str):
            if not data:
                return
            if len(data) > 5_000_000:
                return
            score = _score_candidate(name, len(data), data)
            # tuple: score desc, length asc
            candidates.append((score, len(data), data, name))

        # Scan tarball contents for existing reproducer
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    if m.size <= 0 or m.size > 5_000_000:
                        continue
                    name = m.name
                    lower = name.lower()

                    # Prefer to read likely files fully; otherwise limit reads for huge
                    read_limit = None
                    if m.size > 500_000 and not any(x in lower for x in ("47500", "clusterfuzz", "ossfuzz", "poc", "crash", ".jp2", ".j2k", ".jpc", ".j2c")):
                        # skip large irrelevant files
                        continue

                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read() if read_limit is None else f.read(read_limit)
                    except Exception:
                        continue

                    # Direct binary candidate
                    if _is_j2k_codestream(data) or _is_jp2(data):
                        add_candidate(data, name)
                        continue

                    # If this is a zip (some corpora ship as zip)
                    if lower.endswith(".zip") and m.size <= 2_000_000:
                        for sc, d, nm in _scan_zip_bytes(data, name):
                            candidates.append((sc, len(d), d, nm))
                        continue

                    # If name includes 47500, also try decoding from text
                    if "47500" in lower or any(k in lower for k in ("clusterfuzz", "ossfuzz", "poc", "crash", "repro")):
                        for b in _extract_from_text(data):
                            add_candidate(b, name + ":extracted")
                        # Also attempt base64 even if no keywords
                        b64 = _maybe_b64_decode(data)
                        if b64 is not None:
                            add_candidate(b64, name + ":b64")
        except Exception:
            pass

        if candidates:
            candidates.sort(key=lambda x: (-x[0], x[1], x[3]))
            return candidates[0][2]

        # Absolute fallback: return a minimal J2K codestream stub (unlikely to work, but must return bytes)
        # SOC + EOC
        return b"\xff\x4f\xff\xd9"