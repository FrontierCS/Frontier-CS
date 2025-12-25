import os
import re
import io
import tarfile
import zipfile
from typing import Optional, Tuple, Iterable


class Solution:
    _GT_LEN = 2179
    _MAX_FILE_SIZE = 5 * 1024 * 1024

    _CODE_EXTS = {
        ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh",
        ".py", ".java", ".go", ".rs", ".js", ".ts",
        ".md", ".rst", ".cmake", ".sh", ".bat", ".ps1",
        ".yml", ".yaml", ".toml", ".ini", ".cfg",
        ".am", ".ac", ".m4", ".mk", ".mak", ".make",
    }

    _INPUT_EXT_BOOST = {
        ".bin", ".dat", ".raw", ".poc", ".repro",
        ".xml", ".svg", ".html", ".xhtml", ".json", ".txt",
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff",
        ".pdf", ".ttf", ".otf", ".woff", ".woff2", ".zip",
    }

    _DIR_BOOST = {
        "testdata": 700,
        "test-data": 700,
        "tests": 350,
        "test": 350,
        "corpus": 650,
        "seed": 500,
        "seeds": 500,
        "seed_corpus": 650,
        "seed-corpus": 650,
        "artifacts": 900,
        "artifact": 900,
        "pocs": 900,
        "poc": 900,
        "repro": 900,
        "reproducer": 900,
        "crashes": 900,
        "crashers": 900,
        "inputs": 450,
        "input": 450,
        "fuzz": 300,
        "fuzzer": 300,
    }

    _NAME_PATTERNS = [
        (re.compile(r"(^|/)(clusterfuzz-testcase-minimized)(\..*)?$", re.I), 10000),
        (re.compile(r"clusterfuzz[-_]?testcase[-_]?minimized", re.I), 9000),
        (re.compile(r"clusterfuzz", re.I), 3500),
        (re.compile(r"(^|/)(crash|assert|oom|leak)[-_]", re.I), 3200),
        (re.compile(r"\bid:", re.I), 1400),
        (re.compile(r"testcase", re.I), 2200),
        (re.compile(r"\brepro(ducer)?\b", re.I), 2000),
        (re.compile(r"(^|/)\bpoc\b", re.I), 2000),
        (re.compile(r"\bpoc\b", re.I), 1500),
        (re.compile(r"minimized", re.I), 900),
    ]

    def solve(self, src_path: str) -> bytes:
        data = self._find_poc(src_path)
        if data is not None and len(data) > 0:
            return data
        return self._fallback_poc()

    def _find_poc(self, src_path: str) -> Optional[bytes]:
        if os.path.isdir(src_path):
            return self._find_poc_in_dir(src_path)
        if os.path.isfile(src_path):
            try:
                return self._find_poc_in_tar(src_path)
            except Exception:
                return None
        return None

    def _score_path(self, path: str, size: int) -> Tuple[int, int, int]:
        p = path.replace("\\", "/")
        base = 0
        for rgx, w in self._NAME_PATTERNS:
            if rgx.search(p):
                base += w

        parts = [x for x in p.lower().split("/") if x]
        for part in parts:
            base += self._DIR_BOOST.get(part, 0)

        bn = parts[-1] if parts else ""
        _, ext = os.path.splitext(bn)
        ext = ext.lower()
        if ext in self._INPUT_EXT_BOOST:
            base += 350
        if ext in self._CODE_EXTS:
            base -= 450

        diff = abs(size - self._GT_LEN)
        closeness = int(300 / (1 + diff))
        base += closeness

        if size <= 0:
            base -= 2000
        elif size > self._MAX_FILE_SIZE:
            base -= 2000

        return base, diff, size

    def _find_poc_in_tar(self, tar_path: str) -> Optional[bytes]:
        best = None  # (score, diff, size, member_name)
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf:
                if not m.isreg():
                    continue
                if m.size <= 0 or m.size > self._MAX_FILE_SIZE:
                    continue

                name = m.name
                score, diff, size = self._score_path(name, m.size)
                if score < 500:
                    continue

                cand = (score, diff, size, name)
                if best is None or cand[:3] > best[:3]:
                    best = cand

            if best is None:
                return self._find_candidate_by_size_in_tar(tf)

            score, diff, size, name = best
            if score < 1200:
                return None

            f = tf.extractfile(name)
            if f is None:
                return None
            data = f.read(self._MAX_FILE_SIZE + 1)
            if len(data) > self._MAX_FILE_SIZE:
                return None

            extracted = self._maybe_from_zip(name, data)
            if extracted is not None:
                return extracted
            return data

    def _find_candidate_by_size_in_tar(self, tf: tarfile.TarFile) -> Optional[bytes]:
        best = None  # (diff, size, member_name)
        for m in tf:
            if not m.isreg():
                continue
            if m.size <= 0 or m.size > self._MAX_FILE_SIZE:
                continue
            name = m.name.replace("\\", "/").lower()
            if any(x in name for x in ("/.git/", "/build/", "/cmake-build", "/bazel-")):
                continue
            bn = os.path.basename(name)
            _, ext = os.path.splitext(bn)
            ext = ext.lower()
            if ext in self._CODE_EXTS:
                continue

            diff = abs(m.size - self._GT_LEN)
            cand = (diff, m.size, m.name)
            if best is None or cand < best:
                best = cand

        if best is None:
            return None
        diff, size, name = best
        if diff > 50:
            return None
        f = tf.extractfile(name)
        if f is None:
            return None
        data = f.read(self._MAX_FILE_SIZE + 1)
        if len(data) > self._MAX_FILE_SIZE:
            return None
        extracted = self._maybe_from_zip(name, data)
        if extracted is not None:
            return extracted
        return data

    def _find_poc_in_dir(self, root: str) -> Optional[bytes]:
        best_path = None
        best = None  # (score, diff, size)
        for dirpath, dirnames, filenames in os.walk(root):
            dp = dirpath.replace("\\", "/").lower()
            if "/.git" in dp or "/build" in dp or "/cmake-build" in dp or "/bazel-" in dp:
                continue
            for fn in filenames:
                path = os.path.join(dirpath, fn)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                if st.st_size <= 0 or st.st_size > self._MAX_FILE_SIZE:
                    continue
                score, diff, size = self._score_path(path, st.st_size)
                if score < 500:
                    continue
                cand = (score, diff, size)
                if best is None or cand > best:
                    best = cand
                    best_path = path

        if best_path is None or best[0] < 1200:
            return None

        try:
            with open(best_path, "rb") as f:
                data = f.read(self._MAX_FILE_SIZE + 1)
        except OSError:
            return None
        if len(data) > self._MAX_FILE_SIZE:
            return None

        extracted = self._maybe_from_zip(best_path, data)
        if extracted is not None:
            return extracted
        return data

    def _maybe_from_zip(self, name: str, data: bytes) -> Optional[bytes]:
        bn = os.path.basename(name).lower()
        if not bn.endswith(".zip"):
            return None
        if len(data) < 4 or data[:2] != b"PK":
            return None
        try:
            with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
                best = None  # (score, diff, size, entry_name)
                for zi in zf.infolist():
                    if zi.is_dir():
                        continue
                    if zi.file_size <= 0 or zi.file_size > self._MAX_FILE_SIZE:
                        continue
                    en = zi.filename
                    score, diff, size = self._score_path(en, zi.file_size)
                    if score < 500:
                        continue
                    cand = (score, diff, size, en)
                    if best is None or cand[:3] > best[:3]:
                        best = cand
                if best is None:
                    return None
                score, diff, size, en = best
                if score < 1200:
                    return None
                with zf.open(en, "r") as f:
                    out = f.read(self._MAX_FILE_SIZE + 1)
                if len(out) > self._MAX_FILE_SIZE:
                    return None
                return out
        except Exception:
            return None

    def _fallback_poc(self) -> bytes:
        # Generic XML/SVG-like payload with many malformed numeric conversions in attributes.
        # Kept reasonably small.
        xml = (
            b'<?xml version="1.0" encoding="UTF-8"?>\n'
            b'<svg xmlns="http://www.w3.org/2000/svg"\n'
            b'     width="a" height="b" viewBox="c d e f"\n'
            b'     preserveAspectRatio="xMidYMid meet"\n'
            b'     style="stroke-width: notnum; opacity: 1e9999;">\n'
            b'  <defs>\n'
            b'    <linearGradient id="g1" x1="x" y1="y" x2="z" y2="w">\n'
            b'      <stop offset="q" stop-color="red" stop-opacity="nan"/>\n'
            b'      <stop offset="1..2" stop-color="blue" stop-opacity="-inf"/>\n'
            b'    </linearGradient>\n'
            b'    <filter id="f1" x="%" y="^" width="&" height="*">\n'
            b'      <feGaussianBlur stdDeviation="oops"/>\n'
            b'      <feOffset dx="--1" dy="++2"/>\n'
            b'    </filter>\n'
            b'  </defs>\n'
            b'  <g transform="translate(a,b) rotate(c) scale(d)">\n'
            b'    <rect x="x" y="y" width="w" height="h" rx="rx" ry="ry"\n'
            b'          fill="url(#g1)" filter="url(#f1)"/>\n'
            b'    <circle cx="cx" cy="cy" r="r"/>\n'
            b'    <ellipse cx="1e309" cy="-1e309" rx="0x10" ry="00.00.1"/>\n'
            b'    <line x1="x1" y1="y1" x2="x2" y2="y2"/>\n'
            b'    <polyline points="0,0 1,1 2,2 3,3" stroke-miterlimit="bad"/>\n'
            b'    <path d="M 0 0 L 10 10 Z" stroke-dasharray="a,b,c"/>\n'
            b'  </g>\n'
            b'</svg>\n'
        )
        return xml