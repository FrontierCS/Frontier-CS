import os
import re
import tarfile
from typing import Iterator, Optional


class Solution:
    def _iter_source_texts(self, src_path: str) -> Iterator[str]:
        if not src_path or not os.path.exists(src_path):
            return
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name.lower()
                    if not (name.endswith((".c", ".cc", ".cpp", ".h", ".hpp", ".yy", ".l", ".rl", ".inc"))):
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                    except Exception:
                        continue
                    if not data:
                        continue
                    if len(data) > 3_000_000:
                        data = data[:3_000_000]
                    try:
                        yield data.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
        except Exception:
            return

    def _detect_len_prefixed_format(self, texts: Iterator[str]) -> bool:
        pat_size8 = re.compile(r"\b(size|len|length)\s*<\s*8\b")
        pat_u32 = re.compile(r"\buint32_t\b|\buint_fast32_t\b|\buint_least32_t\b")
        pat_data4 = re.compile(r"\bdata\s*\+\s*4\b|\binput\s*\+\s*4\b|\bbuf\s*\+\s*4\b")
        pat_memcpy4 = re.compile(r"\bmemcpy\s*\(\s*&\w+\s*,\s*\w+\s*,\s*4\s*\)")
        for t in texts:
            if pat_size8.search(t) and (pat_u32.search(t) or pat_memcpy4.search(t)) and pat_data4.search(t):
                return True
        return False

    def _detect_empty_pattern_rejected(self, texts: Iterator[str]) -> bool:
        # Heuristic: look for checks like "if (patlen == 0) return" or similar.
        rejs = [
            re.compile(r"\bif\s*\(\s*(pat(len|tern(_len|_length)?|len|length)|re_len)\s*==\s*0\s*\)\s*return\b"),
            re.compile(r"\bif\s*\(\s*(pat(len|tern(_len|_length)?|len|length)|re_len)\s*<=\s*0\s*\)\s*return\b"),
            re.compile(r"\bif\s*\(\s*(pat(len|tern(_len|_length)?|len|length)|re_len)\s*==\s*0\s*\)\s*{\s*return\b"),
        ]
        for t in texts:
            for r in rejs:
                if r.search(t):
                    return True
        return False

    def solve(self, src_path: str) -> bytes:
        texts1 = list(self._iter_source_texts(src_path))
        len_prefixed = self._detect_len_prefixed_format(iter(texts1))

        if len_prefixed:
            empty_rejected = self._detect_empty_pattern_rejected(iter(texts1))
            if empty_rejected:
                # 4-byte patlen=1, 4-byte subjlen=0, then 1 byte pattern 'a'
                return (1).to_bytes(4, "little") + (0).to_bytes(4, "little") + b"a"
            # 4-byte patlen=0, 4-byte subjlen=0
            return b"\x00" * 8

        return b"\x00" * 8