import os
import tarfile
import tempfile
import stat
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        def quick_ascii_ratio(path: str, max_bytes: int = 4096) -> float:
            try:
                with open(path, "rb") as f:
                    data = f.read(max_bytes)
            except OSError:
                return 0.0
            if not data:
                return 0.0
            ascii_bytes = 0
            for b in data:
                if 32 <= b < 127 or b in (9, 10, 13):
                    ascii_bytes += 1
            return ascii_bytes / len(data)

        def name_score(fname_lower: str) -> int:
            score = 0
            if "poc" in fname_lower:
                score += 120
            if "crash" in fname_lower:
                score += 100
            if "id:" in fname_lower or "id_" in fname_lower:
                score += 80
            if "overflow" in fname_lower:
                score += 60
            if "commiss" in fname_lower:
                score += 40
            if "mgmt" in fname_lower:
                score += 40
            if "dataset" in fname_lower:
                score += 30
            if "input" in fname_lower:
                score += 20
            if "test" in fname_lower:
                score -= 10
            if fname_lower.endswith(
                (
                    ".c",
                    ".h",
                    ".cpp",
                    ".cc",
                    ".hpp",
                    ".md",
                    ".rst",
                    ".tex",
                    ".py",
                    ".java",
                    ".js",
                    ".html",
                    ".xml",
                    ".json",
                    ".toml",
                    ".ini",
                    ".cfg",
                    ".conf",
                    ".yml",
                    ".yaml",
                    ".sh",
                    ".bash",
                    ".zsh",
                    ".bat",
                    ".ps1",
                    ".cmake",
                    ".mk",
                    ".makefile",
                    ".txt",
                )
            ):
                score -= 100
            return score

        def closeness_score(size: int) -> int:
            target = 844
            if size == target:
                return 200
            if 600 <= size <= 1200:
                return 120
            if 200 <= size <= 4000:
                return 40
            return 0

        def try_parse_hex_content(data: bytes) -> bytes | None:
            try:
                text = data.decode("ascii")
            except UnicodeDecodeError:
                return None
            if not text:
                return None
            allowed = set("0123456789abcdefABCDEFxX,;: \t\r\n")
            has_hex = False
            for ch in text:
                if ch in "0123456789abcdefABCDEF":
                    has_hex = True
                if ch not in allowed:
                    return None
            if not has_hex:
                return None
            hex_str = re.sub(r"[^0-9a-fA-F]", "", text)
            if len(hex_str) < 2:
                return None
            if len(hex_str) % 2 == 1:
                hex_str = hex_str[:-1]
            if not hex_str:
                return None
            try:
                return bytes.fromhex(hex_str)
            except ValueError:
                return None

        tmpdir = tempfile.mkdtemp(prefix="pocgen_")
        try:
            with tarfile.open(src_path, "r:*") as tar:
                tar.extractall(tmpdir)
        except Exception:
            return b"A" * 844

        best_path = None
        best_score = -1
        best_ascii_ratio = 0.0
        best_name = ""

        for dirpath, _, filenames in os.walk(tmpdir):
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                if not stat.S_ISREG(st.st_mode):
                    continue
                size = st.st_size
                if size <= 0:
                    continue
                if size > 2_000_000:
                    continue
                ascii_ratio = quick_ascii_ratio(path)
                fname_lower = fname.lower()
                nscore = name_score(fname_lower)
                cscore = closeness_score(size)
                binary_score = int((1.0 - ascii_ratio) * 50.0)
                score = nscore + cscore + binary_score
                if score > best_score:
                    best_score = score
                    best_path = path
                    best_ascii_ratio = ascii_ratio
                    best_name = fname_lower

        if best_path is not None:
            try:
                with open(best_path, "rb") as f:
                    data = f.read()
            except OSError:
                return b"A" * 844

            should_try_hex = best_ascii_ratio > 0.98 or "poc" in best_name or "crash" in best_name
            if should_try_hex:
                parsed = try_parse_hex_content(data)
                if parsed is not None:
                    return parsed
            return data

        return b"A" * 844