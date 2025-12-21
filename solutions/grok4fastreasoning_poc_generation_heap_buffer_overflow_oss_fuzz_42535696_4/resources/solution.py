class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b"%PDF-1.7\n"
        stream_length = 4
        stream_content = b"Q Q\n"
        body_list = [
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n",
            b"4 0 obj\n<< /Length " + str(stream_length).encode("ascii") + b" >>\nstream\n",
            stream_content,
            b"endstream\nendobj\n"
        ]
        body = b"".join(body_list)
        offsets = {}
        current_pos = len(header)
        for i in range(1, 5):
            offsets[i] = current_pos
            current_pos += len(body_list[i-1])
        xref_parts = [
            b"xref\n0 5\n0000000000 65535 f \n"
        ]
        for i in range(1,5):
            off_str = f"{offsets[i]:010d}".encode("ascii")
            xref_parts.append(off_str + b" 00000 n \n")
        xref = b"".join(xref_parts)
        xref_offset = len(header) + len(body)
        trailer = b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n" + f"{xref_offset}".encode("ascii") + b"\n%%EOF"
        full_pdf = header + body + xref + trailer
        return full_pdf
