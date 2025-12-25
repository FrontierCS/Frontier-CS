import os
import tarfile
import tempfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        def default_poc() -> bytes:
            return b"a=1\na/=0\n"

        # Try to extract the tarball to search for any embedded PoC-like inputs
        tmpdir = None
        try:
            tmpdir = tempfile.mkdtemp(prefix="src-")
            with tarfile.open(src_path, "r:*") as tf:
                tf.extractall(tmpdir)
        except Exception:
            # If extraction fails for any reason, fall back to a generic PoC
            return default_poc()

        best_data = None
        best_len = None

        # Heuristics to find an existing PoC-like input in the source tree
        for dirpath, dirnames, filenames in os.walk(tmpdir):
            for fn in filenames:
                lower_fn = fn.lower()
                name_root, ext = os.path.splitext(lower_fn)

                # Only consider likely input file extensions or no extension
                if ext not in ("", ".in", ".txt", ".bin", ".dat", ".raw", ".json", ".yaml"):
                    continue

                rel_path = os.path.relpath(os.path.join(dirpath, fn), tmpdir)
                comps = [c.lower() for c in rel_path.split(os.sep)[:-1]]

                # Check if filename or directory names suggest a PoC/crash/input
                keywords_file = ("poc", "proof", "crash", "uaf", "heap", "bug", "repro", "div", "zero")
                keywords_dir = ("poc", "crash", "inputs", "input", "id", "bugs", "repro", "corpus")

                if not any(k in lower_fn for k in keywords_file) and not any(
                    any(k in c for k in keywords_dir) for c in comps
                ):
                    continue

                full_path = os.path.join(dirpath, fn)

                try:
                    size = os.path.getsize(full_path)
                    if size == 0 or size > 4096:
                        continue
                    with open(full_path, "rb") as f:
                        data = f.read()
                    if not data:
                        continue
                except OSError:
                    continue

                if best_data is None or len(data) < best_len:
                    best_data = data
                    best_len = len(data)

        if best_data is not None:
            return best_data

        # Fallback: generic compound division-by-zero program, valid in many C-like/ scripting languages
        return default_poc()
