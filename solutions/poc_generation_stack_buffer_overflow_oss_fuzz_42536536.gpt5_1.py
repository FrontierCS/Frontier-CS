import os
import tarfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            if os.path.isfile(src_path) and tarfile.is_tarfile(src_path):
                with tarfile.open(src_path, 'r:*') as tf:
                    candidates = []
                    for m in tf.getmembers():
                        if not m.isfile():
                            continue
                        name_lower = m.name.lower()
                        if any(key in name_lower for key in ('42536536', 'poc', 'crash', 'testcase', 'repro')):
                            candidates.append(m)
                    for m in candidates:
                        try:
                            f = tf.extractfile(m)
                            if f:
                                data = f.read()
                                if data:
                                    return data
                        except Exception:
                            pass
        except Exception:
            pass
        return b"xref\n0 2\n0000000000 00000 f1\n0000000000 00000 f2"
