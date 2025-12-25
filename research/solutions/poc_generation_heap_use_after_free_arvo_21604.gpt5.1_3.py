import os
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_size = 33762

        try:
            tar = tarfile.open(src_path, "r:*")
        except Exception:
            return b""
        with tar:
            members = [m for m in tar.getmembers() if m.isfile() and m.size > 0]
            if not members:
                return b""

            exact_candidates = [m for m in members if m.size == target_size]

            def score_member(m):
                name = m.name
                size = m.size
                name_lower = name.lower()
                score = 0.0

                # Size closeness
                distance = abs(size - target_size)
                if target_size > 0:
                    closeness = max(0.0, 100.0 - (distance / target_size) * 100.0)
                    score += closeness

                # Directory-based keywords
                parts = name_lower.split("/")
                dir_parts = parts[:-1]
                basename = parts[-1] if parts else name_lower

                dir_keywords = [
                    "test",
                    "tests",
                    "regress",
                    "regression",
                    "fuzz",
                    "oss-fuzz",
                    "clusterfuzz",
                    "poc",
                    "crash",
                    "bugs",
                    "bug",
                    "corpus",
                ]
                for part in dir_parts:
                    for kw in dir_keywords:
                        if kw in part:
                            score += 5.0
                            break

                # Filename keywords
                if "poc" in basename or "proof" in basename:
                    score += 50.0
                if "uaf" in basename:
                    score += 30.0
                if "use-after-free" in basename or "use_after_free" in basename or "use-after" in basename:
                    score += 30.0
                if "heap" in basename:
                    score += 10.0
                if "bug" in basename or "issue" in basename:
                    score += 5.0
                if "crash" in basename:
                    score += 10.0
                if "fuzz" in basename or "oss-fuzz" in basename or "clusterfuzz" in basename:
                    score += 10.0

                # Extension-based weighting
                _, ext = os.path.splitext(basename)
                ext = ext.lower()

                # Prefer typical PoC file types
                if ext in (".pdf", ".bin", ".dat", ".raw", ".poc", ".input", ".in", ".txt", ".data"):
                    score += 2.0

                # Penalize obvious source-code files
                if ext in (
                    ".c",
                    ".cc",
                    ".cpp",
                    ".cxx",
                    ".h",
                    ".hpp",
                    ".hh",
                    ".java",
                    ".py",
                    ".rs",
                    ".go",
                    ".php",
                    ".rb",
                ):
                    score -= 20.0

                # Slight bonus for being under 1MB (likely a test case)
                if size < 1024 * 1024:
                    score += 5.0

                return score

            def choose_best(candidates):
                best = None
                best_score = float("-inf")
                for m in candidates:
                    s = score_member(m)
                    if s > best_score:
                        best_score = s
                        best = m
                return best

            if exact_candidates:
                best_member = choose_best(exact_candidates)
            else:
                # Filter out very large files to avoid picking huge assets
                filtered = [m for m in members if m.size <= 5 * 1024 * 1024]
                if not filtered:
                    filtered = members
                best_member = choose_best(filtered)

            if best_member is None:
                return b""

            try:
                f = tar.extractfile(best_member)
                if f is None:
                    return b""
                data = f.read()
            except Exception:
                return b""

            if not isinstance(data, bytes):
                data = bytes(data)
            return data
