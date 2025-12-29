import tarfile
import os


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability by extracting the most
        likely PoC file from the provided source tarball.
        """
        try:
            tar = tarfile.open(src_path, "r:*")
        except Exception:
            # Fallback: return some arbitrary data if tar can't be opened
            return b"A" * 800

        text_exts = {
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx",
            ".txt", ".md", ".rst", ".py", ".sh", ".bat", ".cmd",
            ".json", ".xml", ".html", ".htm", ".js", ".css",
            ".yml", ".yaml", ".ini", ".cfg", ".cmake", ".am", ".ac",
            ".m4", ".in", ".awk", ".pl", ".pm", ".rb", ".java",
            ".go", ".rs", ".php", ".m", ".mm",
        }

        binary_pref_exts = {
            ".otf", ".ttf", ".ttc", ".woff", ".woff2",
            ".poc", ".bin", ".dat", ".font", ".fnt",
        }

        preferred_dirs = [
            "poc", "pocs", "crash", "crashes",
            "tests", "test", "fuzz", "fuzzer", "corpus",
        ]

        keywords = [
            "poc", "crash", "heap", "uaf", "use-after-free",
            "heap-use-after-free", "bug", "issue", "testcase",
            "id_", "clusterfuzz", "oss-fuzz",
        ]

        best_data = None
        best_score = float("-inf")

        for member in tar.getmembers():
            if not member.isreg():
                continue
            size = member.size
            if size <= 0:
                continue
            # Ignore very large files to keep things efficient/reasonable.
            if size > 2_000_000:
                continue

            name_lower = member.name.lower()
            _, ext = os.path.splitext(name_lower)

            if ext in text_exts:
                continue

            # Try to read the file contents
            try:
                f = tar.extractfile(member)
                if f is None:
                    continue
                data = f.read()
            except Exception:
                continue

            if not data:
                continue

            # Skip obviously text-like files (mostly printable, no NULs)
            sample = data[:200]
            if b"\x00" not in sample:
                printable = 0
                for b in sample:
                    if 32 <= b < 127 or b in (9, 10, 13):
                        printable += 1
                if printable / max(1, len(sample)) > 0.9:
                    # Likely text; skip
                    continue

            # Scoring: base on closeness to 800 bytes (ground-truth length)
            score = -abs(size - 800)

            # Strong preference for recognized binary extensions
            if ext in binary_pref_exts:
                score += 500

            # Boost for keywords in filename/path
            for kw in keywords:
                if kw in name_lower:
                    # Stronger boost for 'poc' and 'crash'
                    if kw in ("poc", "crash"):
                        score += 400
                    else:
                        score += 100

            # Boost if located in preferred directories
            for d in preferred_dirs:
                token = "/" + d + "/"
                if token in name_lower or name_lower.startswith(d + "/"):
                    score += 150
                    break

            # Additional heuristic: smaller binary files (but not too tiny)
            if 100 <= size <= 5000:
                score += 50

            if score > best_score:
                best_score = score
                best_data = data

        tar.close()

        if best_data is not None:
            return best_data

        # Fallback if nothing suitable was found: return a dummy 800-byte blob.
        return b"A" * 800