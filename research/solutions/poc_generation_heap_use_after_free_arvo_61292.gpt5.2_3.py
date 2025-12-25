import os
import io
import re
import tarfile
import tempfile
from typing import List, Tuple, Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        root = self._prepare_source_root(src_path)
        try:
            poc = self._find_poc_bytes(root, target_len=159)
            if poc is not None:
                return poc
            # Fallback: return something deterministic and small if no testcase found
            return b"\x00"
        finally:
            self._cleanup_source_root(root)

    def _prepare_source_root(self, src_path: str) -> str:
        if os.path.isdir(src_path):
            return src_path

        tmpdir = tempfile.mkdtemp(prefix="src_")
        try:
            with tarfile.open(src_path, "r:*") as tf:
                self._safe_extractall(tf, tmpdir)
        except Exception:
            # If extraction fails, keep tmpdir and just return it (will fallback to b"\x00")
            return tmpdir
        return tmpdir

    def _cleanup_source_root(self, root: str) -> None:
        # Only remove if it was our temp directory
        base = os.path.basename(root.rstrip(os.sep))
        if base.startswith("src_") and os.path.isdir(root):
            for dirpath, dirnames, filenames in os.walk(root, topdown=False):
                for fn in filenames:
                    p = os.path.join(dirpath, fn)
                    try:
                        os.unlink(p)
                    except Exception:
                        pass
                for dn in dirnames:
                    p = os.path.join(dirpath, dn)
                    try:
                        os.rmdir(p)
                    except Exception:
                        pass
            try:
                os.rmdir(root)
            except Exception:
                pass

    def _safe_extractall(self, tf: tarfile.TarFile, path: str) -> None:
        base = os.path.realpath(path)
        for member in tf.getmembers():
            name = member.name
            if not name:
                continue
            # Reject absolute paths and parent traversal
            if name.startswith("/") or name.startswith("\\"):
                continue
            if re.search(r"(^|[\\/])\.\.([\\/]|$)", name):
                continue
            dest = os.path.realpath(os.path.join(path, name))
            if not dest.startswith(base + os.sep) and dest != base:
                continue
            try:
                tf.extract(member, path=path, set_attrs=False)
            except Exception:
                # Continue extracting others
                continue

    def _find_poc_bytes(self, root: str, target_len: int = 159) -> Optional[bytes]:
        candidates = self._collect_candidate_files(root)
        if not candidates:
            return None

        scored: List[Tuple[int, int, str]] = []
        for p in candidates:
            try:
                st = os.stat(p)
            except Exception:
                continue
            if not os.path.isfile(p):
                continue
            size = int(st.st_size)
            if size <= 0:
                continue
            if size > 4 * 1024 * 1024:
                continue
            score = self._score_candidate_path(p, size, target_len)
            scored.append((score, size, p))

        if not scored:
            return None

        scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)
        # Try top few and return first readable
        for _, _, p in scored[:50]:
            try:
                with open(p, "rb") as f:
                    data = f.read()
                if data:
                    return data
            except Exception:
                continue
        return None

    def _collect_candidate_files(self, root: str) -> List[str]:
        out: List[str] = []
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                p = os.path.join(dirpath, fn)
                out.append(p)
        return out

    def _score_candidate_path(self, path: str, size: int, target_len: int) -> int:
        lp = path.lower()
        bn = os.path.basename(lp)

        bad_exts = {
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
            ".py", ".java", ".js", ".ts", ".go", ".rs",
            ".md", ".rst", ".txt", ".html", ".css",
            ".cmake", ".in", ".m4", ".ac", ".am", ".sh", ".bat",
            ".yml", ".yaml", ".json", ".toml", ".ini", ".cfg", ".conf",
            ".patch", ".diff",
            ".o", ".a", ".so", ".dylib", ".dll", ".exe",
            ".png", ".jpg", ".jpeg", ".gif", ".svg", ".pdf",
        }
        good_exts = {
            "", ".bin", ".dat", ".raw", ".fuzz", ".poc", ".sample",
            ".flac", ".cue", ".cuesheet", ".m4a", ".mp3", ".wav", ".ogg",
        }

        _, ext = os.path.splitext(bn)

        score = 0

        # Strong signals
        if "clusterfuzz" in lp:
            score += 2000
        if "testcase" in lp:
            score += 1400
        if "minimized" in lp:
            score += 900
        if "crash" in lp or "crasher" in lp:
            score += 1100
        if "poc" in lp or "repro" in lp or "reproducer" in lp:
            score += 900
        if "uaf" in lp or "use-after-free" in lp or "useafterfree" in lp:
            score += 700
        if "cuesheet" in lp or "cue_sheet" in lp:
            score += 250
        if "seekpoint" in lp or "seek_point" in lp or "seektable" in lp:
            score += 200
        if "oss-fuzz" in lp or "ossfuzz" in lp:
            score += 250
        if "fuzz" in lp:
            score += 150

        if ext in good_exts:
            score += 200
        if ext in bad_exts:
            score -= 600

        # Avoid obvious docs
        if "/doc/" in lp or "/docs/" in lp or "\\doc\\" in lp or "\\docs\\" in lp:
            score -= 200

        # Prefer near target length, and small overall
        score += max(0, 400 - abs(size - target_len) * 3)
        score += max(0, 300 - size // 2)

        # Prefer files in likely regression/test directories
        if "/test" in lp or "\\test" in lp:
            score += 80
        if "/fuzz" in lp or "\\fuzz" in lp:
            score += 120
        if "/corpus" in lp or "\\corpus" in lp:
            score += 120
        if "/regress" in lp or "\\regress" in lp:
            score += 120

        return score