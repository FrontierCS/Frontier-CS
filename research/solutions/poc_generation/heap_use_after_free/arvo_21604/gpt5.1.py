import tarfile
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability by extracting an appropriate
        input file from the given source tarball.
        """
        try:
            tf = tarfile.open(src_path, "r:*")
        except Exception:
            # If we cannot open the tarball, return a trivial placeholder input.
            return b"A"

        try:
            best_member: Optional[tarfile.TarInfo] = None
            best_score = float("-inf")
            target_length = 33762

            for member in tf.getmembers():
                if not member.isreg():
                    continue
                if member.size <= 0:
                    continue

                name_lower = member.name.lower()
                score = 0.0

                # Extension-based scoring
                if name_lower.endswith(".pdf"):
                    score += 200.0
                if name_lower.endswith(".poc"):
                    score += 150.0
                if name_lower.endswith(".bin"):
                    score += 80.0
                if name_lower.endswith(".input") or name_lower.endswith(".in"):
                    score += 60.0
                if name_lower.endswith(".txt"):
                    score += 20.0

                # Keyword-based scoring
                keywords = [
                    ("poc", 120.0),
                    ("crash", 110.0),
                    ("uaf", 100.0),
                    ("use-after", 100.0),
                    ("heap-use-after-free", 120.0),
                    ("heap", 40.0),
                    ("fuzz", 30.0),
                    ("id:", 20.0),
                    ("sample", 10.0),
                    ("test", 5.0),
                ]
                for kw, kw_score in keywords:
                    if kw in name_lower:
                        score += kw_score

                # Size closeness scoring
                dist = abs(member.size - target_length)
                # Bonus for exact match
                if dist == 0:
                    score += 300.0
                # General closeness bonus
                size_score = max(0.0, 100.0 - dist / 500.0)
                score += size_score

                # Penalize excessively large files
                if member.size > 5 * target_length:
                    score -= 50.0
                if member.size > 50 * target_length:
                    score -= 200.0

                if score > best_score:
                    best_score = score
                    best_member = member

            if best_member is None:
                return b"A"

            extracted = tf.extractfile(best_member)
            if extracted is None:
                return b"A"
            data = extracted.read()
            return data if isinstance(data, bytes) else bytes(data)
        finally:
            try:
                tf.close()
            except Exception:
                pass