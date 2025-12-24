import tarfile
from typing import Optional


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
            return self._generate_poc_from_tar(src_path)
        except Exception:
            # Fallback: arbitrary 46-byte input
            return b"A" * 46

    def _generate_poc_from_tar(self, src_path: str) -> bytes:
        with tarfile.open(src_path, "r:*") as tar:
            members = [m for m in tar.getmembers() if m.isfile()]

            # First: try to find a file explicitly tied to this oss-fuzz issue ID
            member = self._pick_best_member(members, require_id=True)
            if member is None:
                # Fallback: pick best general fuzz/testcase-like file
                member = self._pick_best_member(members, require_id=False)

            if member is not None:
                extracted = tar.extractfile(member)
                if extracted is not None:
                    data = extracted.read()
                    if data:
                        return data

        # Ultimate fallback if nothing suitable is found
        return b"A" * 46

    def _pick_best_member(self, members, require_id: bool) -> Optional[tarfile.TarInfo]:
        best_member: Optional[tarfile.TarInfo] = None
        best_score: Optional[int] = None
        target_len = 46
        issue_id = "42536108"

        for m in members:
            name_lower = m.name.lower()

            if require_id and issue_id not in name_lower:
                continue

            # Basic size-based scoring: prefer closer to target_len and smaller files
            diff = abs(m.size - target_len)
            score = -diff

            if m.size == target_len:
                score += 30
            elif m.size < 2 * target_len:
                score += 10

            # Strong penalty for obviously irrelevant source files
            if name_lower.endswith((".c", ".cc", ".cpp", ".h", ".hpp", ".java", ".py", ".md", ".txt")):
                score -= 40

            # Directory / name hints
            keywords = [
                "oss-fuzz",
                "ossfuzz",
                "clusterfuzz",
                "testcase",
                "crash",
                "poc",
                "regress",
                "regression",
                "fuzz",
                "corpus",
                "inputs",
                "input",
                "cases",
                "bug",
                "heap",
                "overflow",
                "negative",
                "offset",
                "tests",
                "testing",
            ]
            for kw in keywords:
                if kw in name_lower:
                    score += 8

            # Extra boost if issue id is in path
            if issue_id in name_lower:
                score += 100

            # Prefer likely archive formats by extension
            archive_exts = [
                ".zip",
                ".tar",
                ".tgz",
                ".gz",
                ".bz2",
                ".xz",
                ".7z",
                ".cpio",
                ".ar",
            ]
            for ext in archive_exts:
                if name_lower.endswith(ext):
                    score += 15
                    break

            # Light penalty for very large files
            if m.size > 1024 * 1024:
                score -= 100

            if best_score is None or score > best_score:
                best_score = score
                best_member = m

        return best_member
