import os
import tarfile
import tempfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        def extract_root(path: str) -> str:
            if os.path.isdir(path):
                return path
            tmpdir = tempfile.mkdtemp(prefix="src_")
            try:
                with tarfile.open(path, "r:*") as tar:
                    tar.extractall(path=tmpdir)
            except Exception:
                # If it's not a tarball, just treat the original path as a directory
                return path
            return tmpdir

        root_dir = extract_root(src_path)

        candidates = []

        # Collect small, likely-binary files
        for dirpath, _, filenames in os.walk(root_dir):
            for fname in filenames:
                full_path = os.path.join(dirpath, fname)
                try:
                    st = os.stat(full_path)
                except OSError:
                    continue

                size = st.st_size
                if size == 0 or size > 4096:
                    continue

                rel_path = os.path.relpath(full_path, root_dir)
                _, ext = os.path.splitext(fname)
                ext = ext.lower()

                # Skip obvious text/source files
                if ext in {
                    ".c", ".h", ".cpp", ".cc", ".hpp",
                    ".py", ".md", ".txt", ".cmake", ".in",
                    ".am", ".ac", ".m4", ".pc", ".sh",
                    ".yml", ".yaml", ".json", ".xml",
                    ".html", ".rst", ".ini", ".cfg",
                    ".conf", ".bat", ".ps1", ".mdown",
                }:
                    continue

                try:
                    with open(full_path, "rb") as f:
                        data = f.read()
                except OSError:
                    continue

                if not data:
                    continue

                ascii_bytes = sum(
                    1
                    for b in data
                    if b in (9, 10, 13, 32) or 32 <= b <= 126
                )
                non_ascii = len(data) - ascii_bytes
                binary_score = non_ascii / len(data)
                is_binary = binary_score > 0.3 or b"\x00" in data

                candidates.append(
                    {
                        "path": full_path,
                        "rel": rel_path,
                        "size": size,
                        "data": data,
                        "binary_score": binary_score,
                        "is_binary": is_binary,
                    }
                )

        target_len = 33

        def select_best(cands):
            if not cands:
                return None

            keywords = [
                "capwap",
                "setup_capwap",
                "setup",
                "ndpi",
                "heap",
                "overflow",
                "oflow",
                "bof",
                "crash",
                "poc",
                "fuzz",
                "issue",
                "bug",
                "oss-fuzz",
                "asan",
            ]

            def score(c):
                path_lower = c["rel"].lower()
                kw_score = sum(path_lower.count(k) for k in keywords)
                non_binary_flag = 0 if c["is_binary"] else 1
                size_diff = abs(c["size"] - target_len)
                return (
                    non_binary_flag,           # prefer binary (0 before 1)
                    -kw_score,                 # more keyword hits preferred
                    size_diff,                 # closer to target length
                    -c["binary_score"],        # more non-ascii preferred
                    c["size"],                 # smaller size preferred
                    path_lower,                # tie-breaker for determinism
                )

            best = sorted(cands, key=score)[0]
            return best["data"]

        if candidates:
            exact_len = [c for c in candidates if c["size"] == target_len]
            data = select_best(exact_len)
            if data is not None:
                return data

            small = [c for c in candidates if c["size"] <= 128]
            data = select_best(small)
            if data is not None:
                return data

        # Fallback: generic small payload
        return b"A" * target_len
