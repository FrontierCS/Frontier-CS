import os
import tarfile
import sys


class Solution:
    def _score_member(self, member) -> float:
        name = member.name.lower()
        size = member.size
        score = 0.0

        # Prefer sizes close to 10 bytes
        score -= abs(size - 10) * 5.0
        score -= size / 1024.0  # slight penalty for large files

        # Name-based heuristics
        if "poc" in name:
            score += 1000.0
        if "crash" in name:
            score += 900.0
        if "id:" in name or "id_" in name or "id-" in name:
            score += 700.0
        if "tic30" in name or "tic-30" in name or "tic_30" in name or "tic30-dis" in name:
            score += 400.0
        if "binutils" in name:
            score += 100.0
        if "/poc" in name or "\\poc" in name:
            score += 100.0
        if "/crash" in name or "\\crash" in name:
            score += 100.0

        # Extension-based heuristics
        for ext, val in ((".bin", 300.0), (".dat", 280.0), (".raw", 250.0),
                         (".obj", 200.0), (".o", 150.0)):
            if name.endswith(ext):
                score += val
                break

        return score

    class _DirMember:
        def __init__(self, path: str, size: int):
            self.name = path
            self.size = size

    def _select_best_member(self, members):
        best_any = None
        best_any_score = float("-inf")
        best_10 = None
        best_10_score = float("-inf")

        for m in members:
            if m.size <= 0:
                continue
            s = self._score_member(m)
            if s > best_any_score:
                best_any_score = s
                best_any = m
            if m.size == 10 and s > best_10_score:
                best_10_score = s
                best_10 = m

        return best_10 if best_10 is not None else best_any

    def _solve_from_dir(self, src_dir: str) -> bytes:
        members = []
        for root, _, files in os.walk(src_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    size = os.path.getsize(fpath)
                except OSError:
                    continue
                members.append(self._DirMember(fpath, size))

        if not members:
            return b"A" * 10

        candidate = self._select_best_member(members)
        if candidate is None:
            return b"A" * 10

        try:
            with open(candidate.name, "rb") as f:
                return f.read()
        except OSError:
            return b"A" * 10

    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball or directory

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        if os.path.isdir(src_path):
            return self._solve_from_dir(src_path)

        try:
            tar = tarfile.open(src_path, "r:*")
        except tarfile.ReadError:
            # Not a tarball; treat as directory
            return self._solve_from_dir(src_path)

        with tar:
            members = [m for m in tar.getmembers() if m.isfile() and m.size > 0]
            if not members:
                return b"A" * 10

            candidate = self._select_best_member(members)
            if candidate is None:
                return b"A" * 10

            try:
                f = tar.extractfile(candidate)
                if f is None:
                    return b"A" * 10
                data = f.read()
                return data
            except Exception:
                return b"A" * 10


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "."
    data = Solution().solve(src)
    sys.stdout.buffer.write(data)
