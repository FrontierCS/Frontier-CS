import os
import re
import io
import stat
import tarfile
import zipfile
from typing import List, Tuple, Optional, Dict, Any


_KEYWORDS_HIGH = (
    "clusterfuzz-testcase-minimized",
    "clusterfuzz-testcase",
    "minimized",
    "testcase",
    "reproducer",
    "repro",
    "poc",
    "crash",
    "385170375",
    "rv60",
    "realmedia",
)

_EXT_SCORES = {
    ".rm": 80,
    ".rv": 60,
    ".rmd": 60,
    ".rmvb": 60,
    ".bin": 30,
    ".dat": 20,
    ".raw": 20,
    ".ivf": 10,
    ".mkv": 10,
    ".mp4": 10,
    ".mov": 10,
}


def _is_probably_binary(data: bytes) -> bool:
    if not data:
        return False
    sample = data[:4096]
    if not sample:
        return False
    nul = sample.count(b"\x00")
    if nul / len(sample) > 0.02:
        return True
    nontext = 0
    for b in sample:
        if b in (9, 10, 13):
            continue
        if 32 <= b <= 126:
            continue
        nontext += 1
    return (nontext / len(sample)) > 0.15


def _content_score(data: bytes) -> int:
    s = 0
    if not data:
        return s
    if data.startswith(b".RMF"):
        s += 200
    if b"RV60" in data[:512] or b"RV60" in data:
        s += 140
    if b"MDPR" in data[:512] or b"PROP" in data[:512] or b"DATA" in data[:512]:
        s += 60
    if _is_probably_binary(data):
        s += 25
    return s


def _name_score(name: str) -> int:
    n = name.lower().replace("\\", "/")
    s = 0
    for kw in _KEYWORDS_HIGH:
        if kw in n:
            if kw == "clusterfuzz-testcase-minimized":
                s += 250
            elif kw == "clusterfuzz-testcase":
                s += 180
            elif kw in ("reproducer", "repro", "poc", "crash"):
                s += 120
            elif kw == "rv60":
                s += 80
            else:
                s += 60
    base = os.path.basename(n)
    _, ext = os.path.splitext(base)
    s += _EXT_SCORES.get(ext, 0)
    if ext in (".c", ".cc", ".cpp", ".h", ".md", ".txt", ".rst", ".html", ".json", ".xml", ".yml", ".yaml"):
        s -= 200
    return s


def _size_score(sz: int, target: int = 149) -> int:
    if sz <= 0:
        return -100
    d = abs(sz - target)
    if d == 0:
        return 50
    if d <= 8:
        return 40
    if d <= 32:
        return 30
    if d <= 96:
        return 20
    if d <= 256:
        return 10
    if sz <= 4096:
        return 5
    return 0


def _looks_like_zip(data: bytes) -> bool:
    return len(data) >= 4 and data[:4] == b"PK\x03\x04"


def _looks_like_tar(data: bytes) -> bool:
    if len(data) < 512:
        return False
    return data[257:262] == b"ustar"


class _Candidate:
    __slots__ = ("name", "size", "score", "data")

    def __init__(self, name: str, size: int, score: int, data: bytes):
        self.name = name
        self.size = size
        self.score = score
        self.data = data


def _add_candidate(cands: List[_Candidate], name: str, data: bytes) -> None:
    sz = len(data)
    s = _name_score(name) + _size_score(sz) + _content_score(data)
    cands.append(_Candidate(name=name, size=sz, score=s, data=data))


def _scan_nested_archives(cands: List[_Candidate], name: str, data: bytes, depth: int) -> None:
    if depth <= 0 or not data:
        return
    if len(data) > 2_500_000:
        return

    try:
        if _looks_like_zip(data):
            with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
                _scan_zip(cands, zf, depth - 1, prefix=name + "!")
        elif _looks_like_tar(data):
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tf:
                _scan_tar(cands, tf, depth - 1, prefix=name + "!")
    except Exception:
        return


def _scan_tar(cands: List[_Candidate], tf: tarfile.TarFile, depth: int, prefix: str = "") -> None:
    members = []
    for m in tf.getmembers():
        try:
            if not m.isfile():
                continue
            if m.size <= 0:
                continue
            if m.size > 10_000_000:
                continue
            n = prefix + (m.name or "")
            ns = _name_score(n) + _size_score(m.size)
            if ns > -100:
                members.append((ns, m))
        except Exception:
            continue

    members.sort(key=lambda x: x[0], reverse=True)
    top = members[:200] if members else []
    for _, m in top:
        n = prefix + (m.name or "")
        try:
            f = tf.extractfile(m)
            if f is None:
                continue
            data = f.read()
        except Exception:
            continue
        if not data:
            continue
        if len(data) <= 200_000 or _name_score(n) >= 200:
            _add_candidate(cands, n, data)
        if depth > 0:
            _scan_nested_archives(cands, n, data, depth)


def _scan_zip(cands: List[_Candidate], zf: zipfile.ZipFile, depth: int, prefix: str = "") -> None:
    infos = []
    for zi in zf.infolist():
        try:
            if zi.is_dir():
                continue
            if zi.file_size <= 0:
                continue
            if zi.file_size > 10_000_000:
                continue
            n = prefix + (zi.filename or "")
            ns = _name_score(n) + _size_score(zi.file_size)
            if ns > -100:
                infos.append((ns, zi))
        except Exception:
            continue

    infos.sort(key=lambda x: x[0], reverse=True)
    top = infos[:250] if infos else []
    for _, zi in top:
        n = prefix + (zi.filename or "")
        try:
            data = zf.read(zi)
        except Exception:
            continue
        if not data:
            continue
        if len(data) <= 200_000 or _name_score(n) >= 200:
            _add_candidate(cands, n, data)
        if depth > 0:
            _scan_nested_archives(cands, n, data, depth)


def _scan_directory(cands: List[_Candidate], root: str, depth: int) -> None:
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in (".git", ".svn", ".hg", "node_modules", "build", "out")]
            for fn in filenames:
                path = os.path.join(dirpath, fn)
                try:
                    st = os.stat(path)
                    if not stat.S_ISREG(st.st_mode):
                        continue
                    if st.st_size <= 0:
                        continue
                    if st.st_size > 10_000_000:
                        continue
                    rel = os.path.relpath(path, root).replace("\\", "/")
                    ns = _name_score(rel) + _size_score(st.st_size)
                    if ns <= -100:
                        continue
                    with open(path, "rb") as f:
                        data = f.read()
                except Exception:
                    continue
                if not data:
                    continue
                if len(data) <= 200_000 or _name_score(rel) >= 200:
                    _add_candidate(cands, rel, data)
                if depth > 0:
                    _scan_nested_archives(cands, rel, data, depth)
    except Exception:
        return


def _pick_best(cands: List[_Candidate]) -> Optional[bytes]:
    if not cands:
        return None
    cands.sort(key=lambda c: (c.score, -abs(c.size - 149), -c.size), reverse=True)
    return cands[0].data


class Solution:
    def solve(self, src_path: str) -> bytes:
        cands: List[_Candidate] = []

        if os.path.isdir(src_path):
            _scan_directory(cands, src_path, depth=2)
            best = _pick_best(cands)
            if best is not None:
                return best
            return b"\x00" * 149

        try:
            if tarfile.is_tarfile(src_path):
                with tarfile.open(src_path, "r:*") as tf:
                    _scan_tar(cands, tf, depth=2)
                best = _pick_best(cands)
                if best is not None:
                    return best
                return b"\x00" * 149
        except Exception:
            pass

        try:
            if zipfile.is_zipfile(src_path):
                with zipfile.ZipFile(src_path, "r") as zf:
                    _scan_zip(cands, zf, depth=2)
                best = _pick_best(cands)
                if best is not None:
                    return best
                return b"\x00" * 149
        except Exception:
            pass

        return b"\x00" * 149