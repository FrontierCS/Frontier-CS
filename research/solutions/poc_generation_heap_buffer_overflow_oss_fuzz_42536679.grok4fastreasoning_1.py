import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        png = b'\x89PNG\r\n\x1a\n'
        # IHDR chunk
        width = 0
        height = 0
        ihdr_data = width.to_bytes(4, 'big') + height.to_bytes(4, 'big') + b'\x08\x00\x00\x00\x00'
        ihdr_header = b'\x00\x00\x00\x0dIHDR'
        ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff
        png += ihdr_header + ihdr_data + ihdr_crc.to_bytes(4, 'big')
        # IDAT chunk with empty deflate stream
        compressor = zlib.compressobj(wbits=-zlib.MAX_WBITS)
        empty_uncompressed = b''
        idat_data = compressor.compress(empty_uncompressed) + compressor.flush()
        idat_len = len(idat_data)
        idat_header = idat_len.to_bytes(4, 'big') + b'IDAT'
        idat_crc = zlib.crc32(b'IDAT' + idat_data) & 0xffffffff
        png += idat_header + idat_data + idat_crc.to_bytes(4, 'big')
        # IEND chunk
        iend_header = b'\x00\x00\x00\x00IEND'
        iend_crc = zlib.crc32(b'IEND') & 0xffffffff
        png += iend_header + iend_crc.to_bytes(4, 'big')
        return png