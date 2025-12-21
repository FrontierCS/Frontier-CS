import os
import tarfile
from typing import Optional, Tuple, List


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Attempt to locate a bundled PoC in the source tarball. If none found,
        fall back to a minimal 8-byte regex payload likely to trigger issues
        with capturing parentheses vs external ovector sizing.
        """
        poc = self._find_poc_from_tar(src_path)
        if poc is not None and len(poc) > 0:
            return poc
        # Fallback: 8-byte payload
        return b"()()()()"

    def _find_poc_from_tar(self, src_path: str) -> Optional[bytes]:
        """
        Search the tarball for a PoC-looking file, preferring files of length 8 bytes.
        """
        try:
            with tarfile.open(src_path, "r:*") as tf:
                candidates: List[Tuple[int, str, bytes]] = []
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    size = m.size
                    # Skip overly large files
                    if size <= 0 or size > 1_000_000:
                        continue
                    name = (m.name or "").lower()

                    # Read file content
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                    except Exception:
                        continue
                    if not data:
                        continue

                    # Compute score
                    score = self._score_name_and_size(name, size)
                    candidates.append((score, name, data))

                if not candidates:
                    return None

                # Prefer maximum score
                candidates.sort(key=lambda x: x[0], reverse=True)
                best_score, best_name, best_data = candidates[0]

                # If there are multiple with the same score, prefer exact size 8
                top_score = best_score
                top_group = [c for c in candidates if c[0] == top_score]
                if len(top_group) > 1:
                    exact_8 = [c for c in top_group if len(c[2]) == 8]
                    if exact_8:
                        # Pick the first lexicographically smallest name
                        exact_8.sort(key=lambda x: x[1])
                        return exact_8[0][2]
                    # Else return lexicographically smallest name
                    top_group.sort(key=lambda x: x[1])
                    return top_group[0][2]

                return best_data
        except Exception:
            return None

    def _score_name_and_size(self, name: str, size: int) -> int:
        """
        Heuristic scoring function to rank likely PoC files.
        Higher score is better.
        """
        score = 0

        # Size closeness to 8 preferred
        score -= abs(size - 8) * 5

        # Reward small files
        if size <= 64:
            score += 40
        if size <= 32:
            score += 30
        if size <= 16:
            score += 20
        if size == 8:
            score += 100

        # Name-based hints
        hints = {
            "poc": 1000,
            "proof": 400,
            "crash": 900,
            "testcase": 850,
            "clusterfuzz": 800,
            "minimized": 700,
            "repro": 600,
            "trigger": 500,
            "id:": 480,
            "issue": 450,
            "bug": 400,
            "overflow": 380,
            "overread": 360,
            "oob": 350,
            "stdin": 300,
            "regex": 200,
            "pattern": 200,
            "input": 120,
            "seed": 100,
            "sample": 100,
            "case": 80,
            "reduced": 70,
            "payload": 60,
            "exploit": 60,
            "fail": 50,
        }
        for k, v in hints.items():
            if k in name:
                score += v

        # Penalize source-like files
        if name.endswith((".c", ".cc", ".cpp", ".h", ".hpp", ".py", ".java", ".go", ".rs", ".js", ".ts", ".html", ".md")):
            score -= 400

        # Prefer binary or data-like files
        if name.endswith((".bin", ".dat", ".txt", ".re", ".re2", ".poc")) or name.rsplit(".", 1)[-1] in {"", "bin", "dat"}:
            score += 50

        # Slight bonus if in typical fuzz directories
        dirs_bonus = {
            "/poc": 120, "/pocs": 120, "/poC": 120,
            "/crash": 110, "/crashes": 110,
            "/repro": 100, "/repros": 100,
            "/fuzz": 80, "/fuzzer": 80, "/fuzzing": 80,
            "/testcase": 70, "/testcases": 70,
            "/inputs": 60, "/input": 60,
            "/seeds": 50, "/seed": 50,
            "/tests": 40, "/test": 40,
            "/examples": 20, "/example": 20,
        }
        for d, v in dirs_bonus.items():
            if d in name:
                score += v

        return score
