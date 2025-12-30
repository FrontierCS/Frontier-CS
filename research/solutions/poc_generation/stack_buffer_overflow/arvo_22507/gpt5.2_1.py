import os
import re
import tarfile
from typing import Dict, Optional


class Solution:
    _INT_MAX_64 = "9223372036854775807"

    def _score_delims_from_format(self, fmt: str, counts: Dict[str, int]) -> None:
        conv_re = re.compile(r'%(?:\*?\d+)?(?:hh|h|ll|l|j|z|t|L)?[diouxX]')
        spans = [m.span() for m in conv_re.finditer(fmt)]
        if len(spans) < 2:
            return
        (s1, e1), (s2, e2) = spans[0], spans[1]
        between = fmt[e1:s2]
        if '.' in between:
            counts['.'] += 1
        if ',' in between:
            counts[','] += 1
        if ':' in between:
            counts[':'] += 1
        if ' ' in between or '\t' in between or '\n' in between or '\r' in between:
            counts[' '] += 1

    def _infer_delim(self, src_path: str) -> str:
        counts: Dict[str, int] = {'.': 0, ' ': 0, ',': 0, ':': 0}

        def bump_if_found(text: str) -> None:
            for m in re.finditer(r'\bsscanf\s*\((?:.|\n)*?\)', text):
                seg = m.group(0)
                fm = re.search(r'"([^"\n]{1,256})"', seg)
                if fm:
                    self._score_delims_from_format(fm.group(1), counts)

            for fm in re.finditer(r'\bstrtok\s*\([^,]+,\s*"([^"]+)"\s*\)', text):
                d = fm.group(1)
                if '.' in d:
                    counts['.'] += 1
                if ',' in d:
                    counts[','] += 1
                if ':' in d:
                    counts[':'] += 1
                if any(ch in d for ch in " \t\r\n"):
                    counts[' '] += 1

            for fm in re.finditer(r"\bstrchr\s*\(\s*[^,]+,\s*'(.?)'\s*\)", text):
                ch = fm.group(1)
                if ch in counts:
                    counts[ch] += 1

        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isreg():
                        continue
                    name = m.name.lower()
                    if not any(name.endswith(ext) for ext in (".c", ".cc", ".cpp", ".h", ".hpp")):
                        continue
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    try:
                        data = f.read(2_000_000)
                    except Exception:
                        continue
                    try:
                        text = data.decode("utf-8", "ignore")
                    except Exception:
                        text = data.decode("latin-1", "ignore")
                    bump_if_found(text)
        except Exception:
            pass

        best = max(counts.items(), key=lambda kv: (kv[1], kv[0] == '.'))
        delim = best[0] if best[1] > 0 else '.'
        if delim not in ('.', ' ', ',', ':'):
            delim = '.'
        return delim

    def solve(self, src_path: str) -> bytes:
        delim = self._infer_delim(src_path)
        s = f"{self._INT_MAX_64}{delim}{self._INT_MAX_64}\n"
        return s.encode("ascii", "strict")