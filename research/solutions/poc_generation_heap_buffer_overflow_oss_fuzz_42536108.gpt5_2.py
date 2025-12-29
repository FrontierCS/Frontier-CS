import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        sig = b'PK\x05\x06'
        disk_no = 0
        disk_cd = 0
        entries_disk = 0
        entries_total = 0
        cd_size = 25
        cd_offset = 0
        comment_len = 24
        eocd = sig + struct.pack('<HHHHIIH', disk_no, disk_cd, entries_disk, entries_total, cd_size, cd_offset, comment_len)
        comment = b'A' * comment_len
        return eocd + comment