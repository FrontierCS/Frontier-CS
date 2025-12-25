class Solution:
    def solve(self, src_path: str) -> bytes:
        items = [
            (1, b"<< /Type /Catalog /Pages 2 0 R >>"),
            (2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"),
            (1, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        ]

        # Build offsets and header
        offsets = [0] * len(items)
        while True:
            header_parts = []
            for i, (objnum, _) in enumerate(items):
                header_parts.append(str(objnum).encode('ascii'))
                header_parts.append(b' ')
                header_parts.append(str(offsets[i]).encode('ascii'))
                header_parts.append(b' ')
            header = b''.join(header_parts).rstrip(b' ')
            header_len = len(header)
            new_offsets = []
            current = header_len
            changed = False
            for i in range(len(items)):
                new_off = current
                if new_off != offsets[i]:
                    changed = True
                new_offsets.append(new_off)
                current += len(items[i][1])
            offsets = new_offsets
            if not changed:
                break

        # Final header
        header_parts = []
        for i, (objnum, _) in enumerate(items):
            header_parts.append(str(objnum).encode('ascii'))
            header_parts.append(b' ')
            header_parts.append(str(offsets[i]).encode('ascii'))
            header_parts.append(b' ')
        header = b''.join(header_parts).rstrip(b' ')
        stream_data = header + b''.join([data for _, data in items])
        N = len(items)
        first = offsets[0]
        length = len(stream_data)

        # PDF parts
        parts = []
        current_pos = 0

        # Header
        header_pdf = b"%PDF-1.5\n%\xe2\xe3\xef\xd3\n\n"
        parts.append(header_pdf)
        current_pos += len(header_pdf)

        # Object 4: ObjStm
        obj4_start = current_pos
        parts.append(b"4 0 obj\n")
        current_pos += len(b"4 0 obj\n")
        objstm_dict = b"<< /Type /ObjStm /N " + str(N).encode('ascii') + b" /First " + str(first).encode('ascii') + b" /Length " + str(length).encode('ascii') + b" >>\n"
        parts.append(objstm_dict)
        current_pos += len(objstm_dict)
        parts.append(b"stream\n")
        current_pos += len(b"stream\n")
        parts.append(stream_data)
        current_pos += len(stream_data)
        parts.append(b"\nendstream\nendobj\n")
        current_pos += len(b"\nendstream\nendobj\n")

        # Object 3: Page
        obj3_start = current_pos
        page_str = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 5 0 R >>\nendobj\n"
        parts.append(b"3 0 obj\n")
        current_pos += len(b"3 0 obj\n")
        parts.append(page_str)
        current_pos += len(page_str)

        # Object 5: Contents
        obj5_start = current_pos
        contents_dict = b"<< /Length 44 >>\n"
        contents_stream = b"BT\n/F1 12 Tf\n100 700 Td\n(Hello World) Tj\nET\n"
        parts.append(b"5 0 obj\n")
        current_pos += len(b"5 0 obj\n")
        parts.append(contents_dict)
        current_pos += len(contents_dict)
        parts.append(b"stream\n")
        current_pos += len(b"stream\n")
        parts.append(contents_stream)
        current_pos += len(contents_stream)
        parts.append(b"\nendstream\nendobj\n")
        current_pos += len(b"\nendstream\nendobj\n")

        # xref
        xref_start = current_pos
        xref_lines = [
            "0000000000 65535 f",
            "0000000000 00001 n",
            "0000000000 00002 n",
            f"{obj3_start:010d} 00000 n",
            f"{obj4_start:010d} 00000 n",
            f"{obj5_start:010d} 00000 n"
        ]
        xref_content = b"xref\n0 6\n" + b"\n".join(line.encode('ascii') for line in xref_lines) + b"\n"
        parts.append(xref_content)
        current_pos += len(xref_content)

        # trailer
        trailer = b"trailer\n<< /Size 6 /Root 1 0 R >>\n"
        parts.append(trailer)
        current_pos += len(trailer)

        # startxref
        startxref_line = f"{xref_start}\n".encode('ascii')
        parts.append(startxref_line)
        current_pos += len(startxref_line)

        # EOF
        eof = b"%%EOF\n"
        parts.append(eof)

        return b"".join(parts)
