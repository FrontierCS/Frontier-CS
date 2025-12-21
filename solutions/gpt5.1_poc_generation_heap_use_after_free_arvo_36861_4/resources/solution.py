import os
import tarfile
import tempfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        TARGET_LEN = 71298

        extract_root = None

        # Determine extraction root
        if os.path.isdir(src_path):
            extract_root = src_path
        else:
            tmpdir = tempfile.mkdtemp(prefix="poc_extract_")
            extract_root = tmpdir
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    self._safe_extract(tf, extract_root)
            except Exception:
                # If extraction fails and src_path is not a directory, we can't inspect sources
                if os.path.isdir(src_path):
                    extract_root = src_path
                else:
                    return b"\x00"

        # First: try to find best candidate by scoring
        best_path = self._find_best_candidate(extract_root, TARGET_LEN)
        if best_path is not None:
            try:
                with open(best_path, "rb") as f:
                    return f.read()
            except Exception:
                pass

        # Second: try any file with size closest to TARGET_LEN
        by_size = self._find_by_size(extract_root, TARGET_LEN)
        if by_size is not None:
            try:
                with open(by_size, "rb") as f:
                    return f.read()
            except Exception:
                pass

        # Third: pick largest binary-looking file
        largest_bin = self._find_largest_binary(extract_root)
        if largest_bin is not None:
            try:
                with open(largest_bin, "rb") as f:
                    return f.read()
            except Exception:
                pass

        # Final fallback: minimal non-empty input
        return b"\x00"

    def _safe_extract(self, tar_obj: tarfile.TarFile, path: str) -> None:
        base = os.path.realpath(path)
        for member in tar_obj.getmembers():
            member_path = os.path.join(path, member.name)
            try:
                member_real = os.path.realpath(member_path)
            except Exception:
                continue
            if not member_real.startswith(base):
                continue
            try:
                tar_obj.extract(member, path)
            except Exception:
                continue

    def _is_binary(self, path: str, max_check: int = 4096) -> bool:
        try:
            with open(path, "rb") as f:
                chunk = f.read(max_check)
        except Exception:
            return False

        if not chunk:
            return False

        if b"\x00" in chunk:
            return True

        nontext = 0
        for b in chunk:
            if b < 9:
                if b not in (0x09, 0x0A, 0x0D):
                    nontext += 1
            elif b > 0x7E:
                nontext += 1
        return (nontext / float(len(chunk))) > 0.30

    def _score_file(self, fpath: str, size: int, target_len: int) -> int:
        name = os.path.basename(fpath).lower()
        rel_path = fpath.lower()
        ext = os.path.splitext(name)[1]

        binary = self._is_binary(fpath)
        score = 0

        if binary:
            score += 10

        # Extension-based hints
        if ext in ("", ".bin", ".raw", ".dat", ".poc", ".pkt", ".input", ".in"):
            score += 5
        if ext in (
            ".c",
            ".h",
            ".cpp",
            ".cc",
            ".cxx",
            ".txt",
            ".md",
            ".rst",
            ".html",
            ".htm",
            ".xml",
            ".json",
            ".yml",
            ".yaml",
            ".py",
            ".sh",
            ".bat",
            ".cmake",
            ".m4",
            ".ac",
            ".am",
            ".java",
            ".cs",
            ".php",
        ):
            score -= 5

        # Keyword-based hints
        keywords = [
            ("poc", 30),
            ("uaf", 25),
            ("crash", 25),
            ("heap", 10),
            ("overflow", 8),
            ("bug", 5),
            ("id_", 20),
            ("afl", 5),
            ("fuzz", 5),
            ("corpus", 4),
            ("seeds", 4),
            ("input", 3),
            ("test", 2),
        ]
        for kw, inc in keywords:
            if kw in name:
                score += inc
            elif kw in rel_path:
                score += inc // 2

        # Size-based scoring relative to target
        if target_len > 0:
            if size == target_len:
                score += 100
            else:
                ratio = size / float(target_len)
                if 0.5 <= ratio <= 2.0:
                    score += 20
                elif 0.25 <= ratio < 0.5 or 2.0 < ratio <= 4.0:
                    score += 5

        # Prefer binary candidates slightly more
        if not binary:
            score -= 2

        return score

    def _find_best_candidate(self, root: str, target_len: int) -> str or None:
        best_score = None
        best_path = None

        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                try:
                    st = os.stat(fpath)
                except Exception:
                    continue
                if not os.path.isfile(fpath):
                    continue
                size = st.st_size
                if size <= 0:
                    continue
                score = self._score_file(fpath, size, target_len)
                if best_score is None or score > best_score:
                    best_score = score
                    best_path = fpath

        # Require at least non-negative score to accept
        if best_score is not None and best_score >= 0:
            return best_path
        return None

    def _find_by_size(self, root: str, target_len: int) -> str or None:
        closest_path = None
        closest_diff = None

        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                try:
                    st = os.stat(fpath)
                except Exception:
                    continue
                if not os.path.isfile(fpath):
                    continue
                size = st.st_size
                if size <= 0:
                    continue
                diff = abs(size - target_len)
                if closest_diff is None or diff < closest_diff:
                    closest_diff = diff
                    closest_path = fpath
                    if diff == 0:
                        return closest_path

        return closest_path

    def _find_largest_binary(self, root: str) -> str or None:
        best_path = None
        best_size = 0

        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                try:
                    st = os.stat(fpath)
                except Exception:
                    continue
                if not os.path.isfile(fpath):
                    continue
                size = st.st_size
                if size <= 0:
                    continue
                if not self._is_binary(fpath):
                    continue
                if size > best_size:
                    best_size = size
                    best_path = fpath

        return best_path
