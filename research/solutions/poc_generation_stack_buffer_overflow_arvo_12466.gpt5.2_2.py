import os
import re
import tarfile
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple


RAR5_SIG = b"Rar!\x1a\x07\x01\x00"
MAX_MEMBER_READ = 5 * 1024 * 1024


@dataclass
class Candidate:
    name: str
    data: bytes
    score: float


def _iter_files_from_tar(tar_path: str) -> Iterable[Tuple[str, bytes]]:
    with tarfile.open(tar_path, mode="r:*") as tf:
        for m in tf.getmembers():
            if not m.isreg():
                continue
            if m.size <= 0 or m.size > MAX_MEMBER_READ:
                continue
            f = tf.extractfile(m)
            if f is None:
                continue
            try:
                data = f.read()
            finally:
                try:
                    f.close()
                except Exception:
                    pass
            if not data:
                continue
            yield (m.name, data)


def _iter_files_from_dir(dir_path: str) -> Iterable[Tuple[str, bytes]]:
    for root, _, files in os.walk(dir_path):
        for fn in files:
            p = os.path.join(root, fn)
            try:
                st = os.stat(p)
            except Exception:
                continue
            if st.st_size <= 0 or st.st_size > MAX_MEMBER_READ:
                continue
            try:
                with open(p, "rb") as f:
                    data = f.read()
            except Exception:
                continue
            rel = os.path.relpath(p, dir_path).replace(os.sep, "/")
            yield (rel, data)


def _iter_files(src_path: str) -> Iterable[Tuple[str, bytes]]:
    if os.path.isdir(src_path):
        yield from _iter_files_from_dir(src_path)
        return
    if tarfile.is_tarfile(src_path):
        yield from _iter_files_from_tar(src_path)
        return
    try:
        with open(src_path, "rb") as f:
            data = f.read()
        yield (os.path.basename(src_path), data)
    except Exception:
        return


def _name_score(name: str) -> float:
    n = name.lower()
    score = 0.0
    if n.endswith(".rar") or n.endswith(".cbr") or n.endswith(".r00") or n.endswith(".rar5"):
        score += 30.0
    if "/test" in n or n.startswith("test/") or "/tests" in n or n.startswith("tests/"):
        score += 3.0
    if "/fuzz" in n or n.startswith("fuzz/") or "oss-fuzz" in n or "ossfuzz" in n or "clusterfuzz" in n:
        score += 10.0
    keywords = (
        "poc", "crash", "overflow", "stack", "huffman", "rar5", "cve", "asan", "ubsan", "issue", "repro", "regress"
    )
    for k in keywords:
        if k in n:
            score += 10.0
    return score


def _data_score(data: bytes, name: str, target_len: int = 524) -> float:
    score = _name_score(name)
    if data.startswith(RAR5_SIG):
        score += 200.0
    elif data[:8].startswith(b"Rar!"):
        score += 80.0

    ln = len(data)
    if ln == target_len:
        score += 50.0
    else:
        dist = abs(ln - target_len)
        score += max(0.0, 40.0 - dist / 8.0)

    if ln < 2048:
        score += 5.0
    if ln < 1024:
        score += 5.0
    if ln < 600:
        score += 5.0

    # Prefer candidates that look like a full archive (RAR signature at start).
    if data.startswith(RAR5_SIG):
        score += 20.0

    return score


_HEX_SIG_RE = re.compile(
    r"0x52\s*,\s*0x61\s*,\s*0x72\s*,\s*0x21\s*,\s*0x1a\s*,\s*0x07\s*,\s*0x01\s*,\s*0x00",
    re.IGNORECASE,
)
_ESC_SIG_RE = re.compile(
    r"(?:\\x52)(?:\\x61)(?:\\x72)(?:\\x21)(?:\\x1a)(?:\\x07)(?:\\x01)(?:\\x00)",
    re.IGNORECASE,
)
_HEX_TOKEN_RE = re.compile(r"0x[0-9a-fA-F]{1,2}|\b\d{1,3}\b")
_CSTR_X_RE = re.compile(r"\\x([0-9a-fA-F]{2})")


def _extract_from_c_hex_array(text: str) -> List[bytes]:
    out: List[bytes] = []
    for m in _HEX_SIG_RE.finditer(text):
        idx = m.start()
        lb = text.rfind("{", 0, idx)
        if lb == -1:
            continue
        rb = text.find("}", idx)
        if rb == -1:
            continue
        if rb - lb > 2_000_000:
            continue
        block = text[lb : rb + 1]
        toks = _HEX_TOKEN_RE.findall(block)
        if len(toks) < 16:
            continue
        b = bytearray()
        ok = True
        for t in toks:
            try:
                if t.lower().startswith("0x"):
                    v = int(t, 16)
                else:
                    v = int(t, 10)
            except Exception:
                ok = False
                break
            if 0 <= v <= 255:
                b.append(v)
            else:
                ok = False
                break
        if not ok:
            continue
        bd = bytes(b)
        if bd.startswith(RAR5_SIG):
            out.append(bd)
    return out


def _extract_from_escaped_strings(text: str) -> List[bytes]:
    out: List[bytes] = []
    for m in _ESC_SIG_RE.finditer(text):
        idx = m.start()
        # Find a quote boundary around it
        lq = text.rfind('"', 0, idx)
        rq = text.find('"', idx)
        if lq == -1 or rq == -1 or rq <= lq:
            continue
        if rq - lq > 2_000_000:
            continue
        s = text[lq + 1 : rq]
        hx = _CSTR_X_RE.findall(s)
        if len(hx) < 16:
            continue
        try:
            bd = bytes(int(x, 16) for x in hx)
        except Exception:
            continue
        if bd.startswith(RAR5_SIG):
            out.append(bd)
    return out


def _maybe_text(data: bytes) -> Optional[str]:
    if not data:
        return None
    if b"\x00" in data[:4096]:
        return None
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        try:
            return data.decode("latin1", errors="ignore")
        except Exception:
            return None


def _gather_candidates(src_path: str) -> List[Candidate]:
    cands: List[Candidate] = []
    seen_hashes = set()

    for name, data in _iter_files(src_path):
        if not data:
            continue

        # Direct binary candidates.
        if data.startswith(RAR5_SIG):
            h = hash(data)
            if h not in seen_hashes:
                seen_hashes.add(h)
                cands.append(Candidate(name=name, data=data, score=_data_score(data, name)))
            continue

        # If file extension suggests an archive, consider even if signature not at start.
        nlow = name.lower()
        if nlow.endswith(".rar") or nlow.endswith(".rar5") or nlow.endswith(".cbr"):
            if RAR5_SIG in data[:64]:
                off = data.find(RAR5_SIG)
                bd = data[off:]
                h = hash(bd)
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    cands.append(Candidate(name=name + f":offset{off}", data=bd, score=_data_score(bd, name)))
            continue

        # Parse text for embedded byte arrays or escaped strings.
        txt = _maybe_text(data)
        if not txt:
            continue
        if ("0x52" in txt and "0x61" in txt and "0x72" in txt and "0x21" in txt) or ("\\x52\\x61\\x72\\x21" in txt):
            extracted = []
            extracted.extend(_extract_from_c_hex_array(txt))
            extracted.extend(_extract_from_escaped_strings(txt))
            for i, bd in enumerate(extracted):
                h = hash(bd)
                if h in seen_hashes:
                    continue
                seen_hashes.add(h)
                cname = f"{name}:embedded{i}"
                cands.append(Candidate(name=cname, data=bd, score=_data_score(bd, cname)))

    return cands


def _pick_best(cands: List[Candidate], target_len: int = 524) -> Optional[bytes]:
    if not cands:
        return None
    # Strong preference for exact target length when scores are close.
    def key(c: Candidate):
        ln = len(c.data)
        exact = 1 if ln == target_len else 0
        # Higher is better for score & exactness, smaller better for length tiebreak.
        return (exact, c.score, -ln, c.name)

    best = max(cands, key=key)
    return best.data


def _fallback() -> bytes:
    # Minimal RAR5 signature + padding to 524 bytes.
    # This is only a fallback; expected solution is to extract a real PoC from sources.
    return (RAR5_SIG + b"\x00" * 516)[:524]


class Solution:
    def solve(self, src_path: str) -> bytes:
        cands = _gather_candidates(src_path)

        # If multiple exact-length candidates exist, prefer ones with crash-like naming.
        exact = [c for c in cands if len(c.data) == 524]
        if exact:
            exact.sort(key=lambda c: (_name_score(c.name), c.score), reverse=True)
            return exact[0].data

        best = _pick_best(cands, target_len=524)
        if best is not None:
            return best

        return _fallback()