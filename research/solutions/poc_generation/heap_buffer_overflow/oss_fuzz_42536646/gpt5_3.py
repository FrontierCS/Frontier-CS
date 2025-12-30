import os
import tarfile
import struct
import binascii
import zlib
import io
import re

class Solution:
    def _detect_format(self, src_path: str) -> str:
        fmt_scores = {
            'qoi': 0,
            'png': 0,
            'gif': 0,
            'bmp': 0,
            'stb': 0,
        }
        try:
            with tarfile.open(src_path, 'r:*') as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    # limit scanning to source-like files
                    name_lower = m.name.lower()
                    if not any(name_lower.endswith(ext) for ext in ('.c', '.cc', '.cpp', '.h', '.hpp', '.m', '.mm', '.rs', '.go', '.txt', '.md', '.cmake', '.build', '.sh', '.py', '.in', '.cfg', '.json', '.yml', '.yaml')):
                        # also scan files in fuzz directories even without extension
                        if 'fuzz' not in name_lower:
                            continue
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    try:
                        data = f.read(200000)  # cap read
                    except Exception:
                        continue
                    if not data:
                        continue
                    s = data.lower()
                    # QOI indicators
                    if b'qoi_decode' in s or b'qoif' in s or b'qoi.h' in s or b'qoi_' in s:
                        fmt_scores['qoi'] += 5
                    if b'png.h' in s or b'libpng' in s or b'lodepng' in s or b'spng.h' in s or b'png_' in s or b'ihdr' in s:
                        fmt_scores['png'] += 4
                    if b'gif_lib.h' in s or b'dgif' in s or b'gif89a' in s or b'gif87a' in s:
                        fmt_scores['gif'] += 3
                    if b'bmp' in s and (b'bmp.h' in s or b'bmpfile' in s or b'bitmap' in s):
                        fmt_scores['bmp'] += 2
                    if b'stbi_load_from_memory' in s or b'stb_image.h' in s:
                        fmt_scores['stb'] += 3
                # choose best
                best = max(fmt_scores.items(), key=lambda kv: kv[1])[0]
                # Map 'stb' to 'png' since stb_image can parse PNG reliably
                if best == 'stb':
                    return 'png'
                if fmt_scores[best] == 0:
                    return 'png'
                return best
        except Exception:
            return 'png'

    def _crc32(self, data: bytes) -> int:
        return binascii.crc32(data) & 0xffffffff

    def _png_chunk(self, t: bytes, d: bytes) -> bytes:
        length = struct.pack(">I", len(d))
        crc = struct.pack(">I", self._crc32(t + d))
        return length + t + d + crc

    def _make_png_zero_dim(self, zero_width=True) -> bytes:
        # PNG signature
        out = [b'\x89PNG\r\n\x1a\n']
        # IHDR
        width = 0 if zero_width else 1
        height = 1 if zero_width else 0
        bit_depth = 8
        color_type = 6  # RGBA
        compression = 0
        filter_method = 0
        interlace = 0
        ihdr = struct.pack(">IIBBBBB", width, height, bit_depth, color_type, compression, filter_method, interlace)
        out.append(self._png_chunk(b'IHDR', ihdr))
        # IDAT: compress a single row's filter byte (for height=1) or empty if height=0
        if height > 0:
            raw = b'\x00'  # filter type 0 for the row with zero pixels
        else:
            raw = b''
        comp = zlib.compress(raw)
        out.append(self._png_chunk(b'IDAT', comp))
        # IEND
        out.append(self._png_chunk(b'IEND', b''))
        return b''.join(out)

    def _make_qoi_zero_dim(self, zero_width=True) -> bytes:
        # QOI header: magic 'qoif', width (BE), height (BE), channels (3 or 4), colorspace (0 or 1)
        width = 0 if zero_width else 1
        height = 1 if zero_width else 0
        channels = 4
        colorspace = 0
        header = b'qoif' + struct.pack(">II", width, height) + bytes([channels, colorspace])
        # QOI end marker: 7 zero bytes and 1 byte 0x01
        end_marker = b'\x00' * 7 + b'\x01'
        return header + end_marker

    def _make_bmp_zero_dim(self, zero_width=True) -> bytes:
        # Minimal BMP with BITMAPINFOHEADER
        width = 0 if zero_width else 1
        height = 1 if zero_width else 0
        bpp = 24
        dib_header_size = 40
        compression = 0
        image_size = 0
        ppm = 2835
        clr_used = 0
        clr_important = 0
        bfType = b'BM'
        bfOffBits = 14 + 40  # No palette
        bfSize = bfOffBits + image_size
        file_header = bfType + struct.pack("<IHHI", bfSize, 0, 0, bfOffBits)
        dib_header = struct.pack("<IIIHHIIIIII",
                                 dib_header_size, width, height, 1, bpp,
                                 compression, image_size, ppm, ppm, clr_used, clr_important)
        return file_header + dib_header

    def solve(self, src_path: str) -> bytes:
        fmt = self._detect_format(src_path)
        if fmt == 'qoi':
            # Prefer zero width, non-zero height
            return self._make_qoi_zero_dim(True)
        elif fmt == 'bmp':
            return self._make_bmp_zero_dim(True)
        else:
            # Default to PNG
            return self._make_png_zero_dim(True)