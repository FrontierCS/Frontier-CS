import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        filler = b"A" * 24
        eocd = struct.pack(
            "<IHHHHIIH",
            0x06054B50,  # End of central directory signature
            0,           # Number of this disk
            0,           # Disk where central directory starts
            1,           # Number of central directory records on this disk
            1,           # Total number of central directory records
            0,           # Size of central directory
            0xFFFFFFF0,  # Offset of start of central directory w.r.t. starting disk
            0            # .ZIP file comment length
        )
        return filler + eocd