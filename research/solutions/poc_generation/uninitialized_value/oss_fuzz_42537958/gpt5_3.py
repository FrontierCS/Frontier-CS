import tarfile
import re
import base64


class Solution:
    def solve(self, src_path: str) -> bytes:
        def read_text_from_tar(tar, member):
            f = tar.extractfile(member)
            if not f:
                return ""
            try:
                return f.read().decode("utf-8", "replace")
            finally:
                f.close()

        def read_bytes_from_tar(tar, member):
            f = tar.extractfile(member)
            if not f:
                return b""
            try:
                return f.read()
            finally:
                f.close()

        def find_transform_fuzzer(tar):
            candidates = []
            for m in tar.getmembers():
                name = m.name.lower()
                if not m.isfile():
                    continue
                if not (name.endswith(".cc") or name.endswith(".c") or name.endswith(".cpp") or name.endswith(".h")):
                    continue
                text = read_text_from_tar(tar, m)
                if "LLVMFuzzerTestOneInput" not in text:
                    continue
                # Prioritize transform fuzzers
                if re.search(r'\btj3?Transform\b', text):
                    return (m.name, text)
                candidates.append((m.name, text))
            # Fallback: a tj3Compress fuzzer (secondary)
            for name, text in candidates:
                if re.search(r'\btj3?Compress\b', text):
                    return (name, text)
            # Fallback: any fuzzer
            return candidates[0] if candidates else (None, None)

        def estimate_prefix_len(text):
            if not text:
                return 0
            # Find integer offsets added to data or subtracted from size
            ints = []
            for m in re.finditer(r'data\s*\+\s*(\d+)', text):
                try:
                    v = int(m.group(1))
                    if 0 < v < 4096:
                        ints.append(v)
                except Exception:
                    pass
            for m in re.finditer(r'size\s*-\s*(\d+)', text):
                try:
                    v = int(m.group(1))
                    if 0 < v < 4096:
                        ints.append(v)
                except Exception:
                    pass
            # Heuristic: use maximum seen small constant as prefix length
            return max(ints) if ints else 0

        def find_smallest_jpeg(tar):
            best = None
            best_size = None
            for m in tar.getmembers():
                if not m.isfile():
                    continue
                lname = m.name.lower()
                if not any(lname.endswith(ext) for ext in (".jpg", ".jpeg", ".jpe", ".jfif")):
                    continue
                b = read_bytes_from_tar(tar, m)
                # quick validation: must start with SOI marker
                if len(b) >= 4 and b[0] == 0xFF and b[1] == 0xD8:
                    if best is None or len(b) < best_size:
                        best = b
                        best_size = len(b)
            return best

        try:
            with tarfile.open(src_path, "r:*") as tar:
                fuzzer_name, fuzzer_text = find_transform_fuzzer(tar)
                prefix_len = estimate_prefix_len(fuzzer_text)
                jpeg_bytes = find_smallest_jpeg(tar)

                if jpeg_bytes is None or len(jpeg_bytes) == 0:
                    # Fallback 1x1 JPEG (base64 for a minimal valid JPEG)
                    # This is a commonly used 1x1 JPEG black pixel
                    b64_jpg = (
                        "/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEB"
                        "AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wAALCAAaABoBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAACP/EABQQAQAAAAAA"
                        "AAAAAAAAAAAAAAD/2gAIAQEAAD8A/9k="
                    )
                    try:
                        jpeg_bytes = base64.b64decode(b64_jpg)
                    except Exception:
                        jpeg_bytes = b"\xff\xd8\xff\xd9"

                prefix = bytes([0] * max(0, prefix_len))
                return prefix + jpeg_bytes
        except Exception:
            # Last-resort very small (invalid) JPEG-like bytes; better than nothing for fallback
            return b"\xff\xd8\xff\xd9"