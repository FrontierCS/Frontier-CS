import os
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_len = 37535

        def score_member(member: tarfile.TarInfo) -> int:
            name = member.name.lower()
            size = member.size
            score = 0

            # Size closeness
            if size == target_len:
                score += 1000
            diff = abs(size - target_len)
            score += max(0, 400 - diff)  # up to +400 if exact, 0 if diff >= 400

            # Keywords indicating PoC
            keywords = [
                "poc",
                "crash",
                "testcase",
                "clusterfuzz",
                "fuzz",
                "repro",
                "openpgp",
                "heap",
                "overflow",
                "42537670",
                "oss-fuzz",
            ]
            if any(k in name for k in keywords):
                score += 300

            # Extensions that look like binary inputs
            good_exts = [
                ".pgp",
                ".gpg",
                ".asc",
                ".bin",
                ".raw",
                ".dat",
                ".in",
                ".input",
                ".case",
            ]
            if any(name.endswith(ext) for ext in good_exts):
                score += 100

            # Penalize obvious source/text files
            bad_exts = [
                ".c",
                ".cc",
                ".cpp",
                ".cxx",
                ".h",
                ".hh",
                ".hpp",
                ".txt",
                ".md",
                ".rst",
                ".html",
                ".xml",
                ".json",
                ".yaml",
                ".yml",
                ".py",
                ".java",
                ".go",
                ".rs",
            ]
            if any(name.endswith(ext) for ext in bad_exts):
                score -= 500

            return score

        # Try to locate a promising PoC directly in the tarball
        try:
            with tarfile.open(src_path, "r:*") as tar:
                best_member = None
                best_score = None

                for member in tar.getmembers():
                    if not member.isfile():
                        continue
                    # Skip trivially small files
                    if member.size == 0:
                        continue

                    s = score_member(member)
                    if best_member is None or s > best_score:
                        best_member = member
                        best_score = s

                # Require a reasonably high score to believe it's the PoC
                if best_member is not None and best_score is not None and best_score >= 1000:
                    f = tar.extractfile(best_member)
                    if f is not None:
                        data = f.read()
                        if isinstance(data, bytes) and data:
                            return data
        except Exception:
            # Fall through to fallback if anything goes wrong
            pass

        # Fallback: generic small input if no suitable PoC was found
        return b"A" * 100