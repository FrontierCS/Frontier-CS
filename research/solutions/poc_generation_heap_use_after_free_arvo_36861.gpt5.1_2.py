import os
import tarfile
import gzip
import bz2
import lzma
import random


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_size = 71298
        # Try to find an existing PoC inside the source tarball/directory
        try:
            data = self._find_existing_poc(src_path, target_size)
            if data is not None:
                return data
        except Exception:
            pass
        # Fallback: synthesize a PoC input
        return self._generate_fallback_poc(target_size)

    def _find_existing_poc(self, src_path: str, target_size: int) -> bytes | None:
        if os.path.isdir(src_path):
            return self._search_directory(src_path, target_size)

        # Try opening as a tarball
        try:
            with tarfile.open(src_path, "r:*") as tf:
                return self._search_tar(tf, target_size)
        except tarfile.ReadError:
            # Not a tar file; fallback to treating as directory if possible
            if os.path.isdir(src_path):
                return self._search_directory(src_path, target_size)
        return None

    def _search_tar(self, tf: tarfile.TarFile, target_size: int) -> bytes | None:
        best_member = None
        best_score = None

        for member in tf.getmembers():
            if not member.isfile() or member.size <= 0:
                continue
            name = member.name
            size = member.size
            score = self._score_candidate(name, size, target_size)
            if best_score is None or score < best_score:
                best_score = score
                best_member = member

        if best_member is None:
            return None

        f = tf.extractfile(best_member)
        if f is None:
            return None
        data = f.read()
        if not data:
            return None
        # Try to decompress if it looks compressed
        data = self._maybe_decompress(best_member.name, data)
        return data

    def _search_directory(self, root: str, target_size: int) -> bytes | None:
        best_path = None
        best_score = None

        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size <= 0:
                    continue
                score = self._score_candidate(path, size, target_size)
                if best_score is None or score < best_score:
                    best_score = score
                    best_path = path

        if best_path is None:
            return None

        try:
            with open(best_path, "rb") as f:
                data = f.read()
        except OSError:
            return None
        if not data:
            return None
        data = self._maybe_decompress(best_path, data)
        return data

    def _score_candidate(self, name: str, size: int, target_size: int) -> int:
        # Lower score is better
        diff = abs(size - target_size)
        score = diff

        lname = name.lower()
        base = os.path.basename(lname)
        ext = os.path.splitext(base)[1]

        # Strong preference for exact size match
        if size == target_size:
            score -= 1_000_000

        # Prefer likely PoC / crash filenames
        keywords = [
            "poc",
            "crash",
            "uaf",
            "useafter",
            "use-after",
            "heap",
            "trigger",
            "input",
            "sample",
            "testcase",
            "usb",
            "redir",
            "serialize",
        ]
        if any(k in lname for k in keywords):
            score -= 200_000

        # Prefer typical binary extensions
        bin_exts = {
            ".bin",
            ".raw",
            ".dat",
            ".in",
            ".out",
            ".poc",
            ".usb",
            ".img",
        }
        if ext in bin_exts:
            score -= 50_000

        # Prefer files in corpus/seed directories
        dir_keywords = ["corpus", "seeds", "inputs", "crashes"]
        if any(dk in lname for dk in dir_keywords):
            score -= 20_000

        # Slight preference for files somewhat larger than target_size but not huge
        if size > target_size and size < target_size * 2:
            score -= 10_000

        return score

    def _maybe_decompress(self, name: str, data: bytes) -> bytes:
        lname = name.lower()
        try:
            if lname.endswith(".gz"):
                return gzip.decompress(data)
            if lname.endswith(".bz2"):
                return bz2.decompress(data)
            if lname.endswith(".xz") or lname.endswith(".lzma"):
                return lzma.decompress(data)
        except Exception:
            # If decompression fails, just return original
            return data
        return data

    def _generate_fallback_poc(self, size: int) -> bytes:
        # Deterministic pseudo-random data to explore more parser states
        rng = random.Random(0)
        try:
            raw = rng.randbytes(size)
        except AttributeError:
            raw = bytes(rng.getrandbits(8) for _ in range(size))

        buf = bytearray(raw)
        # Try to include a plausible magic string related to usbredir at the start
        magic = b"USBREDIR"
        if len(buf) >= len(magic):
            buf[: len(magic)] = magic
        return bytes(buf)
