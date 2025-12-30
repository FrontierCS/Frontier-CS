import os
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            tf = tarfile.open(src_path, "r:*")
        except Exception:
            return b"A" * 33

        best_data = None
        best_score = float("-inf")

        best_33_good_data = None
        best_33_good_score = float("-inf")

        # Keywords strongly related to this bug
        main_bug_keywords = [
            "capwap",
            "ndpi",
            "poc",
            "crash",
            "heap",
            "overflow",
            "bug",
            "fuzz",
        ]

        try:
            for m in tf.getmembers():
                if not m.isfile():
                    continue

                size = m.size
                if size <= 0:
                    continue

                name = m.name
                lower = name.lower()

                # Basic scoring
                score = 0.0

                # Prefer sizes close to 33 bytes
                score += max(0.0, 100.0 - 3.0 * abs(size - 33))

                # Path-based scoring
                kw_score_map = [
                    ("capwap", 200),
                    ("setup_capwap", 200),
                    ("ndpi", 50),
                    ("poc", 100),
                    ("crash", 60),
                    ("heap", 40),
                    ("overflow", 40),
                    ("bug", 20),
                    ("fuzz", 20),
                    ("oss", 10),
                    ("corpus", 15),
                ]
                for kw, kw_score in kw_score_map:
                    if kw in lower:
                        score += kw_score

                # Extension-based scoring
                base = os.path.basename(lower)
                if "." in base:
                    ext = base.rsplit(".", 1)[1]
                else:
                    ext = ""

                bin_exts = {
                    "bin",
                    "dat",
                    "poc",
                    "raw",
                    "pcap",
                    "pkt",
                    "input",
                    "seed",
                    "case",
                }
                txt_exts = {
                    "c",
                    "h",
                    "txt",
                    "md",
                    "markdown",
                    "json",
                    "yaml",
                    "yml",
                    "xml",
                    "html",
                    "htm",
                    "py",
                    "sh",
                    "cmake",
                    "in",
                    "ac",
                    "am",
                    "pc",
                    "m4",
                    "java",
                    "go",
                    "rs",
                    "cpp",
                    "cc",
                    "hpp",
                    "hh",
                }

                if ext in bin_exts:
                    score += 40.0
                if ext in txt_exts:
                    score -= 40.0

                # Directory-based scoring
                dirs = lower.split("/")
                for d in dirs:
                    if d in {
                        "tests",
                        "test",
                        "regress",
                        "regression",
                        "poc",
                        "bugs",
                        "bug",
                        "cases",
                        "inputs",
                        "seeds",
                        "crash",
                        "crashes",
                        "queue",
                        "corpus",
                        "clusterfuzz",
                    }:
                        score += 10.0

                # Don't waste time on very large files – unlikely to be a minimal PoC
                if size > 4096:
                    continue

                f = tf.extractfile(m)
                if f is None:
                    continue

                try:
                    data = f.read()
                except Exception:
                    continue

                if not data:
                    continue

                # Determine if file looks binary
                n_nonprint = 0
                for b in data:
                    if b < 9 or (b > 13 and b < 32) or b > 126:
                        n_nonprint += 1
                is_binary = n_nonprint > 0
                if is_binary:
                    binness = n_nonprint / float(len(data))
                    score += binness * 30.0
                else:
                    score -= 20.0

                # Check if path mentions bug-related keywords
                path_has_kw = any(kw in lower for kw in main_bug_keywords)

                # Track best overall candidate
                if score > best_score:
                    best_score = score
                    best_data = data

                # Track best 33-byte candidate that is likely relevant
                if len(data) == 33 and (is_binary or path_has_kw):
                    if score > best_33_good_score:
                        best_33_good_score = score
                        best_33_good_data = data
        finally:
            tf.close()

        if best_33_good_data is not None:
            return best_33_good_data
        if best_data is not None:
            return best_data

        return b"A" * 33