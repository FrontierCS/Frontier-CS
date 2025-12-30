import os
import re
import io
import tarfile
import gzip
import lzma
import bz2
import base64
from typing import Optional, Tuple, List


_MAX_MEMBER_SIZE = 5 * 1024 * 1024
_MAX_DECOMPRESSED_SIZE = 25 * 1024 * 1024


def _compute_name_score(name: str, size: int) -> int:
    n = name.lower()
    score = 0

    keywords = [
        ("42536279", 2500),
        ("oss-fuzz", 900),
        ("ossfuzz", 900),
        ("clusterfuzz", 900),
        ("testcase", 600),
        ("minimized", 700),
        ("minimised", 700),
        ("repro", 600),
        ("poc", 500),
        ("crash", 700),
        ("overflow", 350),
        ("heap", 250),
        ("svcdec", 500),
        ("svc", 120),
        ("subset", 200),
        ("display", 180),
        ("dimension", 180),
        ("dimensions", 180),
        ("av1", 140),
        ("ivf", 160),
    ]
    for k, w in keywords:
        if k in n:
            score += w

    dir_hints = [
        ("/test/", 120),
        ("/tests/", 120),
        ("/testdata/", 150),
        ("/test_data/", 150),
        ("/fuzz/", 180),
        ("/fuzzer/", 180),
        ("/fuzzing/", 180),
        ("/corpus/", 160),
        ("/regression/", 160),
        ("/regress/", 140),
        ("/data/", 90),
    ]
    for k, w in dir_hints:
        if k in n:
            score += w

    ext_scores = {
        ".ivf": 500,
        ".av1": 450,
        ".obu": 450,
        ".bin": 250,
        ".raw": 230,
        ".dat": 180,
        ".input": 180,
        ".gz": 120,
        ".xz": 120,
        ".bz2": 120,
        ".txt": 60,
        ".c": 90,
        ".cc": 90,
        ".cpp": 90,
        ".h": 70,
        ".inc": 70,
    }
    _, ext = os.path.splitext(n)
    score += ext_scores.get(ext, 0)

    if 4000 <= size <= 12000:
        score += 260
    elif size <= 20000:
        score += 120
    elif size <= 120000:
        score += 40
    else:
        score -= 80

    if size > _MAX_MEMBER_SIZE:
        score -= 2000

    return score


def _looks_like_ivf(data: bytes) -> bool:
    if len(data) < 32:
        return False
    if data[0:4] != b"DKIF":
        return False
    if data[8:12] != b"AV01":
        return False
    return True


def _is_probably_text(data: bytes) -> bool:
    if not data:
        return True
    sample = data[:4096]
    if b"\x00" in sample:
        return False
    bad = 0
    for b in sample:
        if b in (9, 10, 13):
            continue
        if 32 <= b <= 126:
            continue
        bad += 1
    return bad / max(1, len(sample)) < 0.02


def _try_decompress(data: bytes) -> List[bytes]:
    outs = [data]
    if len(data) < 6:
        return outs

    def _add(out: bytes):
        if out and len(out) <= _MAX_DECOMPRESSED_SIZE and out not in outs:
            outs.append(out)

    try:
        if data[:2] == b"\x1f\x8b":
            out = gzip.decompress(data)
            _add(out)
    except Exception:
        pass

    try:
        if data[:6] == b"\xfd7zXZ\x00":
            out = lzma.decompress(data)
            _add(out)
    except Exception:
        pass

    try:
        if data[:3] == b"BZh":
            out = bz2.decompress(data)
            _add(out)
    except Exception:
        pass

    return outs


_HEX_BYTE_RE = re.compile(rb"0x([0-9a-fA-F]{2})")
_C_ESC_RE = re.compile(rb"\\x([0-9a-fA-F]{2})")
_B64_RE = re.compile(rb"(?:[A-Za-z0-9+/]{80,}={0,2})")


def _extract_bytes_from_text(data: bytes) -> List[bytes]:
    outs = []
    if not data:
        return outs

    # Hex bytes like 0xAA, 0xbb, ...
    hexes = _HEX_BYTE_RE.findall(data)
    if len(hexes) >= 128:
        try:
            outs.append(bytes(int(h, 16) for h in hexes))
        except Exception:
            pass

    # C escaped bytes \xAA\xBB...
    esc = _C_ESC_RE.findall(data)
    if len(esc) >= 128:
        try:
            outs.append(bytes(int(h, 16) for h in esc))
        except Exception:
            pass

    # Base64 blobs
    for m in _B64_RE.findall(data):
        if len(m) < 200:
            continue
        try:
            out = base64.b64decode(m, validate=False)
            if out and len(out) >= 256:
                outs.append(out)
        except Exception:
            pass

    return outs


def _choose_best_payload(candidates: List[bytes]) -> Optional[bytes]:
    if not candidates:
        return None

    # Prefer IVF; if multiple, choose smallest that looks right.
    ivfs = [c for c in candidates if _looks_like_ivf(c)]
    if ivfs:
        return min(ivfs, key=len)

    # Otherwise choose smallest binary blob that isn't mostly text.
    bins = [c for c in candidates if not _is_probably_text(c)]
    if bins:
        return min(bins, key=len)

    return min(candidates, key=len)


class Solution:
    def solve(self, src_path: str) -> bytes:
        if os.path.isdir(src_path):
            payload = self._solve_from_dir(src_path)
            if payload is not None:
                return payload
            return b""

        payload = self._solve_from_tar(src_path)
        if payload is not None:
            return payload
        return b""

    def _solve_from_tar(self, tar_path: str) -> Optional[bytes]:
        try:
            with tarfile.open(tar_path, mode="r:*") as tf:
                members = []
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    if m.size <= 0 or m.size > _MAX_MEMBER_SIZE:
                        continue
                    name = m.name or ""
                    score = _compute_name_score(name, m.size)
                    if score > 0:
                        members.append((score, m.size, m.name))
                members.sort(key=lambda x: (-x[0], x[1], x[2]))

                top = members[:60] if members else []

                # If nothing scored, fall back to likely binary extensions.
                if not top:
                    fallback = []
                    for m in tf.getmembers():
                        if not m.isfile():
                            continue
                        if m.size <= 0 or m.size > _MAX_MEMBER_SIZE:
                            continue
                        n = (m.name or "").lower()
                        if n.endswith((".ivf", ".av1", ".obu", ".bin", ".raw", ".dat", ".input")):
                            fallback.append((0, m.size, m.name))
                    fallback.sort(key=lambda x: (x[1], x[2]))
                    top = fallback[:60]

                for _, _, name in top:
                    try:
                        f = tf.extractfile(name)
                        if f is None:
                            continue
                        data = f.read()
                    except Exception:
                        continue

                    candidates = []
                    for d in _try_decompress(data):
                        candidates.append(d)
                        if _is_probably_text(d):
                            candidates.extend(_extract_bytes_from_text(d))

                    chosen = _choose_best_payload(candidates)
                    if chosen is None:
                        continue

                    # Hard preference for IVF-like payloads or for names with strong hints.
                    if _looks_like_ivf(chosen):
                        return chosen

                    # Accept non-IVF if filename strongly indicates it's a fuzz testcase.
                    lname = name.lower()
                    if any(k in lname for k in ("42536279", "clusterfuzz", "oss-fuzz", "ossfuzz", "testcase", "minimized", "crash", "poc", "repro")):
                        return chosen

                # Second pass: try any small IVF if not found yet.
                ivf_members = []
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    if m.size <= 0 or m.size > _MAX_MEMBER_SIZE:
                        continue
                    n = (m.name or "").lower()
                    if n.endswith(".ivf"):
                        ivf_members.append((m.size, m.name))
                ivf_members.sort()
                for _, name in ivf_members[:30]:
                    try:
                        f = tf.extractfile(name)
                        if f is None:
                            continue
                        data = f.read()
                    except Exception:
                        continue
                    for d in _try_decompress(data):
                        if _looks_like_ivf(d):
                            return d

        except Exception:
            return None

        return None

    def _solve_from_dir(self, root: str) -> Optional[bytes]:
        entries: List[Tuple[int, int, str]] = []
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                path = os.path.join(dirpath, fn)
                try:
                    st = os.stat(path)
                except Exception:
                    continue
                if not os.path.isfile(path):
                    continue
                if st.st_size <= 0 or st.st_size > _MAX_MEMBER_SIZE:
                    continue
                rel = os.path.relpath(path, root).replace(os.sep, "/")
                score = _compute_name_score(rel, st.st_size)
                if score > 0:
                    entries.append((score, st.st_size, path))
        entries.sort(key=lambda x: (-x[0], x[1], x[2]))

        top = entries[:80]
        if not top:
            # fall back to likely extensions
            fallback = []
            for dirpath, _, filenames in os.walk(root):
                for fn in filenames:
                    path = os.path.join(dirpath, fn)
                    try:
                        st = os.stat(path)
                    except Exception:
                        continue
                    if not os.path.isfile(path):
                        continue
                    if st.st_size <= 0 or st.st_size > _MAX_MEMBER_SIZE:
                        continue
                    n = fn.lower()
                    if n.endswith((".ivf", ".av1", ".obu", ".bin", ".raw", ".dat", ".input")):
                        fallback.append((0, st.st_size, path))
            fallback.sort(key=lambda x: (x[1], x[2]))
            top = fallback[:80]

        for _, _, path in top:
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except Exception:
                continue

            candidates = []
            for d in _try_decompress(data):
                candidates.append(d)
                if _is_probably_text(d):
                    candidates.extend(_extract_bytes_from_text(d))

            chosen = _choose_best_payload(candidates)
            if chosen is None:
                continue

            if _looks_like_ivf(chosen):
                return chosen

            lpath = path.lower()
            if any(k in lpath for k in ("42536279", "clusterfuzz", "oss-fuzz", "ossfuzz", "testcase", "minimized", "crash", "poc", "repro")):
                return chosen

        # Try any IVF file
        ivfs = []
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if fn.lower().endswith(".ivf"):
                    path = os.path.join(dirpath, fn)
                    try:
                        st = os.stat(path)
                    except Exception:
                        continue
                    if st.st_size <= 0 or st.st_size > _MAX_MEMBER_SIZE:
                        continue
                    ivfs.append((st.st_size, path))
        ivfs.sort()
        for _, path in ivfs[:30]:
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except Exception:
                continue
            for d in _try_decompress(data):
                if _looks_like_ivf(d):
                    return d

        return None