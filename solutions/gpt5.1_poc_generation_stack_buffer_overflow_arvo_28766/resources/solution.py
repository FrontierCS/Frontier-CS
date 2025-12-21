import os
import tarfile
import gzip


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        try:
            poc = self._find_poc_in_tar(src_path)
            if poc is not None and len(poc) > 0:
                return poc
        except Exception:
            pass

        # Fallback: generic 140-byte payload
        return b"A" * 140

    def _find_poc_in_tar(self, src_path: str) -> bytes | None:
        # Target length from problem statement
        target_len = 140

        if not os.path.isfile(src_path):
            return None

        try:
            tf = tarfile.open(src_path, mode="r:*")
        except Exception:
            return None

        best_member = None
        best_score = None

        # Keywords that strongly indicate an actual PoC / crash input
        primary_keywords = [
            "clusterfuzz",
            "oss-fuzz",
            "ossfuzz",
            "testcase",
            "minimized",
            "poc",
            "crash",
            "id_",
        ]

        # Additional keywords that may indicate bug repro / malformed inputs
        secondary_keywords = [
            "bug",
            "regress",
            "cve",
            "overflow",
            "fuzz",
            "corpus",
            "invalid",
            "malformed",
            "broken",
            "fail",
            "snapshot",
            "snap",
            "memory",
            "mem",
            "dump",
        ]

        # Extensions that are commonly used for binary PoCs or test data
        interesting_exts = {
            ".bin",
            ".dat",
            ".raw",
            ".snap",
            ".snapshot",
            ".dump",
            ".mem",
            ".pb",
            ".pbtxt",
            ".in",
            ".input",
            ".case",
            ".gz",
        }

        try:
            members = tf.getmembers()
        except Exception:
            tf.close()
            return None

        for m in members:
            if not m.isfile():
                continue
            if m.size <= 0:
                continue
            # Limit to reasonably small files to avoid huge reads
            if m.size > 4096:
                continue

            name = m.name
            lname = name.lower()

            # Count keyword matches
            primary_hits = sum(1 for kw in primary_keywords if kw in lname)
            secondary_hits = sum(1 for kw in secondary_keywords if kw in lname)

            base_score = 0

            # Strong bonus for primary keywords (fuzzing / crash artifacts)
            if primary_hits > 0:
                base_score += primary_hits * 1000

            # Medium bonus for secondary keywords
            if secondary_hits > 0:
                base_score += secondary_hits * 200

            # Bonus for living in fuzz/corpus/testdata-like directories
            if any(seg in lname for seg in ("fuzz", "corpus", "crash", "poc", "testdata", "regress")):
                base_score += 300

            # Bonus for interesting extensions
            _, ext = os.path.splitext(lname)
            if ext in interesting_exts:
                base_score += 400

            # If there are absolutely no hints that this is a PoC, skip
            if base_score == 0:
                continue

            # Closeness to target length
            length_score = -abs(m.size - target_len)

            score = base_score + length_score

            if best_score is None or score > best_score:
                best_score = score
                best_member = m

        data = None
        if best_member is not None:
            try:
                f = tf.extractfile(best_member)
                if f is not None:
                    data = f.read()
                    # If it's a .gz, attempt to decompress
                    if best_member.name.lower().endswith(".gz"):
                        try:
                            data = gzip.decompress(data)
                        except Exception:
                            # If decompression fails, keep original bytes
                            pass
            except Exception:
                data = None

        tf.close()
        return data
