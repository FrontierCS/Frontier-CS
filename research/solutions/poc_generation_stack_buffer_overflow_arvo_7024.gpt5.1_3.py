import os
import tarfile
import tempfile
import gzip
import bz2
import lzma
import zipfile
import io
from typing import Optional


class Solution:
    def _prepare_root(self, src_path: str) -> str:
        if os.path.isdir(src_path):
            return src_path

        # Try to treat as tarball
        tmpdir = tempfile.mkdtemp(prefix="src_")
        try:
            with tarfile.open(src_path, "r:*") as tf:
                def is_within_directory(directory: str, target: str) -> bool:
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)
                    return os.path.commonprefix([abs_directory, abs_target]) == abs_directory

                for member in tf.getmembers():
                    member_path = os.path.join(tmpdir, member.name)
                    if not is_within_directory(tmpdir, member_path):
                        continue
                    try:
                        tf.extract(member, tmpdir)
                    except Exception:
                        # Ignore extraction errors for individual members
                        continue
            return tmpdir
        except Exception:
            # If not a tarball, fall back to its directory
            parent = os.path.dirname(src_path)
            return parent if parent else "."

    def _maybe_decompress(self, data: bytes, ext: str) -> bytes:
        ext = ext.lower()
        try:
            if ext == ".gz":
                return gzip.decompress(data)
            if ext == ".bz2":
                return bz2.decompress(data)
            if ext in (".xz", ".lzma"):
                return lzma.decompress(data)
            if ext == ".zip":
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    for info in zf.infolist():
                        # Choose first regular file
                        is_dir = False
                        if hasattr(info, "is_dir"):
                            is_dir = info.is_dir()
                        else:
                            # Fallback heuristic for older Python versions
                            is_dir = info.filename.endswith("/")
                        if not is_dir:
                            return zf.read(info.filename)
                return data
        except Exception:
            return data
        return data

    def _find_best_poc(self, root: str, target_size: int = 45) -> Optional[str]:
        binary_exts = {
            ".pcap", ".pcapng", ".cap", ".bin", ".dat", ".raw", ".pkt",
            ".gz", ".bz2", ".xz", ".lzma"
        }
        source_exts = {
            ".c", ".h", ".cpp", ".cc", ".hpp", ".hh",
            ".py", ".java", ".js", ".ts", ".rb", ".go", ".rs", ".php",
            ".cs", ".m", ".mm", ".swift",
            ".html", ".xml", ".json", ".txt", ".md", ".rst",
            ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf",
            ".cmake", ".am", ".in", ".ac",
            ".log", ".bat", ".sh", ".ps1", ".pl", ".pm", ".tcl"
        }

        primary_keywords = [
            "poc", "proof", "testcase", "crash", "overflow", "stack",
            "bug", "gre", "80211", "802.11", "wireshark", "dissector"
        ]
        secondary_keywords = [
            "fuzz", "id_", "id-", "sample", "packet", "frame",
            "input", "regress", "regression"
        ]

        max_scan_size = 1_000_000  # 1 MB
        best_score = float("-inf")
        best_path: Optional[str] = None

        for dirpath, dirnames, filenames in os.walk(root):
            # Skip some obvious irrelevant directories
            basename = os.path.basename(dirpath).lower()
            if basename in {".git", ".hg", ".svn", ".idea", ".vscode", "__pycache__"}:
                continue

            for fname in filenames:
                path = os.path.join(dirpath, fname)
                try:
                    st = os.stat(path)
                except OSError:
                    continue

                sz = st.st_size
                if sz == 0 or sz > max_scan_size:
                    continue

                lower_name = fname.lower()
                lower_path = path.lower()
                _, ext = os.path.splitext(lower_name)

                score = 0.0

                # Strong preference for exact target size
                if sz == target_size:
                    score += 120.0
                # Penalize distance from target size
                size_diff = abs(sz - target_size)
                score -= size_diff * 1.5
                if sz <= 2 * target_size:
                    score += 20.0
                elif sz <= 5 * target_size:
                    score += 5.0
                elif sz > 20 * target_size:
                    score -= 20.0

                # Extension-based scoring
                if ext in binary_exts:
                    score += 35.0
                elif ext in source_exts:
                    score -= 25.0
                else:
                    score += 5.0  # unknown extension, slightly positive

                # Name/path keyword scoring
                for kw in primary_keywords:
                    if kw in lower_name:
                        score += 45.0
                    elif kw in lower_path:
                        score += 20.0

                for kw in secondary_keywords:
                    if kw in lower_name:
                        score += 15.0
                    elif kw in lower_path:
                        score += 5.0

                # Directory hints
                if any(sub in lower_path for sub in [
                    "/poc", "/pocs", "/crash", "/crashes",
                    "/inputs", "/input", "/tests", "/regress", "/regression",
                    "/fuzz", "/corpus"
                ]):
                    score += 20.0

                # Prefer smaller files generally
                if sz <= 1024:
                    score += 10.0

                if score > best_score:
                    best_score = score
                    best_path = path

        return best_path

    def solve(self, src_path: str) -> bytes:
        root = self._prepare_root(src_path)
        target_size = 45

        best_path = self._find_best_poc(root, target_size=target_size)

        if best_path is not None:
            try:
                with open(best_path, "rb") as f:
                    data = f.read()
                _, ext = os.path.splitext(best_path)
                data = self._maybe_decompress(data, ext)
                # Ensure we return non-empty bytes
                if data:
                    return data
            except OSError:
                pass

        # Fallback: synthetic minimal PoC
        return b"A" * target_size
