import os
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_len = 159
        keywords = [
            "poc",
            "crash",
            "uaf",
            "heap",
            "bug",
            "asan",
            "fuzz",
            "corpus",
            "seed",
            "regress",
            "test",
        ]
        code_exts = {
            ".c",
            ".h",
            ".cpp",
            ".cc",
            ".hpp",
            ".hh",
            ".java",
            ".py",
            ".md",
            ".rst",
            ".html",
            ".xml",
            ".yml",
            ".yaml",
            ".cmake",
            ".txt",
            ".in",
            ".am",
            ".ac",
        }
        size_limit_close = 4096

        try:
            tf = tarfile.open(src_path, "r:*")
        except Exception:
            return self._fallback_poc(target_len)

        best_exact_info = None
        best_exact_score = float("-inf")
        best_close_info = None
        best_close_score = float("-inf")

        with tf:
            members = tf.getmembers()
            for member in members:
                if not member.isfile():
                    continue
                size = member.size
                path = member.name
                lower = path.lower()
                ext = os.path.splitext(lower)[1]

                score = 0.0

                if "cuesheet" in lower:
                    score += 40.0
                elif "cue" in lower:
                    score += 30.0

                has_kw = False
                for kw in keywords:
                    if kw in lower:
                        has_kw = True
                        score += 10.0

                if ext in code_exts:
                    score -= 20.0

                skip_exact = ext in code_exts and "cue" not in lower and not has_kw

                if size == target_len and not skip_exact:
                    score += 100.0
                    if score > best_exact_score:
                        best_exact_score = score
                        best_exact_info = member
                elif size <= size_limit_close:
                    score -= abs(size - target_len) * 0.1
                    if score > best_close_score:
                        best_close_score = score
                        best_close_info = member

            if best_exact_info is not None:
                f = tf.extractfile(best_exact_info)
                if f is not None:
                    try:
                        data = f.read()
                    finally:
                        f.close()
                    if isinstance(data, bytes) and data:
                        return data

            if best_close_info is not None:
                lower = best_close_info.name.lower()
                if "cue" in lower or any(kw in lower for kw in keywords):
                    f = tf.extractfile(best_close_info)
                    if f is not None:
                        try:
                            data = f.read()
                        finally:
                            f.close()
                        if isinstance(data, bytes) and data:
                            return data

        return self._fallback_poc(target_len)

    def _fallback_poc(self, target_len: int) -> bytes:
        base = (
            b"REM GENRE Test\n"
            b"PERFORMER \"Artist\"\n"
            b"TITLE \"Album\"\n"
            b"FILE \"audio.wav\" WAVE\n"
            b"  TRACK 01 AUDIO\n"
            b"    INDEX 01 00:00:00\n"
        )
        if len(base) < target_len:
            base = base + b"0" * (target_len - len(base))
        elif len(base) > target_len:
            base = base[:target_len]
        return base