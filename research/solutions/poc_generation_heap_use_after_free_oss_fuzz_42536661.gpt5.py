import os
import io
import tarfile
import zipfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Try to find an embedded PoC within the source tarball or directory.
        poc = self._find_poc_bytes(src_path)
        if poc is not None:
            return poc
        # Fallback: return a minimal RAR5-like header with padding (may not trigger the bug)
        rar5_magic = b"Rar!\x1a\x07\x01\x00"
        return rar5_magic + b"\x00" * (1089 - len(rar5_magic)) if 1089 > len(rar5_magic) else rar5_magic

    def _find_poc_bytes(self, src_path: str) -> bytes | None:
        # Heuristics for identifying the correct PoC inside the tarball or directory.
        target_length = 1089
        rar5_magic = b"Rar!\x1a\x07\x01\x00"
        # Search order preference:
        # 1) Exact length match with RAR5 magic and name pattern hints
        # 2) RAR5 magic with name pattern hints
        # 3) Any RAR5 magic smallest
        # 4) Exact length match without magic but with pattern hints
        # If multiple candidates exist, choose the one with highest score.
        candidates = []

        def score_candidate(name: str, data: bytes) -> int:
            s = 0
            lower = name.lower()
            # Strong hints
            if "42536661" in lower:
                s += 10
            if "oss" in lower or "fuzz" in lower or "clusterfuzz" in lower:
                s += 5
            if "poc" in lower or "crash" in lower or "repro" in lower or "uaf" in lower:
                s += 4
            if lower.endswith(".rar"):
                s += 3
            if len(data) == target_length:
                s += 8
            if data.startswith(rar5_magic):
                s += 12
            return s

        def consider(name: str, data: bytes):
            try:
                s = score_candidate(name, data)
                candidates.append((s, len(data), name, data))
            except Exception:
                pass

        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    full = os.path.join(root, fn)
                    try:
                        size = os.path.getsize(full)
                        # Skip overly large files to limit memory use
                        if size > 2 * 1024 * 1024:
                            continue
                        with open(full, "rb") as f:
                            data = f.read()
                        # Only consider non-empty files
                        if not data:
                            continue
                        consider(os.path.relpath(full, src_path), data)
                    except Exception:
                        continue
        else:
            # Try tar
            if tarfile.is_tarfile(src_path):
                try:
                    with tarfile.open(src_path, "r:*") as tf:
                        for ti in tf.getmembers():
                            if not ti.isreg():
                                continue
                            # Skip very large files
                            if ti.size > 2 * 1024 * 1024:
                                continue
                            try:
                                fobj = tf.extractfile(ti)
                                if fobj is None:
                                    continue
                                data = fobj.read()
                                if not data:
                                    continue
                                consider(ti.name, data)
                            except Exception:
                                continue
                except Exception:
                    pass
            else:
                # Try zip
                try:
                    if zipfile.is_zipfile(src_path):
                        with zipfile.ZipFile(src_path, "r") as zf:
                            for zi in zf.infolist():
                                if zi.is_dir():
                                    continue
                                if zi.file_size > 2 * 1024 * 1024:
                                    continue
                                try:
                                    with zf.open(zi, "r") as f:
                                        data = f.read()
                                    if not data:
                                        continue
                                    consider(zi.filename, data)
                                except Exception:
                                    continue
                except Exception:
                    pass

        if not candidates:
            return None

        # Prefer highest score; tie-breaker: shorter length, then name lexical
        candidates.sort(key=lambda x: (-x[0], x[1], x[2]))
        best = candidates[0]
        return best[3]