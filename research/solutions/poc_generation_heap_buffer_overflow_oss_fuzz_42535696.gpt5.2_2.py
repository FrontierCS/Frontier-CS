import os
import tarfile
from typing import Optional


def _detect_pdf_preferred_from_tar(src_path: str) -> bool:
    try:
        with tarfile.open(src_path, "r:*") as tf:
            checked = 0
            for m in tf:
                if not m.isreg():
                    continue
                name = (m.name or "").lower()
                base = os.path.basename(name)
                if m.size <= 0 or m.size > 2_000_000:
                    continue
                interesting = (
                    ("fuzz" in name)
                    or ("oss-fuzz" in name)
                    or base.endswith(("_fuzzer.c", "_fuzzer.cc", "_fuzzer.cpp"))
                    or ("fuzzer" in base and base.endswith((".c", ".cc", ".cpp", ".h")))
                )
                if not interesting:
                    continue

                f = tf.extractfile(m)
                if f is None:
                    continue
                try:
                    data = f.read(2_000_000)
                finally:
                    try:
                        f.close()
                    except Exception:
                        pass

                low = data.lower()
                if b"llvmfuzzertestoneinput" not in low and b"fuzzertestoneinput" not in low:
                    checked += 1
                    if checked > 2000:
                        break
                    continue

                if b"runpdfbegin" in low or b"runpdf" in low:
                    return True
                if b"pdfi" in low and (b"-sdevice=pdfwrite" in low or b"pdfwrite" in low):
                    return True

                checked += 1
                if checked > 400:
                    break
    except Exception:
        return False
    return False


def _build_min_pdf_with_content(content: bytes) -> bytes:
    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    objs = []

    objs.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objs.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objs.append(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Contents 4 0 R /Resources << >> >>\nendobj\n"
    )

    stream_dict = b"<< /Length " + str(len(content)).encode("ascii") + b" >>\n"
    stream_obj = b"4 0 obj\n" + stream_dict + b"stream\n" + content + (b"\n" if not content.endswith(b"\n") else b"") + b"endstream\nendobj\n"
    objs.append(stream_obj)

    data = bytearray()
    data += header
    offsets = [0]
    for obj in objs:
        offsets.append(len(data))
        data += obj

    xref_off = len(data)
    data += b"xref\n0 5\n"
    data += b"0000000000 65535 f \n"
    for i in range(1, 5):
        off = offsets[i]
        data += f"{off:010d} 00000 n \n".encode("ascii")
    data += b"trailer\n<< /Size 5 /Root 1 0 R >>\n"
    data += b"startxref\n" + str(xref_off).encode("ascii") + b"\n%%EOF\n"
    return bytes(data)


class Solution:
    def solve(self, src_path: str) -> bytes:
        pdf_preferred = _detect_pdf_preferred_from_tar(src_path)

        n = 64

        if pdf_preferred:
            content = (
                b"q\n"
                b"1 w\n0 0 0 RG\n"
                b"10 10 m\n90 90 l\nS\n"
                + (b"q\n" * n)
                + (b"Q\n" * n)
                + b"Q\n"
            )
            return _build_min_pdf_with_content(content)

        ps = (
            b"%!\n"
            b"/s save def\n"
            b"gsave\n"
            b"newpath 10 10 moveto 20 20 lineto stroke\n"
            b"grestore\n"
            b"s restore\n"
            b"gsave\n"
            b"newpath 10 10 moveto 90 90 lineto stroke\n"
            + (b"/N " + str(n).encode("ascii") + b" def\n")
            + b"0 1 N 1 sub { gsave } for\n"
            + b"0 1 N 1 sub { grestore } for\n"
            + b"grestore\n"
            b"showpage\n"
            b"quit\n"
        )
        return ps