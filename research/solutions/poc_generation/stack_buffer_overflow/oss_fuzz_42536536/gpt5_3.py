class Solution:
    def solve(self, src_path: str) -> bytes:
        pre = b"xref\n0 1\n"
        zeros = b"0" * 34
        return pre + zeros + b" 0 f\n"