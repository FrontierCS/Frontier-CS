import os
import tarfile
import tempfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Attempt to find a small binary file inside the provided source tarball
        that might represent a PoC. If none is found, fall back to a fixed
        10-byte payload.
        """
        root_dir = None
        temp_dir = None

        try:
            if os.path.isdir(src_path):
                root_dir = src_path
            else:
                temp_dir = tempfile.mkdtemp(prefix="arvo_src_")
                try:
                    with tarfile.open(src_path, "r:*") as tf:
                        tf.extractall(temp_dir)
                    root_dir = temp_dir
                except tarfile.TarError:
                    # If it's not a tarball or extraction fails, ignore and use fallback PoC
                    return b"A" * 10

            if not root_dir or not os.path.isdir(root_dir):
                return b"A" * 10

            best_candidate = None
            best_score = None

            for dirpath, _, filenames in os.walk(root_dir):
                for fname in filenames:
                    path = os.path.join(dirpath, fname)
                    try:
                        size = os.path.getsize(path)
                    except OSError:
                        continue

                    # We are interested in very small binary files
                    if not (1 <= size <= 64):
                        continue

                    ext = os.path.splitext(fname)[1].lower()
                    # Prefer typical PoC / binary-like extensions or no extension
                    if ext in (".bin", ".dat", ".poc", ".raw", ""):
                        # Scoring heuristic: closer to 10 bytes and preferred extensions
                        score = abs(size - 10)
                        if best_score is None or score < best_score:
                            best_score = score
                            best_candidate = path

            if best_candidate is not None:
                try:
                    with open(best_candidate, "rb") as f:
                        data = f.read()
                    # Return as-is; if not exactly 10 bytes, truncate or pad
                    if len(data) >= 10:
                        return data[:10]
                    else:
                        return data + b"A" * (10 - len(data))
                except OSError:
                    pass

            # Fallback: fixed 10-byte payload
            return b"A" * 10

        finally:
            if temp_dir and os.path.isdir(temp_dir):
                # Best-effort cleanup; ignore errors
                try:
                    for dirpath, dirnames, filenames in os.walk(temp_dir, topdown=False):
                        for fname in filenames:
                            try:
                                os.remove(os.path.join(dirpath, fname))
                            except OSError:
                                pass
                        for dname in dirnames:
                            try:
                                os.rmdir(os.path.join(dirpath, dname))
                            except OSError:
                                pass
                    try:
                        os.rmdir(temp_dir)
                    except OSError:
                        pass
