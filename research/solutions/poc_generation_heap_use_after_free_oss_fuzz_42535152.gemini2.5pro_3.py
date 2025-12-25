import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        
        def build_pdf_object(obj_num: int, gen_num: int, content: bytes) -> bytes:
            return f"{obj_num} {gen_num} obj\n".encode('ascii') + content + b"\nendobj\n"

        # Part 1: Initial PDF
        pdf = b"%PDF-1.7\n%\xE2\xE3\xCF\xD3\n\n"
        offsets1 = {}

        obj1_content = b"<< /Type /Catalog /Pages 2 0 R >>"
        obj1 = build_pdf_object(1, 0, obj1_content)
        offsets1[1] = len(pdf)
        pdf += obj1

        obj2_content = b"<< /Type /Pages /Kids [ 3 0 R ] /Count 1 >>"
        obj2 = build_pdf_object(2, 0, obj2_content)
        offsets1[2] = len(pdf)
        pdf += obj2
        
        obj3_content = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1 1] >>"
        obj3 = build_pdf_object(3, 0, obj3_content)
        offsets1[3] = len(pdf)
        pdf += obj3

        xref1_offset = len(pdf)
        xref1 = b"xref\n0 4\n"
        xref1 += b"0000000000 65535 f \n"
        xref1 += f"{offsets1[1]:010d} 00000 n \n".encode()
        xref1 += f"{offsets1[2]:010d} 00000 n \n".encode()
        xref1 += f"{offsets1[3]:010d} 00000 n \n".encode()
        pdf += xref1
        trailer1 = f"trailer\n<< /Size 4 /Root 1 0 R >>\n".encode()
        pdf += trailer1
        startxref1 = f"startxref\n{xref1_offset}\n".encode()
        pdf += startxref1
        pdf += b"%%EOF\n"

        # Part 2: Incremental Update
        junk_objs_blob = b''
        junk_offsets = {}
        for i in range(10, 200):
            obj_content = b'(' + (b'J' * 100) + str(i).encode() + b')'
            obj = build_pdf_object(i, 0, obj_content)
            junk_offsets[i] = len(pdf) + len(junk_objs_blob)
            junk_objs_blob += obj
        
        pdf += junk_objs_blob

        update_blob = b''
        update_offsets = {}

        obj3_new_content = b'(' + (b'B' * 10000) + b')'
        obj3_new = build_pdf_object(3, 0, obj3_new_content)
        update_offsets[3] = len(pdf) + len(update_blob)
        update_blob += obj3_new
        
        num_stream_objs = 100
        stream_obj_numbers = range(200, 200 + num_stream_objs)
        
        stream_header_parts = []
        stream_content_parts = []
        
        for i, obj_num in enumerate(stream_obj_numbers):
            content_part = f"<< /MyStreamObj {i} >>".encode()
            obj_offset = sum(len(p) for p in stream_content_parts)
            stream_header_parts.append(f"{obj_num} {obj_offset}".encode())
            stream_content_parts.append(content_part)

        stream_header = b' '.join(stream_header_parts) + b' '
        stream_content = b''.join(stream_content_parts)

        uncompressed_stream = stream_header + stream_content
        compressed_stream = zlib.compress(uncompressed_stream)
        
        obj_stream_header = f"<< /Type /ObjStm /N {num_stream_objs} /First {len(stream_header)} /Filter /FlateDecode /Length {len(compressed_stream)} >>".encode()
        obj4_content = obj_stream_header + b"\nstream\n" + compressed_stream + b"\nendstream"
        obj4 = build_pdf_object(4, 0, obj4_content)
        update_offsets[4] = len(pdf) + len(update_blob)
        update_blob += obj4
        
        pdf += update_blob

        xref2_offset = len(pdf)
        max_obj_num = 199 + num_stream_objs
        
        xref2 = b"xref\n"
        xref2 += b"3 2\n"
        xref2 += f"{update_offsets[3]:010d} 00000 n \n".encode()
        xref2 += f"{update_offsets[4]:010d} 00000 n \n".encode()
        xref2 += b"10 190\n"
        for i in range(10, 200):
            xref2 += f"{junk_offsets[i]:010d} 00000 n \n".encode()
        
        pdf += xref2
        
        trailer2 = f"""trailer
<< /Size {max_obj_num + 1} /Root 1 0 R /Prev {xref1_offset} >>
""".encode()
        pdf += trailer2
        
        startxref2 = f"startxref\n{xref2_offset}\n".encode()
        pdf += startxref2
        pdf += b"%%EOF\n"

        return pdf
