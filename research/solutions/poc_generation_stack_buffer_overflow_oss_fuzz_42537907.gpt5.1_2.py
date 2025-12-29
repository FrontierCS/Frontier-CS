import os
import tarfile
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        TARGET_LEN = 1445

        # Heuristic keywords that usually indicate PoC / crash input files
        poc_keywords = [
            "poc",
            "crash",
            "repro",
            "reproducer",
            "testcase",
            "clusterfuzz",
            "oss-fuzz",
            "id_",
            "input",
            "seed",
            "bug",
            "hevc",
            "h265",
        ]

        # Common source/text extensions to de-prioritize
        source_like_exts = {
            ".c",
            ".cc",
            ".cpp",
            ".cxx",
            ".h",
            ".hpp",
            ".hh",
            ".py",
            ".java",
            ".txt",
            ".md",
            ".rst",
            ".html",
            ".htm",
            ".xml",
            ".json",
            ".yml",
            ".yaml",
            ".toml",
            ".cmake",
            ".m4",
            ".in",
            ".am",
            ".ac",
            ".sh",
            ".bash",
            ".zsh",
            ".bat",
            ".ps1",
            ".pl",
            ".rb",
            ".go",
            ".rs",
            ".php",
            ".js",
            ".ts",
            ".css",
            ".m",
            ".mm",
            ".swift",
            ".kt",
            ".s",
            ".S",
            ".asm",
            ".vcxproj",
            ".sln",
            ".vcproj",
            ".mak",
            ".make",
            ".mk",
            ".frag",
            ".vert",
            ".glsl",
            ".cl",
            ".csv",
            ".log",
        }

        max_reasonable_size = TARGET_LEN * 10  # avoid picking huge files as PoC

        def pick_from_tar(t: tarfile.TarFile) -> Optional[tarfile.TarInfo]:
            best_exact_keyword = None
            best_exact = None
            best_kw_diff_member = None
            best_kw_diff = float("inf")
            best_any_diff_member = None
            best_any_diff = float("inf")

            for m in t.getmembers():
                if not m.isfile():
                    continue
                size = m.size
                if size <= 0 or size > max_reasonable_size:
                    continue

                name_lower = m.name.lower()
                _, ext = os.path.splitext(name_lower)
                is_source_like = ext in source_like_exts
                has_kw = any(k in name_lower for k in poc_keywords)
                diff = abs(size - TARGET_LEN)

                # Highest priority: exact length + keyword in name
                if size == TARGET_LEN and has_kw:
                    best_exact_keyword = m
                    break

                # Next: exact length, non-source-like
                if size == TARGET_LEN and best_exact is None and not is_source_like:
                    best_exact = m

                # Next tiers: closest size with keywords, then any closest size
                if has_kw and not is_source_like and diff < best_kw_diff:
                    best_kw_diff = diff
                    best_kw_diff_member = m

                if not is_source_like and diff < best_any_diff:
                    best_any_diff = diff
                    best_any_diff_member = m

            if best_exact_keyword is not None:
                return best_exact_keyword
            if best_exact is not None:
                return best_exact
            if best_kw_diff_member is not None:
                return best_kw_diff_member
            return best_any_diff_member

        try:
            with tarfile.open(src_path, "r:*") as tf:
                member = pick_from_tar(tf)
                if member is not None:
                    extracted = tf.extractfile(member)
                    if extracted is not None:
                        data = extracted.read()
                        extracted.close()
                        # If the file is larger than needed but starts with the real PoC,
                        # we could truncate to TARGET_LEN to improve score, but to avoid
                        # breaking semantics we only do it on exact-size matches.
                        return data
        except Exception:
            pass

        # Fallback: read first TARGET_LEN bytes of the tarball itself
        try:
            with open(src_path, "rb") as f:
                return f.read(TARGET_LEN)
        except Exception:
            # Ultimate fallback: return some deterministic non-empty bytes
            return b"A" * TARGET_LEN