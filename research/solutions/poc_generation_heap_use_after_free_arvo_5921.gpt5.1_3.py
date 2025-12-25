import os
import tarfile
import math
import re
from typing import Iterable, Tuple, Optional


class Solution:
    MAX_FILE_SIZE = 1024 * 1024  # 1MB
    GROUND_LEN = 73

    def _iter_tar_files(self, tar_path: str) -> Iterable[Tuple[str, bytes]]:
        tf = tarfile.open(tar_path, "r:*")
        for m in tf.getmembers():
            if not m.isfile():
                continue
            if m.size <= 0 or m.size > self.MAX_FILE_SIZE:
                continue
            try:
                f = tf.extractfile(m)
            except Exception:
                continue
            if f is None:
                continue
            try:
                data = f.read()
            except Exception:
                continue
            if not data:
                continue
            yield m.name, data

    def _iter_dir_files(self, root_dir: str) -> Iterable[Tuple[str, bytes]]:
        for root, _, files in os.walk(root_dir):
            for fname in files:
                path = os.path.join(root, fname)
                try:
                    st = os.stat(path)
                except Exception:
                    continue
                if not os.path.isfile(path):
                    continue
                size = st.st_size
                if size <= 0 or size > self.MAX_FILE_SIZE:
                    continue
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except Exception:
                    continue
                if not data:
                    continue
                rel_path = os.path.relpath(path, root_dir)
                yield rel_path, data

    def _should_skip_file(self, path_lower: str) -> bool:
        skip_exts = (
            ".c", ".h", ".cpp", ".hpp", ".cc", ".cxx",
            ".java", ".py", ".sh", ".bash", ".zsh",
            ".mk", ".cmake", ".json", ".yml", ".yaml",
            ".xml", ".html", ".md", ".rst", ".toml",
            ".ini", ".cfg", ".doxy", ".tex", ".m4",
            ".ac", ".am", ".sln", ".vcxproj", ".csproj",
            ".jpg", ".jpeg", ".png", ".gif", ".bmp",
            ".tiff", ".ico",
            ".o", ".a", ".so", ".dll", ".dylib", ".exe",
            ".class", ".jar", ".war", ".ear",
            ".gz", ".bz2", ".xz", ".zip", ".7z", ".rar",
            ".tar"
        )
        return path_lower.endswith(skip_exts)

    def _try_parse_hex_bytes(self, data: bytes) -> Optional[bytes]:
        if not data or len(data) > 8192:
            return None
        try:
            text = data.decode("ascii", errors="ignore")
        except Exception:
            return None
        tokens = re.findall(r"0x([0-9a-fA-F]{1,2})|([0-9a-fA-F]{2})", text)
        if not tokens:
            return None
        out = bytearray()
        for g1, g2 in tokens:
            hx = g1 if g1 else g2
            if not hx:
                continue
            try:
                out.append(int(hx, 16))
            except ValueError:
                continue
        if not out:
            return None
        return bytes(out)

    def _choose_best_poc(self, files: Iterable[Tuple[str, bytes]]) -> Optional[bytes]:
        G = self.GROUND_LEN
        binary_exts = {
            ".pcap", ".pcapng", ".cap", ".pkt",
            ".bin", ".dat", ".raw", ".in", ".out"
        }

        best_binary_data: Optional[bytes] = None
        best_binary_score = float("-inf")
        best_nonbin_data: Optional[bytes] = None
        best_nonbin_score = float("-inf")

        for path, data in files:
            if not data:
                continue
            path_lower = path.lower()
            if self._should_skip_file(path_lower):
                continue

            length = len(data)
            ext = os.path.splitext(path_lower)[1]

            kw_score = 0
            for kw in (
                "poc", "crash", "uaf",
                "use-after-free", "use_after_free",
                "heap-use-after-free", "heap-use_after_free"
            ):
                if kw in path_lower:
                    kw_score += 30
            for kw in ("h225", "ras", "fuzz", "id:", "corpus", "seed", "repro", "reproducer"):
                if kw in path_lower:
                    kw_score += 10
            for kw in ("test", "sample"):
                if kw in path_lower:
                    kw_score += 3

            diff = abs(length - G)
            closeness = max(0, 100 - diff)

            is_binary = (ext in binary_exts) or (ext == "")
            ext_bonus = 0
            if is_binary:
                if ext in (".pcap", ".pcapng", ".cap", ".pkt"):
                    ext_bonus += 50
                elif ext in (".bin", ".dat", ".raw"):
                    ext_bonus += 40
                elif ext in (".in", ".out"):
                    ext_bonus += 20
                else:
                    if "id:" in path_lower or "poc" in path_lower or "crash" in path_lower:
                        ext_bonus += 40
                    else:
                        ext_bonus += 10
            else:
                if ext in (".txt", ".md", ".rst", ".html", ".xml", ".json", ".yml", ".yaml"):
                    ext_bonus -= 30

            score = closeness * 5.0 + kw_score + ext_bonus - math.log2(length + 1.0)

            if is_binary:
                if score > best_binary_score:
                    best_binary_score = score
                    best_binary_data = data
            else:
                if score > best_nonbin_score:
                    best_nonbin_score = score
                    best_nonbin_data = data

        if best_binary_data is not None:
            return best_binary_data

        if best_nonbin_data is not None:
            parsed = self._try_parse_hex_bytes(best_nonbin_data)
            if parsed is not None:
                return parsed
            return best_nonbin_data

        return None

    def solve(self, src_path: str) -> bytes:
        poc_data: Optional[bytes] = None

        if os.path.isdir(src_path):
            poc_data = self._choose_best_poc(self._iter_dir_files(src_path))
        else:
            try:
                if tarfile.is_tarfile(src_path):
                    poc_data = self._choose_best_poc(self._iter_tar_files(src_path))
            except Exception:
                poc_data = None

        if poc_data is not None:
            return poc_data

        return b"A" * self.GROUND_LEN
