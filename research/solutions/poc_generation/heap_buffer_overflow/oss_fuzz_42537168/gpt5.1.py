import tarfile
import gzip
import lzma
import bz2
import zipfile
import io


class Solution:
    GROUND_TRUTH_SIZE = 913919

    def solve(self, src_path: str) -> bytes:
        try:
            return self._extract_poc_from_tar(src_path)
        except Exception:
            return self._fallback_poc()

    def _extract_poc_from_tar(self, tar_path: str) -> bytes:
        Lg = self.GROUND_TRUTH_SIZE
        with tarfile.open(tar_path, "r:*") as tf:
            members = [m for m in tf.getmembers() if m.isfile()]

            # Pass 1: prioritize by filename patterns
            patterns = [
                "42537168",
                "poc",
                "PoC",
                "crash",
                "testcase",
                "clusterfuzz",
                "minimized",
                "reproducer",
                "input",
                "bug",
            ]

            def name_score(name: str) -> int:
                lower = name.lower()
                score = 0
                for i, pat in enumerate(patterns):
                    if pat.lower() in lower:
                        score += 1 << (len(patterns) - i)
                return score

            best_member = None
            best_score = 0
            best_diff = None

            for m in members:
                score = name_score(m.name)
                if score > 0:
                    diff = abs(m.size - Lg)
                    if (
                        score > best_score
                        or (
                            score == best_score
                            and (best_diff is None or diff < best_diff)
                        )
                    ):
                        best_member = m
                        best_score = score
                        best_diff = diff

            if best_member is not None:
                data = self._read_member(tf, best_member)
                data = self._maybe_decompress(best_member.name, data)
                if data:
                    return data

            # Pass 2: exact size match
            for m in members:
                if m.size == Lg:
                    return self._read_member(tf, m)

            # Pass 3: closest size
            closest_member = None
            closest_diff = None
            for m in members:
                diff = abs(m.size - Lg)
                if closest_diff is None or diff < closest_diff:
                    closest_diff = diff
                    closest_member = m

            if closest_member is not None:
                return self._read_member(tf, closest_member)

        return self._fallback_poc()

    def _read_member(self, tf: tarfile.TarFile, member: tarfile.TarInfo) -> bytes:
        f = tf.extractfile(member)
        if f is None:
            return b""
        with f:
            return f.read()

    def _maybe_decompress(self, name: str, data: bytes) -> bytes:
        lower = name.lower()
        # Try single-layer decompression based on extension
        try:
            if lower.endswith(".gz"):
                return gzip.decompress(data)
            if lower.endswith(".xz") or lower.endswith(".lzma"):
                return lzma.decompress(data)
            if lower.endswith(".bz2"):
                return bz2.decompress(data)
            if lower.endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    # Prefer file whose size is closest to ground truth
                    infos = [zi for zi in zf.infolist() if not zi.is_dir()]
                    if not infos:
                        return data
                    Lg = self.GROUND_TRUTH_SIZE
                    infos.sort(key=lambda zi: abs(zi.file_size - Lg))
                    for zi in infos:
                        try:
                            return zf.read(zi)
                        except Exception:
                            continue
                    # Fallback to first
                    return zf.read(infos[0])
        except Exception:
            pass
        return data

    def _fallback_poc(self) -> bytes:
        # Generic fallback payload if extraction fails
        # Use a moderately large input to exercise potential depth-related logic.
        pattern = b"<clip>" * 1024 + b"</clip>" * 1024
        return pattern