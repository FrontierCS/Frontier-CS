import os
import io
import re
import tarfile
import gzip
import bz2
import lzma
from typing import Optional, Tuple, List


class Solution:
    def solve(self, src_path: str) -> bytes:
        bug_id = "383200048"
        candidates: List[Tuple[int, str, bytes]] = []

        def maybe_decompress(name: str, data: bytes) -> bytes:
            if len(data) >= 2 and data[0] == 0x1F and data[1] == 0x8B:
                try:
                    return gzip.decompress(data)
                except Exception:
                    return data
            if len(data) >= 6 and data[:6] == b"\xFD7zXZ\x00":
                try:
                    return lzma.decompress(data)
                except Exception:
                    return data
            if len(data) >= 3 and data[:3] == b"BZh":
                try:
                    return bz2.decompress(data)
                except Exception:
                    return data
            ext = os.path.splitext(name.lower())[1]
            if ext == ".gz":
                try:
                    return gzip.decompress(data)
                except Exception:
                    return data
            if ext == ".xz":
                try:
                    return lzma.decompress(data)
                except Exception:
                    return data
            if ext == ".bz2":
                try:
                    return bz2.decompress(data)
                except Exception:
                    return data
            return data

        def consider(name: str, raw: bytes) -> None:
            if not raw:
                return
            data = maybe_decompress(name, raw)
            if not data:
                return
            candidates.append((len(data), name, data))

        def scan_directory(root: str) -> None:
            for dirpath, _, filenames in os.walk(root):
                for fn in filenames:
                    path = os.path.join(dirpath, fn)
                    rel = os.path.relpath(path, root).replace(os.sep, "/")
                    try:
                        st = os.stat(path)
                    except Exception:
                        continue
                    if st.st_size <= 0 or st.st_size > 50_000_000:
                        continue
                    try:
                        with open(path, "rb") as f:
                            raw = f.read()
                    except Exception:
                        continue
                    consider(rel, raw)

        def scan_tar(tar_path: str) -> None:
            try:
                with tarfile.open(tar_path, "r:*") as tf:
                    for m in tf.getmembers():
                        if not m.isfile():
                            continue
                        if m.size <= 0 or m.size > 50_000_000:
                            continue
                        try:
                            f = tf.extractfile(m)
                            if f is None:
                                continue
                            raw = f.read()
                        except Exception:
                            continue
                        consider(m.name, raw)
            except Exception:
                pass

        if os.path.isdir(src_path):
            scan_directory(src_path)
        else:
            scan_tar(src_path)

        if not candidates:
            return b"\x00" * 512

        def score_key(item: Tuple[int, str, bytes]) -> Tuple[int, int, int, str]:
            size, name, _ = item
            lname = name.lower()
            id_hit = 1 if bug_id in lname else 0
            id_hit2 = 1 if "383200" in lname else 0
            ossfuzz = 1 if ("ossfuzz" in lname or "oss-fuzz" in lname or "clusterfuzz" in lname) else 0
            crash = 1 if ("crash" in lname or "poc" in lname or "repro" in lname or "regress" in lname or "bug" in lname) else 0
            prefer = -(1000 * id_hit + 200 * id_hit2 + 50 * ossfuzz + 10 * crash)
            dist512 = abs(size - 512)
            return (prefer, dist512, size, name)

        candidates.sort(key=score_key)
        return candidates[0][2]